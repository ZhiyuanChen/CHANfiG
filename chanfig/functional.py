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

from .nested_dict import NestedDict
from .utils import PathStr


def load(file: PathStr, *args, **kwargs) -> NestedDict:
    r"""
    Load a file into a `NestedDict`.

    This function simply calls `NestedDict.load`.

    Args:
        file: The file to load.
        *args: The arguments to pass to `NestedDict.load`.
        **kwargs: The keyword arguments to pass to `NestedDict.load`.

    See Also:
        [`chanfig.NestedDict.load`][chanfig.NestedDict.load]

    Examples:
        >>> from chanfig import load
        >>> config = load("example.yaml")
        >>> config
        NestedDict(
          ('a'): 1
          ('b'): 2
          ('c'): 3
        )
    """

    return NestedDict.load(file, *args, **kwargs)  # type: ignore
