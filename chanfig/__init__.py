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

from yaml import add_representer
from yaml.representer import SafeRepresenter

from . import utils
from ._version import __version__, __version_tuple__, version
from .config import Config
from .default_dict import DefaultDict
from .flat_dict import FlatDict, to_dict
from .functional import load, save
from .nested_dict import NestedDict, apply, apply_
from .parser import ConfigParser
from .registry import GlobalRegistry, Registry
from .variable import Variable

__all__ = [
    "Variable",
    "Config",
    "NestedDict",
    "FlatDict",
    "Registry",
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


add_representer(FlatDict, SafeRepresenter.represent_dict)
add_representer(NestedDict, SafeRepresenter.represent_dict)
add_representer(DefaultDict, SafeRepresenter.represent_dict)
add_representer(Config, SafeRepresenter.represent_dict)
SafeRepresenter.add_representer(FlatDict, SafeRepresenter.represent_dict)
SafeRepresenter.add_representer(NestedDict, SafeRepresenter.represent_dict)
SafeRepresenter.add_representer(DefaultDict, SafeRepresenter.represent_dict)
SafeRepresenter.add_representer(Config, SafeRepresenter.represent_dict)
