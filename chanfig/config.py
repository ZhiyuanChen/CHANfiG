from __future__ import annotations

from argparse import ArgumentParser
from contextlib import contextmanager
from functools import wraps
from sys import argv
from typing import Any, Callable, Iterable, Optional, Sequence
from warnings import warn

from .nested_dict import NestedDict


class ConfigParser(ArgumentParser):  # pylint: disable=C0115
    def parse(
        self,
        args: Optional[Sequence[str]] = None,
        config: Optional[Config] = None,
        default_config: Optional[str] = None,
    ) -> Config:
        r"""
        Parse the arguments for config.

        There are three levels of config:

        1. The base config parsed into the function,
        2. The config file located at the path of default_config (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Args:
            args (Optional[Sequence[str]]): The arguments to parse. Defaults to sys.argv[1:].
            config (Optional[Config]): The base config. Defaults to an empty Config.
            default_config (Optional[str]): The path to a config file.

        Example:
        ```python
        >>> c = Config(a=0)
        >>> c.to(dict)
        {'a': 0}
        >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).to(dict)
        {'a': 1, 'b': 2, 'c': 3}

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
                raise ValueError(f"default_config is set to {default_config}, but not found in args")

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
        if self.getattr("frozen"):
            raise ValueError("Attempting to alter a frozen config. Run config.defrost() to defrost first")
        return func(self, *args, **kwargs)

    return decorator


class Config(NestedDict):
    r"""
    Config is an extension of NestedDict.

    The differences between Config and a regular NestedDict lies in 3 aspects:

    1. Config has `default_factory` set to `Config` and `convert_mapping` set to `True` by default.
    2. Config has a `frozen` attribute, which can be toggled with `freeze`(`lock`), `defrost`(`unlock`), and `unlocked`.
    3. Config has a ConfigParser built-in, and supports `add_argument` and `parse`.

    Note that since Config has `default_factory` set to `Config`,
    accessing anything that does not exist will create a new empty Config sub-attribute.

    It is recommended to call `config.freeze()` or `config.to(NestedDict)` to avoid this behavior.
    """

    default_factory: Optional[Callable]
    frozen: bool = False
    convert_mapping: bool = True
    delimiter: str = "."
    indent: int = 2
    parser: ConfigParser

    def __init__(self, *args, **kwargs):
        self.setattr("frozen", False)
        self.setattr("parser", ConfigParser())
        super().__init__(*args, default_factory=Config, **kwargs)
        self.setattr("convert_mapping", True)

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from Config.

        `__getitem__` and `__getattr__` are alias of this method.

        Note that default here will override the default_factory if specified.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> d = Config()
        >>> d['i.d'] = 1013
        >>> d.get('i.d')
        1013
        >>> d['i.d']
        1013
        >>> d.i.d
        1013
        >>> d.get('c', 2)
        2
        >>> d.c
        Config()
        >>> del d.c
        >>> d.freeze()
        Config(
          (i): NestedDict(
            (d): 1013
          )
        )
        >>> d.c
        Traceback (most recent call last):
        KeyError: 'Config does not contain c'

        ```
        """

        if name in self or not self.getattr("frozen"):
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
        Set value of Config.

        `__setitem__` and `__setattr__` are alias of this method.

        Args:
            name (str): Key name.
            value (Any): Value to set.

        Example:
        ```python
        >>> c = Config()
        >>> c['i.d'] = 1013
        >>> c.i.d
        1013
        >>> c.freeze().to(dict)
        {'i': {'d': 1013}}
        >>> c['i.d'] = 1031
        Traceback (most recent call last):
        ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first
        >>> c.defrost().to(dict)
        {'i': {'d': 1013}}
        >>> c['i.d'] = 1031
        >>> c.i.d
        1031

        ```
        """

        return super().set(name, value, convert_mapping)

    __setitem__ = set
    __setattr__ = set

    @frozen_check
    def delete(self, name: str) -> None:
        r"""
        Remove value from Config.

        `__delitem__`, `__delattr__` and `remove` are alias of this method.

        Args:
            name (str): Key name.

        Example:
        ```python
        >>> d = Config(d=1016, n='chang')
        >>> d.d
        1016
        >>> d.n
        'chang'
        >>> d.delete('d')
        >>> "d" in d
        False
        >>> d.d
        Config()
        >>> "d" in d
        True
        >>> del d.n
        >>> d.n
        Config()
        >>> del d.f
        Traceback (most recent call last):
        KeyError: 'f'

        ```
        """

        super().remove(name)

    __delitem__ = delete
    __delattr__ = delete
    remove = delete

    @frozen_check
    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Pop value from Config.

        Args:
            name (str): Key name.
            default (Optional[Any]): Default value if name does not present.

        Example:
        ```python
        >>> c = Config()
        >>> c['i.d'] = 1013
        >>> c.pop('i.d')
        1013
        >>> c.pop('i.d', True)
        True
        >>> c.freeze().to(dict)
        {'i': {}}
        >>> c['i.d'] = 1031
        Traceback (most recent call last):
        ValueError: Attempting to alter a frozen config. Run config.defrost() to defrost first
        >>> c.defrost().to(dict)
        {'i': {}}
        >>> c['i.d'] = 1031
        >>> c.pop('i.d')
        1031

        ```
        """

        return super().pop(name, default)

    def freeze(self, recursive: bool = True) -> Config:
        r"""
        Freeze the config.

        `lock` is an alias of this method.

        Args:
            recursive (bool): freeze all sub-configs recursively. Defaults to True.

        Example:
        ```python
        >>> c = Config()
        >>> c.getattr('frozen')
        False
        >>> c.freeze().to(dict)
        {}
        >>> c.getattr('frozen')
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
        Defrost the config.

        `unlock` is an alias of this method.

        Args:
            recursive (bool): defrost all sub-configs recursively. Defaults to True.

        Example:
        ```python
        >>> c = Config()
        >>> c.getattr('frozen')
        False
        >>> c.freeze().to(dict)
        {}
        >>> c.getattr('frozen')
        True
        >>> c.defrost().to(dict)
        {}
        >>> c.getattr('frozen')
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
        Context manager which temporarily unlocks the config.

        Example:
        ```python
        >>> c = Config()
        >>> c.freeze().to(dict)
        {}
        >>> with c.unlocked():
        ...     c['i.d'] = 1013
        >>> c.to(dict)
        {'i': {'d': 1013}}

        ```
        """

        was_frozen = self.getattr("frozen")
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
        Parse the arguments for config.
        There are three levels of config:

        1. The base config parsed into the function,
        2. The config file located at the path of default_config (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Args:
            args (Optional[Sequence[str]]): The arguments to parse. Defaults to sys.argv[1:].
            default_config (Optional[str]): The path to a config file.

        Example:
        ```python
        >>> c = Config(a=0)
        >>> c.to(dict)
        {'a': 0}
        >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).to(dict)
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        return self.getattr("parser").parse(args, self, default_config)

    parse_config = parse

    def add_argument(self, *args, **kwargs) -> None:
        r"""
        Add an argument to the parser.
        """

        self.getattr("parser").add_argument(*args, **kwargs)
