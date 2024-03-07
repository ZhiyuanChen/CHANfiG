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

import sys
from argparse import ArgumentParser, Namespace, _StoreAction
from ast import literal_eval
from collections.abc import Sequence
from contextlib import suppress
from typing import TYPE_CHECKING, Any
from warnings import warn

from .nested_dict import NestedDict
from .utils import Null, parse_bool
from .variable import Variable

if TYPE_CHECKING:
    from .config import Config


class ConfigParser(ArgumentParser):  # pylint: disable=C0115
    r"""
    Parser to parse command-line arguments for CHANfiG.

    `ConfigParser` is a subclass of `argparse.ArgumentParser`.
    It provides new `parse_config` and `parse` method to parse command-line arguments to `CHANfiG.Config` object.

    `parse_config` will read the configuration and determine possible arguments and their types.
    This makes it more favourable than `parse` as it has strict name checking.

    `parse` will try to parse any command-line arguments, even if they are not pre-defined by `add_argument`.
    This allows to relief the burden of adding tons of arguments for each tuneable parameter.
    In the meantime, there is no mechanism to notify you if you made a typo in command-line arguments.

    `ConfigParser` override `parse_args` method to ensure the output is a `NestedDict`.
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._registries["action"][None] = StoreAction
        self._registries["action"]["store"] = StoreAction

    def parse_config(  # pylint: disable=R0912
        self,
        args: Sequence[str] | None = None,
        config: Config | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
    ) -> Config:
        r"""
        Parse the arguments for `Config`.

        You may optionally specify a name for `default_config`,
        and CHANfiG will read the file under this name.

        There are three levels of config:

        1. The base `Config` parsed into this method,
        2. The base config file located at the path of `default_config` (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Args:
            args (Sequence[str] | None, optional): Command-line arguments. Defaults to `None`.
            config (NestedDict | None, optional): existing configuration.
            default_config (str | None, optional): Path to default config file. Defaults to `Config`.
            no_default_config_action (str, optional): Action when `default_config` is not found.
                Can be one of `["raise", "warn", "ignore"]`. Defaults to `"raise"`.

        Returns:
            config: The parsed `Config`.

        Raises:
            ValueError: If `default_config` is specified but not found in args,
                and `no_default_config_action` is neither `warn` nor `ignore`.
            ValueError: If `no_default_config_action` is not in `raise`, `warn` and `ignore`.

        See Also:
            [`parse`][chanfig.ConfigParser.parse]: Parse all command-line arguments.

        Examples:
            Note that all examples uses NestedDict instead of Config for avoiding circular import.
            >>> p = ConfigParser()
            >>> p.parse_config(['--a', '1'], config=NestedDict(a=2)).dict()
            {'a': 1}

            You can only parse argument that is defined in `Config`.
            error: unrecognized arguments: --b 1
            >>> p = ConfigParser()
            >>> p.parse_config(['--b', '1'], config=NestedDict(a=2)).dict()  # doctest: +SKIP
            Traceback (most recent call last):
            SystemExit: 2
        """

        if args is None:
            args = sys.argv[1:]

        if config is None:
            raise ValueError("config must be specified")
        self.add_config_arguments(config)

        if no_default_config_action not in ("warn", "ignore", "raise"):
            raise ValueError(
                f"no_default_config_action must be one of 'warn', 'ignore', 'raise', bug got {no_default_config_action}"
            )

        # parse the command-line arguments
        parsed = self.parse_args(args)

        # parse the default config file
        if default_config is not None:
            parsed = self.merge_default_config(parsed, default_config, no_default_config_action)

        if config.getattr("parser", None) is not self:
            config.setattr("parser", self)
        return config.merge(parsed)

    def parse(  # pylint: disable=R0912
        self,
        args: Sequence[str] | None = None,
        config: Config | None = None,
        default_config: str | None = None,
        no_default_config_action: str = "raise",
    ) -> Config:
        r"""
        Parse the arguments for `Config`.

        You may optionally specify a name for `default_config`,
        and CHANfiG will read the file under this name.

        There are three levels of config:

        1. The base `Config` parsed into this method,
        2. The base config file located at the path of `default_config` (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Args:
            args (Sequence[str] | None, optional): Command-line arguments. Defaults to `None`.
            config (NestedDict | None, optional): existing configuration.
            default_config (str | None, optional): Path to default config file. Defaults to `Config`.
            no_default_config_action (str, optional): Action when `default_config` is not found.
                Can be one of `["raise", "warn", "ignore"]`. Defaults to `"raise"`.

        Returns:
            config: The parsed `Config`.

        Raises:
            ValueError: If `default_config` is specified but not found in args,
                and `no_default_config_action` is neither `warn` nor `ignore`.
            ValueError: If `no_default_config_action` is not in `raise`, `warn` and `ignore`.

        See Also:
            [`parse_config`][chanfig.ConfigParser.parse_config]: Only parse valid config arguments.

        Examples:
            Note that all examples uses NestedDict instead of Config for avoiding circular import.
            >>> p = ConfigParser()
            >>> p.parse(['--i.d', '1013', '--f.n', 'chang']).dict()
            {'i': {'d': 1013}, 'f': {'n': 'chang'}}

            Values in command line overrides values in `default_config` file.
            >>> p = ConfigParser()
            >>> p.parse(['--a', '2', '--config', 'tests/test.yaml'], default_config='config').dict()
            {'a': 2, 'b': 2, 'c': 3, 'config': 'tests/test.yaml'}

            Values in `default_config` file overrides values in `Config` object.
            >>> p = ConfigParser()
            >>> p.parse(['--config', 'tests/test.yaml'], config=NestedDict(a=2), default_config='config').dict()
            {'a': 1, 'b': 2, 'c': 3, 'config': 'tests/test.yaml'}

            ValueError will be raised when `default_config` is specified but not presented in command line.
            >>> p = ConfigParser()
            >>> p.parse(['--a', '2'], default_config='config').dict()
            Traceback (most recent call last):
            RuntimeError: default_config is set to config, but not found in args.

            ValueError will be suppressed when `default_config` is specified bug not presented in command line,
            and `no_default_config_action` is set to `ignore` or `warn`.
            >>> p = ConfigParser()
            >>> p.parse(['--a', '2'], default_config='config', no_default_config_action='ignore').dict()
            {'a': 2}

            ValueError will be raised when `no_default_config_action` is not in `raise`, `ignore`, and `warn`.
            >>> p = ConfigParser()
            >>> p.parse(['--a', '2'], default_config='config', no_default_config_action='suppress').dict()
            Traceback (most recent call last):
            ValueError: no_default_config_action must be one of 'warn', 'ignore', 'raise', bug got suppress
        """

        if args is None:
            args = sys.argv[1:]

        if config is None:
            from .config import Config  # pylint: disable=C0415

            config = Config()
        else:
            self.add_config_arguments(config)

        if no_default_config_action not in ("warn", "ignore", "raise"):
            raise ValueError(
                f"no_default_config_action must be one of 'warn', 'ignore', 'raise', bug got {no_default_config_action}"
            )

        # add the command-line arguments
        key_value_args = []
        for arg in args:
            if args == "--":
                break
            if arg.startswith("-"):
                key_value_args.append(arg.split("=", maxsplit=1))
            else:
                if not key_value_args:
                    continue
                key_value_args[-1].append(arg)
        for key_value in key_value_args:
            if key_value[0] not in self:
                if len(key_value) > 2:
                    self.add_argument(key_value[0], nargs="+")
                else:
                    self.add_argument(key_value[0])

        # parse the command-line arguments
        parsed = self.parse_args(args)

        # parse the default config file
        if default_config is not None:
            parsed = self.merge_default_config(parsed, default_config, no_default_config_action)

        if config.getattr("parser", None) is not self:
            config.setattr("parser", self)
        return config.merge(parsed)

    def parse_args(  # type: ignore[override]
        self, args: Sequence[str] | None = None, namespace: NestedDict | None = None, eval_str: bool = True
    ) -> NestedDict:
        r"""
        Parse command line arguments and convert types.

        This function first calls `ArgumentParser.parse_args` to parse command line arguments.
        It ensures the returned parsed values is stored in a NestedDict instance.
        If `eval_str` is specified, it also performs `literal_eval` on all `str` values.

        Args:
            args (Sequence[str] | None, optional): Command-line arguments. Defaults to `None`.
            namespace (NestedDict | None, optional): existing configuration.
            eval_str (bool, optional): Whether to evaluate string values.
        """
        parsed: dict | Namespace = super().parse_args(args, namespace)
        if isinstance(parsed, Namespace):
            parsed = vars(parsed)
        if not isinstance(parsed, NestedDict):
            parsed = NestedDict({key: value for key, value in parsed.items() if value is not Null})
        if eval_str:
            for key, value in parsed.all_items():
                if isinstance(value, str):
                    with suppress(TypeError, ValueError, SyntaxError):
                        value = literal_eval(value)
                    parsed[key] = value
        return parsed

    def add_config_arguments(self, config):
        for key, value in config.all_items():
            if isinstance(value, Variable):
                dtype = value._type or value.dtype  # pylint: disable=W0212
            elif value is not None:
                dtype = type(value)
            else:
                dtype = None
            name = "--" + key
            if name not in self:
                help = value._help if isinstance(value, Variable) else None  # pylint: disable=W0212,W0622
                if isinstance(value, (list, tuple, dict, set)):
                    self.add_argument(name, type=dtype, nargs="+", help=help, dest=key)
                elif isinstance(value, bool):
                    self.add_argument(name, type=parse_bool, help=help, dest=key)
                else:
                    self.add_argument(name, type=dtype, help=help, dest=key)

    def merge_default_config(self, parsed, default_config: str, no_default_config_action: str = "raise") -> NestedDict:
        message = f"default_config is set to {default_config}, but not found in args."
        if default_config in parsed:
            path = parsed[default_config]
            warn(f"Config has 'default_config={path}' specified, its values will override values in Config")
            return NestedDict.load(path).merge(parsed)
        if no_default_config_action == "ignore":
            pass
        elif no_default_config_action == "warn":
            warn(message, category=RuntimeWarning, stacklevel=2)
        else:
            raise RuntimeError(message)
        return parsed

    @staticmethod
    def identity(string):
        r"""
        https://stackoverflow.com/questions/69896931/cant-pickle-local-object-argumentparser-init-locals-identity
        """

        return string

    def __contains__(self, name: str):
        if name in self._option_string_actions:
            return True
        return False


class StoreAction(_StoreAction):  # pylint: disable=R0903
    def __init__(  # pylint: disable=R0913
        self,
        option_strings,
        dest,
        nargs=None,
        const=None,
        default=Null,
        type=None,  # pylint: disable=W0622
        choices=None,
        required=False,
        help=None,  # pylint: disable=W0622
        metavar=None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )
        if self.default is not Null:
            warn(
                f"Default value for argument {self.dest} is set to {self.default}, "
                "Default value defined in argument will be overwritten by default value defined in Config",
            )
