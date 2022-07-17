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
from typing import Any, Callable, IO, Iterable, MutableMapping, Optional, Union
from warnings import warn

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml import load as yaml_load

PathStr = Union[PathLike, str]
File = Union[PathStr, IO]

YAML = ("yml", "yaml")
JSON = ("json")
PYTHON = ("py")


class Dumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


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
    def parse(self, args: Iterable[str] = None, config: Config = None, default_config: str = None) -> Config:
        if args is None:
            args = sys.argv[1:]
        for arg in args:
            if arg.startswith("--") and args != "--" and arg not in self._option_string_actions:
                self.add_argument(arg)
        if config is None:
            config = Config()
        if default_config is not None and (path := getattr(config, default_config, None)) is not None:
            warn(f"Config has 'default_config={path}' specified, its values will override values in Config")
        parsed, _ = self.parse_known_args(args, config.clone())
        if default_config is not None and (path := getattr(config, default_config, None)) is not None:
            config = type(config).load(path)
        config.update(parsed)
        return config

    parse_config = parse


class Config(Namespace):
    """
    Basic Config
    """

    delimiter: str = "."
    indent: int = 2
    frozen: bool = False
    parser: ConfigParser = ConfigParser()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def __getattr__(self, name: str) -> Any:
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            return getattr(self[name], rest)
        else:
            return super().__getattribute__(name)

    __getitem__ = __getattr__

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        try:
            return getattr(self, name)
        except AttributeError:
            return default

    def set(self, name: str, value: Any, convert_mapping: bool = False) -> None:
        if self.frozen:
            raise AttributeError(f"Attempting to set {name}={value} on a frozen config. Run config.defrost() to defrost first")
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            if not hasattr(self, name):
                setattr(self, name, Config())
            setattr(self[name], rest, value)
        elif convert_mapping and isinstance(value, MutableMapping):
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
        if self.frozen:
            raise AttributeError(f"Attempting to delete {name} on a frozen config. Run config.defrost() to defrost first")
        del self.__dict__[name]

    __delitem__ = remove
    __delattr__ = remove

    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        if self.frozen:
            raise AttributeError(f"Attempting to pop {name} on a frozen config. Run config.defrost() to defrost first")
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

    def dict(self, cls: Callable = dict) -> MutableMapping:
        dic = cls()
        for k, v in self.__dict__.items():
            if isinstance(v, Config):
                dic[k] = v.dict(cls)
            else:
                dic[k] = v
        return dic

    def update(self, other: Union[PathStr, Config, MutableMapping, Iterable], **kwargs) -> Config:
        if isinstance(other, (PathLike, str)):
            other = self.load(other)
        if isinstance(other, (Config, MutableMapping)):
            for key, value in other.items():
                if isinstance(value, (Config, MutableMapping)) and isinstance(self[key], (Config, MutableMapping)):
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

    def difference(self, other: Union[File, Config, MutableMapping, Iterable]) -> Config:
        if isinstance(other, str):
            other = self.load(other)
        if isinstance(other, (Config, MutableMapping)):
            return Config(**{key: value for key, value in other.items() if key not in self or self[key] != value})
        elif isinstance(other, Iterable):
            return Config(**{key: value for key, value in other if key not in self or self[key] != value})
        return None

    diff = difference

    def intersection(self, other: Union[File, Config, MutableMapping, Iterable]) -> Config:
        if isinstance(other, str):
            other = self.load(other)
        if isinstance(other, (Config, MutableMapping)):
            return Config(**{key: value for key, value in other.items() if key in self and self[key] == value})
        elif isinstance(other, Iterable):
            return Config(**{key: value for key, value in other if key in self and self[key] == value})
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

    def dump(self, file: File, method: str = "yaml", *args, **kwargs) -> None:
        method = method.lower()
        if method in YAML:
            self.yaml(file=file, *args, **kwargs)
        elif method in JSON:
            self.json(file=file, *args, **kwargs)
        else:
            raise FileError(f"method {method} should be in {JSON} or {YAML}")

    @classmethod
    def load(cls, path: PathStr, **kwargs) -> Config:
        extension = splitext(path)[-1][1:].lower()
        with cls.open(path) as fp:
            if extension in JSON:
                config = cls.from_json(fp.read(), **kwargs)
            elif extension in YAML:
                config = cls.from_yaml(fp.read(), **kwargs)
            else:
                raise FileError(f"file {path} should have extensions {JSON} or {YAML}, but got {extension}")
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
        elif isinstance(file, (IO, )):
            yield file
        else:
            raise ValueError(f"file {file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}")

    def parse(self) -> Config:
        return self.parser.parse_config(config=self)

    parse_config = parse

    def apply(self, func: Callable) -> Config:
        for value in self.__dict__.values():
            if isinstance(value, Config):
                value.apply(func)
        func(self)
        return self

    def freeze(self) -> None:
        def _freeze(config: Config) -> None:
            config.frozen = True
        self.apply(_freeze)

    def defrost(self) -> None:
        def _defrost(config: Config) -> None:
            config.frozen = False
        self.apply(_defrost)

    def __len__(self) -> int:
        return len(self.__dict__)

    def __contains__(self, name: str) -> bool:
        return hasattr(self, name)

    def __eq__(self, other: Config) -> bool:
        if not isinstance(other, Config):
            return NotImplemented
        return self.dict() == other.dict()

    def __bool__(self):
        return bool(self)

    def __str__(self) -> str:
        return self.yamls()
