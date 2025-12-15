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

from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from inspect import ismethod
from typing import Any, Sequence, Set


def to_dict(obj: Any, flatten: bool = False) -> Mapping | Sequence | Set:
    r"""
    Convert an object to a dict.

    Note that when converting a `set` object, it may be converted to a `tuple` object if its values is not hashable.

    Args:
        obj: Object to be converted.
        flatten: Whether to flatten nested structures.

    Examples:
        >>> from chanfig import FlatDict, Variable

        >>> to_dict(1)
        1
        >>> to_dict([1, 2, 3])
        [1, 2, 3]
        >>> to_dict((1, 2, 3))
        (1, 2, 3)
        >>> to_dict({1, 2, 3})
        {1, 2, 3}
        >>> to_dict({'a': 1, 'b': 2})
        {'a': 1, 'b': 2}
        >>> to_dict(Variable(1))
        1
        >>> to_dict(FlatDict(a=[[[[[FlatDict(b=1)]]]]]))
        {'a': [[[[[{'b': 1}]]]]]}
        >>> to_dict(FlatDict(a={FlatDict(b=1)}))
        {'a': ({'b': 1},)}
    """
    # Handle circular import
    from ..flat_dict import FlatDict
    from ..variable import Variable

    if flatten and isinstance(obj, FlatDict):
        return {k: to_dict(v) for k, v in obj.all_items()}
    if isinstance(obj, Mapping):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(to_dict(v) for v in obj)
    if isinstance(obj, set):
        try:
            return {to_dict(v) for v in obj}
        except TypeError:
            return tuple(to_dict(v) for v in obj)
    if isinstance(obj, Variable):
        return obj.value
    if is_dataclass(obj):
        return asdict(obj)  # type: ignore[arg-type]
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return obj


def to_chanfig(obj: Any, cls: type | None = None) -> Any:
    r"""
    Convert arbitrary data structure to CHANfiG objects when possible.

    This function recursively converts mappings to FlatDict instances
    and handles nested structures of arbitrary depth.

    Args:
        obj: Object to be converted.
        cls: Class to use for creating FlatDict instances. Defaults to `FlatDict`.

    Examples:
        >>> to_chanfig({'a': 1, 'b': 2})
        FlatDict(
          ('a'): 1
          ('b'): 2
        )
        >>> to_chanfig([1, 2, 3])
        [1, 2, 3]
        >>> to_chanfig([{'a': 1}, {'b': 2}])
        [FlatDict(('a'): 1), FlatDict(('b'): 2)]
        >>> to_chanfig([[1, 2], [3, 4]])
        FlatDict(
          (1): 2
          (3): 4
        )
        >>> to_chanfig([[1, 2, 3], [4, 5, 6]])
        [[1, 2, 3], [4, 5, 6]]
    """
    # Handle circular import
    from ..flat_dict import FlatDict

    if cls is None:
        cls = FlatDict

    if isinstance(obj, Mapping):
        result = cls()
        for k, v in obj.items():
            result[k] = to_chanfig(v, cls)
        return result
    if isinstance(obj, (list, tuple)) and all(isinstance(item, (list, tuple)) and len(item) == 2 for item in obj):
        try:
            result = cls()
            for k, v in obj:
                result[k] = to_chanfig(v, cls)
            return result
        except (ValueError, TypeError):
            pass
    if isinstance(obj, (list, tuple)):
        return type(obj)(to_chanfig(item, cls) for item in obj)
    if isinstance(obj, set):
        try:
            return {to_chanfig(item, cls) for item in obj}
        except TypeError:
            return tuple(to_chanfig(item, cls) for item in obj)
    return obj


def parse_bool(value: bool | str | int) -> bool:
    r"""
    Convert various types of values to boolean.

    This function converts different input types (bool, str, int) to their boolean equivalent.

    Examples:
        >>> parse_bool(True)
        True
        >>> parse_bool("yes")
        True
        >>> parse_bool(1)
        True
        >>> parse_bool(0)
        False
        >>> parse_bool("false")
        False
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        raise ValueError(f"Only 0 or 1 is allowed for boolean value, but got {value}.")
    if isinstance(value, str):
        if value.lower() in ("yes", "true", "t", "y", "1"):
            return True
        if value.lower() in ("no", "false", "f", "n", "0"):
            return False
    raise ValueError(f"Boolean value is expected, but got {value}.")


def apply(obj: Any, func: Callable, *args: Any, **kwargs: Any) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this method is meant for non-in-place modification of `obj` and should return the original object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    See Also:
        [`apply_`][chanfig.utils.apply.apply_]: Apply an in-place operation.
    """
    # Handle circular import
    from ..nested_dict import NestedDict

    is_method = ismethod(func)

    def _invoke(target):
        return func(*args, **kwargs) if is_method else func(target, *args, **kwargs)

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
            return tuple(apply(v, func, *args, **kwargs) for v in obj)
    return _invoke(obj)


def apply_(obj: Any, func: Callable, *args: Any, **kwargs: Any) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this method is meant for in-place modification of `obj` and should return the modified object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    See Also:
        [`apply`][chanfig.utils.apply.apply]: Apply a non-in-place operation.
    """
    # pylint: disable=C0103
    is_method = ismethod(func)

    def _invoke(target):
        return func(*args, **kwargs) if is_method else func(target, *args, **kwargs)

    if isinstance(obj, Mapping):
        for v in obj.values():
            apply_(v, func, *args, **kwargs)
    if isinstance(obj, (list, tuple, set)):
        for v in obj:
            apply_(v, func, *args, **kwargs)
    return _invoke(obj)
