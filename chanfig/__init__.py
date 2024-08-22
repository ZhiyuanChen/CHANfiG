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

from yaml import add_multi_representer
from yaml.representer import SafeRepresenter

try:
    from enum import StrEnum
except ImportError:
    StrEnum = None  # type: ignore

try:
    from strenum import LowercaseStrEnum
    from strenum import StrEnum as UppercaseStrEnum
except ImportError:
    UppercaseStrEnum = None
    LowercaseStrEnum = None

from . import utils
from ._version import __version__, __version_tuple__, version
from .config import Config
from .configclasses import configclass
from .default_dict import DefaultDict
from .flat_dict import FlatDict, to_dict
from .functional import load, save
from .nested_dict import NestedDict, apply, apply_
from .parser import ConfigParser
from .registry import ConfigRegistry, GlobalRegistry, Registry
from .variable import Variable

__all__ = [
    "Variable",
    "configclass",
    "Config",
    "NestedDict",
    "FlatDict",
    "Registry",
    "ConfigRegistry",
    "GlobalRegistry",
    "DefaultDict",
    "ConfigParser",
    "load",
    "save",
    "to_dict",
    "apply",
    "apply_",
    "utils",
    "version",
    "__version__",
    "__version_tuple__",
]


add_multi_representer(FlatDict, SafeRepresenter.represent_dict)
SafeRepresenter.add_multi_representer(FlatDict, SafeRepresenter.represent_dict)

if StrEnum is not None:
    add_multi_representer(StrEnum, SafeRepresenter.represent_str)
    SafeRepresenter.add_multi_representer(StrEnum, SafeRepresenter.represent_str)
if UppercaseStrEnum is not None:
    add_multi_representer(UppercaseStrEnum, SafeRepresenter.represent_str)
    SafeRepresenter.add_multi_representer(UppercaseStrEnum, SafeRepresenter.represent_str)
if LowercaseStrEnum is not None:
    add_multi_representer(LowercaseStrEnum, SafeRepresenter.represent_str)
    SafeRepresenter.add_multi_representer(LowercaseStrEnum, SafeRepresenter.represent_str)
