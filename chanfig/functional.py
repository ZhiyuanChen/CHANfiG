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

from io import IOBase
from json import dumps as json_dumps
from os.path import splitext
from typing import Any

from yaml import dump as yaml_dump

from .flat_dict import FlatDict, to_dict
from .nested_dict import NestedDict
from .utils import JSON, YAML, File, PathStr


def save(obj, file: File, method: str | None = None, *args: Any, **kwargs: Any) -> None:  # pylint: disable=W1113
    r"""
    Save `FlatDict` to file.

    Raises:
        ValueError: If save to `IO` and `method` is not specified.
        TypeError: If save to unsupported extension.

    **Alias**:

    + `save`

    Examples:
        >>> obj = {"a": 1, "b": 2, "c": 3}
        >>> save(obj, "test.yaml")
        >>> save(obj, "test.json")
        >>> save(obj, "test.conf")
        Traceback (most recent call last):
        TypeError: `file='test.conf'` should be in ('json',) or ('yml', 'yaml'), but got conf.
        >>> with open("test.yaml", "w") as f:
        ...     save(obj, f)
        Traceback (most recent call last):
        ValueError: `method` must be specified when saving to IO.
    """

    if isinstance(obj, FlatDict):
        return obj.save(file, method, *args, **kwargs)

    data = to_dict(obj)
    if method is None:
        if isinstance(file, IOBase):
            raise ValueError("`method` must be specified when saving to IO.")
        method = splitext(file)[-1][1:]  # type: ignore
    extension = method.lower()  # type: ignore
    if extension in YAML:
        with FlatDict.open(file, mode="w") as fp:  # pylint: disable=C0103
            yaml_dump(data, fp, *args, **kwargs)
        return
    if extension in JSON:
        with FlatDict.open(file, mode="w") as fp:  # pylint: disable=C0103
            fp.write(json_dumps(data, *args, **kwargs))
        return
    raise TypeError(f"`file={file!r}` should be in {JSON} or {YAML}, but got {extension}.")  # type: ignore


def load(file: PathStr, cls: type = NestedDict, *args: Any, **kwargs: Any) -> NestedDict:  # pylint: disable=W1113
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
