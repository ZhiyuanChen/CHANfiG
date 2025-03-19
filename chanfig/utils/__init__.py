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

from .annotation import conform_annotation, get_annotations, honor_annotation
from .functional import apply, apply_, parse_bool, to_chanfig, to_dict
from .io import (
    JSON_EXTENSIONS,
    YAML_EXTENSIONS,
    File,
    JsonEncoder,
    PathStr,
    SafeDumper,
    SafeLoader,
    YamlDumper,
    YamlLoader,
    load,
    save,
)
from .null import NULL, Null
from .placeholder import find_circular_reference, find_placeholders

__all__ = [
    "get_annotations",
    "conform_annotation",
    "honor_annotation",
    "find_placeholders",
    "find_circular_reference",
    "NULL",
    "Null",
    "JsonEncoder",
    "YamlDumper",
    "YamlLoader",
    "SafeLoader",
    "SafeDumper",
    "JSON_EXTENSIONS",
    "YAML_EXTENSIONS",
    "File",
    "PathStr",
    "parse_bool",
    "to_dict",
    "to_chanfig",
    "apply",
    "apply_",
    "load",
    "save",
]
