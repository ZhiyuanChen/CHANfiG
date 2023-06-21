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

from argparse import _StoreAction
from inspect import ismethod
from json import JSONEncoder
from os import PathLike
from typing import IO, Any, Callable, Mapping, TypeVar, Union
from warnings import warn

from yaml import SafeDumper, SafeLoader

PathStr = Union[PathLike, str, bytes]
File = Union[PathStr, IO]

YAML = ("yml", "yaml")
JSON = ("json",)
PYTHON = ("py",)

_K = TypeVar("_K")
_V = TypeVar("_V")


def apply(obj: Any, func: Callable, *args, **kwargs) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this function is meant for non-in-place modification of `obj` and should return the original object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    Returns:
        (Any): Return value of `func`.

    See Also:
        [`apply_`][chanfig.utils.apply_]: Apply a in-place operation.
    """

    if isinstance(obj, Mapping):
        return type(obj)({k: apply(v, func, *args, **kwargs) for k, v in obj.items()})  # type: ignore
    if isinstance(obj, (list, tuple)):
        return type(obj)(apply(v, func, *args, **kwargs) for v in obj)  # type: ignore
    if isinstance(obj, set):
        try:
            return type(obj)(apply(v, func, *args, **kwargs) for v in obj)  # type: ignore
        except TypeError:
            tuple(apply(v, func, *args, **kwargs) for v in obj)  # type: ignore
    return func(*args, **kwargs) if ismethod(func) else func(obj, *args, **kwargs)


def apply_(obj: Any, func: Callable, *args, **kwargs) -> Any:
    r"""
    Apply `func` to all children of `obj`.

    Note that this function is meant for non-in-place modification of `obj` and should return a new object.

    Args:
        obj: Object to apply function.
        func: Function to be applied.
        *args: Positional arguments to be passed to `func`.
        **kwargs: Keyword arguments to be passed to `func`.

    Returns:
        (Any): Return value of `func`.

    See Also:
        [`apply_`][chanfig.utils.apply_]: Apply a in-place operation.
    """

    if isinstance(obj, Mapping):
        [apply_(v, func, *args, **kwargs) for v in obj.values()]  # type: ignore
    if isinstance(obj, (list, tuple, set)):
        [apply_(v, func, *args, **kwargs) for v in obj]  # type: ignore
    return func(*args, **kwargs) if ismethod(func) else func(obj, *args, **kwargs)


class Singleton(type):
    r"""
    Metaclass for Singleton Classes.
    """

    __instances__: Mapping[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances__:
            cls.__instances__[cls] = super().__call__(*args, **kwargs)
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

    def __call__(self, *args, **kwargs):
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


class YamlLoader(SafeLoader):  # pylint: disable=R0901,R0903
    r"""
    YAML Loader for Config.
    """


Null = NULL()


class StoreAction(_StoreAction):  # pylint: disable=R0903
    def __init__(  # pylint: disable=R0913
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=Null,
        type=None,  # pylint: disable=W0622
        choices=None,
        required=False,
        help=None,  # pylint: disable=W0622
        metavar=None,
    ):
        if dest is not None and type is not None:
            warn(f"type of argument {dest} is set to {type}, but CHANfiG will ignore it.")
            type = None
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )
        if self.default is not Null:
            warn(
                f"Default value for argument {self.dest} is set to {self.default}, "
                "Default value defined in argument will be overwritten by default value defined in Config",
            )
