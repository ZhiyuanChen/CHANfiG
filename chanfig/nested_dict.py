# CHANfiG
# Copyright (C) 2022-Present, DanLing Team

# This file is part of CHANfiG.

# CHANfiG is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0

# CHANfiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager, nullcontext
from functools import wraps
from os import PathLike
from typing import Any

from typing_extensions import Self

try:
    from functools import cached_property  # pylint: disable=C0412
except ImportError:
    try:
        from backports.cached_property import cached_property  # type: ignore[no-redef]
    except ImportError:
        cached_property = property  # type: ignore[misc, assignment] # pylint: disable=C0103

from .default_dict import DefaultDict
from .flat_dict import FlatDict
from .utils import NULL, Null, PathStr, apply, apply_
from .variable import Variable


class NestedDict(DefaultDict):  # pylint: disable=E1136
    r"""
    `NestedDict` further extends `DefaultDict` object by introducing a nested structure with `separator`.
    By default, `separator` is `.`, but it could be modified in subclass or by calling `dict.setattr('separator', S)`.

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
        separator: str = "."
            separator for nested structure.

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
        >>> NestedDict({"i.d": [{'c': 1016}, {'k': 1031}]})
        NestedDict(
          ('i'): NestedDict(
            ('d'): [NestedDict(
              ('c'): 1016
            ), NestedDict(
              ('k'): 1031
            )]
          )
        )
        >>> d = NestedDict({"f.n": "chang"}, default_factory=NestedDict)
        >>> d.i.d = 1016
        >>> d['i.d']
        1016
        >>> d.i.d
        1016
        >>> d.dict()
        {'f': {'n': 'chang'}, 'i': {'d': 1016}}
    """

    convert_mapping = False
    separator = "."
    fallback = False

    def __init__(
        self,
        *args: Any,
        default_factory: Callable | NULL = Null,
        convert_mapping: bool | None = None,
        fallback: bool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(default_factory, *args, **kwargs)
        if convert_mapping is not None:
            self.setattr("convert_mapping", convert_mapping)
        if fallback is not None:
            self.setattr("fallback", fallback)

    def all_keys(self) -> Generator:
        r"""
        Get all keys of `NestedDict`.

        Examples:
            >>> d = NestedDict({'a': 1, 'b': {'c': 2, 'd': 3}})
            >>> list(d.all_keys())
            ['a', 'b.c', 'b.d']
        """

        separator = self.getattr("separator", ".")

        @wraps(self.all_keys)
        def all_keys(self, prefix=Null):
            for key, value in self.items():
                if prefix is not Null:
                    key = str(prefix) + str(separator) + str(key)
                if isinstance(value, NestedDict):
                    yield from all_keys(value, key)
                else:
                    yield key

        return all_keys(self)

    def all_values(self) -> Generator:
        r"""
        Get all values of `NestedDict`.

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

        Examples:
            >>> d = NestedDict({'a': 1, 'b': {'c': 2, 'd': 3}})
            >>> list(d.all_items())
            [('a', 1), ('b.c', 2), ('b.d', 3)]
        """

        separator = self.getattr("separator", ".")

        @wraps(self.all_items)
        def all_items(self, prefix=Null):
            for key, value in self.items():
                if prefix is not Null:
                    key = str(prefix) + str(separator) + str(key)
                if isinstance(value, NestedDict):
                    yield from all_items(value, key)
                else:
                    yield key, value

        return all_items(self)

    def apply(self, func: Callable, *args: Any, **kwargs: Any) -> Self:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for non-in-place modification of `obj`, for example, [`to`][chanfig.NestedDict.to].

        Args:
            func (Callable):

        See Also:
            [`apply_`][chanfig.NestedDict.apply_]: Apply an in-place operation.
            [`apply`][chanfig.utils.apply.apply]: Implementation of `apply`.

        Examples:
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

    def apply_(self, func: Callable, *args: Any, **kwargs: Any) -> Self:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for in-place modification of `obj`, for example, [`freeze`][chanfig.Config.freeze].

        Args:
            func (Callable):

        See Also:
            [`apply`][chanfig.NestedDict.apply]: Apply a non-in-place operation.
            [`apply_`][chanfig.utils.apply.apply_]: Implementation of `apply_` method.

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

    def get(self, name: Any, default: Any = None, fallback: bool | None = None) -> Any:
        r"""
        Get value from `NestedDict`.

        Note that `default` has higher priority than `default_factory`.

        Raises:
            KeyError: If `NestedDict` does not contain `name` and `default`/`default_factory` is not specified.
            TypeError: If `name` is not hashable.

        Examples:
            >>> d = NestedDict({"i.d": 1016}, default_factory=NestedDict)
            >>> d.get('i.d')
            1016
            >>> d['i.d']
            1016
            >>> d.i.d
            1016
            >>> d.get('i.d', None)
            1016
            >>> d.get('f', 2)
            2
            >>> d.get('a.b', None)
            >>> d.f
            NestedDict(<class 'chanfig.nested_dict.NestedDict'>, )
            >>> del d.f
            >>> d = NestedDict({"i.d": 1016})
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

        separator = self.getattr("separator", ".")
        if fallback is None:
            fallback = self.getattr("fallback", False)
        fallback_name = name.split(separator)[-1] if isinstance(name, str) else name
        fallback_value = Null
        try:
            while isinstance(name, str) and separator in name:
                if fallback and fallback_name in self:
                    fallback_value = self.get(fallback_name)
                name, rest = name.split(separator, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (KeyError, AttributeError, TypeError):
            if fallback and fallback_value is not Null:
                return fallback_value
            if default is not Null:
                return default
            raise KeyError(name) from None
        if (fallback and fallback_value is not Null) and (not isinstance(self, Iterable) or name not in self):
            return fallback_value
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
            >>> d.set('i.d', 1016)
            >>> d.get('i.d')
            1016
            >>> d.dict()
            {'i': {'d': 1016}}
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
        separator = self.getattr("separator", ".")
        if convert_mapping is None:
            convert_mapping = self.getattr("convert_mapping", False)
        default_factory = self.getattr("default_factory", self.empty) or self.empty
        try:
            while isinstance(name, str) and separator in name:
                name, rest = name.split(separator, 1)
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
                    default_factory = self.getattr("default_factory", self.empty) or self.empty
        except (AttributeError, TypeError):
            raise KeyError(name) from None

        if (
            convert_mapping
            and not isinstance(value, default_factory if isinstance(default_factory, type) else type(self))
            and not isinstance(value, Variable)
        ):
            if isinstance(value, Mapping):
                try:
                    value = default_factory(**value)
                except TypeError:
                    value = default_factory(value)
            if isinstance(value, list):
                value = [default_factory(v) if isinstance(v, Mapping) else v for v in value]
            if isinstance(value, tuple):
                value = tuple(default_factory(v) if isinstance(v, Mapping) else v for v in value)
            if isinstance(value, set):
                value = {default_factory(v) if isinstance(v, Mapping) else v for v in list(value)}
        if isinstance(self, NestedDict):
            super().set(name, value)
        elif isinstance(self, Mapping):
            dict.__setitem__(self, name, value)
        else:
            raise ValueError(
                f"Cannot set `{full_name}` to `{value}`, as `{separator.join(full_name.split(separator)[:-1])}={self}`."
            )

    def delete(self, name: Any) -> None:
        r"""
        Delete value from `NestedDict`.

        Args:
            name:

        Examples:
            >>> d = NestedDict({"i.d": 1016, "f.n": "chang"})
            >>> d.i.d
            1016
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

        separator = self.getattr("separator", ".")
        try:
            while isinstance(name, str) and separator in name:
                name, rest = name.split(separator, 1)
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

        Examples:
            >>> d = NestedDict({"i.d": 1016, "f.n": "chang", "n.a.b.c": 1}, default_factory=NestedDict)
            >>> d.pop('i.d')
            1016
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

        separator = self.getattr("separator", ".")
        try:
            while isinstance(name, str) and separator in name:
                name, rest = name.split(separator, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        if not isinstance(self, dict) or name not in self:
            if default is not Null:
                return default
            raise KeyError(name)
        return super().pop(name)

    def setdefault(  # type: ignore[override]  # pylint: disable=R0912,W0221
        self,
        name: Any,
        value: Any,
        convert_mapping: bool | None = None,
    ) -> Any:
        r"""
        Set default value for `NestedDict`.

        Args:
            name:
            value:
            convert_mapping: Whether to convert `Mapping` to `NestedDict`.
                Defaults to `self.getattr("convert_mapping", False)`.

        Examples:
            >>> d = NestedDict({"i.d": 1016, "f.n": "chang", "n.a.b.c": 1})
            >>> d.setdefault("d.i", 1031)
            1031
            >>> d.setdefault("i.d", "chang")
            1016
            >>> d.setdefault("f.n", 1016)
            'chang'
            >>> d.setdefault("n.a.b.d", 2)
            2
        """
        # pylint: disable=W0642

        full_name = name
        separator = self.getattr("separator", ".")
        if convert_mapping is None:
            convert_mapping = self.getattr("convert_mapping", False)
        default_factory = self.getattr("default_factory", self.empty) or self.empty
        try:
            while isinstance(name, str) and separator in name:
                name, rest = name.split(separator, 1)
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
                    default_factory = self.getattr("default_factory", self.empty) or self.empty
        except (AttributeError, TypeError):
            raise KeyError(name) from None

        if isinstance(self, NestedDict) and name in self:
            return super().get(name)
        elif isinstance(self, Mapping) and name in self:
            dict.__getitem__(self, name)

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
                f"Cannot set `{full_name}` to `{value}`, as `{separator.join(full_name.split(separator)[:-1])}={self}`."
            )
        return value

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

    def sort(self, key: Callable | None = None, reverse: bool = False, recursive: bool = True) -> Self:
        r"""
        Sort `NestedDict`.

        Args:
            recursive (bool): Whether to apply `sort` recursively.

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
            [1]
        """

        if recursive:
            for value in self.values():
                if isinstance(value, FlatDict):
                    value.sort(key=key, reverse=reverse)
        return super().sort(key=key, reverse=reverse)

    @staticmethod
    def _merge(this: FlatDict, that: Iterable, overwrite: bool = True) -> Mapping:
        if not that:
            return this
        if isinstance(that, Mapping):
            that = that.items()
        with this.converting() if isinstance(this, NestedDict) else nullcontext():
            for key, value in that:
                if key in this and isinstance(this[key], Mapping):
                    if isinstance(value, Mapping):
                        NestedDict._merge(this[key], value, overwrite)
                    elif overwrite:
                        if isinstance(this, NestedDict):
                            this.set(key, value)
                        else:
                            this[key] = value
                elif key in dir(this) and isinstance(getattr(this.__class__, key, None), (property, cached_property)):
                    if isinstance(getattr(this, key, None), FlatDict):
                        getattr(this, key).merge(value, overwrite=overwrite)
                    else:
                        setattr(this, key, value)
                elif overwrite or key not in this:
                    if isinstance(this, NestedDict):
                        this.set(key, value)
                    else:
                        this[key] = value
        return this

    def intersect(self, other: Mapping | Iterable | PathStr, recursive: bool = True) -> Self:  # pylint: disable=W0221
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
        return self.empty(self._intersect(self, other, recursive))

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
    ) -> Self:
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
        return self.empty(self._difference(self, other, recursive))

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

    def __contains__(self, name: Any) -> bool:
        separator = self.getattr("separator", ".")
        try:
            while isinstance(name, str) and separator in name:
                name, rest = name.split(separator, 1)
                if super().__contains__(name):
                    self, name = self[name], rest  # pylint: disable=W0642
                else:
                    return False
            return super().__contains__(name)
        except (TypeError, KeyError):  # TypeError when name is not in self
            return False
