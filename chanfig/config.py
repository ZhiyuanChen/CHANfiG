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

from collections.abc import Callable, Iterable
from contextlib import contextmanager
from functools import wraps
from typing import Any

from typing_extensions import Self

from .nested_dict import NestedDict
from .parser import ConfigParser
from .utils import NULL, Null


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


class Config(NestedDict):
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
        >>> c.i.d = 1016
        >>> c.i.d
        1016
        >>> c.d.i
        Config(<class 'chanfig.config.Config'>, )
        >>> c.freeze().dict()
        {'f': {'n': 'chang'}, 'i': {'d': 1016}, 'd': {'i': {}}}
        >>> c.d.i = 1016
        Traceback (most recent call last):
        ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
        >>> c.d.e
        Traceback (most recent call last):
        AttributeError: 'Config' object has no attribute 'e'
        >>> with c.unlocked():
        ...     del c.d
        >>> c.dict()
        {'f': {'n': 'chang'}, 'i': {'d': 1016}}
    """

    parser = None  # ConfigParser, Python 3.7 does not support forward reference
    frozen = False
    convert_mapping = True

    def __init__(
        self,
        *args: Any,
        default_factory: Callable | NULL = Null,
        convert_mapping: bool | None = True,
        **kwargs: Any,
    ):
        if default_factory is Null:
            default_factory = Config
        self.setattr("frozen", False)
        super().__init__(*args, default_factory=default_factory, convert_mapping=convert_mapping, **kwargs)

    def post(self) -> None:
        r"""
        Post-processing hook for `Config`.

        Override this method to perform custom post-processing after the config is initialised.
        There is no need to call `super().post()` -- `boot` handles framework concerns
        (interpolation, validation, clearing `default_factory`) automatically after `post` returns.

        Note that you should always call `boot` rather than calling `post` directly,
        as `boot` recursively calls `post` on sub-configs.

        See Also:
            [`boot`][chanfig.Config.boot]: Apply `post` recursively.

        Examples:
            >>> c = Config()
            >>> c.dne
            Config(<class 'chanfig.config.Config'>, )
            >>> c.boot()
            Config(
              ('dne'): Config()
            )
            >>> c.dne2
            Traceback (most recent call last):
            AttributeError: 'Config' object has no attribute 'dne2'
            >>> class PostConfig(Config):
            ...     def post(self):
            ...         if isinstance(self.data, str):
            ...             self.data = Config(feature=self.data, label=self.data)
            >>> c = PostConfig(data="path")
            >>> c.boot()
            PostConfig(
              ('data'): Config(
                ('feature'): 'path'
                ('label'): 'path'
              )
            )
        """

    def boot(self) -> Self:
        r"""
        Apply `post` recursively, then finalise the config.

        `boot` walks the config tree bottom-up: it boots every sub-config first, then calls
        `self.post()` for custom user logic, and finally runs the framework bookkeeping
        (interpolation, validation, clearing `default_factory`).

        By default, `boot` is called after `Config` is parsed.
        If you don't need to parse command-line arguments, you should call `boot` manually.

        See Also:
            [`post`][chanfig.Config.post]

        Examples:
            >>> class DataConfig(Config):
            ...     def post(self):
            ...         if isinstance(self.path, str):
            ...             self.path = Config(feature=self.path, label=self.path)
            >>> class BootConfig(Config):
            ...     def __init__(self, *args, **kwargs):
            ...         super().__init__(*args, **kwargs)
            ...         self.dataset = DataConfig(path="path")
            ...     def post(self):
            ...         if isinstance(self.id, str):
            ...             self.id += "_id"
            >>> c = BootConfig(id="boot")
            >>> c.boot()
            BootConfig(
              ('id'): 'boot_id'
              ('dataset'): DataConfig(
                ('path'): Config(
                  ('feature'): 'path'
                  ('label'): 'path'
                )
              )
            )
        """

        self._boot()
        self.interpolate()
        self._validate(self)
        self.apply_(lambda c: c.setattr("default_factory", Null) if isinstance(c, Config) else None)
        return self

    def _boot(self) -> None:
        r"""
        Recursively call `post` on sub-configs, then on self.

        This is the internal recursive helper for `boot`.
        Framework-wide concerns (interpolation, validation, clearing `default_factory`)
        are handled by the top-level `boot` after the full tree has been posted.
        """

        for value in self.values():
            if isinstance(value, Config):
                value._boot()  # noqa: SLF001
                value.popattr("parser", None)
        self.post()

    def parse(
        self,
        args: Iterable[str] | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
        boot: bool = True,
        strict: bool = False,
    ) -> Self:
        r"""
        Parse command-line arguments with `ConfigParser`.

        By default, `parse` accepts all command-line arguments (including ones not pre-defined
        in the config). Set ``strict=True`` to only accept arguments that already exist in the config.

        By default, this method internally calls `Config.boot()`.
        To disable this behaviour, set `boot` to `False`.

        Args:
            args (Iterable[str] | None, optional): Command-line arguments. Defaults to `None`.
            default_config (str | None, optional): Path to default config file. Defaults to `None`.
            no_default_config_action (str, optional): Action when `default_config` is not found.
                Can be one of `["raise", "warn", "ignore"]`. Defaults to `"raise"`.
            boot (bool, optional): If `True`, call `Config.boot()` after parsing. Defaults to `True`.
            strict (bool, optional): If `True`, only parse arguments pre-defined in `Config`.
                Defaults to `False`.

        See Also:
            [`chanfig.ConfigParser.parse`][chanfig.ConfigParser.parse]
            [`chanfig.ConfigParser.parse_config`][chanfig.ConfigParser.parse_config]

        Examples:
            >>> c = Config(a=0)
            >>> c.dict()
            {'a': 0}
            >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> c = Config(a=0, b=0, c=0)
            >>> c.parse(['--a', '1', '--b', '2', '--c', '3'], strict=True).dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        if self.getattr("parser") is None:
            self.setattr("parser", ConfigParser())
        parser = self.getattr("parser")
        if strict:
            parser.parse_config(args, self, default_config, no_default_config_action)
        else:
            parser.parse(args, self, default_config, no_default_config_action)
        if boot:
            self.boot()
        return self

    def parse_config(
        self,
        args: Iterable[str] | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
        boot: bool = True,
    ) -> Self:
        r"""
        Shorthand for ``parse(..., strict=True)``.

        See Also:
            [`parse`][chanfig.Config.parse]

        Examples:
            >>> c = Config(a=0, b=0, c=0)
            >>> c.dict()
            {'a': 0, 'b': 0, 'c': 0}
            >>> c.parse_config(['--a', '1', '--b', '2', '--c', '3']).dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        return self.parse(
            args,
            default_config=default_config,
            no_default_config_action=no_default_config_action,
            boot=boot,
            strict=True,
        )

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

        if self.getattr("parser") is None:
            self.setattr("parser", ConfigParser())
        return self.getattr("parser").add_argument(*args, **kwargs)

    def freeze(self, recursive: bool = True) -> Self:
        r"""
        Freeze `Config`.

        Args:
            recursive:

        **Alias**:

        + `lock`

        Examples:
            >>> c = Config(**{'i.d': 1016})
            >>> c.getattr('frozen')
            False
            >>> c.freeze(recursive=False).dict()
            {'i': {'d': 1016}}
            >>> c.getattr('frozen')
            True
            >>> c.i.getattr('frozen')
            False
            >>> c.lock().dict()  # alias
            {'i': {'d': 1016}}
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

    def lock(self, recursive: bool = True) -> Self:
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
            ...     c['i.d'] = 1016
            Traceback (most recent call last):
            ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
            >>> c.i.d = 1016
            >>> c.dict()
            {'i': {'d': 1016}}
        """

        was_frozen = self.getattr("frozen", False)
        try:
            self.freeze()
            yield self
        finally:
            if not was_frozen:
                self.defrost()

    def defrost(self, recursive: bool = True) -> Self:
        r"""
        Defrost `Config`.

        Args:
            recursive:

        **Alias**:

        + `unlock`

        Examples:
            >>> c = Config(**{'i.d': 1016})
            >>> c.getattr('frozen')
            False
            >>> c.freeze().dict()
            {'i': {'d': 1016}}
            >>> c.getattr('frozen')
            True
            >>> c.defrost(recursive=False).dict()
            {'i': {'d': 1016}}
            >>> c.getattr('frozen')
            False
            >>> c.i.getattr('frozen')
            True
            >>> c.unlock().dict()  # alias
            {'i': {'d': 1016}}
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

    def unlock(self, recursive: bool = True) -> Self:
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
            ...     c['i.d'] = 1016
            >>> c.defrost().dict()
            {'i': {'d': 1016}}
        """

        was_frozen = self.getattr("frozen", False)
        try:
            self.defrost()
            yield self
        finally:
            if was_frozen:
                self.freeze()

    def get(self, name: Any, default: Any = None, fallback: bool | None = None) -> Any:
        r"""
        Get value from `Config`.

        When the config is not frozen, behaves like `NestedDict.get` (missing keys are created
        via ``default_factory``). When frozen, missing keys raise `KeyError` unless *default*
        or *fallback* provides a value.

        Raises:
            KeyError: If `Config` is frozen, does not contain `name`,
                and no `default`/`fallback` is available.

        Examples:
            >>> d = Config(**{"i.d": 1016})
            >>> d.get('i.d')
            1016
            >>> d['i.d']
            1016
            >>> d.i.d
            1016
            >>> d.get('f', 2)
            2
            >>> d.f
            Config(<class 'chanfig.config.Config'>, )
            >>> del d.f
            >>> d.freeze()
            Config(<class 'chanfig.config.Config'>,
              ('i'): Config(<class 'chanfig.config.Config'>,
                ('d'): 1016
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
            return super().get(name, default, fallback)
        # Frozen and missing — try fallback, then default, then raise.
        if fallback:
            separator = self.getattr("separator", ".")
            fallback_name = name.split(separator)[-1] if isinstance(name, str) else name
            if fallback_name in self:
                return super().get(fallback_name, default, False)
        if default is not Null:
            return default
        suggestion = self._suggest_key(name)
        message = f"{name!r}. Did you mean '{suggestion}'?" if suggestion else name
        raise KeyError(message)

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
            >>> c['i.d'] = 1016
            >>> c.i.d
            1016
            >>> c.freeze().dict()
            {'i': {'d': 1016}}
            >>> c['i.d'] = 1016
            Traceback (most recent call last):
            ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
            >>> c.defrost().dict()
            {'i': {'d': 1016}}
            >>> c['i.d'] = 1016
            >>> c.i.d
            1016
        """

        return super().set(name, value, convert_mapping)

    @frozen_check
    def delete(self, name: Any) -> None:
        r"""
        Delete value from `Config`.

        Args:
            name:

        Examples:
            >>> d = Config(**{"i.d": 1016, "f.n": "chang"})
            >>> d.i.d
            1016
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

        Examples:
            >>> c = Config()
            >>> c['i.d'] = 1016
            >>> c.pop('i.d')
            1016
            >>> c.pop('i.d', True)
            True
            >>> c.freeze().dict()
            {'i': {}}
            >>> c['i.d'] = 1016
            Traceback (most recent call last):
            ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first.
            >>> c.defrost().dict()
            {'i': {}}
            >>> c['i.d'] = 1016
            >>> c.pop('i.d')
            1016
        """

        return super().pop(name, default)
