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

import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace, _StoreAction
from ast import literal_eval
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import Field
from inspect import isclass
from typing import TYPE_CHECKING, Any
from warnings import warn

from typing_extensions import _should_collect_from_parameters, get_args, get_origin  # type: ignore[attr-defined]

try:
    from types import NoneType
except ImportError:
    NoneType = type(None)  # type: ignore[misc, assignment]

from .nested_dict import NestedDict
from .utils import Null, get_cached_annotations, parse_bool, suggest_key
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
        self._container_actions: dict[str, dict[str, Any]] = {}

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

        self._warn_argument_typos(args, config)
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
            >>> p.parse(['--i.d', '1016', '--f.n', 'chang']).dict()
            {'i': {'d': 1016}, 'f': {'n': 'chang'}}

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
            RuntimeError: ConfigParser has default_config set to config, but it is not found in args.

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

        def _is_negative_number(token: str) -> bool:
            if not isinstance(token, str) or not token.startswith("-") or token.startswith("--"):
                return False
            try:
                float(token)
                return True
            except ValueError:
                return False

        def _normalize_args(arg_list: Sequence[str]) -> list[str]:
            normalized: list[str] = []
            for token in arg_list:
                if normalized:
                    prev = normalized[-1]
                    if (
                        _is_negative_number(token)
                        and isinstance(prev, str)
                        and prev.startswith("-")
                        and not _is_negative_number(prev)
                        and "=" not in prev
                    ):
                        normalized[-1] = f"{prev}={token}"
                        continue
                normalized.append(token)
            return normalized

        if args is not None:
            args = list(args)
        args = _normalize_args(args or [])

        # add the command-line arguments
        key_value_args: list[list[str]] = []
        for arg in args:
            if arg == "--":
                break
            if arg.startswith("-"):
                if _is_negative_number(arg):
                    if key_value_args:
                        key_value_args[-1].append(arg)
                    continue
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

        self._warn_argument_typos(args, config)
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
        for dest, meta in self._container_actions.items():
            if dest not in parsed:
                continue
            parsed_value = parsed[dest]
            if parsed_value in (Null, None):
                continue
            parsed[dest] = self._convert_container_value(parsed_value, meta)
        return parsed

    def error(self, message: str) -> None:  # type: ignore[override]
        """
        Override default error handler to provide typo suggestions for arguments.
        """

        suggestions = []
        if "unrecognized arguments:" in message:
            unknowns = message.split("unrecognized arguments:", 1)[1].strip().split()
            candidates = self._suggestion_candidates()
            for unknown in unknowns:
                token = unknown.split("=", 1)[0]
                suggestion = suggest_key(token, candidates, cutoff=0.6)
                if suggestion:
                    suggestions.append(f"{unknown} -> {suggestion}")
        if suggestions:
            message = f"{message}\nDid you mean:\n  " + "\n  ".join(suggestions)
        super().error(message)

    def _suggestion_candidates(self) -> list[str]:
        candidates: list[str] = []
        for action in self._actions:
            candidates.extend(getattr(action, "option_strings", ()))
            dest = getattr(action, "dest", None)
            if dest:
                candidates.append(f"--{dest}")
        return candidates

    def _warn_argument_typos(self, args: Sequence[str] | None, config: Config | None) -> None:
        if config is None:
            return
        known_keys = set(config.all_keys())
        if not known_keys:
            return
        if args is None:
            args = sys.argv[1:]
        for token in self._extract_option_tokens(args):
            if token in known_keys:
                continue
            suggestion = suggest_key(token, known_keys, cutoff=0.6)
            if suggestion:
                warn(
                    f"Unrecognized argument '--{token}'. Did you mean '--{suggestion}'?",  # noqa: B028
                    RuntimeWarning,
                    stacklevel=2,
                )

    @staticmethod
    def _extract_option_tokens(args: Sequence[str]) -> list[str]:
        tokens: list[str] = []
        for arg in args:
            if not arg.startswith("--"):
                continue
            token = arg[2:]
            if "=" in token:
                token = token.split("=", 1)[0]
            tokens.append(token)
        return tokens

    def add_config_arguments(self, config: Config):
        for key, dtype in get_cached_annotations(config).items():
            self.add_config_argument(key, dtype=dtype)
        for key, value in config.all_items():
            self.add_config_argument(key, value)

    def add_config_argument(self, key, value: Any | None = None, dtype: type | None = None):
        if dtype is None:
            if isinstance(value, Variable):
                dtype = value._type or value.dtype  # pylint: disable=W0212
            elif isinstance(value, Field):
                dtype = value.type  # type: ignore[assignment]
            elif value is not None:
                dtype = type(value)
        if _should_collect_from_parameters(dtype):
            args = get_args(dtype)
            if len(args) == 2 and NoneType in args:
                dtype = args[0] if args[0] is not NoneType else args[1]
        name = "--" + key
        if name not in self:
            help = None  # pylint: disable=W0622
            if isinstance(value, Variable):
                help = value._help  # pylint: disable=W0212
            elif isinstance(value, Field):
                help = value.metadata.get("help")
            container_meta = self._infer_container_argument(dtype, value)
            if container_meta is not None:
                nargs = container_meta.get("nargs", "+")
                action = self.add_argument(
                    name,
                    nargs=nargs,
                    type=container_meta["item_parser"],
                    help=help,
                    dest=key,
                )
                self._container_actions[key] = container_meta
                return action
            if dtype is None or not isclass(dtype):
                return self.add_argument(name, help=help, dest=key)
            if issubclass(dtype, bool):
                return self.add_argument(name, type=parse_bool, help=help, dest=key)
            return self.add_argument(name, type=dtype, help=help, dest=key)

    def _infer_container_argument(self, dtype: Any, value: Any | None = None) -> dict[str, Any] | None:
        """
        Determine if the argument represents a container (list/tuple/set/dict) and
        provide parsing metadata when applicable.
        """

        def first_type(iterable):
            try:
                item = next(iter(iterable))
            except Exception:
                return None
            return type(item)

        origin = get_origin(dtype) or dtype
        args = get_args(dtype)
        container_type = None
        key_type = None
        value_type = None
        item_type = None
        tuple_item_types = None

        if origin in (list, tuple, set, dict):
            container_type = origin
            if origin is dict and args:
                key_type, value_type = (args + (None, None))[:2]
            elif args:
                if origin is tuple and len(args) > 1 and args[-1] is not Ellipsis:
                    tuple_item_types = args
                else:
                    item_type = args[0]
        elif isinstance(dtype, type) and issubclass(dtype, (list, tuple, set, dict)):
            container_type = dtype

        if container_type is None:
            # Try to infer from value when dtype is unavailable
            if isinstance(value, (list, tuple, set)):
                container_type = type(value)
                item_type = first_type(value)
            elif isinstance(value, dict):
                container_type = dict
                key_type = first_type(value.keys())
                value_type = first_type(value.values())
        else:
            if item_type is None and isinstance(value, (list, tuple, set)):
                item_type = first_type(value)
            if container_type is dict and isinstance(value, dict):
                if key_type is None:
                    key_type = first_type(value.keys())
                if value_type is None:
                    value_type = first_type(value.values())

        if container_type is None:
            return None

        def build_item_parser(expected_type):
            if expected_type is None:
                return self.identity
            if expected_type in (bool,):
                return parse_bool
            if isclass(expected_type):
                return expected_type
            origin_type = get_origin(expected_type)
            if origin_type in (list, tuple, set, dict):
                return self.identity
            return self.identity

        nargs = "+"
        if container_type is tuple and tuple_item_types is not None:
            item_parser = self.identity
            tuple_item_parsers = [build_item_parser(item) for item in tuple_item_types]
            nargs = len(tuple_item_parsers)  # type: ignore[assignment]
            return {
                "container_type": container_type,
                "item_parser": item_parser,
                "item_type": item_type,
                "tuple_item_parsers": tuple_item_parsers,
                "nargs": nargs,
            }
        if container_type is dict:
            key_parser = build_item_parser(key_type)
            value_parser = build_item_parser(value_type)

            def parse_kv(token: str):
                if "=" not in token:
                    raise ArgumentTypeError(f"Expected KEY=VALUE, got {token!r}")
                raw_key, raw_value = token.split("=", 1)
                return key_parser(raw_key), value_parser(raw_value)

            item_parser = parse_kv
        else:
            item_parser = build_item_parser(item_type)

        return {
            "container_type": container_type,
            "item_parser": item_parser,
            "item_type": item_type,
            "nargs": nargs,
        }

    def _convert_container_value(self, value: Any, meta: Mapping[str, Any]) -> Any:
        container_type = meta["container_type"]
        if container_type is dict:
            if isinstance(value, dict):
                return value
            pairs: list[tuple] = []
            if isinstance(value, (list, tuple, set)):
                for item in value:
                    if isinstance(item, dict):
                        pairs.extend(item.items())
                    elif isinstance(item, (list, tuple)) and len(item) == 2:
                        pairs.append((item[0], item[1]))
                    else:
                        raise ArgumentTypeError(f"Cannot parse {item!r} as key-value pair.")
            else:
                raise ArgumentTypeError(f"Cannot parse {value!r} as key-value pairs.")
            return dict(pairs)

        if container_type is list:
            if isinstance(value, list):
                return value
            if isinstance(value, tuple):
                return list(value)
            return [value]

        if container_type is tuple:
            tuple_item_parsers = meta.get("tuple_item_parsers")
            if tuple_item_parsers:
                if isinstance(value, tuple):
                    items = list(value)
                elif isinstance(value, list):
                    items = value
                else:
                    items = [value]
                if len(items) != len(tuple_item_parsers):
                    raise ArgumentTypeError(f"Expected {len(tuple_item_parsers)} values for tuple, got {len(items)}.")
                converted = []
                for parser, item in zip(tuple_item_parsers, items):
                    try:
                        converted.append(parser(item))
                    except (TypeError, ValueError) as exc:
                        raise ArgumentTypeError(f"Cannot parse tuple item {item!r}.") from exc
                return tuple(converted)
            if isinstance(value, tuple):
                return value
            if isinstance(value, list):
                return tuple(value)
            return (value,)

        if container_type is set:
            if isinstance(value, set):
                return value
            if isinstance(value, (list, tuple)):
                return set(value)
            return {value}
        return value

    def merge_default_config(self, parsed, default_config: str, no_default_config_action: str = "raise") -> NestedDict:
        if default_config in parsed:
            path = parsed[default_config]
            warn(
                f"{self.__class__.__name__} has 'default_config={path}' specified, "
                "its values will override values in Config"
            )
            return NestedDict.load(path).merge(parsed)
        message = f"{self.__class__.__name__} has default_config set to {default_config}, but it is not found in args."
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
