# CHANfiG
# Copyright (C) 2022-Present, DanLing Team

# This file is part of CHANfiG.

# CHANfiG is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0

# CHANfiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from __future__ import annotations

import os
from io import IOBase
from json import JSONEncoder
from json import dumps as json_dumps
from os import PathLike
from os.path import splitext
from typing import IO, Any, Union

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml.constructor import ConstructorError
from yaml.nodes import ScalarNode, SequenceNode

PathStr = Union[PathLike, str, bytes]
File = Union[PathStr, IO, IOBase]

YAML_EXTENSIONS = ("yml", "yaml")
JSON_EXTENSIONS = ("json",)
PYTHON_EXTENSIONS = ("py",)


class JsonEncoder(JSONEncoder):
    r"""
    JSON encoder for Config.
    """

    def default(self, o: Any) -> Any:
        if hasattr(o, "__json__"):
            return o.__json__()
        if hasattr(o, "to_dict"):
            return o.to_dict()
        return super().default(o)


class YamlDumper(SafeDumper):  # pylint: disable=R0903
    r"""
    YAML Dumper for Config.
    """

    def increase_indent(self, flow: bool = False, indentless: bool = False):  # pylint: disable=W0235
        return super().increase_indent(flow, indentless)


class YamlLoader(SafeLoader):
    r"""
    YAML Loader for Config.
    """

    def __init__(self, stream):
        super().__init__(stream)
        self._root = os.path.abspath(os.path.dirname(stream.name)) if hasattr(stream, "name") else os.getcwd()
        self.add_constructor("!include", self._include)
        self.add_constructor("!includes", self._includes)
        self.add_constructor("!env", self._env)

    @staticmethod
    def _include(loader: YamlLoader, node):
        relative_path = loader.construct_scalar(node)
        include_path = os.path.join(loader._root, relative_path)

        if not os.path.exists(include_path):
            raise FileNotFoundError(f"Included file not found: {include_path}")

        return load(include_path)

    @staticmethod
    def _includes(loader: YamlLoader, node):
        if not isinstance(node, SequenceNode):
            raise ConstructorError(None, None, f"!includes tag expects a sequence, got {node.id}", node.start_mark)
        files = loader.construct_sequence(node)
        return [YamlLoader._include(loader, ScalarNode("tag:yaml.org,2002:str", file)) for file in files]

    @staticmethod
    def _env(loader: YamlLoader, node):
        env_var = loader.construct_scalar(node)
        value = os.getenv(env_var)
        if value is None:
            raise ValueError(f"Environment variable '{env_var}' not set.")
        return value


# Merged functions from functional.py
def save(  # pylint: disable=W1113
    obj, file: File, method: str = None, *args: Any, **kwargs: Any  # type: ignore[assignment]
) -> None:
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
    # Import FlatDict here to avoid circular imports
    from .flat_dict import FlatDict, to_dict

    if isinstance(obj, FlatDict):
        obj.save(file, method, *args, **kwargs)
        return

    data = to_dict(obj)
    if method is None:
        if isinstance(file, IOBase):
            raise ValueError("`method` must be specified when saving to IO.")
        method = splitext(file)[-1][1:]
    extension = method.lower()
    if extension in YAML_EXTENSIONS:
        with FlatDict.open(file, mode="w") as fp:  # pylint: disable=C0103
            yaml_dump(data, fp, *args, **kwargs)
        return
    if extension in JSON_EXTENSIONS:
        with FlatDict.open(file, mode="w") as fp:  # pylint: disable=C0103
            fp.write(json_dumps(data, *args, **kwargs))
        return
    raise TypeError(f"`file={file!r}` should be in {JSON_EXTENSIONS} or {YAML_EXTENSIONS}, but got {extension}.")


def load(file: PathStr, cls=None, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=W1113
    r"""
    Load a file into a `FlatDict`.

    This function simply calls `cls.load`, by default, `cls` is `NestedDict`.

    Args:
        file: The file to load.
        cls: The class of the file to load. Defaults to `NestedDict`.
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
    # Import here to avoid circular imports
    from .nested_dict import NestedDict

    if cls is None:
        cls = NestedDict

    return cls.load(file, *args, **kwargs)
