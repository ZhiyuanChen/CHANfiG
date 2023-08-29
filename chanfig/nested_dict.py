# CHANfiG, Easier Configuration.
# Copyright (c) 2022-2023, CHANfiG Contributors
# This program is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager, nullcontext
from functools import wraps
from inspect import ismethod
from os import PathLike
from typing import Any

try:
    from functools import cached_property  # pylint: disable=C0412
except ImportError:
    try:
        from backports.cached_property import cached_property  # type: ignore
    except ImportError:
        cached_property = property  # type: ignore # pylint: disable=C0103

from .default_dict import DefaultDict
from .flat_dict import FlatDict
from .utils import Null, PathStr
from .variable import Variable


def apply(obj: Any, func: Callable, *args: Any, **kwargs: Any) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this method is meant for non-in-place modification of `obj` and should return the original object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    Returns:
        (Any): Return value of `func`.

    See Also:
        [`apply_`][chanfig.nested_dict.apply_]: Apply an in-place operation.
    """

    if isinstance(obj, NestedDict):
        return obj.empty_like(**{k: apply(v, func, *args, **kwargs) for k, v in obj.items()})
    if isinstance(obj, Mapping):
        return {k: apply(v, func, *args, **kwargs) for k, v in obj.items()}
    if isinstance(obj, list):
        return [apply(v, func, *args, **kwargs) for v in obj]
    if isinstance(obj, tuple):
        return tuple(apply(v, func, *args, **kwargs) for v in obj)
    if isinstance(obj, set):
        try:
            return {apply(v, func, *args, **kwargs) for v in obj}
        except TypeError:
            tuple(apply(v, func, *args, **kwargs) for v in obj)
    return func(*args, **kwargs) if ismethod(func) else func(obj, *args, **kwargs)


def apply_(obj: Any, func: Callable, *args: Any, **kwargs: Any) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this method is meant for non-in-place modification of `obj` and should return a new object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    Returns:
        (Any): Return value of `func`.

    See Also:
        [`apply_`][chanfig.nested_dict.apply]: Apply a non-in-place operation.
    """

    if isinstance(obj, Mapping):
        for v in obj.values():
            apply_(v, func, *args, **kwargs)
    if isinstance(obj, (list, tuple, set)):
        for v in obj:
            apply_(v, func, *args, **kwargs)
    return func(*args, **kwargs) if ismethod(func) else func(obj, *args, **kwargs)


