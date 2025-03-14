# CHANfiG, Easier Configuration.
# Copyright (c) 2022-Present, CHANfiG Contributors

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

import os
import sys
from argparse import ArgumentTypeError
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from io import IOBase
from json import JSONEncoder
from os import PathLike
from re import compile, findall  # pylint: disable=W0622
from types import GetSetDescriptorType, ModuleType
from typing import IO, Any, Union, no_type_check

import typing_extensions
from typing_extensions import get_args, get_origin
from yaml import SafeDumper, SafeLoader
from yaml.constructor import ConstructorError
from yaml.nodes import ScalarNode, SequenceNode

try:  # python 3.10+
    from types import UnionType  # type: ignore[attr-defined] # pylint: disable=C0412
except ImportError:
    UnionType = Union  # type: ignore[misc, assignment]

GLOBAL_NS = {k: v for k, v in typing_extensions.__dict__.items() if not k.startswith("_")}
PY310_PLUS = sys.version_info >= (3, 10)

PathStr = Union[PathLike, str, bytes]
File = Union[PathStr, IO, IOBase]

YAML = ("yml", "yaml")
JSON = ("json",)
PYTHON = ("py",)


# flake8: noqa
@no_type_check
def get_annotations(  # pylint: disable=all
    obj, *, globalns: Mapping | None = None, localns: Mapping | None = None, eval_str: bool = True
):
    """Compute the annotations dict for an object.

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


def honor_annotation(data: Any, annotation: type) -> Any:
    if data is None:
        return data
    origin_type = get_origin(annotation)
    arg_types = get_args(annotation)
    try:
        if origin_type is Union:
            if not any(isinstance(data, t) for t in arg_types if t is not type(None)):
                for t in arg_types:
                    if t is not type(None):
                        return t(data)
            return data
        if origin_type is not None and arg_types and not isinstance(data, origin_type):
            return origin_type(data)
        if isinstance(annotation, type) and not isinstance(data, annotation):
            return annotation(data)
    except (ValueError, TypeError):
        return data
    return data


@no_type_check
def isvalid(data: Any, expected_type: type) -> bool:
    if expected_type is Any:
        return True
    expected_origin = get_origin(expected_type)
    if expected_origin not in (
        Callable,
        GetSetDescriptorType,
        UnionType,
        Union,
        None,
    ):
        if issubclass(expected_origin, Sequence):
            inner_type = get_args(expected_type)[0]
            return isinstance(data, expected_origin) and all(isinstance(item, inner_type) for item in data)
        if issubclass(expected_origin, Mapping):
            key_type, value_type = get_args(expected_type)
            return isinstance(data, expected_origin) and all(
                isinstance(key, key_type) and isinstance(value, value_type) for key, value in data.items()
            )
        raise TypeError(f"Expected type {expected_type} is not supported.")
    if expected_origin is UnionType and not PY310_PLUS:
        return any(isinstance(data, inner_type) for inner_type in get_args(expected_type))
    return isinstance(data, expected_type)


class Dict(type(dict)):  # type: ignore[misc]
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # if hasattr(cls, '__before_init__'):
        #     cls.__before_init__()
        instance = super().__call__(*args, **kwargs)
        instance.__post_init__()
        instance.validate()
        return instance


class Singleton(type):
    r"""
    Metaclass for Singleton Classes.
    """

    __instances__: Mapping[type, object] = {}

    def __call__(cls, *args: Any, **kwargs: Any):
        if cls not in cls.__instances__:
            cls.__instances__[cls] = super().__call__(*args, **kwargs)  # type: ignore[index]
        return cls.__instances__[cls]


class NULL(metaclass=Singleton):
    r"""
    NULL class.

    `get` method in CHANfiG may accept `None` or `Ellipse`(`...`) as value of `default`.
    Therefore, it is mandatory to have a different default value for `default`.

    `Null` is an instance of `NULL` and is recommended to be used as `obj is Null`.
    """

    def __repr__(self):
        return "Null"

    def __nonzero__(self):
        return False

    def __len__(self):
        return 0

    def __call__(self, *args: Any, **kwargs: Any):
        return self

    def __contains__(self, name):
        return False

    def __iter__(self):
        return self

    def __next__(self):
        raise StopIteration

    def __getattr__(self, name):
        return self

    def __getitem__(self, index):
        return self


class JsonEncoder(JSONEncoder):
    r"""
    JSON encoder for Config.
    """

    def default(self, o: Any) -> Any:
        if hasattr(o, "__json__"):
            return o.__json__()
        return super().default(o)


class YamlDumper(SafeDumper):  # pylint: disable=R0903
    r"""
    YAML Dumper for Config.
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False):  # pylint: disable=W0235
        return super().increase_indent(flow, indentless)


class YamlLoader(SafeLoader):
    r"""
    YAML Loader for Config.
    """

    def __init__(self, stream):
        super().__init__(stream)
        self._root = os.path.abspath(os.path.dirname(stream.name)) if hasattr(stream, "name") else os.getcwd()
        self.add_constructor("!include", self._include)
        self.add_constructor("!includes", self._includes)
        self.add_constructor("!env", self._env)

    @staticmethod
    def _include(loader: YamlLoader, node):
        relative_path = loader.construct_scalar(node)
        include_path = os.path.join(loader._root, relative_path)

        if not os.path.exists(include_path):
            raise FileNotFoundError(f"Included file not found: {include_path}")
        from .functional import load

        return load(include_path)

    @staticmethod
    def _includes(loader: YamlLoader, node):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None, f"!includes tag expects a sequence, got {node.id}", node.start_mark)
        files = loader.construct_sequence(node)
        return [YamlLoader._include(loader, ScalarNode("tag:yaml.org,2002:str", file)) for file in files]

    @staticmethod
    def _env(loader: YamlLoader, node):
        env_var = loader.construct_scalar(node)
        value = os.getenv(env_var)
        if value is None:
            raise ValueError(f"Environment variable '{env_var}' not set.")
        return value


Null = NULL()

PLACEHOLDER_PATTERN = compile(r"\${([^}]*)}")


def find_placeholders(text: str) -> list[str]:
    if not isinstance(text, str):
        return []
    return findall(PLACEHOLDER_PATTERN, str(text))


def find_circular_reference(graph: Mapping) -> list[str] | None:
    def dfs(node, visited, path):  # pylint: disable=R1710
        path.append(node)
        if node in visited:
            return path
        visited.add(node)
        for child in graph.get(node, []):
            result = dfs(child, visited, path)
            if result is not None:
                return result
        visited.remove(node)

    for key in graph:
        result = dfs(key, set(), [])
        if result is not None:
            return result

    return None


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if value.lower() in ("yes", "true", "t", "y", "1"):
        return True
    if value.lower() in ("no", "false", "f", "n", "0"):
        return False
    raise ArgumentTypeError(f"Boolean value is expected, but got {value}.")
