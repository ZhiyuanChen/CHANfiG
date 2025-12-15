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

import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from functools import lru_cache, partial
from types import ModuleType
from typing import Any, Union, no_type_check

import typing_extensions
from typing_extensions import get_args, get_origin

try:  # python 3.10+
    from types import UnionType  # type: ignore[attr-defined] # pylint: disable=C0412
except ImportError:
    UnionType = Union  # type: ignore[misc, assignment]

GLOBAL_NS = {k: v for k, v in typing_extensions.__dict__.items() if not k.startswith("_")}
PY310_PLUS = sys.version_info >= (3, 10)


# flake8: noqa
@no_type_check
def get_annotations(  # pylint: disable=all
    obj, *, globalns: Mapping | None = None, localns: Mapping | None = None, eval_str: bool = True
) -> Mapping:
    r"""
    Compute the annotations dict for an object.

    obj may be a callable, class, or module.
    Passing in an object of any other type raises TypeError.

    Returns a dict.  get_annotations() returns a new dict every time
    it's called; calling it twice on the same object will return two
    different but equivalent dicts.

    This function handles several details for you:

      * If `eval_str` is true, values of type str will
        be un-stringized using `eval()`.  This is intended
        for use with stringized annotations
        (`from __future__ import annotations`).
      * `globalns` fall back to public member of `typing`.
      * If obj doesn't have an annotations dict, returns an
        empty dict.  (Functions and methods always have an
        annotations dict; classes, modules, and other types of
        callables may not.)
      * Ignores inherited annotations on classes.  If a class
        doesn't have its own annotations dict, returns an empty dict.
      * All accesses to object members and dict values are done
        using `getattr()` and `dict.get()` for safety.
      * Always, always, always returns a freshly-created dict.

    `eval_str` controls whether or not values of type str are replaced
    with the result of calling eval() on those values:

      * If `eval_str` is true, eval() is called on values of type str.
      * If `eval_str` is false (the default), values of type str are unchanged.

    `globalns` and `localns` are passed in to `eval()`; see the documentation
    for `eval()` for more information.

    `globalns` fall back to public member of `typing`.

    If either `globalns` or `localns` is
    None, this function may replace that value with a context-specific
    default, contingent on `type(obj)`:

      * If `obj` is a module, globalns defaults to `obj.__dict__`.
      * If `obj` is a class, globalns defaults to
        `sys.modules[obj.__module__].__dict__` and `localns`
        defaults to the obj class namespace.
      * If `obj` is a callable, `globalns` defaults to `obj.__globals__`,
        although if obj is a wrapped function (using
        functools.update_wrapper()) it is first unwrapped.
      * If `obj` is an instance, `globalns` defaults to
        `sys.modules[obj.__module__].__dict__` and localns
        defaults to the obj class namespace.
    """
    if isinstance(obj, type):
        # class
        annos = getattr(obj, "__annotations__", None)
        obj_globalns = None
        module_name = getattr(obj, "__module__", None)
        if module_name:
            module = sys.modules.get(module_name, None)
            if module:
                obj_globalns = getattr(module, "__dict__", None)
        obj_localns = dict(vars(obj))
        unwrap = obj
    elif isinstance(obj, ModuleType):
        # module
        annos = getattr(obj, "__annotations__", None)
        obj_globalns = getattr(obj, "__dict__")
        obj_localns = None
        unwrap = None
    elif callable(obj):
        # this includes types.Function, types.BuiltinFunctionType,
        # types.BuiltinMethodType, functools.partial, functools.singledispatch,
        # "class funclike" from Lib/test/test_inspect... on and on it goes.
        annos = getattr(obj, "__annotations__", None)
        obj_globalns = getattr(obj, "__globals__", None)
        obj_localns = None
        unwrap = obj
    else:
        # obj
        annos = getattr(type(obj), "__annotations__", None)
        obj_globalns = None
        module_name = getattr(obj, "__module__", None)
        if module_name:
            module = sys.modules.get(module_name, None)
            if module:
                obj_globalns = getattr(module, "__dict__", None)
        obj_localns = dict(vars(obj))
        unwrap = obj

    if annos is None or not annos:
        return {}

    if not isinstance(annos, dict):
        raise ValueError(f"{obj!r}.__annotations__ is neither a dict nor None")

    if unwrap is not None:
        while True:
            if hasattr(unwrap, "__wrapped__"):
                unwrap = unwrap.__wrapped__
                continue
            if isinstance(unwrap, partial):
                unwrap = unwrap.func
                continue
            break
        if hasattr(unwrap, "__globals__"):
            obj_globalns = unwrap.__globals__

    # globalns = GLOBAL_NS | globalns if globalns is not None else obj_globalns
    if globalns is None:
        globalns = obj_globalns
    globalns = {**GLOBAL_NS, **globalns}
    if localns is None:
        localns = obj_localns

    ret = {}
    for key, value in annos.items():
        if eval_str and isinstance(value, str):
            try:
                value = eval(value, globalns, localns)  # pylint: disable=W0123
            except NameError:
                raise ValueError(
                    f"Type annotation '{key}: {value}' in {obj!r} is invalid.\n"
                    "If you are running on an earlier version of Python, "
                    "please ensure annotations does not contain forward references."
                ) from None
            except TypeError:
                raise ValueError(
                    f"Type annotation '{key}: {value}' in {obj!r} is invalid.\n"
                    "If you are running on an earlier version of Python, "
                    "please ensure you are not using future features such as PEP604."
                ) from None
        ret[key] = value
    return ret


