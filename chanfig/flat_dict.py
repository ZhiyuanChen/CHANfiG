from __future__ import annotations

from ast import literal_eval
from collections import OrderedDict
from collections.abc import Mapping
from contextlib import contextmanager
from copy import copy, deepcopy
from json import dumps as json_dumps
from json import loads as json_loads
from os import PathLike
from os.path import splitext
from typing import IO, Any, Callable, Iterable, Optional, Union, TypeVar

from yaml import dump as yaml_dump
from yaml import load as yaml_load

from .utils import FileError, JsonEncoder, YamlDumper, YamlLoader
from .variable import Variable

PathStr = Union[PathLike, str, bytes]
File = Union[PathStr, IO]

YAML = ("yml", "yaml")
JSON = ("json",)
PYTHON = ("py",)

K = TypeVar("K")
V = TypeVar("V")


class FlatDict(OrderedDict[K, V]):

    # pylint: disable=R0904

    r"""
    FlatDict with attribute-style access.

    FlatDict inherits from built-in FlatDict of collections.
    It also comes with many easy to use helper function, such as `difference`, `intersection` and full IO supports.
    FlatDict works best with `Variable` objects.

    Example:
    ```python
    >>> d = FlatDict()
    >>> d.d = 1013
    >>> d['d']
    1013
    >>> d['i'] = 1031
    >>> d.i
    1031
    >>> d.a = Variable(1)
    >>> d.b = d.a
    >>> d.a, d.b
    (1, 1)
    >>> d.a += 1
    >>> d.a, d.b
    (2, 2)
    >>> d.a = 3
    >>> d.a, d.b
    (3, 3)
    >>> d.a = Variable('hello')
    >>> f"{d.a}, world!"
    'hello, world!'
    >>> d.a = d.a + ', world!'
    >>> d.b
    'hello, world!'

    ```
    """

    default_factory: Optional[Callable]
    indent: int = 2

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        super().__init__()
        if default_factory is not None:
            if callable(default_factory):
                self.setattr("default_factory", default_factory)
            else:
                raise TypeError(
                    f"default_factory={default_factory} should be of type Callable, but got {type(default_factory)}"
                )
        self.setattr("indent", 2)
        self._init(*args, **kwargs)

    def _init(self, *args, **kwargs) -> None:
        r"""
        Initialise values from arguments for FlatDict.

        This method is called in `__init__`.

        Args:
            *args: [(key1, value1), (key2, value2)].
            **kwargs: {key1: value1, key2: value2}.
        """

        for key, value in args:
            self.set(key, value)
        for key, value in kwargs.items():
            self.set(key, value)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from FlatDict.

        `__getitem__` and `__getattr__` are alias of this method.

        Note that default here will override the default_factory if specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = FlatDict(d=1013)
        >>> d.get('d')
        1013
        >>> d['d']
        1013
        >>> d.d
        1013
        >>> d.get('f', 2)
        2
        >>> d.get('f')
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain f'

        ```
        """

        return super().__getitem__(name) if default is None else self.__missing__(name, default)

    __getitem__ = get
    __getattr__ = get

    def getattr(self, name: str, default: Optional[Any] = None):
        r"""
        Get attribute of FlatDict.

        Note that if won't return value in the FlatDict, nor will it create new one if default_factory is specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = FlatDict(a=1, default_factory=list)
        >>> d.getattr('default_factory')
        <class 'list'>
        >>> d.getattr('b', 2)
        2
        >>> d.getattr('a')
        Traceback (most recent call last):
        AttributeError: FlatDict has no attribute a

        ```
        """

        try:
            if name in self.__dict__:
                return self.__dict__[name]
            if name in self.__class__.__dict__:
                return self.__class__.__dict__[name]
            return super().getattr(name, default)  # type: ignore
        except AttributeError:
            if default is not None:
                return default
            raise AttributeError(f"{self.__class__.__name__} has no attribute {name}") from None

    def set(self, name: str, value: Any) -> None:
        r"""
        Set value of FlatDict.

        `__setitem__` and `__setattr__` are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        Example:
        ```python
        >>> d = FlatDict()
        >>> d.set('d', 1013)
        >>> d.get('d')
        1013
        >>> d['d'] = 1031
        >>> d.d
        1031
        >>> d.d = 'chang'
        >>> d['d']
        'chang'

        ```
        """

        if isinstance(value, str):
            try:
                value = literal_eval(value)
            except (TypeError, ValueError, SyntaxError):
                pass
        if name in self and isinstance(self[name], Variable):
            self[name].set(value)
        else:
            super().__setitem__(name, value)

    __setitem__ = set
    __setattr__ = set

    def setattr(self, name: str, value: Any):
        r"""
        Set attribute of FlatDict.

        Note that it won't alter values in the FlatDict.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        Example:
        ```python
        >>> d = FlatDict()
        >>> d.setattr('attr', 'value')
        >>> d.getattr('attr')
        'value'

        ```
        """

        self.__dict__[name] = value

    def delete(self, name: str) -> None:
        r"""
        Remove value from FlatDict.

        `__delitem__`, `__delattr__` and `remove` are alias of this method.

        Args:
            name (str): Key name.

        Example:
        ```python
        >>> d = FlatDict(d=1016, n='chang')
        >>> d.d
        1016
        >>> d.n
        'chang'
        >>> d.delete('d')
        >>> d.d
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain d'
        >>> del d.n
        >>> d.n
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain n'
        >>> del d.f
        Traceback (most recent call last):
        KeyError: 'f'

        ```
        """

        super().__delitem__(name)

    __delitem__ = delete
    __delattr__ = delete
    remove = delete

    def delattr(self, name: str) -> None:
        r"""
        Remove attribute of FlatDict.

        Note that it won't remove values in the FlatDict.

        Args:
            name (str): Key name.

        Example:
        ```python
        >>> d = FlatDict()
        >>> d.setattr('name', 'chang')
        >>> d.getattr('name')
        'chang'
        >>> d.delattr('name')
        >>> d.getattr('name')
        Traceback (most recent call last):
        AttributeError: FlatDict has no attribute name

        ```
        """

        del self.__dict__[name]

    def __missing__(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Allow dict to have default value if it doesn't exist.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = FlatDict(default_factory=list)
        >>> d.n
        []
        >>> d.get('d', 1031)
        1031
        >>> d.__missing__('d', 1031)
        1031

        ```
        """

        if default is None:
            # default_factory might not in __dict__ and cannot be replaced with if self.getattr("default_factory")
            if "default_factory" not in self.__dict__:
                raise KeyError(f"{self.__class__.__name__} does not contain {name}")
            default_factory = self.getattr("default_factory")
            default = default_factory()
            if isinstance(default, FlatDict):
                default.__dict__.update(self.__dict__)
            super().__setitem__(name, default)
        return default

    def to(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert FlatDict to other Mapping.

        `to` and `dict` are alias of this method.

        Args:
            cls (Callable): Target class to be converted to. Defaults to dict.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        # pylint: disable=C0103

        return cls(**{k: v.value if isinstance(v, Variable) else v for k, v in self.items()})

    convert = to
    dict = to

    def update(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:  # type: ignore
        r"""
        Update FlatDict values w.r.t. other.

        `merge`, `merge_from_file`, and `union` are alias of this method.

        Args:
            other (Mapping | Iterable | PathStr): Other values to update.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.update(n).to(dict)
        {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.update(l).to(dict)
        {'a': 1, 'b': 'b', 'c': 3, 'd': 4}

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            for key, value in other.items():
                if key in self and isinstance(self[key], (Mapping,)) and isinstance(value, (Mapping,)):
                    self[key].update(value)
                else:
                    self[key] = value
        elif isinstance(other, Iterable):
            for key, value in other:  # type: ignore
                self[key] = value
        return self

    merge = update
    merge_from_file = update
    union = update

    def difference(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:
        r"""
        Difference between FlatDict values and other.

        `diff` is an alias of this method.

        Args:
            other (Mapping | Iterable | PathStr): Other values to compare.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.difference(n).to(dict)
        {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.difference(l).to(dict)
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}")

        return self.empty_like(
            **{key: value for key, value in other if key not in self or self[key] != value}  # type: ignore
        )

    diff = difference

    def intersection(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:
        r"""
        Intersection between FlatDict values and other.

        `inter` is an alias of this method.

        Args:
            other (Mapping | Iterable | PathStr): Other values to join.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.intersection(n).to(dict)
        {}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.intersection(l).to(dict)
        {'c': 3}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}")
        return self.empty_like(
            **{key: value for key, value in other if key in self and self[key] == value}  # type: ignore
        )

    inter = intersection

    def copy(self) -> FlatDict:
        r"""
        Create a shallow copy of FlatDict.

        Example:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.copy()
        >>> c.to(dict)
        {'a': []}
        >>> d.a.append(1)
        >>> c.to(dict)
        {'a': [1]}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        return copy(self)

    def deepcopy(self, memo: Optional[Mapping] = None) -> FlatDict:
        r"""
        Create a deep copy of FlatDict.

        `clone` and `__deepcopy__` are alias of this method.

        Example:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.deepcopy()
        >>> c.to(dict)
        {'a': []}
        >>> d.a.append(1)
        >>> c.to(dict)
        {'a': []}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        # pylint: disable=C0103

        if memo is not None and id(self) in memo:
            return memo[id(self)]
        ret = self.empty_like()
        for k, v in self.items():
            if isinstance(v, FlatDict):
                ret[k] = v.deepcopy(memo=memo)
            else:
                ret[k] = deepcopy(v)
        return ret

    __deepcopy__ = deepcopy

    clone = deepcopy

    @classmethod
    def empty(cls, *args, **kwargs):
        r"""
        Initialise an empty FlatDict.

        This method is helpful when you inheriting the FlatDict with default values defined in `__init__()`.
        As use type(self)() in this case would copy all the default values, which might now be desired.

        Example:
        ```python
        >>> d = FlatDict(a=[])
        >>> c = d.empty()
        >>> c.to(dict)
        {}

        ```
        """

        empty = cls()
        empty.clear()
        empty._init(*args, **kwargs)
        return empty

    def empty_like(self, *args, **kwargs):
        r"""
        Initialise an empty copy of FlatDict.

        This method will preserve everything in `__dict__`.

        Example:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.empty_like()
        >>> c.to(dict)
        {}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        empty = self.empty(*args, **kwargs)
        empty.__dict__.update(self.__dict__)
        return empty

    def json(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump FlatDict to json file.

        This function calls `self.jsons()` to generate json string.
        You may overwrite `jsons` in case something is not json serializable.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.json("example.json")

        ```
        """

        with self.open(file, mode="w") as fp:  # pylint: disable=C0103
            fp.write(self.jsons(*args, **kwargs))

    @classmethod
    def from_json(cls, file: File, *args, **kwargs) -> FlatDict:
        r"""
        Construct FlatDict from json file.

        This function calls `self.from_jsons()` to construct object from json string.
        You may overwrite `from_jsons` in case something is not json serializable.

        Example:
        ```python
        >>> d = FlatDict.from_json('example.json')
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            return cls.from_jsons(fp.read(), *args, **kwargs)

    def jsons(self, *args, **kwargs) -> str:
        r"""
        Dump FlatDict to json string.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.jsons()
        '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}'

        ```
        """

        if "cls" not in kwargs:
            kwargs["cls"] = JsonEncoder
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return json_dumps(self.to(dict), *args, **kwargs)

    @classmethod
    def from_jsons(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct FlatDict from json string.

        Example:
        ```python
        >>> d = FlatDict.from_jsons('{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}')
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        return cls(**json_loads(string, *args, **kwargs))

    def yaml(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump FlatDict to yaml file.

        This function calls `self.yamls()` to generate yaml string.
        You may overwrite `yamls` in case something is not yaml serializable.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.yaml("example.yaml")

        ```
        """

        with self.open(file, mode="w") as fp:  # pylint: disable=C0103
            self.yamls(fp, *args, **kwargs)

    @classmethod
    def from_yaml(cls, file: File, *args, **kwargs) -> FlatDict:
        r"""
        Construct FlatDict from yaml file.

        This function calls `self.from_yamls()` to construct object from yaml string.
        You may overwrite `from_yamls` in case something is not yaml serializable.

        ```python
        >>> d = FlatDict.from_yaml('example.yaml')
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            return cls.from_yamls(fp.read(), *args, **kwargs)

    def yamls(self, *args, **kwargs) -> str:
        r"""
        Dump FlatDict to yaml string.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.yamls()
        'a: 1\nb: 2\nc: 3\n'

        ```
        """

        if "Dumper" not in kwargs:
            kwargs["Dumper"] = YamlDumper
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent")
        return yaml_dump(self.to(dict), *args, **kwargs)  # type: ignore

    @classmethod
    def from_yamls(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct FlatDict from yaml string.

        Example:
        ```python
        >>> d = FlatDict.from_yamls('a: 1\nb: 2\nc: 3\n')
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        if "Loader" not in kwargs:
            kwargs["Loader"] = YamlLoader
        return cls(**yaml_load(string, *args, **kwargs))

    def dump(self, file: File, method: Optional[str] = None, *args, **kwargs) -> None:  # pylint: disable=W1113
        r"""
        Dump FlatDict to file.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.dump("example.yaml")

        ```
        """

        if method is None:
            if isinstance(file, IO):
                raise ValueError("method must be specified when dumping to file-like object")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in YAML:
            return self.yaml(file=file, *args, **kwargs)  # type: ignore
        if extension in JSON:
            return self.json(file=file, *args, **kwargs)  # type: ignore
        raise FileError(f"file {file} should be in {JSON} or {YAML}, but got {extension}")  # type: ignore

    @classmethod
    def load(cls, file: File, method: Optional[str] = None, *args, **kwargs) -> FlatDict:  # pylint: disable=W1113
        """
        Load FlatDict from file.

        Example:
        ```python
        >>> d = FlatDict.load("example.yaml")
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        if method is None:
            if isinstance(file, IO):
                raise ValueError("method must be specified when loading from file-like object")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in JSON:
            return cls.from_json(file, *args, **kwargs)
        if extension in YAML:
            return cls.from_yaml(file, *args, **kwargs)
        raise FileError("file {file} should be in {JSON} or {YAML}, but got {extension}")

    @staticmethod
    @contextmanager
    def open(file: File, *args, **kwargs):
        """
        Open file IO from file path or file-like object.
        """

        if isinstance(file, (PathLike, str)):
            file = open(file, *args, **kwargs)  # pylint: disable=W1514
            try:
                yield file
            finally:
                file.close()  # type: ignore
        elif isinstance(file, (IO,)):
            yield file
        else:
            raise TypeError(
                f"file={file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}"  # type: ignore
            )

    @staticmethod
    def extra_repr() -> str:  # pylint: disable=C0116
        return ""

    def __repr__(self):
        r"""
        Representation of FlatDict.

        Example:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> repr(d)
        'FlatDict(\n  (a): 1\n  (b): 2\n  (c): 3\n)'

        ```
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

    def _add_indent(self, text):
        lines = text.split("\n")
        # don't do anything for single-line stuff
        if len(lines) == 1:
            return text
        first = lines.pop(0)
        lines = [(self.getattr("indent") * " ") + line for line in lines]
        lines = "\n".join(lines)
        lines = first + "\n" + lines
        return lines

    def __setstate__(self, states, *args, **kwargs):
        for name, value in states.items():
            self.setattr(name, value)
