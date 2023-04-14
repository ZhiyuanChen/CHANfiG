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

from typing import Any, Callable, Optional

from .flat_dict import FlatDict
from .utils import Null


class DefaultDict(FlatDict):
    r"""
    `DefaultDict` inherits from `FlatDict` and incorporates support of `default_factory`
    in the same manner as `collections.defaultdict`.
    If `default_factory is not None`, the value will be set to `default_factory()`
    when you access a key that does not exist in `DefaultDict`.

    You may specify `DefaultDict(default_factory=FlatDict)` when creating `DefaultDict` or
    by calling `dict.setattr('default_factory', FlatDict)` for existing `DefaultDict` objects.

    Note that just like `collections.defaultdict`, `default_factory()` is called without any arguments.

    Attributes:
        default_factory: Default factory for defaultdict behavior.

    Raises:
        TypeError: If `default_factory` is not callable.

    ```python
    >>> d = DefaultDict(list)
    >>> d.a.append(1)
    >>> d.a
    [1]
    >>> d = DefaultDict([])
    Traceback (most recent call last):
    TypeError: `default_factory=[]` must be Callable, but got <class 'list'>.

    ```
    """

    default_factory: Optional[Callable] = None

    def __init__(self, default_factory: Optional[Callable] = None, *args, **kwargs) -> None:  # pylint: disable=W1113
        super().__init__(*args, **kwargs)
        if default_factory is not None:
            if callable(default_factory):
                self.setattr("default_factory", default_factory)
            else:
                raise TypeError(
                    f"`default_factory={default_factory}` must be Callable, but got {type(default_factory)}."
                )

    def __missing__(self, name: Any, default=Null) -> Any:  # pylint: disable=R1710
        if default is Null:
            if not self.hasattr("default_factory"):
                raise KeyError(name) from None
            default = self.getattr("default_factory")()
        if isinstance(default, FlatDict):
            default.__dict__.update(self.__dict__)
        super().set(name, default)
        return default

    def __repr__(self) -> str:
        if self.default_factory is None:
            return super().__repr__()
        super_repr = super().__repr__()[len(self.__class__.__name__) :]  # noqa: E203
        if len(super_repr) == 2:
            return f"{self.__class__.__name__}({self.default_factory}, )"
        return f"{self.__class__.__name__}({self.default_factory}," + super_repr[1:]

    def add(self, name: Any):
        r"""
        Add a new default factory to the dictionary.

        Args:
            name:

        Raises:
            ValueError: If `default_factory` is None.

        Examples:
        ```python
        >>> d = DefaultDict(default_factory=DefaultDict)
        >>> d.add('d')
        DefaultDict()
        >>> d.get('d')
        DefaultDict()
        >>> d['n'] = 'chang'
        >>> d.n
        'chang'
        >>> d.n = 'liu'
        >>> d['n']
        'liu'

        ```
        """
        if self.default_factory is None:
            raise ValueError("Cannot add to a DefaultDict with no default_factory")
        self[name] = self.default_factory()  # pylint: disable=E1102
        return self[name]
