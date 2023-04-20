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

from __future__ import annotations

import sys
from argparse import ArgumentParser
from contextlib import contextmanager
from functools import wraps
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

    def parse(  # pylint: disable=R0912
        self,
        args: Optional[Sequence[str]] = None,
        config: Optional[Config] = None,
        default_config: Optional[str] = None,
        no_default_config_action: str = "raise",
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
            no_default_config_action: What to do when `default_config` is specified but not found in args.

        Returns:
            config: The parsed `Config`.

        Raises:
            ValueError: If `default_config` is specified but not found in args,
                and `no_default_config_action` is neither `warn` nor `igonre`.
            ValueError: If `no_default_config_action` is not in `raise`, `warn` and `igonre`.

        Examples:
        ```python
        >>> p = ConfigParser()
        >>> p.parse(['--i.d', '1013', '--f.n', 'chang']).dict()
        {'i': {'d': 1013}, 'f': {'n': 'chang'}}

        # Values in command line arguments overrides values in `default_config` file.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2', '--config', 'example.yaml'], default_config='config').dict()
        {'a': 2, 'b': 2, 'c': 3, 'config': 'example.yaml'}

        # Values in `default_config` file overrides values in `Config` object.
        >>> c = Config(a=2)
        >>> c.parse(['--config', 'example.yaml'], default_config='config').dict()
        {'a': 1, 'b': 2, 'c': 3, 'config': 'example.yaml'}

        # ValueError will be raised when `default_config` is specified but not presented in command line arguments.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2'], default_config='config').dict()
        Traceback (most recent call last):
        ValueError: default_config is set to config, but not found in args.

        # ValueError will be suppressed when `default_config` is specified bug not presented in command line arguments,
        # and `no_default_config_action` is set to `ignore` or `warn`.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2'], default_config='config', no_default_config_action='ignore').dict()
        {'a': 2}

        # ValueError will be raised when `no_default_config_action` is not in `raise`, `ignore`, and `warn`.
        >>> p = ConfigParser()
        >>> p.parse(['--a', '2'], default_config='config', no_default_config_action='suppress').dict()
        Traceback (most recent call last):
        ValueError: no_default_config_action must be one of 'warn', 'ignore', 'raise', bug got suppress

        ```
        """

        if no_default_config_action not in ("warn", "ignore", "raise"):
            raise ValueError(
                f"no_default_config_action must be one of 'warn', 'ignore', 'raise', bug got {no_default_config_action}"
            )

        if args is None:
            args = sys.argv[1:]
        key_value_args = []
        for arg in args:
            if args == "--":
                break
            if arg.startswith("--"):
                key_value_args.append(arg.split("=", maxsplit=1))
            else:
                if not key_value_args:
                    continue
                key_value_args[-1].append(arg)
        for key_value in key_value_args:
            if key_value[0] not in self._option_string_actions:
                if len(key_value) > 2:
                    self.add_argument(key_value[0], nargs="+")
                else:
                    self.add_argument(key_value[0])
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
            elif no_default_config_action == "ignore":
                pass
            elif no_default_config_action == "warn":
                warn(f"default_config is set to {default_config}, but not found in args.")
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

    Config also supports a `post` method, which will be called after `Config` is parsed.

    This is useful when you want to perform some post-processing on the config.
    For example, some values may be a combination of other values, and you may define them in `post`.

    You could also manually call `post` if you you don't need to parse command-line arguments.

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
    Config(<class 'chanfig.config.Config'>, )
    >>> c.freeze().dict()
    {'f': {'n': 'chang'}, 'i': {'d': 1013}, 'd': {'i': {}}}
    >>> c.d.i = 1013
    Traceback (most recent call last):
    ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
    >>> c.d.e
    Traceback (most recent call last):
    AttributeError: 'Config' object has no attribute 'e'
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

    def post(self) -> Config:
        r"""
        Post process of `Config`.

        Some `Config` may need to do some post process after `Config` is initialized.

        You can override this method to do such post process.

        By default, `post` does nothing and returns `self`.

        Returns:
            self:

        Examples:
        ```python
        >>> class PostConfig(Config):
        ...     def post(self):
        ...         if isinstance(self.data, str):
        ...             self.data = Config(feature=self.data, label=self.data)
        ...         return self
        >>> c = PostConfig(data="path")
        >>> c.post()
        PostConfig(<class 'chanfig.config.Config'>,
          ('data'): Config(<class 'chanfig.config.Config'>,
            ('feature'): 'path'
            ('label'): 'path'
          )
        )

        ```
        """

        return self

    def parse(
        self,
        args: Optional[Iterable[str]] = None,
        default_config: Optional[str] = None,
        no_default_config_action: str = "raise",
    ) -> Config:
        r"""

        Parse command line arguments with `ConfigParser`.

        This function internally calls `Config.post`.

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

        self.getattr("parser", ConfigParser()).parse(args, self, default_config, no_default_config_action)
        self.post()
        return self

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

    def get(self, name: Any, default: Any = Null) -> Any:
        r"""
        Get value from `Config`.

        Note that `default` has higher priority than `default_factory`.

        Args:
            name:
            default:

        Returns:
            value:
                If `Config` does not contain `name`, return `default`.
                If `default` is not specified, return `default_factory()`.

        Raises:
            KeyError: If `Config` does not contain `name` and `default`/`default_factory` is not specified.

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
        Config(<class 'chanfig.config.Config'>, )
        >>> del d.f
        >>> d.freeze()
        Config(<class 'chanfig.config.Config'>,
          ('i'): Config(<class 'chanfig.config.Config'>,
            ('d'): 1013
          )
        )
        >>> d.f
        Traceback (most recent call last):
        AttributeError: 'Config' object has no attribute 'f'
        >>> d["f.n"]
        Traceback (most recent call last):
        KeyError: 'f.n'

        ```
        """

        if "default_factory" not in self:  # did not call super().__init__() in sub-class
            self.setattr("default_factory", Config)
        if name in self or not self.getattr("frozen", False):
            return super().get(name, default)
        raise KeyError(name)

    @frozen_check
    def set(
        self,
        name: Any,
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

    @frozen_check
    def delete(self, name: Any) -> None:
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
        Config(<class 'chanfig.config.Config'>, )
        >>> "i.d" in d
        True
        >>> del d.f.n
        >>> d.f.n
        Config(<class 'chanfig.config.Config'>, )
        >>> del d.c
        Traceback (most recent call last):
        AttributeError: 'Config' object has no attribute 'c'

        ```
        """

        super().delete(name)

    @frozen_check
    def pop(self, name: Any, default: Any = Null) -> Any:
        r"""
        Pop value from `Config`.

        Args:
            name:
            default:

        Returns:
            value: If `Config` does not contain `name`, return `default`.

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