@lru_cache(maxsize=512)
def _cached_annotations_for_class(cls: type) -> Mapping:
    return get_annotations(cls)


def get_cached_annotations(obj) -> Mapping:
    """
    Lightweight cached wrapper around `get_annotations` keyed by class.

    The returned mapping is copied to preserve the original `get_annotations` contract
    of producing a fresh dict for each call.
    """

    try:
        cls = obj if isinstance(obj, type) else obj.__class__
    except Exception:
        return get_annotations(obj)
    try:
        cached = _cached_annotations_for_class(cls)
    except TypeError:
        return get_annotations(obj)
    return dict(cached)


def honor_annotation(data: Any, annotation: type) -> Any:
    r"""
    Attempt to convert data to match the expected type annotation.

    This function tries to honor the type annotation by converting the data
    when possible, rather than rejecting it. It works with:
    - Basic types (int, str, etc.)
    - Container types (List, Dict, etc.)
    - Union types (including Optional)
    - Nested generic types

    Unlike `conform_annotation` which validates type compatibility,
    this function tries to adapt the data to match the annotation.

    Examples:
        >>> honor_annotation("42", int)
        42
        >>> honor_annotation(42, str)
        '42'
        >>> honor_annotation("name", Union[int, str])
        'name'
        >>> honor_annotation(123, Union[int, str])
        123
    """
    if data is None or annotation is Any:
        return data
    origin_type = get_origin(annotation)
    arg_types = get_args(annotation)
    with suppress(Exception):
        if origin_type is Union or origin_type is UnionType:
            if any(conform_annotation(data, t) for t in arg_types):
                return data
            for t in arg_types:
                if t is not type(None):
                    with suppress(ValueError, TypeError):
                        return t(data)
            return data
        if origin_type is not None and arg_types:
            if issubclass(origin_type, tuple) and len(arg_types) == len(data):
                return origin_type(honor_annotation(item, arg) for item, arg in zip(data, arg_types))
            if isinstance(data, origin_type):
                if not data:
                    return data
                if origin_type is tuple and len(arg_types) > 1 and arg_types[-1] is not Ellipsis:
                    if len(data) == len(arg_types):
                        return tuple(honor_annotation(item, arg) for item, arg in zip(data, arg_types))
                    return data
                if issubclass(origin_type, Sequence) and not isinstance(data, str):
                    item_type = arg_types[0]
                    item_origin = get_origin(item_type)
                    item_args = get_args(item_type)
                    if item_origin is not None and item_args:
                        return origin_type([honor_annotation(item, item_type) for item in data])
                    return origin_type(honor_annotation(item, item_type) for item in data)
                if issubclass(origin_type, Mapping):
                    key_type, value_type = arg_types[:2]
                    return origin_type(
                        {honor_annotation(k, key_type): honor_annotation(v, value_type) for k, v in data.items()}
                    )
                if issubclass(origin_type, (set, frozenset)):
                    item_type = arg_types[0]
                    return origin_type(honor_annotation(item, item_type) for item in data)
            else:
                with suppress(ValueError, TypeError):
                    return origin_type(data)
            return data
        if isinstance(annotation, type) and not isinstance(data, annotation):
            with suppress(ValueError, TypeError):
                return annotation(data)
            return data
    return data


def conform_annotation(data: Any, annotation: type) -> bool:
    r"""
    Check if data is valid according to the expected type.

    This function handles complex type annotations including:
    - Basic types (int, str, etc.)
    - Container types (List, Dict, etc.)
    - Union types (including Optional)
    - Nested generic types
    """
    if annotation is Any:
        return True
    if annotation is type(None):
        return data is None
    origin_type = get_origin(annotation)
    arg_types = get_args(annotation)
    if origin_type in (Union, UnionType):
        return any(conform_annotation(data, arg_type) for arg_type in arg_types)
    if origin_type is Callable:
        return callable(data)
    if origin_type is not None and arg_types:
        if not isinstance(data, origin_type):
            return False
        if not data:
            return True
        if origin_type is tuple and len(arg_types) > 1 and arg_types[-1] is not Ellipsis:
            if len(data) != len(arg_types):
                return False
            return all(conform_annotation(item, type_) for item, type_ in zip(data, arg_types))
        if issubclass(origin_type, Sequence) and not isinstance(data, str):
            item_type = arg_types[0]
            return all(conform_annotation(item, item_type) for item in data)
        if issubclass(origin_type, Mapping):
            key_type, value_type = arg_types[:2]
            return all(conform_annotation(k, key_type) and conform_annotation(v, value_type) for k, v in data.items())
        if issubclass(origin_type, (set, frozenset)):
            item_type = arg_types[0]
            return all(conform_annotation(item, item_type) for item in data)
        return isinstance(data, origin_type)
    try:
        return isinstance(data, annotation)
    except TypeError:
        return False
