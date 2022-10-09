from __future__ import annotations

import sys
from argparse import ArgumentParser, Namespace
from ast import literal_eval
from collections import OrderedDict
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from json import dump as json_dump
from json import dumps as json_dumps
from json import load as json_load
from os import PathLike
from os.path import splitext
from typing import IO, Any, Callable, Iterable, Mapping, Optional, Union
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


class NestedDict(Namespace):
    """
    Basic Config
    """

    _delimiter: str = "."
    _indent: int = 2
    _convert_mapping: bool = False
    _storage: OrderedDict

    def __init__(self, *args, **kwargs):
        super().__setattr__("_storage", OrderedDict())
        for key, value in args:
            self.set(key, value, convert_mapping=True)
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        if "_storage" not in self.__dict__:
            raise AttributeError("cannot access value before Config.__init__() call")

        @wraps(self.get)
        def get(self, name):
            if self._delimiter in name:
                name, rest = name.split(self._delimiter, 1)
                return getattr(self[name], rest)
            elif name in self._storage:
                return self._storage[name]
            else:
                raise AttributeError(
                    f"{self.__class__.__name__} has no attribute {name}"
                )

        if default is not None:
            try:
                return get(self, name)
            except AttributeError:
                return default
        return get(self, name)

    __getitem__ = get
    __getattr__ = get

    def getattr(self, name: str, default: Optional[Any] = None):
        return getattr(self, name, default)

    def set(
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        if "_storage" not in self.__dict__:
            raise AttributeError("cannot assign value before Config.__init__() call")
        if convert_mapping is None:
            convert_mapping = self._convert_mapping
        if self._delimiter in name:
            name, rest = name.split(self._delimiter, 1)
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
            self._storage[name] = value

    __setitem__ = set
    __setattr__ = set

    def setattr(self, name: str, value: Any):
        super().__setattr__(name, value)

    def remove(self, name: str) -> None:
        del self._storage[name]

    __delitem__ = remove
    __delattr__ = remove

    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        attr = self.get(name, default)
        self.remove(name)
        return attr

    def __iter__(self) -> Iterable:
        return iter(self._storage)

    def keys(self) -> Iterable:
        return self._storage.keys()

    def values(self) -> Iterable:
        return self._storage.values()

    def items(self) -> Iterable:
        return self._storage.items()

    def all_keys(self):
        @wraps(self.all_keys)
        def all_keys(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self._delimiter + key
                if isinstance(value, Config):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self):
        for value in self.values():
            if isinstance(value, Config):
                yield from value.all_values()
            else:
                yield value

    def all_items(self):
        @wraps(self.all_items)
        def all_items(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self._delimiter + key
                if isinstance(value, Config):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def dict(self, cls: Callable = dict) -> Mapping:
        dic = cls()
        for k, v in self._storage.items():
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
        return Config(**self)

    __copy__ = copy

    def deepcopy(self) -> Config:
        return Config(**{k: deepcopy(v) for k, v in self.all_items()})

    __deepcopy__ = deepcopy

    clone = deepcopy

    def clear(self) -> None:
        self._storage.clear()

    def json(self, file: File, *args, **kwargs) -> None:
        if "indent" not in kwargs:
            kwargs["indent"] = self._indent
        with self.open(file, mode="w") as fp:
            json_dump(self.dict(), fp, *args, **kwargs)

    def jsons(self, *args, **kwargs) -> str:
        if "indent" not in kwargs:
            kwargs["indent"] = self._indent
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
            kwargs["indent"] = self._indent
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

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        return self._parser.parse_config(args, self, default_config)

    parse_config = parse

    def apply(self, func: Callable) -> Config:
        for value in self._storage.values():
            if isinstance(value, Config):
                value.apply(func)
        func(self)
        return self

    def __len__(self) -> int:
        return len(self._storage)

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

    def extra_repr(self) -> str:
        return ""

    def __repr__(self):
        extra_lines = []
        extra_repr = self.extra_repr()
        # empty string will be split into list ['']
        if extra_repr:
            extra_lines = extra_repr.split("\n")
        child_lines = []
        for key, value in self.items():
            value_str = repr(value)
            value_str = self._add_indent(value_str)
            child_lines.append("(" + key + "): " + value_str)
        lines = extra_lines + child_lines

        main_str = self.__class__.__name__ + "("
        if lines:
            # simple one-liner info, which most builtin Modules will use
            if len(extra_lines) == 1 and not child_lines:
                main_str += extra_lines[0]
            else:
                main_str += "\n  " + "\n  ".join(lines) + "\n"

        main_str += ")"
        return main_str

    def _add_indent(self, s):
        st = s.split("\n")
        # don't do anything for single-line stuff
        if len(st) == 1:
            return s
        first = st.pop(0)
        st = [(self._indent * " ") + line for line in st]
        st = "\n".join(st)
        st = first + "\n" + st
        return st


class Config(NestedDict):
    """
    Basic Config
    """

    _frozen: bool = False
    _convert_mapping: bool = True
    _parser: ConfigParser = ConfigParser()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def frozen_check(func: Callable):
        @wraps(func)
        def decorator(self, *args, **kwargs):
            if self._frozen and not ("_frozen" in args or "_frozen" in kwargs):
                raise AttributeError(
                    "Attempting to alter a frozen config. Run config.defrost() to defrost first"
                )
            func(self, *args, **kwargs)

        return decorator

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        if not self._frozen:
            try:
                return super().get(name, default)
            except AttributeError:
                super().__setattr__(name, Config())
                return self[name]
        return super().get(name, default)

    __getitem__ = get
    __getattr__ = get

    @frozen_check
    def set(
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        return super().set(name, value, convert_mapping)

    __setitem__ = set
    __setattr__ = set

    @frozen_check
    def remove(self, name: str) -> None:
        super().remove(name)

    __delitem__ = remove
    __delattr__ = remove

    @frozen_check
    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        super().pop(name, default)

    def freeze(self, recursive: Optional[bool] = True) -> Config:
        @wraps(self.freeze)
        def freeze(config: Config) -> None:
            config.__dict__["_frozen"] = True

        if recursive:
            self.apply(freeze)
        else:
            freeze(self)
        return self

    def defrost(self, recursive: Optional[bool] = True) -> None:
        @wraps(self.defrost)
        def defrost(config: Config) -> None:
            config.__dict__["_frozen"] = False

        if recursive:
            self.apply(defrost)
        else:
            defrost(self)
