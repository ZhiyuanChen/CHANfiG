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

from __future__ import annotations

from argparse import ArgumentParser
from contextlib import contextmanager
from functools import wraps
from sys import argv
from typing import Any, Callable, Iterable, Optional, Sequence
from warnings import warn

from .nested_dict import NestedDict
from .utils import Null


class ConfigParser(ArgumentParser):  # pylint: disable=C0115
    r"""
    Parser to parse command line arguments for CHANfiG.

    `ConfigParser` is a subclass of `argparse.ArgumentParser`.
    It provides a new `parse` method to parse command line arguments to `CHANfiG.Config` object.

    Different to `ArgumentParser.parse_args`, `ConfigParser.parse` will try to parse any command line arguments,
    even if they are not pre-defined by `ArgumentParser.add_argument`.
    This allows to relief the burden of adding tons of arguments for each tuneable parameter.
    In the meantime, there is no mechanism to notify you if you made a typo in command line arguments.

    Note that `ArgumentParser.parse_args` method is not overridden in `ConfigParser`.
    This is because it is still possible to construct `CHANfiG.Config` with `ArgumentParser.parse_args`,
    which has strict checking on command line arguments.
    """

    def parse(
        self,
        args: Optional[Sequence[str]] = None,
        config: Optional[Config] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        r"""
        Parse the arguments for `Config`.

        You may optionally specify a name for `default_config`,
        and CHANfiG will read the file under this name.

        There are three levels of config:

        1. The base `Config` parsed into the function,
        2. The base config file located at the path of `default_config` (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Args:
            args: The arguments to parse.
                Defaults to sys.argv[1:].
            config: The base `Config`.
            default_config: Path to the base config file.

        Returns:
            config: The parsed `Config`.

        Raises:
            ValueError: If `default_config` is specified but not found in args.

        Examples:
        ```python
        >>> p = ConfigParser()
        >>> p.parse(['--i.d', '1013', '--n.f', 'chang']).dict()
        {'i': {'d': 1013}, 'n': {'f': 'chang'}}

        # Values in command line arguments overrides values in `default_config` file.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2', '--config', 'example.yaml'], default_config='config').dict()
        {'a': 2, 'b': 2, 'c': 3, 'config': 'example.yaml'}

        # Values in `default_config` file overrides values in `Config` object.
        >>> c = Config(a=2)
        >>> c.parse(['--config', 'example.yaml'], default_config='config').dict()
        {'a': 1, 'b': 2, 'c': 3, 'config': 'example.yaml'}

        # ValueError will be raised when `default_config` name is specified but not presented in command line arguments.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2'], default_config='config').dict()
        Traceback (most recent call last):
        ValueError: default_config is set to config, but not found in args.

        ```
        """

        if args is None:
            args = argv[1:]
        for arg in args:
            if arg.startswith("--") and args != "--":
                arg = arg.split("=")[0]
                if arg not in self._option_string_actions:
                    self.add_argument(arg)
        if config is None:
            config = Config()
        parsed = vars(self.parse_args(args))

        # parse the config file
        if default_config is not None:
            if default_config in parsed:
                path = parsed[default_config]
                warn(f"Config has 'default_config={path}' specified, its values will override values in Config")
                # create a temp config to avoid issues when users inherit from Config
                config = config.update(Config.load(path))  # type: ignore
            else:
                raise ValueError(f"default_config is set to {default_config}, but not found in args.")

        # parse the command line arguments
        config = config.update(parsed)  # type: ignore
        return config  # type: ignore

    parse_config = parse

    @staticmethod
    def identity(string):
        r"""
        https://stackoverflow.com/questions/69896931/cant-pickle-local-object-argumentparser-init-locals-identity
        """

        return string


def frozen_check(func: Callable):
    r"""
    Decorator check if the object is frozen.
    """

    @wraps(func)
    def decorator(self, *args, **kwargs):
        if self.getattr("frozen", False):
            raise ValueError("Attempting to alter a frozen config. Run config.defrost() to defrost first.")
        return func(self, *args, **kwargs)

    return decorator


class Config(NestedDict):
    r"""
    `Config` is an extension of `NestedDict`.

    The differences between `Config` and `NestedDict` lies in 3 aspects:

    1. `Config` has `default_factory` set to `Config` and `convert_mapping` set to `True` by default.
    2. `Config` has a `frozen` attribute,
        which can be toggled with `freeze`(`lock`), `defrost`(`unlock`), and `unlocked`.
    3. `Config` has a `ConfigParser` built-in, and supports `add_argument` and `parse`.

    Notes:
        Since `Config` has `default_factory` set to `Config`,
        accessing anything that does not exist will create a new empty Config sub-attribute.

        A **frozen** `Config` does not have this behavior and
        will raises `KeyError` when accessing anything that does not exist.

        It is recommended to call `config.freeze()` or `config.to(NestedDict)` to avoid this behavior.

    Attributes:
        parser (ConfigParser): Parser for command line arguments.
        frozen (bool): If `True`, the config is frozen and cannot be altered.

    Examples:
    ```python
    >>> c = Config(**{"f.n": "chang"})
    >>> c.i.d = 1013
    >>> c.i.d
    1013
    >>> c.d.i
    Config()
    >>> c.freeze().dict()
    {'f': {'n': 'chang'}, 'i': {'d': 1013}, 'd': {'i': {}}}
    >>> c.d.i = 1013
    Traceback (most recent call last):
    ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
    >>> c.d.e
    Traceback (most recent call last):
    KeyError: 'Config does not contain e'
    >>> with c.unlocked():
    ...     del c.d
    >>> c.dict()
    {'f': {'n': 'chang'}, 'i': {'d': 1013}}

    ```
    """

    parser: ConfigParser
    frozen: bool = False

    def __init__(self, *args, **kwargs):
        if not self.hasattr("default_mapping"):
            self.setattr("default_mapping", Config)
        if "default_factory" not in kwargs:
            kwargs["default_factory"] = Config
        super().__init__(*args, **kwargs)
        self.setattr("parser", ConfigParser())

    def freeze(self, recursive: bool = True) -> Config:
        r"""
        Freeze `Config`.

        Args:
            recursive:

        **Alias**:

        + `lock`

        Examples:
        ```python
        >>> c = Config(**{'i.d': 1013})
        >>> c.getattr('frozen')
        False
        >>> c.freeze(recursive=False).dict()
        {'i': {'d': 1013}}
        >>> c.getattr('frozen')
        True
        >>> c.i.getattr('frozen')
        False
        >>> c.freeze(recursive=True).dict()
        {'i': {'d': 1013}}
        >>> c.i.getattr('frozen')
        True

        ```
        """

        @wraps(self.freeze)
        def freeze(config: Config) -> None:
            config.setattr("frozen", True)

        if recursive:
            self.apply(freeze)
        else:
            freeze(self)
        return self

    lock = freeze

    def defrost(self, recursive: bool = True) -> Config:
        r"""
        Defrost `Config`.

        Args:
            recursive:

        **Alias**:

        + `unlock`

        Examples:
        ```python
        >>> c = Config(**{'i.d': 1013})
        >>> c.getattr('frozen')
        False
        >>> c.freeze().dict()
        {'i': {'d': 1013}}
        >>> c.getattr('frozen')
        True
        >>> c.defrost(recursive=False).dict()
        {'i': {'d': 1013}}
        >>> c.getattr('frozen')
        False
        >>> c.i.getattr('frozen')
        True
        >>> c.defrost().dict()
        {'i': {'d': 1013}}
        >>> c.i.getattr('frozen')
        False

        ```
        """

        @wraps(self.defrost)
        def defrost(config: Config) -> None:
            config.setattr("frozen", False)

        if recursive:
            self.apply(defrost)
        else:
            defrost(self)
        return self

    unlock = defrost

    @contextmanager
    def unlocked(self):
        """
        Context manager which temporarily unlocks `Config`.

        Examples:
        ```python
        >>> c = Config()
        >>> c.freeze().dict()
        {}
        >>> with c.unlocked():
        ...     c['i.d'] = 1013
        >>> c.defrost().dict()
        {'i': {'d': 1013}}

        ```
        """

        was_frozen = self.getattr("frozen", False)
        try:
            self.defrost()
            yield self
        finally:
            if was_frozen:
                self.freeze()

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        r"""

        Parse command line arguments with `ConfigParser`.

        See Also: [`chanfig.ConfigParser.parse`][chanfig.ConfigParser.parse]

        Examples:
        ```python
        >>> c = Config(a=0)
        >>> c.dict()
        {'a': 0}
        >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        return self.getattr("parser", ConfigParser()).parse(args, self, default_config)

    parse_config = parse

    def add_argument(self, *args, **kwargs) -> None:
        r"""
        Add an argument to `ConfigParser`.

        Examples:
        ```python
        >>> c = Config(a=0)
        >>> c.add_argument("--a", type=int, default=1)
        >>> c.parse([]).dict()
        {'a': 1}

        ```
        """

        self.getattr("parser", ConfigParser()).add_argument(*args, **kwargs)

    def get(self, name: str, default: Any = Null) -> Any:
        r"""
        Get value from `Config`.

        Note that `default` has higher priority than `default_factory`.

        Args:
            name:
            default:

        Returns:
            value:
                If name does not exist, return `default`.
                If `default` is not specified, return `default_factory()`.

        Raises:
            KeyError: If name does not exist and `default`/`default_factory` is not specified.

        **Alias**:

        + `__getitem__`
        + `__getattr__`

        Examples:
        ```python
        >>> d = Config(**{"i.d": 1013})
        >>> d.get('i.d')
        1013
        >>> d['i.d']
        1013
        >>> d.i.d
        1013
        >>> d.get('f', 2)
        2
        >>> d.f
        Config()
        >>> del d.f
        >>> d.freeze()
        Config(
          ('i'): Config(
            ('d'): 1013
          )
        )
        >>> d.f
        Traceback (most recent call last):
        KeyError: 'Config does not contain f'

        ```
        """

        if "default_factory" not in self:  # did not call super().__init__() in sub-class
            self.setattr("default_factory", Config)
        if name in self or not self.getattr("frozen", False):
            return super().get(name, default)
        raise KeyError(f"{self.__class__.__name__} does not contain {name}")

    __getitem__ = get
    __getattr__ = get

    @frozen_check
    def set(
        self,
        name: str,
        value: Any,
        convert_mapping: Optional[bool] = None,
    ) -> None:
        r"""
        Set value of `Config`.

        Args:
            name:
            value:

        Raises:
            ValueError: If `Config` is frozen.

        **Alias**:

        + `__setitem__`
        + `__setattr__`

        Examples:
        ```python
        >>> c = Config()
        >>> c['i.d'] = 1013
        >>> c.i.d
        1013
        >>> c.freeze().dict()
        {'i': {'d': 1013}}
        >>> c['i.d'] = 1013
        Traceback (most recent call last):
        ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
        >>> c.defrost().dict()
        {'i': {'d': 1013}}
        >>> c['i.d'] = 1013
        >>> c.i.d
        1013

        ```
        """

        return super().set(name, value, convert_mapping)

    __setitem__ = set
    __setattr__ = set

    @frozen_check
    def delete(self, name: str) -> None:
        r"""
        Delete value from `Config`.

        Args:
            name:

        **Alias**:

        + `__delitem__`
        + `__delattr__`

        Examples:
        ```python
        >>> d = Config(**{"i.d": 1013, "f.n": "chang"})
        >>> d.i.d
        1013
        >>> d.f.n
        'chang'
        >>> d.delete('i.d')
        >>> "i.d" in d
        False
        >>> d.i.d
        Config()
        >>> "i.d" in d
        True
        >>> del d.f.n
        >>> d.f.n
        Config()
        >>> del d.c
        Traceback (most recent call last):
        KeyError: 'c'

        ```
        """

        super().delete(name)

    __delitem__ = delete
    __delattr__ = delete

    @frozen_check
    def pop(self, name: str, default: Any = Null) -> Any:
        r"""
        Pop value from `Config`.

        Args:
            name:
            default:

        Returns:
            value: If name does not exist, return `default`.

        Examples:
        ```python
        >>> c = Config()
        >>> c['i.d'] = 1013
        >>> c.pop('i.d')
        1013
        >>> c.pop('i.d', True)
        True
        >>> c.freeze().dict()
        {'i': {}}
        >>> c['i.d'] = 1013
        Traceback (most recent call last):
        ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
        >>> c.defrost().dict()
        {'i': {}}
        >>> c['i.d'] = 1013
        >>> c.pop('i.d')
        1013

        ```
        """

        return super().pop(name, default)
