from __future__ import annotations

import sys
from argparse import ArgumentParser
from ast import literal_eval
from collections import OrderedDict as OrderedDict_
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
from typing import IO, Any, Callable, Iterable, Optional, Sequence, Union
from typing_extensions import LiteralString
from warnings import warn

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml import load as yaml_load

PathStr = Union[PathLike, str, bytes, LiteralString]
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
        args: Optional[Sequence[str]] = None,
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

    @staticmethod
    def identity(string):
        return string


class OrderedDict(OrderedDict_):
    """
    Default OrderedDict with attributes
    """

    default_factory: Optional[Callable] = None
    indent: int = 2

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        super().__init__()
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
        Get value from OrderedDict.
        __getitem__ and __getattr__ are alias of this method.
        Note that default here will override the default_factory if specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        >>> d = OrderedDict(d=1013)
        >>> d.get('d')
        1013
        >>> d['d']
        1013
        >>> d.d
        1013
        >>> d.get('f', 2)
        2
        >>> d.get('e')
        Traceback (most recent call last):
        KeyError: 'OrderedDict does not contain e'
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
        Get attribute of OrderedDict.
        Note that if won't return value in the OrderedDict, nor will it create new one if default_factory is specified.

        Args:
            name (str): Key name.
            default (Any, optional): Default value if name does not present.

        >>> d = OrderedDict(a=1, default_factory=list)
        >>> d.getattr('default_factory')
        <class 'list'>
        >>> d.getattr('b', 2)
        2
        >>> d.getattr('a')
        Traceback (most recent call last):
        AttributeError: OrderedDict has no attribute a
        """
        try:
            return self.__dict__[name]
        except KeyError:
            if default is not None:
                return default
            raise AttributeError(
                f"{self.__class__.__name__} has no attribute {name}"
            ) from None

    def set(self, name: str, value: Any) -> None:
        r"""
        Set value of OrderedDict.
        __setitem__ and __setattr__ are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = OrderedDict()
        >>> d.set('d', 1013)
        >>> d.get('d')
        1013
        >>> d['d'] = 1031
        >>> d['d']
        1031
        >>> d.d = 'chang'
        >>> d.d
        'chang'
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
        Set attribute of OrderedDict.
        Note that it won't alter values in the OrderedDict.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = OrderedDict()
        >>> d.setattr('attr', 'value')
        >>> d.getattr('attr')
        'value'
        """
        self.__dict__[name] = value

    def delete(self, name: str) -> None:
        r"""
        Remove value from OrderedDict.
        __delitem__, __delattr__ and remove are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = OrderedDict(d=1016, n='chang')
        >>> d.d
        1016
        >>> d.n
        'chang'
        >>> d.delete('d')
        >>> d.d
        Traceback (most recent call last):
        KeyError: 'OrderedDict does not contain d'
        >>> del d.n
        >>> d.n
        Traceback (most recent call last):
        KeyError: 'OrderedDict does not contain n'
        >>> del d.f
        Traceback (most recent call last):
        KeyError: 'f'
        """
        super().__delitem__(name)

    __delitem__ = delete
    __delattr__ = delete
    remove = delete

    def delattr(self, name: str) -> None:
        r"""
        Remove attribute of OrderedDict.
        Note that it won't remove values in the OrderedDict.

        Args:
            name (str): Key name.

        >>> d = OrderedDict()
        >>> d.setattr('name', 'chang')
        >>> d.getattr('name')
        'chang'
        >>> d.delattr('name')
        >>> d.getattr('name')
        Traceback (most recent call last):
        AttributeError: OrderedDict has no attribute name
        """
        del self.__dict__[name]

    def __missing__(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Allow dict to have default value if it doesn't exist.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        >>> d = OrderedDict(default_factory=list)
        >>> d.n
        []
        >>> d.get('d', 1031)
        1031
        >>> d.__missing__('d', 1031)
        1031
        """
        if default is None:
            if self.getattr("default_factory") is None:
                raise KeyError(f"{self.__class__.__name__} does not contain {name}")
            default = self.getattr("default_factory")()
        self.set(name, default)
        return default

    def convert(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert OrderedDict to other Mapping.

        Args:
            cls (Callable): Target class to be convereted to.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> d.convert(dict)
        {'a': 1, 'b': 2, 'c': 3}
        """
        return cls(**self)

    to = convert
    dict = convert

    def update(self, other: Union[Mapping, Iterable, PathStr]) -> OrderedDict:
        r"""
        Update OrderedDict values w.r.t. other.

        Args:
            other (Mapping | Iterable | PathStr): Other values to update.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.update(n).dict()
        {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.update(l).dict()
        {'a': 1, 'b': 'b', 'c': 3, 'd': 4}
        """
        if isinstance(other, (PathLike, str, bytes)):
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

    def difference(self, other: Union[Mapping, Iterable, PathStr]) -> OrderedDict:
        r"""
        Difference between OrderedDict values and other.

        Args:
            other (Mapping | Iterable | PathStr): Other values to compare.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.difference(n).dict()
        {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.difference(l).dict()
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>
        """
        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(
                f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}"
            )
        return type(self)(
            **{
                key: value
                for key, value in other
                if key not in self or self[key] != value
            }
        )

    diff = difference

    def intersection(self, other: Union[Mapping, Iterable, PathStr]) -> Mapping:
        r"""
        Intersection between OrderedDict values and other.

        Args:
            other (Mapping | Iterable | PathStr): Other values to join.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.intersection(n).dict()
        {}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.intersection(l).dict()
        {'c': 3}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>
        """
        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(
                f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}"
            )
        return type(self)(
            **{key: value for key, value in other if key in self and self[key] == value}
        )

    def copy(self) -> OrderedDict:
        return type(self)(**self)

    __copy__ = copy

    def deepcopy(self, memo=None) -> OrderedDict:
        return type(self)(**{k: deepcopy(v) for k, v in self.items()})

    __deepcopy__ = deepcopy

    clone = deepcopy

    def json(self, file: File, *args, **kwargs) -> None:
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        with self.open(file, mode="w") as fp:
            json_dump(self.to(dict), fp, *args, **kwargs)

    @classmethod
    def from_json(cls, file: File, **kwargs) -> OrderedDict:
        with cls.open(file) as fp:
            return cls(**json_load(fp, **kwargs))

    def jsons(self, *args, **kwargs) -> str:
        r"""
        Dump OrderedDict to json string.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> d.jsons()
        '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}'
        """
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return json_dumps(self.to(dict), *args, **kwargs)

    @classmethod
    def from_jsons(cls, string: str, **kwargs) -> OrderedDict:
        r"""
        Construct OrderedDict from json string.

        >>> d = OrderedDict.from_jsons('{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}
        """
        return cls(**json_loads(string, **kwargs))

    def yaml(self, file: File, *args, **kwargs) -> None:
        with self.open(file, mode="w") as fp:
            self.yamls(fp, *args, **kwargs)

    @classmethod
    def from_yaml(cls, string: str, **kwargs) -> OrderedDict:
        if "Loader" not in kwargs:
            kwargs["Loader"] = SafeLoader
        return cls(**yaml_load(string, **kwargs))

    def yamls(self, *args, **kwargs) -> str:
        r"""
        Dump OrderedDict to yaml string.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> d.yamls()
        'a: 1\nb: 2\nc: 3\n'
        """
        if "Dumper" not in kwargs:
            kwargs["Dumper"] = Dumper
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return yaml_dump(self.to(dict), *args, **kwargs)

    @classmethod
    def from_yamls(cls, string: str, **kwargs) -> OrderedDict:
        r"""
        Construct OrderedDict from yaml string.

        >>> d = OrderedDict.from_yamls('a: 1\nb: 2\nc: 3\n')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}
        """
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
    def load(cls, path: PathStr, **kwargs) -> OrderedDict:
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
        Representation of OrderedDict.

        >>> d = OrderedDict(a=1, b=2, c=3)
        >>> repr(d)
        'OrderedDict(\n  (a): 1\n  (b): 2\n  (c): 3\n)'
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

    def __setstate__(self, states, *args, **kwargs):
        for name, value in states.items():
            self.setattr(name, value)


class NestedDict(OrderedDict):
    """
    Nested Dict
    """

    convert_mapping: bool = False
    default_factory: Optional[Callable] = None
    delimiter: str = "."
    indent: int = 2

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        self.setattr("convert_mapping", False)
        self.setattr("delimiter", ".")
        self.setattr("indent", 2)
        self.setattr("default_factory", default_factory)
        for key, value in args:
            self.set(key, value, convert_mapping=True)
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from NestedDict.
        __getitem__ and __getattr__ are alias of this method.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        >>> d = NestedDict()
        >>> d['i.d'] = 1013
        >>> d.get('i.d')
        1013
        >>> d['i.d']
        1013
        >>> d.i.d
        1013
        >>> d.get('c', 2)
        2
        >>> d.get('c')
        Traceback (most recent call last):
        KeyError: 'NestedDict does not contain c'
        """

        @wraps(self.get)
        def get(self, name):
            if self.getattr("delimiter") in name:
                name, rest = name.split(self.getattr("delimiter"), 1)
                return getattr(self[name], rest)
            else:
                return super().get(name)

        if default is not None:
            try:
                return get(self, name)
            except KeyError:
                return default
        return get(self, name)

    __getitem__ = get
    __getattr__ = get

    def set(
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        r"""
        Set value of NestedDict.
        __setitem__ and __setattr__ are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        >>> d = NestedDict()
        >>> d.set('i.d', 1031)
        >>> d.i.d
        1031
        >>> d['b.c'] = 'chang'
        >>> d.b.c
        'chang'
        """
        if convert_mapping is None:
            convert_mapping = self.convert_mapping
        if self.getattr("delimiter") in name:
            name, rest = name.split(self.getattr("delimiter"), 1)
            if name not in self:
                super().set(name, type(self)())
            self[name][rest] = value
        elif (
            convert_mapping
            and not isinstance(value, NestedDict)
            and isinstance(value, Mapping)
        ):
            self[name] = type(self)(**value)
        else:
            if isinstance(value, str):
                try:
                    value = literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
            super().__setitem__(name, value)

    __setitem__ = set
    __setattr__ = set

    def all_keys(self):
        r"""
        Get all keys of NestedDict.

        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_keys())
        ['a', 'b.c', 'b.d']
        """

        @wraps(self.all_keys)
        def all_keys(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self.getattr("delimiter") + key
                if isinstance(value, NestedDict):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self):
        r"""
        Get all values of NestedDict.

        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_values())
        [1, 2, 3]
        """
        for value in self.values():
            if isinstance(value, NestedDict):
                yield from value.all_values()
            else:
                yield value

    def all_items(self):
        r"""
        Get all items of NestedDict.

        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_items())
        [('a', 1), ('b.c', 2), ('b.d', 3)]
        """

        @wraps(self.all_items)
        def all_items(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + self.getattr("delimiter") + key
                if isinstance(value, NestedDict):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def apply(self, func: Callable) -> NestedDict:
        for value in self.values():
            if isinstance(value, NestedDict):
                value.apply(func)
        func(self)
        return self


def frozen_check(func: Callable):
    @wraps(func)
    def decorator(self, *args, **kwargs):
        if self.getattr("frozen"):
            raise ValueError(
                "Attempting to alter a frozen config. Run config.defrost() to defrost first"
            )
        func(self, *args, **kwargs)

    return decorator


class Config(NestedDict):
    """
    Basic Config
    """

    frozen: bool = False
    convert_mapping: bool = False
    default_factory: Optional[Callable] = None
    delimiter: str = "."
    indent: int = 2
    parser: ConfigParser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setattr("frozen", False)
        self.setattr("convert_mapping", True)
        self.setattr("parser", ConfigParser())
        self.setattr("default_factory", NestedDict)

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
            config.setattr("frozen", True)

        if recursive:
            self.apply(freeze)
        else:
            freeze(self)
        return self

    def defrost(self, recursive: Optional[bool] = True) -> None:
        @wraps(self.defrost)
        def defrost(config: Config) -> None:
            config.setattr("frozen", False)

        if recursive:
            self.apply(defrost)
        else:
            defrost(self)

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        return self.getattr("parser").parse_config(args, self, default_config)

    parse_config = parse

    def add_argument(self, *args, **kwargs) -> None:
        self.getattr("parser").add_argument(*args, **kwargs)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
