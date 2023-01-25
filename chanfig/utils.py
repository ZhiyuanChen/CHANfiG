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
from typing import Any

from yaml import SafeDumper, SafeLoader

from .variable import Variable


class FileError(ValueError):
    """
    Error for file operations.
    """


class JsonEncoder(JSONEncoder):
    """
    JSON encoder for Config.
    """

    def default(self, o: Any) -> Any:
        if isinstance(o, Variable):
            return o.value
        if hasattr(o, "__json__"):
            return o.__json__()
        return super().default(o)


class YamlDumper(SafeDumper):
    """
    YAML Dumper for Config.
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False):  # pylint: disable=W0235
        return super().increase_indent(flow, indentless)


class YamlLoader(SafeLoader):  # pylint: disable=R0901
    """
    YAML Loader for Config.
    """
