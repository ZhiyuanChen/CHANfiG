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

        Parameters
        ----------
        args: Optional[Sequence[str]] = sys.argv[1:]
            The arguments to parse.
        config: Optional[Config] = Config()
            The base config.
        default_config: Optional[str] = None
            The path to a config file.

        Returns
        -------
        config: Config
            The parsed config.

        Raises
        ------
        ValueError
            If default_config is specified but not found in args.

        Examples
        --------
        ```python
        >>> c = Config(a=0)
        >>> c.dict()
        {'a': 0}
        >>> c.parse(['--a', '1', '--b', '2', '--c', '3']).dict()
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
        if self.getattr("frozen", False):
            raise ValueError("Attempting to alter a frozen config. Run config.defrost() to defrost first.")
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

    Attributes
    ----------
    parser: ConfigParser = ConfigParser()
        Parser for command line arguments.
    frozen: bool = False
        If `True`, the config is frozen and cannot be altered.

    Examples
    --------
    ```python
    >>> c = Config(**{"f.n": "chang"})
    >>> c.i.d = 1013
    >>> c.i.d
    1013
    >>> c.d.i
    Config()
    >>> c.freeze()
    Config(
      (f): Config(
        (n): 'chang'
      )
      (i): Config(
        (d): 1013
      )
      (d): Config(
        (i): Config()
      )
    )
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

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Get value from Config.

        Note that `default` will override the `default_factory` if specified.

        Parameters
        ----------
        name: str
        default: Optional[Any] = None

        Returns
        -------
        value: Any
            If name does not exist, return `default`.
            If `default` is not specified, return `default_factory()`.

        Raises
        ------
        KeyError
            If name does not exist and `default`/`default_factory` is not specified.

        **Alias**:

        + `__getitem__`
        + `__getattr__`

        Examples
        --------
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
          (i): Config(
            (d): 1013
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
        Set value of Config.

        Parameters
        ----------
        name: str
        value: Any

        Raises
        ------
        ValueError
            If Config is frozen.

        **Alias**:

        + `__setitem__`
        + `__setattr__`

        Examples
        --------
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
        Delete value from Config.

        Parameters
        ----------
        name: str

        **Alias**:

        + `__delitem__`
        + `__delattr__`

        Examples
        --------
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
    def pop(self, name: str, default: Optional[Any] = None) -> Any:
        r"""
        Pop value from Config.

        Parameters
        ----------
        name: str
        default: Optional[Any] = None

        Examples
        --------
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

    def freeze(self, recursive: bool = True) -> Config:
        r"""
        Freeze the config.

        Parameters
        ----------
        recursive: bool = True

        **Alias**:

        + `lock`

        Examples
        --------
        ```python
        >>> c = Config()
        >>> c.getattr('frozen')
        False
        >>> c.freeze().dict()
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

        Parameters
        ----------
        recursive: bool = True

        **Alias**:

        + `unlock`

        Examples
        --------
        ```python
        >>> c = Config()
        >>> c.getattr('frozen')
        False
        >>> c.freeze().dict()
        {}
        >>> c.getattr('frozen')
        True
        >>> c.defrost().dict()
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

        Examples
        --------
        ```python
        >>> c = Config()
        >>> c.freeze().dict()
        {}
        >>> with c.unlocked():
        ...     c['i.d'] = 1013
        >>> c.dict()
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
        Parse the arguments for config.
        There are three levels of config:

        1. The base config parsed into the function,
        2. The config file located at the path of default_config (if specified),
        3. The config specified in arguments.

        Higher levels override lower levels (i.e. 3 > 2 > 1).

        Parameters
        ----------
            args (Optional[Sequence[str]]): The arguments to parse. Defaults to sys.argv[1:].
            default_config (Optional[str]): The path to a config file.

        Examples
        --------
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
        Add an argument to the parser.

        Examples
        --------
        ```python
        >>> c = Config(a=0)
        >>> c.add_argument("--a", type=int, default=1)
        >>> c.parse([]).dict()
        {'a': 1}

        ```
        """

        self.getattr("parser", ConfigParser()).add_argument(*args, **kwargs)
