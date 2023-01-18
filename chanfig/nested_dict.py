from __future__ import annotations

from collections.abc import Mapping
from functools import wraps
from os import PathLike
from typing import Any, Callable, Iterable, Optional, Union

from .flat_dict import FlatDict, PathStr, TorchDevice, TorchDtype
from .variable import Variable


class NestedDict(FlatDict):
    r"""
    `NestedDict` further extends `FlatDict` object by introducing a nested structure with delimiter.

    `d = NestedDict(**{"a.b.c": 1})` is equivalent to `d = NestedDict(**{"a": {"b": {"c": 1}}})`,
    and you can access the value by `d["a.b.c"]` or more simply `d.a.b.c`.

    With `default_factory`, you can create nested `NestedDict` objects automatically.

    This behavior allows you to pass keyword arguments to other function like `func1(**d.func1)`.

    `NestedDict` also has `all_keys`, `all_values`, `all_items` methods to get all keys, values, items
    respectively in the nested structure.

    When `convert_mapping` specified, all new values with a type of `Mapping` will be converted to `default_mapping`.
    Note that `convert_mapping` is automatically applied to arguments at initialisation.

    Attributes
    ----------
    default_mapping: Callable = NestedDict
        Default mapping when performing `convert_mapping`.
    convert_mapping: bool = False
        If `True`, all new values with a type of `Mapping` will be converted to `default_mapping`.
    delimiter: str = "."
        Delimiter for nested structure.

    Examples
    --------
    ```python
    >>> d = NestedDict(**{"f.n": "chang"}, default_factory=NestedDict)
    >>> d.i.d = 1013
    >>> d['i.d']
    1013
    >>> d.i.d
    1013
    >>> d.dict()
    {'f': {'n': 'chang'}, 'i': {'d': 1013}}

    ```
    """

    default_mapping: Callable
    convert_mapping: bool = False
    delimiter: str = "."

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs):
        if not self.hasattr("default_mapping"):
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

        Note that `default` will override the `default_factory` if specified.

        Parameters
        ----------
        name: str
        default: Optional[Any] = None

        Returns
        -------
        value: Any
            If name does not exist, return `default`.
            If `default` is not specified, return `default_factory()`.

        Raises
        ------
        KeyError
            If name does not exist and `default`/`default_factory` is not specified.

        **Alias**:

        + `__getitem__`
        + `__getattr__`

        Examples
        --------
        ```python
        >>> d = NestedDict(**{"i.d": 1013}, default_factory=NestedDict)
        >>> d.get('i.d')
        1013
        >>> d['i.d']
        1013
        >>> d.i.d
        1013
        >>> d.get('f', 2)
        2
        >>> d.f
        NestedDict()
        >>> del d.f
        >>> d = NestedDict()
        >>> d.f
        Traceback (most recent call last):
        KeyError: 'NestedDict does not contain f.'

        ```
        """

        delimiter = self.getattr("delimiter", ".")
        while delimiter in name:
            name, rest = name.split(delimiter, 1)
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

        Parameters
        ----------
        name: str
        value: Any
        convert_mapping: Optional[bool] = self.convert_mapping
            Whether convert mapping to NestedDict.

        **Alias**:

        + `__setitem__`
        + `__setattr__`

        Examples
        --------
        ```python
        >>> d = NestedDict(default_factory=NestedDict)
        >>> d.set('i.d', 1013)
        >>> d.get('i.d')
        1013
        >>> d
        NestedDict(
          (i): NestedDict(
            (d): 1013
          )
        )
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

        delimiter = self.getattr("delimiter", ".")
        default_mapping = self.getattr("default_mapping", NestedDict)
        if convert_mapping is None:
            convert_mapping = self.convert_mapping
        while delimiter in name:
            name, rest = name.split(delimiter, 1)
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

    def delete(self, name: str) -> None:
        r"""
        Delete value from NestedDict.

        Parameters
        ----------
        name: str

        **Alias**:

        + `__delitem__`
        + `__delattr__`

        Examples
        --------
        ```python
        >>> d = NestedDict(**{"i.d": 1013, "f.n": "chang"}, default_factory=NestedDict)
        >>> d.i.d
        1013
        >>> d.f.n
        'chang'
        >>> d.delete('i.d')
        >>> "i.d" in d
        False
        >>> d.i.d
        Traceback (most recent call last):
        KeyError: 'NestedDict does not contain d.'
        >>> del d.f.n
        >>> d.f.n
        Traceback (most recent call last):
        KeyError: 'NestedDict does not contain n.'
        >>> del d.c
        Traceback (most recent call last):
        KeyError: 'c'

        ```
        """

        delimiter = self.getattr("delimiter", ".")
        while delimiter in name:
            name, rest = name.split(delimiter, 1)
            self, name = self[name], rest  # pylint: disable=W0642
        super().__delitem__(name)

    __delitem__ = delete
    __delattr__ = delete

    def __contains__(self, name: str) -> bool:  # type: ignore
        r"""
        Determine if NestedDict contains name.

        Parameters
        ----------
        name: str

        Examples
        --------
        ```python
        >>> d = NestedDict(**{"i.d": 1013, "f.n": "chang"}, default_factory=NestedDict)
        >>> 'i.d' in d
        True
        >>> 'f.n' in d
        True
        >>> 'i' in d
        True
        >>> 'd' in d
        False

        ```
        """

        delimiter = self.getattr("delimiter", ".")
        while delimiter in name:
            name, rest = name.split(delimiter, 1)
            self, name = self[name], rest  # pylint: disable=W0642
        return super().__contains__(name)

    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Pop value from NestedDict.

        Parameters
        ----------
        name: str
        default: Optional[Any] = None

        Examples
        --------
        ```python
        >>> d = NestedDict(**{"i.d": 1013, "f.n": "chang"}, default_factory=NestedDict)
        >>> d.pop('i.d')
        1013
        >>> d.pop('i.d', True)
        True
        >>> d.pop('i.d')
        Traceback (most recent call last):
        KeyError: 'd'

        ```
        """

        delimiter = self.getattr("delimiter", ".")
        if delimiter in name:
            name, rest = name.split(delimiter, 1)
            if name not in self:
                raise KeyError(f"{self.__class__.__name__} does not contain {name}")
            return self[name].pop(rest, default)
        return super().pop(name, default) if default is not None else super().pop(name)

    def all_keys(self):
        r"""
        Get all keys of NestedDict.

        Examples
        --------
        ```python
        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_keys())
        ['a', 'b.c', 'b.d']

        ```
        """

        delimiter = self.getattr("delimiter", ".")

        @wraps(self.all_keys)
        def all_keys(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + delimiter + key
                if isinstance(value, NestedDict):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self):
        r"""
        Get all values of NestedDict.

        Examples
        --------
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

        Examples
        --------
        ```python
        >>> d = NestedDict(**{'a': 1, 'b': {'c': 2, 'd': 3}})
        >>> list(d.all_items())
        [('a', 1), ('b.c', 2), ('b.d', 3)]

        ```
        """

        delimiter = self.getattr("delimiter", ".")

        @wraps(self.all_items)
        def all_items(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = prefix + delimiter + key
                if isinstance(value, NestedDict):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def apply(self, func: Callable) -> NestedDict:
        r"""
        Recursively apply a function to the object and its children.

        Parameters
        ----------
        func: Callable

        Examples
        --------
        ```python
        >>> d = NestedDict()
        >>> d.a = NestedDict()
        >>> def func(d):
        ...     d.t = 1
        >>> d.apply(func).dict()
        {'a': {'t': 1}, 't': 1}

        ```
        """

        for value in self.values():
            if isinstance(value, NestedDict):
                value.apply(func)
        func(self)
        return self

    def difference(  # pylint: disable=W0221
        self, other: Union[Mapping, Iterable, PathStr], recursive: bool = True
    ) -> NestedDict:
        r"""
        Difference between NestedDict values and other.

        Parameters
        ----------
        other: Mapping | Iterable | PathStr
        recursive: bool = True

        **Alias**:

        + `diff`

        Examples
        --------
        ```python
        >>> d = NestedDict(**{'a': 1, 'b.c': 2, 'b.d': 3})
        >>> n = {'a': 1, 'b.c': 3, 'b.d': 3, 'e': 4}
        >>> d.difference(n).dict()
        {'b': {'c': 3}, 'e': 4}
        >>> d.difference(n, recursive=False).dict()
        {'b': {'c': 3, 'd': 3}, 'e': 4}
        >>> l = [('a', 1), ('d', 4)]
        >>> d.difference(l).dict()
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>.

        ```
        """

        # pylint: disable=R0801

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(**other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}.")

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

        Parameters
        ----------
        other: Mapping | Iterable | PathStr
        recursive: bool = True

        **Alias**:

        + `inter`

        Examples
        --------
        ```python
        >>> d = NestedDict(**{'a': 1, 'b.c': 2, 'b.d': 3})
        >>> n = {'a': 1, 'b.c': 3, 'b.d': 3, 'e': 4}
        >>> d.intersection(n).dict()
        {'a': 1, 'b': {'d': 3}}
        >>> d.intersection(n, recursive=False).dict()
        {'a': 1}
        >>> l = [('a', 1), ('d', 4)]
        >>> d.intersection(l).dict()
        {'a': 1}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>.

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(**other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}.")

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

    def to(self, cls: Union[str, TorchDevice, TorchDtype]) -> Any:
        r"""
        Convert values of `NestedDict` to target class.

        Parameters
        ----------
        cls: str | torch.device | torch.dtype

        Examples
        --------
        ```python
        >>> import torch
        >>> d = NestedDict(**{'i.d': torch.tensor(1013)})
        >>> d.cpu().dict()
        {'i': {'d': tensor(1013)}}

        ```
        """

        return self.apply(lambda d: super().to(cls))

    def dict(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert `NestedDict` to other `Mapping`.

        Parameters
        ----------
        cls: Callable = dict
            Target class to be converted to.

        Examples
        --------
        ```python
        >>> d = NestedDict(**{"f.n": "chang"}, default_factory=NestedDict)
        >>> d['i.d'] = 1013
        >>> d.dict()
        {'f': {'n': 'chang'}, 'i': {'d': 1013}}

        ```
        """

        # pylint: disable=C0103

        ret = cls()
        for k, v in self.items():
            if isinstance(v, Variable):
                v = v.value
            if isinstance(v, FlatDict):
                v = v.dict(cls)
            ret[k] = v
        return ret


class DefaultDict(NestedDict):
    r"""
    `NestedDict` with `default_factory` set to `NestedDict` by default.

    Note that just like `collections.defaultdict`, the `default_factory()` is called without any arguments.

    In addition, if you access a key that does not exist, the value will be set to `default_factory()`.
    """

    def __init__(self, *args, **kwargs):
        if "default_factory" not in kwargs:
            kwargs["default_factory"] = NestedDict
        super().__init__(*args, **kwargs)
