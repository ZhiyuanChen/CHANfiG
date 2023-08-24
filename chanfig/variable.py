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

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from copy import copy
from typing import Any, Generic, List, Optional, TypeVar

from .utils import Null

V = TypeVar("V")


class Variable(Generic[V]):  # pylint: disable=R0902
    r"""
    Mutable wrapper for immutable objects.

    Args:
        value: The value to wrap.
        type: Desired type of the value.
        choices: Possible values of the value.
        validator: `Callable` that validates the value.
        required: Whether the value is required.
        help: Help message of the value.

    Raises:
        RuntimeError: If `required` is `True` and `value` is `Null`.
        TypeError: If `type` is specified and `value` is not an instance of `type`.
        ValueError: |
            If `choices` is specified and `value` is not in `choices`.
            If `validator` is specified and `validator` returns `False`.

    Attributes:
        value: The wrapped value.
        dtype: The type of the wrapped value.

    Notes:
        `Variable` by default wrap the instance type to type of the wrapped object.
        Therefore, `isinstance(Variable(1), int)` will return `True`.

        To temporarily disable this behaviour, you can call context manager `with Variable.unwrapped()`.

        To permanently disable this behaviour, you can call `Variable.unwrap()`.

    Examples:
        >>> v = Variable(1)
        >>> n = v
        >>> v, n
        (1, 1)
        >>> v += 1
        >>> v, n
        (2, 2)
        >>> v.value = 3
        >>> v, n
        (3, 3)
        >>> n.set(4)
        >>> v, n
        (4, 4)
        >>> n = 5
        >>> v, n
        (4, 5)
        >>> f'{v} < {n}'
        '4 < 5'
        >>> isinstance(v, int)
        True
        >>> type(v)
        <class 'chanfig.variable.Variable'>
        >>> v.dtype
        <class 'int'>
        >>> with v.unwrapped():
        ...    isinstance(v, int)
        False
        >>> v = Variable('hello')
        >>> f'{v}, world!'
        'hello, world!'
        >>> v += ', world!'
        >>> v
        'hello, world!'
        >>> "hello" in v
        True
    """

    wrap_type: bool = True
    _storage: List[Any]
    _type: Optional[type] = None
    _choices: Optional[list] = None
    _validator: Optional[Callable] = None
    _required: bool = False
    _help: Optional[str] = None

    def __init__(  # pylint: disable=R0913
        self,
        value: Any = Null,
        type: type | None = None,  # pylint: disable=W0622
        choices: list | None = None,
        validator: Callable | None = None,
        required: bool = False,
        help: str | None = None,  # pylint: disable=W0622
    ) -> None:
        self._storage = [value]
        self._type = type
        self._choices = choices
        self._validator = validator
        self._required = required
        self._help = help

    @property  # type: ignore
    def __class__(self) -> type:
        return self.value.__class__ if self.wrap_type else type(self)

    @property
    def value(self) -> Any:
        r"""
        Fetch the object wrapped in `Variable`.
        """

        return self._storage[0]

    @value.setter
    def value(self, value) -> None:
        r"""
        Assign value to the object wrapped in `Variable`.
        """

        self.validate(value)
        self._storage[0] = self._get_value(value)

    @property
    def dtype(self) -> type:
        r"""
        Data type of the object wrapped in `Variable`.

        Examples:
            >>> id = Variable(1013)
            >>> type(id)
            <class 'chanfig.variable.Variable'>
            >>> id.dtype
            <class 'int'>
            >>> issubclass(id.dtype, int)
            True
        """

        return self.value.__class__

    @property
    def storage(self) -> list[Any]:
        r"""
        Storage of `Variable`.
        """

        return self._storage

    @property
    def type(self) -> type | None:
        return self._type

    @property
    def choices(self) -> list | None:
        return self._choices

    @property
    def validator(self) -> Callable | None:
        return self._validator

    @property
    def required(self) -> bool:
        return self._required

    @property
    def help(self) -> str:
        return self._help or ""

    def validate(self, *args) -> None:
        r"""
        Validate if the value is valid.
        """

        if len(args) == 0:
            value = self.value
        elif len(args) == 1:
            value = args[0]
        else:
            raise ValueError("Too many arguments.")
        if self._required and value is Null:
            raise RuntimeError("Value is required.")
        if self._type is not None and not isinstance(value, self._type):
            raise TypeError(f"Value {value} is not of type {self._type}.")
        if self._choices is not None and value not in self._choices:
            raise ValueError(f"Value {value} is not in choices {self._choices}.")
        if self._validator is not None and not self._validator(value):
            raise ValueError(f"Value {value} is not valid.")

    def get(self) -> Any:
        r"""
        Fetch the object wrapped in `Variable`.
        """

        return self.value

    def set(self, value) -> None:
        r"""
        Assign value to the object wrapped in `Variable`.

        `Variable.set` is extremely useful when you want to change the value without changing the reference.

        In `FlatDict.set`, all assignments of `Variable` calls `Variable.set` Internally.
        """

        self.value = value

    def __get__(self, obj, objtype=None):
        return self

    def __set__(self, obj, value):
        self.value = value

    def to(self, cls: Callable) -> Any:  # pylint: disable=C0103
        r"""
        Convert the object wrapped in `Variable` to target `cls`.

        Args:
            cls: The type to convert to.

        Examples:
            >>> id = Variable(1013)
            >>> id.to(float)
            1013.0
            >>> id.to(str)
            '1013.0'
        """

        self.value = cls(self.value)
        return self

    def int(self) -> int:
        r"""
        Convert the object wrapped in `Variable` to python `int`.

        Examples:
            >>> id = Variable(1013.0)
            >>> id.int()
            1013
        """

        return self.to(int)

    def float(self) -> float:
        r"""
        Convert the object wrapped in `Variable` to python `float`.

        Examples:
            >>> id = Variable(1013)
            >>> id.float()
            1013.0
        """

        return self.to(float)

    def str(self) -> str:
        r"""
        Convert the object wrapped in `Variable` to python `float`.

        Examples:
            >>> id = Variable(1013)
            >>> id.str()
            '1013'
        """

        return self.to(str)

    def wrap(self) -> None:
        r"""
        Wrap the type of `Variable`.

        Examples:
            >>> id = Variable(1013)
            >>> id.unwrap()
            >>> isinstance(id, int)
            False
            >>> id.wrap()
            >>> isinstance(id, int)
            True
        """

        self.wrap_type = True

    def unwrap(self) -> None:
        r"""
        Unwrap the type of `Variable`.

        Examples:
            >>> id = Variable(1013)
            >>> id.unwrap()
            >>> isinstance(id, int)
            False
        """

        self.wrap_type = False

    @contextmanager
    def unwrapped(self):
        r"""
        Context manager which temporarily unwrap the `Variable`.

        Examples:
            >>> id = Variable(1013)
            >>> isinstance(id, int)
            True
            >>> with id.unwrapped():
            ...    isinstance(id, int)
            False
        """

        wrap_type = self.wrap_type
        self.wrap_type = False
        try:
            yield self
        finally:
            self.wrap_type = wrap_type

    @staticmethod
    def _get_value(obj) -> Any:
        if isinstance(obj, Variable):
            return obj.value
        return obj

    def __getattr__(self, attr) -> Any:
        return getattr(self.value, attr)

    def __lt__(self, other) -> bool:
        return self.value < self._get_value(other)

    def __le__(self, other) -> bool:
        return self.value <= self._get_value(other)

    def __eq__(self, other) -> bool:
        return self.value == self._get_value(other)

    def __ne__(self, other) -> bool:
        return self.value != self._get_value(other)

    def __ge__(self, other) -> bool:
        return self.value >= self._get_value(other)

    def __gt__(self, other) -> bool:
        return self.value > self._get_value(other)

    def __index__(self):
        return self.value.__index__()

    def __invert__(self):
        return ~self.value

    def __abs__(self):
        return abs(self.value)

    def __add__(self, other):
        return Variable(self.value + self._get_value(other))

    def __radd__(self, other):
        return Variable(self._get_value(other) + self.value)

    def __iadd__(self, other):
        self.value += self._get_value(other)
        return self

    def __and__(self, other):
        return Variable(self.value & self._get_value(other))

    def __rand__(self, other):
        return Variable(self._get_value(other) & self.value)

    def __iand__(self, other):
        self.value &= self._get_value(other)
        return self

    def __floordiv__(self, other):
        return Variable(self.value // self._get_value(other))

    def __rfloordiv__(self, other):
        return Variable(self._get_value(other) // self.value)

    def __ifloordiv__(self, other):
        self.value //= self._get_value(other)
        return self

    def __mod__(self, other):
        return Variable(self.value % self._get_value(other))

    def __rmod__(self, other):
        return Variable(self._get_value(other) % self.value)

    def __imod__(self, other):
        self.value %= self._get_value(other)
        return self

    def __mul__(self, other):
        return Variable(self.value * self._get_value(other))

    def __rmul__(self, other):
        return Variable(self._get_value(other) * self.value)

    def __imul__(self, other):
        self.value *= self._get_value(other)
        return self

    def __matmul__(self, other):
        return Variable(self.value @ self._get_value(other))

    def __rmatmul__(self, other):
        return Variable(self._get_value(other) @ self.value)

    def __imatmul__(self, other):
        self.value @= self._get_value(other)
        return self

    def __pow__(self, other):
        return Variable(self.value ** self._get_value(other))

    def __rpow__(self, other):
        return Variable(self._get_value(other) ** self.value)

    def __ipow__(self, other):
        self.value **= self._get_value(other)
        return self

    def __truediv__(self, other):
        return Variable(self.value / self._get_value(other))

    def __rtruediv__(self, other):
        return Variable(self._get_value(other) / self.value)

    def __itruediv__(self, other):
        self.value /= self._get_value(other)
        return self

    def __sub__(self, other):
        return Variable(self.value - self._get_value(other))

    def __rsub__(self, other):
        return Variable(self._get_value(other) - self.value)

    def __isub__(self, other):
        self.value -= self._get_value(other)
        return self

    def __copy__(self):
        return Variable(self.value)

    def __deepcopy__(self, memo: Mapping | None = None):
        return Variable(copy(self.value))

    def __format__(self, format_spec):
        return self.value if isinstance(self, str) else format(self.value, format_spec)

    def __iter__(self):
        return iter(self.value)

    def __next__(self):
        return next(self.value)

    def __hash__(self):
        return hash(self.value)

    def __repr__(self):
        return repr(self.value)

    def __str__(self):
        return self.value if isinstance(self, str) else str(self.value)

    def __json__(self):
        return self.value

    def __contains__(self, name):
        return name in self.value
