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

from yaml import add_representer
from yaml.representer import SafeRepresenter

from . import utils
from ._version import __version__, __version_tuple__, version
from .config import Config, ConfigParser
from .default_dict import DefaultDict
from .flat_dict import FlatDict
from .nested_dict import NestedDict
from .registry import Registry
from .variable import Variable

__all__ = [
    "Variable",
    "Config",
    "NestedDict",
    "FlatDict",
    "Registry",
    "DefaultDict",
    "ConfigParser",
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
