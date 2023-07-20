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

from typing import Any, Type

from .nested_dict import NestedDict
from .utils import PathStr


def load(file: PathStr, cls: Type = NestedDict, *args: Any, **kwargs: Any) -> NestedDict:
    r"""
    Load a file into a `NestedDict`.

    This function simply calls `NestedDict.load`.

    Args:
        file: The file to load.
        *args: The arguments to pass to `NestedDict.load`.
        **kwargs: The keyword arguments to pass to `NestedDict.load`.

    See Also:
        [`load`][chanfig.FlatDict.load]

    Examples:
        >>> from chanfig import load
        >>> config = load("tests/test.yaml")
        >>> config
        NestedDict(
          ('a'): 1
          ('b'): 2
          ('c'): 3
        )
    """

    return cls.load(file, *args, **kwargs)  # type: ignore
