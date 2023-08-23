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

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from functools import wraps
from typing import Any

from .nested_dict import NestedDict
from .parser import ConfigParser
from .utils import Null


def frozen_check(func: Callable):
    r"""
    Decorator check if the object is frozen.
    """

    @wraps(func)
    def decorator(self, *args: Any, **kwargs: Any):
        if self.getattr("frozen", False):
            raise ValueError("Attempting to alter a frozen config. Run config.defrost() to defrost first.")
        return func(self, *args, **kwargs)

    return decorator


class Config(NestedDict):  # type: ignore
    r"""
    `Config` is an extension of `NestedDict`.

    The differences between `Config` and `NestedDict` lies in 3 aspects:

    1. `Config` has `default_factory` set to `Config` and `convert_mapping` set to `True` by default.
    2. `Config` has a `frozen` attribute, which can be toggled with `freeze`(`lock`) & `defrost`(`unlock`)
        or temporarily changed with `locked` & `unlocked`.
    3. `Config` has a `ConfigParser` built-in, and supports `add_argument` and `parse`.

    Config also features a `post` method and a `boot` method to support lazy-initilisation.
    This is useful when you want to perform some post-processing on the config.
    For example, some values may be a combination of other values, and you may define them in `post`.

    `boot` is introduced to call all `post` methods in the nested structure of `Config` object.
    By default, `boot` will be called to after `Config` is parsed.

    You could also manually call `boot` if you you don't parse command-line arguments.

    Notes:
        Since `Config` has `default_factory` set to `Config`,
        accessing anything that does not exist will create a new empty Config sub-attribute.

        A **frozen** `Config` does not have this behaviour and
        will raises `KeyError` when accessing anything that does not exist.

        It is recommended to call `config.freeze()` or `config.to(NestedDict)` to avoid this behaviour.

    Attributes:
        parser (ConfigParser): Parser for command-line arguments.
        frozen (bool): If `True`, the config is frozen and cannot be altered.

    Examples:
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
    """

    parser: None  # ConfigParser, Python 3.7 does not support forward reference
    frozen: bool = False

    def __init__(self, *args: Any, default_factory: Callable | None = None, **kwargs: Any):
        if default_factory is None:
            default_factory = Config
        super().__init__(*args, default_factory=default_factory, **kwargs)

    def post(self) -> Config:
        r"""
        Post process of `Config`.

        Some `Config` may need to do some post process after `Config` is initialised.
        `post` is provided for this lazy-initialisation purpose.

        By default, `post` does nothing and returns `self`.

        Note that you should always call `boot` to apply `post` rather than calling `post` directly,
        as `boot` recursively call `post` on sub-configs.

        See Also: [`boot`][chanfig.Config.boot]

        Returns:
            self:

        Examples:
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
        """

        self.validate()
        return self

    def boot(self) -> Config:
        r"""
        Apply `post` recursively.

        Sub-config may have their own `post` method.
        `boot` is provided to apply `post` recursively.

        By default, `boot` is called after `Config` is parsed.
        If you don't need to parse command-line arguments, you should call `boot` manually.

        See Also: [`post`][chanfig.Config.post]

        Returns:
            self:

        Examples:
            >>> class DataConfig(Config):
            ...     def post(self):
            ...         if isinstance(self.path, str):
            ...             self.path = Config(feature=self.path, label=self.path)
            ...         return self
            >>> class BootConfig(Config):
            ...     def __init__(self, *args, **kwargs):
            ...         super().__init__(*args, **kwargs)
            ...         self.dataset = DataConfig(path="path")
            ...     def post(self):
            ...         if isinstance(self.id, str):
            ...             self.id += "_id"
            ...         return self
            >>> c = BootConfig(id="boot")
            >>> c.boot()
            BootConfig(<class 'chanfig.config.Config'>,
              ('id'): 'boot_id'
              ('dataset'): DataConfig(<class 'chanfig.config.Config'>,
                ('path'): Config(<class 'chanfig.config.Config'>,
                  ('feature'): 'path'
                  ('label'): 'path'
                )
              )
            )
        """

        for value in self.values():
            if isinstance(value, Config):
                value.boot()
        self.post()
        return self

    def parse(
        self,
        args: Iterable[str] | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
        boot: bool = True,
    ) -> Config:
        r"""

        Parse command-line arguments with `ConfigParser`.

        `parse` will try to parse all command-line arguments,
        you don't need to pre-define them but typos may cause trouble.

        By default, this method internally calls `Config.boot()`.
        To disable this behaviour, set `boot` to `False`.

        Args:
            args (Iterable[str] | None, optional): Command-line arguments. Defaults to `None`.
            default_config (str | None, optional): Path to default config file. Defaults to `None`.
            no_default_config_action (str, optional): Action when `default_config` is not found.
                Can be one of `["raise", "warn", "ignore"]`. Defaults to `"raise"`.
            boot (bool, optional): If `True`, call `Config.boot()` after parsing. Defaults to `True`.

        See Also:
            [`chanfig.ConfigParser.parse`][chanfig.ConfigParser.parse]: Implementation of `parse`.
            [`parse_config`][chanfig.Config.parse_config]: Only parse valid config arguments.

        Examples:
            >>> c = Config(a=0)
            >>> c.dict()
            {'a': 0}
            >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        if not self.hasattr("parser"):
            self.setattr("parser", ConfigParser())
        self.getattr("parser").parse(args, self, default_config, no_default_config_action)
        if boot:
            self.boot()
        return self

    def parse_config(
        self,
        args: Iterable[str] | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
        boot: bool = True,
    ) -> Config:
        r"""

        Parse command-line arguments with `ConfigParser`.

        `parse_config` only parse command-line arguments that is in defined in `Config`.

        By default, this method internally calls `Config.boot()`.
        To disable this behaviour, set `boot` to `False`.

        Args:
            args (Iterable[str] | None, optional): Command-line arguments. Defaults to `None`.
            default_config (str | None, optional): Path to default config file. Defaults to `None`.
            no_default_config_action (str, optional): Action when `default_config` is not found.
                Can be one of `["raise", "warn", "ignore"]`. Defaults to `"raise"`.
            boot (bool, optional): If `True`, call `Config.boot()` after parsing. Defaults to `True`.

        See Also:
            [`chanfig.ConfigParser.parse_config`][chanfig.ConfigParser.parse_config]: Implementation of `parse_config`.
            [`parse`][chanfig.Config.parse]: Parse all command-line arguments.

        Examples:
            >>> c = Config(a=0, b=0, c=0)
            >>> c.dict()
            {'a': 0, 'b': 0, 'c': 0}
            >>> c.parse_config(['--a', '1', '--b', '2', '--c', '3']).dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        if not self.hasattr("parser"):
            self.setattr("parser", ConfigParser())
        self.getattr("parser").parse_config(args, self, default_config, no_default_config_action)
        if boot:
            self.boot()
        return self

    def add_argument(self, *args: Any, **kwargs: Any) -> None:
        r"""
        Add an argument to `ConfigParser`.

        Note that value defined in `Config` will override the default value defined in `add_argument`.

        Examples:
            >>> c = Config(a=0, c=1)
            >>> arg = c.add_argument("--a", type=int, default=1)
            >>> arg = c.add_argument("--b", type=int, default=2)
            >>> c.parse(['--c', '4']).dict()
            {'a': 1, 'c': 4, 'b': 2}
        """

        if not self.hasattr("parser"):
            self.setattr("parser", ConfigParser())
        return self.getattr("parser").add_argument(*args, **kwargs)

    def freeze(self, recursive: bool = True) -> Config:
        r"""
        Freeze `Config`.

        Args:
            recursive:

        **Alias**:

        + `lock`

        Examples:
            >>> c = Config(**{'i.d': 1013})
            >>> c.getattr('frozen')
            False
            >>> c.freeze(recursive=False).dict()
            {'i': {'d': 1013}}
            >>> c.getattr('frozen')
            True
            >>> c.i.getattr('frozen')
            False
            >>> c.lock().dict()  # alias
            {'i': {'d': 1013}}
            >>> c.i.getattr('frozen')
            True
        """

        @wraps(self.freeze)
        def freeze(config: Config) -> None:
            if isinstance(config, Config):
                config.setattr("frozen", True)

        if recursive:
            self.apply_(freeze)
        else:
            freeze(self)
        return self

    def lock(self, recursive: bool = True) -> Config:
        r"""
        Alias of [`freeze`][chanfig.Config.freeze].
        """
        return self.freeze(recursive=recursive)

    @contextmanager
    def locked(self):
        """
        Context manager which temporarily locks `Config`.

        Examples:
            >>> c = Config()
            >>> with c.locked():
            ...     c['i.d'] = 1013
            Traceback (most recent call last):
            ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
            >>> c.i.d = 1013
            >>> c.dict()
            {'i': {'d': 1013}}
        """

        was_frozen = self.getattr("frozen", False)
        try:
            self.freeze()
            yield self
        finally:
            if not was_frozen:
                self.defrost()

    def defrost(self, recursive: bool = True) -> Config:
        r"""
        Defrost `Config`.

        Args:
            recursive:

        **Alias**:

        + `unlock`

        Examples:
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
            >>> c.unlock().dict()  # alias
            {'i': {'d': 1013}}
            >>> c.i.getattr('frozen')
            False
        """

        @wraps(self.defrost)
        def defrost(config: Config) -> None:
            if isinstance(config, Config):
                config.setattr("frozen", False)

        if recursive:
            self.apply_(defrost)
        else:
            defrost(self)
        return self

    def unlock(self, recursive: bool = True) -> Config:
        r"""
        Alias of [`defrost`][chanfig.Config.defrost].
        """
        return self.defrost(recursive=recursive)

    @contextmanager
    def unlocked(self):
        """
        Context manager which temporarily unlocks `Config`.

        Examples:
            >>> c = Config()
            >>> c.freeze().dict()
            {}
            >>> with c.unlocked():
            ...     c['i.d'] = 1013
            >>> c.defrost().dict()
            {'i': {'d': 1013}}
        """

        was_frozen = self.getattr("frozen", False)
        try:
            self.defrost()
            yield self
        finally:
            if was_frozen:
                self.freeze()

    def get(self, name: Any, default: Any = None) -> Any:
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

        Examples:
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
        """

        if not self.hasattr("default_factory"):  # did not call super().__init__() in sub-class
            self.setattr("default_factory", Config)
        if name in self or not self.getattr("frozen", False):
            return super().get(name, default)
        raise KeyError(name)

    @frozen_check
    def set(
        self,
        name: Any,
        value: Any,
        convert_mapping: bool | None = None,
    ) -> None:
        r"""
        Set value of `Config`.

        Args:
            name:
            value:
            convert_mapping: Whether to convert `Mapping` to `NestedDict`.
                Defaults to self.convert_mapping.

        Raises:
            ValueError: If `Config` is frozen.

        Examples:
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
        """

        return super().set(name, value, convert_mapping)

    @frozen_check
    def delete(self, name: Any) -> None:
        r"""
        Delete value from `Config`.

        Args:
            name:

        Examples:
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
        """

        return super().pop(name, default)
