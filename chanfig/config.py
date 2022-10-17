from __future__ import annotations

import sys
from argparse import ArgumentParser
from ast import literal_eval
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from json import dump as json_dump
from json import dumps as json_dumps
from json import load as json_load
from json import loads as json_loads
from os import PathLike
from os.path import splitext
from typing import IO, Any, Callable, Iterable, Optional, Union
from warnings import warn

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml import load as yaml_load

PathStr = Union[PathLike, str, bytes]
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
        parsed, _ = self.parse_known_args(args)
        if (
            default_config is not None
            and (path := getattr(parsed, default_config, None)) is not None
        ):
            config = type(config).load(path)
        config.update(vars(parsed))
        return config

    parse_config = parse


class Dict(OrderedDict):
    """
    Default OrderedDict with attributes
    """

    default_factory: Callable
    indent: int

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        if default_factory is not None and not isinstance(default_factory, Callable):
            raise TypeError(
                f"default_factory={default_factory} should be of type Callable, but got {type(default_factory)}"
            )
        self.setattr("default_factory", default_factory)
        self.setattr("indent", 2)
        for key, value in args:
            self.set(key, value)
        for key, value in kwargs.items():
            self.set(key, value)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from Dict.
        __getitem__ and __getattr__ are alias of this method.
        Note that default here will override the default_factory if specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        >>> d = Dict(a=1)
        >>> d.get('a')
        1
        >>> d['a']
        1
        >>> d.a
        1
        >>> d.get('b', 2)
        2
        >>> d.get('c')
        Traceback (most recent call last):
        KeyError: 'c'
        """
        return (
            super().__getitem__(name)
            if default is None
            else self.__missing__(name, default)
        )

    __getitem__ = get
    __getattr__ = get

    def getattr(self, name: str, default: Optional[Any] = None):
        r"""
        Get attribute of Dict object.
        Note that if won't return value in the Dict, nor will it create new one if default_factory is specified.

        Args:
            name (str): Key name.
            default (Any, optional): Default value if name does not present.

        >>> d = Dict(a=1, default_factory=list)
        >>> d.getattr('default_factory')
        <class 'list'>
        >>> d.getattr('b', 2)
        2
        >>> d.getattr('a')
        Traceback (most recent call last):
        AttributeError: a
        """
        try:
            return self.__dict__[name]
        except KeyError:
            if default is not None:
                return default
            raise AttributeError(name) from None

    def set(self, name: str, value: Any) -> None:
        r"""
        Set value of Dict.
        __setitem__ and __setattr__ are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = Dict()
        >>> d.set('a', 1)
        >>> d.get('a')
        1
        >>> d['b'] = 2
        >>> d['b']
        2
        >>> d.c = 3
        >>> d.c
        3
        """
        if isinstance(value, str):
            try:
                value = literal_eval(value)
            except (ValueError, SyntaxError):
                pass
        super().__setitem__(name, value)

    __setitem__ = set
    __setattr__ = set

    def setattr(self, name: str, value: Any):
        r"""
        Set attribute of Dict object.
        Note that it won't alter values in the Dict.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = Dict()
        >>> d.setattr('attr', 1)
        >>> d.getattr('attr')
        1
        """
        self.__dict__[name] = value

    def delete(self, name: str) -> None:
        r"""
        Remove value from Dict.
        __delitem__, __delattr__ and remove are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = Dict(a=1, b=2)
        >>> d.a
        1
        >>> d.b
        2
        >>> d.delete('a')
        >>> d.a
        Traceback (most recent call last):
        KeyError: 'a'
        >>> del d.b
        >>> d.b
        Traceback (most recent call last):
        KeyError: 'b'
        >>> del d.c
        Traceback (most recent call last):
        KeyError: 'c'
        """
        super().__delitem__(name)

    __delitem__ = delete
    __delattr__ = delete
    remove = delete

    def delattr(self, name: str) -> None:
        r"""
        Remove attribute of Dict object.
        Note that it won't remove values in the Dict.

        Args:
            name (str): Key name.

        >>> d = Dict()
        >>> d.setattr('attr', 1)
        >>> d.getattr('attr')
        1
        >>> d.delattr('attr')
        >>> d.getattr('attr')
        Traceback (most recent call last):
        AttributeError: attr
        """
        del self.__dict__[name]

    def __missing__(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Allow dict to have default value if it doesn't exist.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        >>> d = Dict(default_factory=list)
        >>> d.a
        []
        >>> d.get('a', 1)
        1
        >>> d.__missing__('a', 1)
        1
        """
        if default is None:
            if self.getattr("default_factory") is None:
                raise KeyError(name)
            default = self.getattr("default_factory")()
        self.set(name, default)
        return default

    def convert(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert Dict to other Mapping.

        Args:
            cls (Callable): Target class to be convereted to.

        >>> d = Dict(a=1, b=2, c=3)
        >>> d.convert(dict)
        {'a': 1, 'b': 2, 'c': 3}
        """
        return cls(**self)

    to = convert
    dict = convert

    def update(self, other: Union[File, Mapping, Iterable]) -> Dict:
        r"""
        Update Dict values w.r.t. other.

        Args:
            other (File | Mapping | Iterable): Other values to update.

        >>> d = Dict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.update(n).dict()
        {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.update(l).dict()
        {'a': 1, 'b': 'b', 'c': 3, 'd': 4}
        """
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            for key, value in other.items():
                if (
                    key in self
                    and isinstance(self[key], (Mapping,))
                    and isinstance(value, (Mapping,))
                ):
                    self[key].update(value)
                else:
                    self[key] = value
        elif isinstance(other, Iterable):
            for key, value in other:
                self[key] = value
        return self

    merge = update
    merge_from_file = update
    union = update

    def difference(self, other: Union[File, Mapping, Iterable]) -> Dict:
        r"""
        Difference between Dict values and other.

        Args:
            other (File | Mapping | Iterable): Other values to compare.

        >>> d = Dict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.difference(n).dict()
        {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.difference(l).dict()
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or File, but got <class 'int'>
        """
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(
                f"other={other} should be of type Mapping, Iterable or File, but got {type(other)}"
            )
        return type(self)(
            **{
                key: value
                for key, value in other
                if key not in self or self[key] != value
            }
        )

    diff = difference

    def intersection(self, other: Union[File, Mapping, Iterable]) -> Mapping:
        r"""
        Intersection between Dict values and other.

        Args:
            other (File | Mapping | Iterable): Other values to join.

        >>> d = Dict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.intersection(n).dict()
        {}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.intersection(l).dict()
        {'c': 3}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or File, but got <class 'int'>
        """
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(
                f"other={other} should be of type Mapping, Iterable or File, but got {type(other)}"
            )
        return type(self)(
            **{key: value for key, value in other if key in self and self[key] == value}
        )

    def copy(self) -> Dict:
        return type(self)(**self)

    __copy__ = copy

    def deepcopy(self, memo=None) -> Dict:
        return type(self)(**{k: deepcopy(v) for k, v in self.items()})

    __deepcopy__ = deepcopy

    clone = deepcopy

    def json(self, file: File, *args, **kwargs) -> None:
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        with self.open(file, mode="w") as fp:
            json_dump(self.dict(), fp, *args, **kwargs)

    @classmethod
    def from_json(cls, string: str, **kwargs) -> Dict:
        return cls(**json_load(string, **kwargs))

    def jsons(self, *args, **kwargs) -> str:
        r"""
        Dump Dict to json string.

        >>> d = Dict(a=1, b=2, c=3)
        >>> d.jsons()
        '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}'
        """
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return json_dumps(self.dict(), *args, **kwargs)

    @classmethod
    def from_jsons(cls, string: str, **kwargs) -> Dict:
        r"""
        Construct Dict from json string.

        >>> d = Dict.from_jsons('{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}
        """
        return cls(**json_loads(string, **kwargs))

    def yaml(self, file: File, *args, **kwargs) -> None:
        with self.open(file, mode="w") as fp:
            self.yamls(fp, *args, **kwargs)

    @classmethod
    def from_yaml(cls, string: str, **kwargs) -> Dict:
        if "Loader" not in kwargs:
            kwargs["Loader"] = SafeLoader
        return cls(**yaml_load(string, **kwargs))

    def yamls(self, *args, **kwargs) -> str:
        r"""
        Dump Dict to yaml string.

        >>> d = Dict(a=1, b=2, c=3)
        >>> d.yamls()
        'a: 1\nb: 2\nc: 3\n'
        """
        if "Dumper" not in kwargs:
            kwargs["Dumper"] = Dumper
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return yaml_dump(self.dict(), *args, **kwargs)

    @classmethod
    def from_yamls(cls, string: str, **kwargs) -> Dict:
        r"""
        Construct Dict from yaml string.

        >>> d = Dict.from_yamls('a: 1\nb: 2\nc: 3\n')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}
        """
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
    def load(cls, path: PathStr, **kwargs) -> Dict:
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
            raise TypeError(
                f"file={file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}"
            )

    def extra_repr(self) -> str:
        return ""

    def __repr__(self):
        r"""
        Representation of Dict object.

        >>> d = Dict(a=1, b=2, c=3)
        >>> repr(d)
        'Dict(\n  (a): 1\n  (b): 2\n  (c): 3\n)'
        """
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
        st = [(self.getattr("indent") * " ") + line for line in st]
        st = "\n".join(st)
        st = first + "\n" + st
        return st


class NestedDict(Mapping):
    """
    Nested Dict
    """

    _delimiter: str = "."
    _indent: int = 2
    _convert_mapping: bool = False
    _storage: Dict

    def __init__(self, *args, **kwargs):
        super().__setattr__("_storage", Dict())
        for key, value in args:
            self.set(key, value, convert_mapping=True)
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        if "_storage" not in self.__dict__:
            raise AttributeError(
                "cannot access value before NestedDict.__init__() call"
            )

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
        return super().__getattr__(self, name, default)

    def set(
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        if "_storage" not in self.__dict__:
            raise AttributeError(
                "cannot assign value before NestedDict.__init__() call"
            )
        if convert_mapping is None:
            convert_mapping = self._convert_mapping
        if self._delimiter in name:
            name, rest = name.split(self._delimiter, 1)
            if not hasattr(self, name):
                setattr(self, name, type(self)())
            setattr(self[name], rest, value)
        elif (
            convert_mapping
            and not isinstance(value, NestedDict)
            and isinstance(value, Mapping)
        ):
            setattr(self, name, type(self)(**value))
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
                if isinstance(value, NestedDict):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self):
        for value in self.values():
            if isinstance(value, NestedDict):
                yield from value.all_values()
            else:
                yield value

    def all_items(self):
        @wraps(self.all_items)
        def all_items(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self._delimiter + key
                if isinstance(value, NestedDict):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def dict(self, cls: Callable = dict) -> Mapping:
        dic = cls()
        for k, v in self._storage.items():
            if isinstance(v, NestedDict):
                dic[k] = v.dict(cls)
            else:
                dic[k] = v
        return dic

    def update(self, other: Union[File, Mapping, Iterable], **kwargs) -> NestedDict:
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            for key, value in other.items():
                if isinstance(value, (Mapping,)) and isinstance(self[key], (Mapping,)):
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

    def difference(self, other: Union[File, Mapping, Iterable]) -> NestedDict:
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            return type(self)(
                **{
                    key: value
                    for key, value in other.items()
                    if key not in self or self[key] != value
                }
            )
        elif isinstance(other, Iterable):
            return type(self)(
                **{
                    key: value
                    for key, value in other
                    if key not in self or self[key] != value
                }
            )
        return None

    diff = difference

    def intersection(self, other: Union[File, Mapping, Iterable]) -> Mapping:
        if isinstance(other, (PathLike, str, bytes, IO)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            return type(self)(
                **{
                    key: value
                    for key, value in other.items()
                    if key in self and self[key] == value
                }
            )
        elif isinstance(other, Iterable):
            return type(self)(
                **{
                    key: value
                    for key, value in other
                    if key in self and self[key] == value
                }
            )
        return None

    def copy(self) -> NestedDict:
        return type(self)(**self)

    __copy__ = copy

    def deepcopy(self, memo=None) -> NestedDict:
        return type(self)(**{k: deepcopy(v) for k, v in self.all_items()})

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
    def from_json(cls, string: str, **kwargs) -> NestedDict:
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
    def from_yaml(cls, string: str, **kwargs) -> NestedDict:
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
    def load(cls, path: File, **kwargs) -> NestedDict:
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
            raise TypeError(
                f"file={file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}"
            )

    def apply(self, func: Callable) -> NestedDict:
        for value in self._storage.values():
            if isinstance(value, NestedDict):
                value.apply(func)
        func(self)
        return self

    def __len__(self) -> int:
        return len(self._storage)

    def __contains__(self, name: str) -> bool:
        return name in self._storage

    def __eq__(self, other: Mapping) -> bool:
        if isinstance(other, NestedDict):
            return self.dict() == other.dict()
        if isinstance(other, Mapping):
            return self.dict() == other
        raise NotImplementedError

    def __bool__(self):
        return bool(self._storage)

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
                super().__setattr__(name, type(self)())
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

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        return self._parser.parse_config(args, self, default_config)

    parse_config = parse

    add_argument = _parser.add_argument


if __name__ == "__main__":
    import doctest

    doctest.testmod()