class NestedDict(DefaultDict):  # type: ignore # pylint: disable=E1136
    r"""
    `NestedDict` further extends `DefaultDict` object by introducing a nested structure with `delimiter`.
    By default, `delimiter` is `.`, but it could be modified in subclass or by calling `dict.setattr('delimiter', D)`.

    `d = NestedDict({"a.b.c": 1})` is equivalent to `d = NestedDict({"a": {"b": {"c": 1}}})`,
    and you can access members either by `d["a.b.c"]` or more simply by `d.a.b.c`.

    This behaviour allows you to pass keyword arguments to other functions as easy as `func1(**d.func1)`.

    Since `NestedDict` inherits from `DefaultDict`, it also supports `default_factory`.
    With `default_factory`, you can assign `d.a.b.c = 1` without assign `d.a = NestedDict()` in the first place.
    Note that the constructor of `NestedDict` is different from `DefaultDict`, `default_factory` is not a positional
    argument, and must be set in a keyword argument.

    `NestedDict` also introduce `all_keys`, `all_values`, `all_items` methods to get all keys, values, items
    respectively in the nested structure.

    Attributes:
        convert_mapping: bool = False
            If `True`, all new values with type of `Mapping` will be converted to `default_factory`.
            If `default_factory` is `Null`, will create an empty instance via `self.empty` as `default_factory`.
        delimiter: str = "."
            Delimiter for nested structure.

    Notes:
        When `convert_mapping` specified, all new values with type of `Mapping` will be converted to `default_factory`.
        If `default_factory` is `Null`, will create an empty instance via `self.empty` as `default_factory`.

        `convert_mapping` is automatically applied to arguments during initialisation.

    Examples:
        >>> NestedDict({"f.n": "chang"})
        NestedDict(
          ('f'): NestedDict(
            ('n'): 'chang'
          )
        )
        >>> d = NestedDict({"f.n": "chang"}, default_factory=NestedDict)
        >>> d.i.d = 1013
        >>> d['i.d']
        1013
        >>> d.i.d
        1013
        >>> d.dict()
        {'f': {'n': 'chang'}, 'i': {'d': 1013}}
    """

    convert_mapping: bool = False
    delimiter: str = "."

    def __init__(
        self, *args: Any, default_factory: Callable | None = None, convert_mapping: bool = False, **kwargs: Any
    ) -> None:
        with self.converting():
            super().__init__(default_factory)
            if len(args) == 1 and isinstance(args[0], Mapping):
                for key, value in args[0].items():
                    self.set(key, value)
            elif len(args) == 1 and isinstance(args[0], Iterable):
                for key, value in args[0]:
                    self.set(key, value)
            elif len(args) > 0:
                for key, value in args:
                    self.set(key, value)
            for key, value in kwargs.items():
                self.set(key, value)

    def all_keys(self) -> Generator:
        r"""
        Get all keys of `NestedDict`.

        Returns:
            (Generator):

        Examples:
            >>> d = NestedDict({'a': 1, 'b': {'c': 2, 'd': 3}})
            >>> list(d.all_keys())
            ['a', 'b.c', 'b.d']
        """

        delimiter = self.getattr("delimiter", ".")

        @wraps(self.all_keys)
        def all_keys(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = str(prefix) + str(delimiter) + str(key)
                if isinstance(value, NestedDict):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self) -> Generator:
        r"""
        Get all values of `NestedDict`.

        Returns:
            (Generator):

        Examples:
            >>> d = NestedDict({'a': 1, 'b': {'c': 2, 'd': 3}})
            >>> list(d.all_values())
            [1, 2, 3]
        """

        for value in self.values():
            if isinstance(value, NestedDict):
                yield from value.all_values()
            else:
                yield value

    def all_items(self) -> Generator:
        r"""
        Get all items of `NestedDict`.

        Returns:
            (Generator):

        Examples:
            >>> d = NestedDict({'a': 1, 'b': {'c': 2, 'd': 3}})
            >>> list(d.all_items())
            [('a', 1), ('b.c', 2), ('b.d', 3)]
        """

        delimiter = self.getattr("delimiter", ".")

        @wraps(self.all_items)
        def all_items(self, prefix=""):
            for key, value in self.items():
                if prefix:
                    key = str(prefix) + str(delimiter) + str(key)
                if isinstance(value, NestedDict):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def apply(self, func: Callable, *args: Any, **kwargs: Any) -> NestedDict:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for non-in-place modification of `obj`, for example, [`to`][chanfig.NestedDict.to].

        Args:
            func (Callable):

        See Also:
            [`apply_`][chanfig.NestedDict.apply_]: Apply an in-place operation.
            [`apply`][chanfig.nested_dict.apply]: Implementation of `apply`.

        tionples:
            >>> def func(d):
            ...     if isinstance(d, NestedDict):
            ...         d.t = 1
            >>> d = NestedDict()
            >>> d.a = NestedDict()
            >>> d.b = [NestedDict(),]
            >>> d.c = (NestedDict(),)
            >>> d.d = {NestedDict(),}
            >>> d.apply(func).dict()
            {'a': {}, 'b': [{}], 'c': ({},), 'd': ({},)}
        """

        return apply(self, func, *args, **kwargs)

    def apply_(self, func: Callable, *args: Any, **kwargs: Any) -> NestedDict:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for in-place modification of `obj`, for example, [`freeze`][chanfig.Config.freeze].

        Args:
            func (Callable):

        See Also:
            [`apply`][chanfig.NestedDict.apply]: Apply a non-in-place operation.
            [`apply_`][chanfig.nested_dict.apply_]: Implementation of `apply_` method.

        Examples:
            >>> def func(d):
            ...     if isinstance(d, NestedDict):
            ...         d.t = 1
            >>> d = NestedDict()
            >>> d.a = NestedDict()
            >>> d.b = [NestedDict(),]
            >>> d.c = (NestedDict(),)
            >>> d.d = {NestedDict(),}
            >>> d.apply_(func).dict()
            {'a': {'t': 1}, 'b': [{'t': 1}], 'c': ({'t': 1},), 'd': ({'t': 1},), 't': 1}
        """

        apply_(self, func, *args, **kwargs)
        return self

    def get(self, name: Any, default: Any = None) -> Any:
        r"""
        Get value from `NestedDict`.

        Note that `default` has higher priority than `default_factory`.

        Args:
            name:
            default:

        Returns:
            value:
                If `NestedDict` does not contain `name`, return `default`.
                If `default` is not specified, return `default_factory()`.

        Raises:
            KeyError: If `NestedDict` does not contain `name` and `default`/`default_factory` is not specified.
            TypeError: If `name` is not hashable.

        Examples:
            >>> d = NestedDict({"i.d": 1013}, default_factory=NestedDict)
            >>> d.get('i.d')
            1013
            >>> d['i.d']
            1013
            >>> d.i.d
            1013
            >>> d.get('i.d', None)
            1013
            >>> d.get('f', 2)
            2
            >>> d.f
            NestedDict(<class 'chanfig.nested_dict.NestedDict'>, )
            >>> del d.f
            >>> d = NestedDict({"i.d": 1013})
            >>> d.e
            Traceback (most recent call last):
            AttributeError: 'NestedDict' object has no attribute 'e'
            >>> d.e = {}
            >>> d.get('e.f', Null)
            Traceback (most recent call last):
            KeyError: 'f'
            >>> d.get('e.f')
            >>> d.get('e.f', 1)
            1
            >>> d.e.f
            Traceback (most recent call last):
            AttributeError: 'dict' object has no attribute 'f'
        """

        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        # if value is a python dict
        if not isinstance(self, NestedDict):
            if name not in self and default is not Null:
                return default
            return self[name]
        return super().get(name, default)

    def set(  # pylint: disable=W0221
        self,
        name: Any,
        value: Any,
        convert_mapping: bool | None = None,
    ) -> None:
        r"""
        Set value of `NestedDict`.

        Args:
            name:
            value:
            convert_mapping: Whether to convert `Mapping` to `NestedDict`.
                Defaults to self.convert_mapping.

        Examples:
            >>> d = NestedDict(default_factory=NestedDict)
            >>> d.set('i.d', 1013)
            >>> d.get('i.d')
            1013
            >>> d.dict()
            {'i': {'d': 1013}}
            >>> d['f.n'] = 'chang'
            >>> d.f.n
            'chang'
            >>> d.n.l = 'liu'
            >>> d['n.l']
            'liu'
            >>> d['f.n.e'] = "error"
            Traceback (most recent call last):
            ValueError: Cannot set `f.n.e` to `error`, as `f.n=chang`.
            >>> d['f.n.e.a'] = "error"
            Traceback (most recent call last):
            KeyError: 'e'
            >>> d.f.n.e.a = "error"
            Traceback (most recent call last):
            AttributeError: 'str' object has no attribute 'e'
            >>> d.setattr('convert_mapping', True)
            >>> d.a.b = {'c': {'d': 1}, 'e.f' : 2}
            >>> d.a.b.c.d
            1
            >>> d['c.d'] = {'c': {'d': 1}, 'e.f' : 2}
            >>> d.c.d['e.f']
            2
            >>> d.setattr('convert_mapping', False)
            >>> d.set('e.f', {'c': {'d': 1}, 'e.f' : 2}, convert_mapping=True)
            >>> d['e.f']['c.d']
            1
        """
        # pylint: disable=W0642

        full_name = name
        if convert_mapping is None:
            convert_mapping = self.getattr("convert_mapping", False)
        delimiter = self.getattr("delimiter", ".")
        default_factory = self.getattr("default_factory", self.empty)
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                if name in dir(self) and isinstance(getattr(self.__class__, name), (property, cached_property)):
                    self, name = getattr(self, name), rest
                elif name not in self and isinstance(self, Mapping):
                    default = (
                        self.__missing__(name, default_factory()) if hasattr(self, "__missing__") else default_factory()
                    )
                    self, name = default, rest
                else:
                    self, name = self[name], rest
                if isinstance(self, NestedDict):
                    default_factory = self.getattr("default_factory", self.empty)
        except (AttributeError, TypeError):
            raise KeyError(name) from None

        if (
            convert_mapping
            and isinstance(value, Mapping)
            and not isinstance(value, default_factory if isinstance(default_factory, type) else type(self))
            and not isinstance(value, Variable)
        ):
            try:
                value = default_factory(**value)
            except TypeError:
                value = default_factory(value)
        if isinstance(self, NestedDict):
            super().set(name, value)
        elif isinstance(self, Mapping):
            dict.__setitem__(self, name, value)
        else:
            raise ValueError(
                f"Cannot set `{full_name}` to `{value}`, as `{delimiter.join(full_name.split(delimiter)[:-1])}={self}`."
            )

    def delete(self, name: Any) -> None:
        r"""
        Delete value from `NestedDict`.

        Args:
            name:

        Examples:
            >>> d = NestedDict({"i.d": 1013, "f.n": "chang"})
            >>> d.i.d
            1013
            >>> d.f.n
            'chang'
            >>> d.delete('i.d')
            >>> d.dict()
            {'i': {}, 'f': {'n': 'chang'}}
            >>> d.i.d
            Traceback (most recent call last):
            AttributeError: 'NestedDict' object has no attribute 'd'
            >>> del d.f.n
            >>> d.dict()
            {'i': {}, 'f': {}}
            >>> d.f.n
            Traceback (most recent call last):
            AttributeError: 'NestedDict' object has no attribute 'n'
            >>> del d.e
            Traceback (most recent call last):
            AttributeError: 'NestedDict' object has no attribute 'e'
            >>> del d['f.n']
            Traceback (most recent call last):
            KeyError: 'n'
            >>> d.e = {'a': {'b': 1}}
            >>> del d['e.a.b']
        """

        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        # if value is a python dict
        if not isinstance(self, NestedDict):
            del self[name]
            return
        super().delete(name)

    def pop(self, name: Any, default: Any = Null) -> Any:
        r"""
        Pop value from `NestedDict`.

        Args:
            name:
            default:

        Returns:
            value: If `NestedDict` does not contain `name`, return `default`.

        Examples:
            >>> d = NestedDict({"i.d": 1013, "f.n": "chang", "n.a.b.c": 1}, default_factory=NestedDict)
            >>> d.pop('i.d')
            1013
            >>> d.pop('i.d', True)
            True
            >>> d.pop('i.d')
            Traceback (most recent call last):
            KeyError: 'd'
            >>> d.pop('e')
            Traceback (most recent call last):
            KeyError: 'e'
            >>> d.pop('e.f')
            Traceback (most recent call last):
            KeyError: 'f'
        """

        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        if not isinstance(self, dict) or name not in self:
            if default is not Null:
                return default
            raise KeyError(name)
        return super().pop(name)

    def validate(self) -> None:
        r"""
        Validate `NestedDict`.

        Raises:
            TypeError: If `Variable` has invalid type.
            ValueError: If `Variable` has invalid value.

        Examples:
            >>> d = NestedDict({"i.d": Variable(1016, type=int, validator=lambda x: x > 0)})
            >>> d = NestedDict({"i.d": Variable(1016, type=str, validator=lambda x: x > 0)})
            Traceback (most recent call last):
            TypeError: 'd' has invalid type. Value 1016 is not of type <class 'str'>.
            >>> d = NestedDict({"i.d": Variable(-1, type=int, validator=lambda x: x > 0)})
            Traceback (most recent call last):
            ValueError: 'd' has invalid value. Value -1 is not valid.
        """

        self.apply_(self._validate)

    def sort(self, key: Callable | None = None, reverse: bool = False, recursive: bool = True) -> NestedDict:
        r"""
        Sort `NestedDict`.

        Args:
            recursive (bool): Whether to apply `sort` recursively.

        Returns:
            (NestedDict):

        Examples:
            >>> l = [1]
            >>> d = NestedDict({"a": 1, "b": {"c": 2, "d": 3}, "b.e.f": l})
            >>> d.sort().dict()
            {'a': 1, 'b': {'c': 2, 'd': 3, 'e': {'f': [1]}}}
            >>> d = NestedDict({"b.e.f": l, "b.d": 3, "a": 1, "b.c": 2})
            >>> d.sort().dict()
            {'a': 1, 'b': {'c': 2, 'd': 3, 'e': {'f': [1]}}}
            >>> d = NestedDict({"b.e.f": l, "b.d": 3, "a": 1, "b.c": 2})
            >>> d.sort(recursive=False).dict()
            {'a': 1, 'b': {'e': {'f': [1]}, 'd': 3, 'c': 2}}
            >>> l.append(2)
            >>> d.b.e.f
            [1, 2]
        """

        if recursive:
            for value in self.values():
                if isinstance(value, FlatDict):
                    value.sort(key=key, reverse=reverse)
        return super().sort(key=key, reverse=reverse)  # type: ignore

    @staticmethod
    def _merge(this: FlatDict, that: Iterable, overwrite: bool = True) -> Mapping:
        if not that:
            return this
        elif isinstance(that, Mapping):
            that = that.items()
        context = this.converting() if isinstance(this, NestedDict) else nullcontext()
        with context:
            for key, value in that:
                if key in this and isinstance(this[key], Mapping):
                    if isinstance(value, Mapping):
                        NestedDict._merge(this[key], value, overwrite)
                    elif isinstance(this, NestedDict):
                        this.set(key, value)
                    elif overwrite:
                        this[key] = value
                elif key in dir(this) and isinstance(getattr(this.__class__, key), (property, cached_property)):
                    getattr(this, key).merge(value, overwrite=overwrite)
                elif overwrite or key not in this:
                    if isinstance(this, NestedDict):
                        this.set(key, value)
                    else:
                        this[key] = value
        return this

    def intersect(  # pylint: disable=W0221
        self, other: Mapping | Iterable | PathStr, recursive: bool = True
    ) -> NestedDict:
        r"""
        Intersection of `NestedDict` and `other`.

        Args:
            other (Mapping | Iterable | PathStr):
            recursive (bool):

        Examples:
            >>> d = NestedDict({'a': 1, 'b.c': 2, 'b.d': 3, 'c.d.e': 4, 'c.d.f': 5, 'c.e': 6})
            >>> n = {'b': {'c': 3, 'd': 5}, 'c.d.e': 4, 'c.d': {'f': 5}, 'd': 0}
            >>> d.intersect(n).dict()
            {'c': {'d': {'e': 4, 'f': 5}}}
            >>> d.intersect("tests/test.yaml").dict()
            {'a': 1}
            >>> d.intersect(n, recursive=False).dict()
            {}
            >>> l = [('a', 1), ('d', 4)]
            >>> d.intersect(l).dict()
            {'a': 1}
            >>> d.intersect(1)
            Traceback (most recent call last):
            TypeError: `other=1` should be of type Mapping, Iterable or PathStr, but got <class 'int'>.
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")
        return self.empty(self._intersect(self, other, recursive))  # type: ignore

    @staticmethod
    def _intersect(this: NestedDict, that: Iterable, recursive: bool = True) -> Mapping:
        ret: NestedDict = NestedDict()
        for key, value in that:
            if key in this:
                if isinstance(this[key], NestedDict) and isinstance(value, Mapping) and recursive:
                    intersects = this[key].intersect(value)
                    if intersects:
                        ret[key] = intersects
                elif this[key] == value:
                    ret[key] = value
        return ret

    def difference(  # pylint: disable=W0221, C0103
        self, other: Mapping | Iterable | PathStr, recursive: bool = True
    ) -> NestedDict:
        r"""
        Difference between `NestedDict` and `other`.

        Args:
            other (Mapping | Iterable | PathStr):
            recursive (bool):

        Examples:
            >>> d = NestedDict({'a': 1, 'b.c': 2, 'b.d': 3, 'c.d.e': 4, 'c.d.f': 5, 'c.e': 6})
            >>> n = {'b': {'c': 3, 'd': 5}, 'c.d.e': 4, 'c.d': {'f': 5}, 'd': 0}
            >>> d.difference(n).dict()
            {'b': {'c': 3, 'd': 5}, 'd': 0}
            >>> d.difference("tests/test.yaml").dict()
            {'b': 2, 'c': 3}
            >>> d.difference(n, recursive=False).dict()
            {'b': {'c': 3, 'd': 5}, 'c': {'d': {'e': 4, 'f': 5}}, 'd': 0}
            >>> l = [('a', 1), ('d', 4)]
            >>> d.difference(l).dict()
            {'d': 4}
            >>> d.difference(1)
            Traceback (most recent call last):
            TypeError: `other=1` should be of type Mapping, Iterable or PathStr, but got <class 'int'>.
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")
        return self.empty(self._difference(self, other, recursive))  # type: ignore

    @staticmethod
    def _difference(this: NestedDict, that: Iterable, recursive: bool = True) -> Mapping:
        ret: NestedDict = NestedDict()
        for key, value in that:
            if key not in this:
                ret[key] = value
            elif isinstance(this[key], NestedDict) and isinstance(value, Mapping) and recursive:
                differences = this[key].difference(value)
                if differences:
                    ret[key] = differences
            elif this[key] != value:
                ret[key] = value
        return ret

    @contextmanager
    def converting(self):
        convert_mapping = self.getattr("convert_mapping", False)
        try:
            self.setattr("convert_mapping", True)
            yield
        finally:
            self.setattr("convert_mapping", convert_mapping)

    def __contains__(self, name: Any) -> bool:  # type: ignore
        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                if super().__contains__(name):
                    self, name = self[name], rest  # pylint: disable=W0642
                else:
                    return False
            return super().__contains__(name)
        except (TypeError, KeyError):  # TypeError when name is not in self
            return False
