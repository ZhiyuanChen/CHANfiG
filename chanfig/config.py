from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace
from ast import literal_eval
from contextlib import contextmanager
from copy import copy, deepcopy
from functools import wraps
from json import dump as json_dump
from json import dumps as json_dumps
from json import load as json_load
from os import PathLike as PathLike
from os.path import splitext
from typing import Any, Callable, IO, Iterable, Mapping, Optional, Union
from warnings import warn

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml import load as yaml_load

PathStr = Union[PathLike, str]
File = Union[PathStr, IO]

YAML = ("yml", "yaml")
JSON = ("json",)
PYTHON = ("py",)


class Dumper(SafeDumper):
    def increase_indent(
        self, flow: Optional[bool] = False, indentless: Optional[bool] = False
    ):
        return super().increase_indent(flow, indentless)


class FileError(ValueError):
    pass


class ConfigParser(ArgumentParser):
    r"""
    Parse the arguments for config.
    There are three levels of config:
    1. The base config parsed into the function,
    2. The config file located at the path of default_config (if specified),
    3. The config specified in arguments.
    Higher levels override lower levels (i.e. 3 > 2 > 1).
    """

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        config: Optional[Config] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        if args is None:
            args = sys.argv[1:]
        for arg in args:
            if (
                arg.startswith("--")
                and args != "--"
                and arg not in self._option_string_actions
            ):
                self.add_argument(arg)
        if config is None:
            config = Config()
        if (
            default_config is not None
            and (path := getattr(config, default_config, None)) is not None
        ):
            warn(
                f"Config has 'default_config={path}' specified, its values will override values in Config"
            )
        parsed, _ = self.parse_known_args(args, config.clone())
        if (
            default_config is not None
            and (path := getattr(config, default_config, None)) is not None
        ):
            config = type(config).load(path)
        config.update(parsed)
        return config

    parse_config = parse


