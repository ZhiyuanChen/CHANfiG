# CHANfiG, Easier Configuration.
# Copyright (c) 2022-2023, CHANfiG Contributors
# This program is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - Unlicense
# - GNU GPL 2.0 (or any later version)
# - MIT
# - Apache 2.0
# - BSD 2-Clause
# - BSD 3-Clause
# - BSD 4-Clause
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from __future__ import annotations

from functools import wraps
from os import PathLike
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Mapping
from warnings import warn

from .default_dict import DefaultDict
from .utils import _K, _V, Null, PathStr, apply, apply_
from .variable import Variable

if TYPE_CHECKING:
    from torch import device as TorchDevice
    from torch import dtype as TorchDtype


class NestedDict(DefaultDict[_K, _V]):  # pylint: disable=E1136
    r"""
    `NestedDict` further extends `DefaultDict` object by introducing a nested structure with `delimiter`.
    By default, `delimiter` is `.`, but it could be modified in subclass or by calling `dict.setattr('delimiter', D)`.

    `d = NestedDict({"a.b.c": 1})` is equivalent to `d = NestedDict({"a": {"b": {"c": 1}}})`,
    and you can access members either by `d["a.b.c"]` or more simply by `d.a.b.c`.

    This behavior allows you to pass keyword arguments to other function as easy as `func1(**d.func1)`.

    Since `NestedDict` inherits from `DefaultDict`, it also supports `default_factory`.
    With `default_factory`, you can assign `d.a.b.c = 1` without assign `d.a = NestedDict()` in the first place.
    Note that the constructor of `NestedDict` is different from `DefaultDict`, `default_factory` is not a positional
    argument, and must be set in a keyword argument.

    `NestedDict` also introduce `all_keys`, `all_values`, `all_items` methods to get all keys, values, items
    respectively in the nested structure.

    Attributes:
        convert_mapping: bool = False
            If `True`, all new values with a type of `Mapping` will be converted to `default_factory`.
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

    def __init__(self, *args, default_factory: Callable | None = None, **kwargs) -> None:
        super().__init__(default_factory)
        self.merge(*args, **kwargs)

    def all_keys(self) -> Iterator:
        r"""
        Get all keys of `NestedDict`.

        Returns:
            (Iterator):

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

    def all_values(self) -> Iterator:
        r"""
        Get all values of `NestedDict`.

        Returns:
            (Iterator):

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

    def all_items(self) -> Iterator[tuple]:
        r"""
        Get all items of `NestedDict`.

        Returns:
            (Iterator):

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

    def apply(self, func: Callable, *args, **kwargs) -> NestedDict:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for non-in-place modification of `obj`, for example, [`to`][chanfig.NestedDict.to].

        Args:
            func(Callable):

        See Also:
            [`apply_`][chanfig.NestedDict.apply_]: Apply a in-place operation.

            [`apply`][chanfig.utils.apply]: implementation of `apply` method.

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

    def apply_(self, func: Callable, *args, **kwargs) -> NestedDict:
        r"""
        Recursively apply a function to `NestedDict` and its children.

        Note:
            This method is meant for in-place modification of `obj`, for example, [`freeze`][chanfig.Config.freeze].

        Args:
            func(Callable):

        See Also:
            [`apply`][chanfig.NestedDict.apply]: Apply a non-in-place operation.

            [`apply_`][chanfig.utils.apply_]: implementation of `apply_` method.

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

    def get(self, name: Any, default: Any = Null) -> Any:
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
            >>> d.get('e.f')
            Traceback (most recent call last):
            KeyError: 'f'
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
            convert_mapping: Whether convert mapping to NestedDict.
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
            convert_mapping = self.convert_mapping
        delimiter = self.getattr("delimiter", ".")
        default_factory = self.getattr("default_factory", self.empty)
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                default_factory = self.getattr("default_factory", self.empty)
                if name in dir(self) and isinstance(getattr(self.__class__, name), property):
                    self, name = getattr(self, name), rest
                elif name not in self:
                    self, name = self.__missing__(name, default_factory()), rest
                else:
                    self, name = self[name], rest
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        if convert_mapping and isinstance(value, Mapping):
            value = default_factory(value)
        if isinstance(self, Mapping):
            if not isinstance(self, NestedDict):
                dict.__setitem__(self, name, value)
            else:
                super().set(name, value)
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
        """

        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                self, name = self[name], rest  # pylint: disable=W0642
        except (AttributeError, TypeError):
            raise KeyError(name) from None
        super().delete(name)

    def validate(self) -> None:
        r"""
        Validate if all `Variable` in `NestedDict` are valid.

        Raises:
            TypeError: If `Variable` has invalid type.
            ValueError: If `Variable` has invalid value.

        Examples:
            >>> d = NestedDict({"i.d": Variable(1016, type=int, validator=lambda x: x > 0)})
            >>> d.validate()
            >>> d = NestedDict({"i.d": Variable(1016, type=str, validator=lambda x: x > 0)})
            >>> d.validate()
            Traceback (most recent call last):
            TypeError: 'i.d' has invalid type. Value 1016 is not of type <class 'str'>.
            >>> d = NestedDict({"i.d": Variable(-1, type=int, validator=lambda x: x > 0)})
            >>> d.validate()
            Traceback (most recent call last):
            ValueError: 'i.d' has invalid value. Value -1 is not valid.
        """

        for name, value in self.all_items():
            if isinstance(value, Variable):
                try:
                    value.validate()
                except TypeError as exc:
                    raise TypeError(f"'{name}' has invalid type. {exc}") from None
                except ValueError as exc:
                    raise ValueError(f"'{name}' has invalid value. {exc}") from None

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

    def merge(self, *args, **kwargs) -> NestedDict:
        r"""
        Merge another container into `NestedDict`.

        Args:
            *args: `Mapping` or `Iterable` to merge.
            convert_mapping: Whether to convert `Mapping` to `NestedDict`.
            **kwargs: `Mapping` to merge.

        Returns:
            self:

        **Alias**:

        + `union`

        Examples:
            >>> d = NestedDict({'a': 1, 'b.c': 2, 'b.d': 3, 'c.d.e': 4, 'c.d.f': 5, 'c.e': 6})
            >>> n = {'b': {'c': 3, 'd': 5}, 'c.d.e': 4, 'c.d': {'f': 5}, 'd': 0}
            >>> d.merge(n).dict()
            {'a': 1, 'b': {'c': 3, 'd': 5}, 'c': {'d': {'e': 4, 'f': 5}, 'e': 6}, 'd': 0}
            >>> NestedDict(a=1, b=1, c=1).union(NestedDict(b='b', c='c', d='d')).dict()  # alias
            {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
        """

        @wraps(self.merge)
        def merge(this: NestedDict, that: Iterable) -> Mapping:
            if isinstance(that, Mapping):
                that = that.items()
            for key, value in that:
                if key in this and isinstance(this[key], Mapping):
                    if isinstance(value, Mapping):
                        merge(this[key], value)
                    else:
                        this.set(key, value, convert_mapping=True)
                else:
                    this.set(key, value, convert_mapping=True)
            return this

        if len(args) == 1:
            args = args[0]
            if isinstance(args, (PathLike, str, bytes)):
                args = self.load(args)  # type: ignore
                warn(
                    "merge file is deprecated and maybe removed in a future release. Use `merge_from_file` instead.",
                    PendingDeprecationWarning,
                )
            merge(self, args)
        else:
            merge(self, args)
        merge(self, kwargs.items())
        return self

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
            >>> d.intersect("example.yaml").dict()
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
            other = self.empty_like(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")

        @wraps(self.intersect)
        def intersect(this: NestedDict, that: Iterable) -> Mapping:
            ret = {}
            for key, value in that:
                if key in this:
                    if isinstance(this[key], NestedDict) and isinstance(value, Mapping) and recursive:
                        intersects = this[key].intersect(value)
                        if intersects:
                            ret[key] = intersects
                    elif this[key] == value:
                        ret[key] = value
            return ret

        return self.empty_like(intersect(self, other))  # type: ignore

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
            >>> d.difference("example.yaml").dict()
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
            other = self.empty_like(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")

        @wraps(self.difference)
        def difference(this: NestedDict, that: Iterable) -> Mapping:
            ret = {}
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

        return self.empty_like(difference(self, other))  # type: ignore

    def to(self, cls: str | TorchDevice | TorchDtype) -> Any:
        r"""
        Convert values of `NestedDict` to target `cls`.

        Args:
            cls (str | torch.device | torch.dtype):

        Examples:
            >>> import torch
            >>> d = NestedDict({'i.d': torch.tensor(1013), 'f.n': 'chang'})
            >>> d.cpu().dict()
            {'i': {'d': tensor(1013)}, 'f': {'n': 'chang'}}
        """

        def to(obj: Any) -> Any:  # pylint: disable=C0103
            if hasattr(obj, "to"):
                return obj.to(cls)
            return obj

        return self.apply(to)

    def dropnull(self) -> NestedDict:
        r"""
        Drop key-value pairs with `Null` value.

        Returns:
            (NestedDict):

        Examples:
            >>> d = NestedDict({"a.b": Null, "b.c.d": Null, "b.c.e.f": Null, "c.d.e.f": Null, "h.j": 1})
            >>> d.dict()
            {'a': {'b': Null}, 'b': {'c': {'d': Null, 'e': {'f': Null}}}, 'c': {'d': {'e': {'f': Null}}}, 'h': {'j': 1}}
            >>> d.dropnull().dict()
            {'h': {'j': 1}}
        """

        return NestedDict({k: v for k, v in self.all_items() if v is not Null})

    def __contains__(self, name: Any) -> bool:  # type: ignore
        delimiter = self.getattr("delimiter", ".")
        try:
            while isinstance(name, str) and delimiter in name:
                name, rest = name.split(delimiter, 1)
                self, name = self[name], rest  # pylint: disable=W0642
            return super().__contains__(name)
        except (TypeError, KeyError):  # TypeError when name is not in self
            return False
