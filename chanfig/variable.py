from collections.abc import Mapping
from contextlib import contextmanager
from copy import copy
from typing import Any, Callable, List, Optional


class Variable:
    r"""
    Mutable wrapper for immutable objects.

    Example:
    ```python
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
    >>> v.set(4)
    >>> v, n
    (4, 4)
    >>> v = 5
    >>> v, n
    (5, 4)
    >>> f'4 < {v}'
    '4 < 5'
    >>> v = Variable('hello')
    >>> f'{v}, world!'
    'hello, world!'
    >>> v += ', world!'
    >>> v
    'hello, world!'

    ```
    """

    wrap_type: bool = True
    storage: List[Any]

    def __init__(self, value):
        self.storage = [value]

    @property  # type: ignore
    def __class__(self):
        return self.value.__class__ if self.wrap_type else type(self)

    @property
    def value(self):
        r"""
        Actual object stored in the Variable.
        """

        return self.storage[0]

    @value.setter
    def value(self, value):
        r"""
        Assign value to object stored in the Variable.
        """

        self.storage[0] = self._get_value(value)

    @property
    def dtype(self):
        r"""
        Data type of Variable.
        """

        return self.value.__class__

    def get(self):
        r"""
        alias of value.
        """

        return self.value

    def set(self, value):
        r"""
        alias of value.setter.
        """

        self.value = value

    @staticmethod
    def _get_value(obj):
        if isinstance(obj, Variable):
            return obj.value
        return obj

    def __getattr__(self, attr):
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

    def __index__(self) -> int:  # pylint: disable=E0601
        return int(self.value)

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

    def __deepcopy__(self, memo: Optional[Mapping] = None):
        return Variable(copy(self.value))

    def __format__(self, format_spec):
        return self.value if isinstance(self, str) else format(self.value, format_spec)

    def __repr__(self):
        return repr(self.value)

    def to(self, cls: Callable) -> Any:  # pylint: disable=C0103
        r"""
        Convert the value to a different type.

        `convert` is an alias of this method.

        Args:
            cls (Callable): The type to convert to.

        Example:
        ```python
        >>> id = Variable(1013)
        >>> id.to(float)
        1013.0
        >>> id.to(str)
        '1013.0'

        ```
        """

        self.value = cls(self.value)
        return self

    def int(self) -> int:
        r"""
        Convert the value to a python default int.

        Example:
        ```python
        >>> id = Variable(1013.0)
        >>> id.int()
        1013

        ```
        """

        return self.to(int)

    def float(self) -> float:
        r"""
        Convert the value to a python default float.

        Example:
        ```python
        >>> id = Variable(1013)
        >>> id.float()
        1013.0

        ```
        """

        return self.to(float)

    def str(self) -> str:
        r"""
        Convert the value to a python default float.

        Example:
        ```python
        >>> id = Variable(1013)
        >>> id.str()
        '1013'

        ```
        """

        return self.to(str)

    @contextmanager
    def unwraped(self):
        """
        Context manager which temporarily unwrap the Variable.

        Example:
        ```python
        >>> v = Variable(1)
        >>> isinstance(v, int)
        True
        >>> with v.unwraped():
        ...    isinstance(v, int)
        False

        ```
        """

        wrap_type = self.wrap_type
        self.wrap_type = False
        try:
            yield self
        finally:
            self.wrap_type = wrap_type