class Dict(Namespace):
    """
    Basic Config
    """

    delimiter: str = "."
    indent: int = 2
    convert_mapping: bool = False

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        @wraps(self.get)
        def get(self, name):
            if self.delimiter in name:
                name, rest = name.split(self.delimiter, 1)
                return getattr(self[name], rest)
            else:
                return super().__getattribute__(name)

        if default is not None:
            try:
                return get(self, name)
            except AttributeError:
                return default
        return get(self, name)

    __getitem__ = get
    __getattr__ = get

    def set(
        self, name: str, value: Any, convert_mapping: Optional[bool] = True
    ) -> None:
        if convert_mapping is None:
            convert_mapping = self.convert_mapping
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            if not hasattr(self, name):
                setattr(self, name, Config())
            setattr(self[name], rest, value)
        elif convert_mapping and isinstance(value, Mapping):
            setattr(self, name, Config(**value))
        else:
            if isinstance(value, str):
                try:
                    value = literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
            super().__setattr__(name, value)

    __setitem__ = set
    __setattr__ = set

    def remove(self, name: str) -> None:
        del self.__dict__[name]

    __delitem__ = remove
    __delattr__ = remove

    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        attr = self.get(name, default)
        self.remove(name)
        return attr

    def __iter__(self) -> Iterable:
        return iter(self.__dict__)

    def keys(self) -> Iterable:
        return self.__dict__.keys()

    def values(self) -> Iterable:
        return self.__dict__.values()

    def items(self) -> Iterable:
        return self.__dict__.items()

    def all_keys(self):
        @wraps(self.all_keys)
        def _iter(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self.delimiter + key
                if isinstance(value, Config):
                    yield from _iter(value, key)
                else:
                    yield key

        return _iter(self)

    def all_values(self):
        for value in self.values():
            if isinstance(value, Config):
                yield from value.all_values()
            else:
                yield value

    def all_items(self):
        @wraps(self.all_items)
        def _iter(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self.delimiter + key
                if isinstance(value, Config):
                    yield from _iter(value, key)
                else:
                    yield key, value

        return _iter(self)

    def dict(self, cls: Callable = dict) -> Mapping:
        dic = cls()
        for k, v in self.__dict__.items():
            if isinstance(v, Config):
                dic[k] = v.dict(cls)
            else:
                dic[k] = v
        return dic

    def update(self, other: Union[File, Config, Mapping, Iterable], **kwargs) -> Config:
        if isinstance(other, (PathLike, str, IO)):
            other = self.load(other)
        if isinstance(other, (Config, Mapping)):
            for key, value in other.items():
                if isinstance(value, (Config, Mapping)) and isinstance(
                    self[key], (Config, Mapping)
                ):
                    self[key].update(value)
                else:
                    self[key] = value
        elif isinstance(other, Iterable):
            for key, value in other:
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value
        return self

    merge = update
    merge_from_file = update
    union = update

    def difference(self, other: Union[File, Config, Mapping, Iterable]) -> Config:
        if isinstance(other, (PathLike, str, IO)):
            other = self.load(other)
        if isinstance(other, (Config, Mapping)):
            return Config(
                **{
                    key: value
                    for key, value in other.items()
                    if key not in self or self[key] != value
                }
            )
        elif isinstance(other, Iterable):
            return Config(
                **{
                    key: value
                    for key, value in other
                    if key not in self or self[key] != value
                }
            )
        return None

    diff = difference

    def intersection(self, other: Union[File, Config, Mapping, Iterable]) -> Config:
        if isinstance(other, (PathLike, str, IO)):
            other = self.load(other)
        if isinstance(other, (Config, Mapping)):
            return Config(
                **{
                    key: value
                    for key, value in other.items()
                    if key in self and self[key] == value
                }
            )
        elif isinstance(other, Iterable):
            return Config(
                **{
                    key: value
                    for key, value in other
                    if key in self and self[key] == value
                }
            )
        return None

    def copy(self) -> Config:
        return copy(self)

    def deepcopy(self) -> Config:
        return deepcopy(self)

    clone = deepcopy

    def clear(self) -> None:
        self.__dict__.clear()

    def json(self, file: File, *args, **kwargs) -> None:
        if "indent" not in kwargs:
            kwargs["indent"] = self.indent
        with self.open(file, mode="w") as fp:
            json_dump(self.dict(), fp, *args, **kwargs)

    def jsons(self, *args, **kwargs) -> str:
        if "indent" not in kwargs:
            kwargs["indent"] = self.indent
        return json_dumps(self.dict(), *args, **kwargs)

    @classmethod
    def from_json(cls, string: str, **kwargs) -> Config:
        return cls(**json_load(string, **kwargs))

    def yaml(self, file: File, *args, **kwargs) -> None:
        with self.open(file, mode="w") as fp:
            self.yamls(fp, *args, **kwargs)

    def yamls(self, *args, **kwargs) -> str:
        if "Dumper" not in kwargs:
            kwargs["Dumper"] = Dumper
        if "indent" not in kwargs:
            kwargs["indent"] = self.indent
        return yaml_dump(self.dict(dict), *args, **kwargs)

    @classmethod
    def from_yaml(cls, string: str, **kwargs) -> Config:
        if "Loader" not in kwargs:
            kwargs["Loader"] = SafeLoader
        return cls(**yaml_load(string, **kwargs))

    def dump(self, file: File, method: Optional[str] = "yaml", *args, **kwargs) -> None:
        method = method.lower()
        if method in YAML:
            self.yaml(file=file, *args, **kwargs)
        elif method in JSON:
            self.json(file=file, *args, **kwargs)
        else:
            raise FileError(f"method {method} should be in {JSON} or {YAML}")

    @classmethod
    def load(cls, path: File, **kwargs) -> Config:
        extension = splitext(path)[-1][1:].lower()
        with cls.open(path) as fp:
            if extension in JSON:
                config = cls.from_json(fp.read(), **kwargs)
            elif extension in YAML:
                config = cls.from_yaml(fp.read(), **kwargs)
            else:
                raise FileError(
                    f"file {path} should have extensions {JSON} or {YAML}, but got {extension}"
                )
        return config

    @staticmethod
    @contextmanager
    def open(file: File, *args, **kwargs):
        if isinstance(file, (PathLike, str)):
            file = open(file, *args, **kwargs)
            try:
                yield file
            finally:
                file.close()
        elif isinstance(file, (IO,)):
            yield file
        else:
            raise ValueError(
                f"file {file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}"
            )

    def parse(self) -> Config:
        return self.parser.parse_config(config=self)

    parse_config = parse

    def apply(self, func: Callable) -> Config:
        for value in self.__dict__.values():
            if isinstance(value, Config):
                value.apply(func)
        func(self)
        return self

    def freeze(self, recursive: Optional[bool] = True) -> None:
        @wraps(self.freeze)
        def freeze(config: Config) -> None:
            config._frozen = True

        if recursive:
            self.apply(freeze)
        else:
            freeze(self)

    def defrost(self, recursive: Optional[bool] = True) -> None:
        @wraps(self.defrost)
        def defrost(config: Config) -> None:
            del config._frozen

        if recursive:
            self.apply(defrost)
        else:
            defrost(self)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __contains__(self, name: str) -> bool:
        return hasattr(self, name)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Config):
            return self.dict() == other.dict()
        if isinstance(other, Mapping):
            return self.dict() == other
        raise NotImplementedError

    def __bool__(self):
        return bool(self)

    def __str__(self) -> str:
        return self.yamls()


class Config(Dict):
    """
    Basic Config
    """

    _frozen: bool = False
    parser: ConfigParser = ConfigParser()
    convert_mapping: bool = True

    def test(func: Callable):
        @wraps(func)
        def decorator(self, *args, **kwargs):
            if self._frozen and not ("_frozen" in args or "_frozen" in kwargs):
                raise AttributeError(
                    "Attempting to alter a frozen config. Run config.defrost() to defrost first"
                )
            func(self, *args, **kwargs)

        return decorator

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        @wraps(self.get)
        def get(self, name):
            if self.delimiter in name:
                name, rest = name.split(self.delimiter, 1)
                return getattr(self[name], rest)
            else:
                try:
                    return super().__getattribute__(name)
                except AttributeError:
                    self.set(name, type(self)())
                    return self[name]

        if default is not None:
            try:
                return get(self, name)
            except AttributeError:
                return default
        return get(self, name)

    __getitem__ = get
    __getattr__ = get

    @test
    def set(
        self, name: str, value: Any, convert_mapping: Optional[bool] = True
    ) -> None:
        if convert_mapping is None:
            convert_mapping = self.convert_mapping
        # __import__("pdb").set_trace()
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            if not hasattr(self, name):
                setattr(self, name, Config())
            setattr(self[name], rest, value)
        elif convert_mapping and isinstance(value, Mapping):
            setattr(self, name, Config(**value))
        else:
            if isinstance(value, str):
                try:
                    value = literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
            super().__setattr__(name, value)

    __setitem__ = set
    __setattr__ = set

    @test
    def remove(self, name: str) -> None:
        del self.__dict__[name]

    __delitem__ = remove
    __delattr__ = remove

    @test
    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        attr = self.get(name, default)
        self.remove(name)
        return attr
