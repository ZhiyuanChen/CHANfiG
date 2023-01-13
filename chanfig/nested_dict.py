from __future__ import annotations

from collections.abc import Mapping
from functools import wraps
from os import PathLike
from typing import Any, Callable, Iterable, Optional, Union, TypeVar

from .flat_dict import FlatDict, PathStr
from .variable import Variable

K = TypeVar("K")
V = TypeVar("V")


class NestedDict(FlatDict[K, V]):
    r"""
    NestedDict is basically an FlatDict object that create a nested structure with delimiter.

    It also has `all_keys`, `all_values`, `all_items` methods to get all keys, values, items
    respectively in the nested structure.
    """

    convert_mapping: bool = False
    default_factory: Optional[Callable]
    default_mapping: Optional[Callable]
    delimiter: str = "."
    indent: int = 2

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        self.setattr("delimiter", ".")
        self.setattr("convert_mapping", False)
        self.setattr("default_mapping", NestedDict)
        super().__init__(*args, default_factory=default_factory, **kwargs)

    def _init(self, *args, **kwargs) -> None:
        for key, value in args:
            self.set(key, value, convert_mapping=True)
        for key, value in kwargs.items():
            self.set(key, value, convert_mapping=True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from NestedDict.

        `__getitem__` and `__getattr__` are alias of this method.

        Note that default here will override the default_factory if specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = NestedDict(default_factory=NestedDict)
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
        NestedDict()
        >>> d = NestedDict()
        >>> d.get('c')
        Traceback (most recent call last):
        KeyError: 'NestedDict does not contain c'

        ```
        """

        while self.getattr("delimiter") in name:
            name, rest = name.split(self.getattr("delimiter"), 1)
            self, name = self[name], rest  # pylint: disable=W0642
        return super().get(name, default)

    __getitem__ = get
    __getattr__ = get

    def set(  # pylint: disable=W0221
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        r"""
        Set value of NestedDict.

        `__setitem__` and `__setattr__` are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.
            convert_mapping (Optional[bool]): Whether convert mapping to NestedDict. Defaults to self.convert_mapping.

        Example:
        ```python
        >>> d = NestedDict(default_factory=NestedDict)
        >>> d.set('i.d', 1013)
        >>> d.i.d
        1013
        >>> d.d.i = 1031
        >>> d['d.i']
        1031
        >>> d['n.l'] = 'chang'
        >>> d.n.l
        'chang'
        >>> d.f.n = 'liu'
        >>> d['f.n']
        'liu'
        >>> d.setattr('convert_mapping', True)
        >>> d.a.b = {'c': {'d': 1}, 'e.f' : 2}
        >>> d.a.b.c.d
        1
        >>> d.a.b.e.f
        2

        ```
        """

        default_mapping = self.getattr("default_mapping")
        if convert_mapping is None:
            convert_mapping = self.convert_mapping
        while self.getattr("delimiter") in name:
            name, rest = name.split(self.getattr("delimiter"), 1)
            if name not in self:
                if convert_mapping:
                    super().__setitem__(name, default_mapping())
                else:
                    self.__missing__(name)
            self, name = self[name], rest  # pylint: disable=W0642
        if convert_mapping and isinstance(value, Mapping):
            value = default_mapping(**value)
        super().__setitem__(name, value)

    __setitem__ = set
    __setattr__ = set

    def __contains__(self, name: str) -> bool:  # type: ignore
        r"""
        Determine if NestedDict contains name.

        Args:
            name (str): Key name.

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b.c': 2})
        >>> 'a' in d
        True
        >>> 'b.c' in d
        True
        >>> 'b' in d
        True
        >>> 'd' in d
        False

        ```
        """

        while self.getattr("delimiter") in name:
            name, rest = name.split(self.getattr("delimiter"), 1)
            self, name = self[name], rest  # pylint: disable=W0642
        return super().__contains__(name)

    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Pop value from NestedDict.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = NestedDict(default_factory=NestedDict)
        >>> d['i.d'] = 1013
        >>> d.pop('i.d')
        1013
        >>> d.pop('i.d', True)
        True
        >>> d.pop('i.d')
        Traceback (most recent call last):
        KeyError: 'd'

        ```
        """

        if self.getattr("delimiter") in name:
            name, rest = name.split(self.getattr("delimiter"), 1)
            if name not in self:
                raise KeyError(f"{self.__class__.__name__} does not contain {name}")
            return self[name].pop(rest, default)
        return super().pop(name, default) if default is not None else super().pop(name)

    def all_keys(self):
        r"""
        Get all keys of NestedDict.

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_keys())
        ['a', 'b.c', 'b.d']

        ```
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

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_values())
        [1, 2, 3]

        ```
        """

        for value in self.values():
            if isinstance(value, NestedDict):
                yield from value.all_values()
            else:
                yield value

    def all_items(self):
        r"""
        Get all items of NestedDict.

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_items())
        [('a', 1), ('b.c', 2), ('b.d', 3)]

        ```
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
        r"""
        Recursively apply a function to the object and its children.

        Args:
            func (Callable): Function to be applied to.

        Example:
        ```python
        >>> d = NestedDict()
        >>> d.a = NestedDict()
        >>> def func(d):
        ...     d.t = 1
        >>> d.apply(func).to(dict)
        {'a': {'t': 1}, 't': 1}

        ```
        """

        for value in self.values():
            if isinstance(value, NestedDict):
                value.apply(func)
        func(self)
        return self

    def to(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert NestedDict to other Mapping.

        `to` and `dict` are alias of this method.

        Args:
            cls (Callable): Target class to be converted to.

        Example:
        ```python
        >>> d = NestedDict(default_factory=NestedDict, a=1, b=2, c=3)
        >>> d['i.d'] = 1013
        >>> d.to(dict)
        {'a': 1, 'b': 2, 'c': 3, 'i': {'d': 1013}}

        ```
        """

        # pylint: disable=C0103

        ret = cls()
        for k, v in self.items():
            if isinstance(v, Variable):
                v = v.value
            if isinstance(v, FlatDict):
                v = v.to(cls)
            ret[k] = v
        return ret

    convert = to
    dict = to

    def difference(  # pylint: disable=W0221
        self, other: Union[Mapping, Iterable, PathStr], recursive: bool = True
    ) -> NestedDict:
        r"""
        Difference between NestedDict values and other.

        `diff` is an alias of this method.

        Args:
            other (Mapping | Iterable | PathStr): Other values to compare.
            recursive (bool): Whether to compare recursively. Defaults to True.

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b.c': 2, 'b.d': 3})
        >>> n = {'a': 1, 'b.c': 3, 'b.d': 3, 'e': 4}
        >>> d.difference(n).to(dict)
        {'b': {'c': 3}, 'e': 4}
        >>> d.difference(n, recursive=False).to(dict)
        {'b': {'c': 3, 'd': 3}, 'e': 4}
        >>> l = [('a', 1), ('d', 4)]
        >>> d.difference(l).to(dict)
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>

        ```
        """

        # pylint: disable=R0801

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(**other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}")

        @wraps(self.difference)
        def difference(this: NestedDict, that: Iterable) -> Mapping:
            ret = {}
            for key, value in that:
                if key not in this:
                    ret[key] = value
                elif isinstance(this[key], NestedDict) and recursive:
                    ret[key] = this[key].difference(value)
                elif this[key] != value:
                    ret[key] = value
            return ret

        return self.empty_like(**difference(self, other))  # type: ignore

    diff = difference

    def intersection(  # pylint: disable=W0221
        self, other: Union[Mapping, Iterable, PathStr], recursive: bool = True
    ) -> NestedDict:
        r"""
        Intersection between NestedDict values and other.

        `inter` is an alias of this method.

        Args:
            other (Mapping | Iterable | PathStr): Other values to join.
            recursive (bool): Whether to compare recursively. Defaults to True.

        Example:
        ```python
        >>> d = NestedDict(**{'a': 1, 'b.c': 2, 'b.d': 3})
        >>> n = {'a': 1, 'b.c': 3, 'b.d': 3, 'e': 4}
        >>> d.intersection(n).to(dict)
        {'a': 1, 'b': {'d': 3}}
        >>> d.intersection(n, recursive=False).to(dict)
        {'a': 1}
        >>> l = [('a', 1), ('d', 4)]
        >>> d.intersection(l).to(dict)
        {'a': 1}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(**other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}")

        @wraps(self.intersection)
        def intersection(this: NestedDict, that: Iterable) -> Mapping:
            ret = {}
            for key, value in that:
                if key in this:
                    if isinstance(this[key], NestedDict) and recursive:
                        ret[key] = this[key].intersection(value)
                    elif this[key] == value:
                        ret[key] = value
            return ret

        return self.empty_like(**intersection(self, other))  # type: ignore

    inter = intersection


class DefaultDict(NestedDict):
    r"""
    NestedDict with default_factory set to NestedDict by default.

    Note that just like `collections.defaultdict`, the default_factory is called without any arguments.

    In addition, if you access a key that does not exist, the value will be set to default_factory().
    """

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        if default_factory is None:
            default_factory = NestedDict
        super().__init__(*args, default_factory=default_factory, **kwargs)
