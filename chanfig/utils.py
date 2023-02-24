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
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from json import JSONEncoder
from typing import Any, Mapping

from yaml import SafeDumper, SafeLoader

from .variable import Variable


class Singleton(type):
    r"""
    Metaclass for Singleton Classes.
    """

    __instances__: Mapping[type, object] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls.__instances__:
            cls.__instances__[cls] = super(Singleton, cls).__call__(*args, **kwargs)
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

    def __next__(self):  # pylint: disable=R0201
        raise StopIteration


class FileError(ValueError):
    r"""
    Error for file operations.
    """


class JsonEncoder(JSONEncoder):
    r"""
    JSON encoder for Config.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, Variable):
            return o.value
        if hasattr(o, "__json__"):
            return o.__json__()
        return super().default(o)


class YamlDumper(SafeDumper):
    r"""
    YAML Dumper for Config.
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False):  # pylint: disable=W0235
        return super().increase_indent(flow, indentless)


class YamlLoader(SafeLoader):  # pylint: disable=R0901
    r"""
    YAML Loader for Config.
    """


Null = NULL()
