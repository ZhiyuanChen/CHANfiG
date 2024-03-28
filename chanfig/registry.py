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

from collections.abc import Callable, MutableMapping
from copy import deepcopy
from functools import wraps
from typing import Any

from .nested_dict import NestedDict


class Registry(NestedDict):
    """
    `Registry` for components.

    `Registry` provides 3 core functionalities:

    - Register a new component.
    - Lookup for a component.
    - Build a component.

    To facilitate the usage scenario, `registry` is designed to be a decorator.
    You could register a component by simply calling `registry.register`, and it will be registered with its name.
    You may also specify the name of the component by calling `registry.register(name="ComponentName")`.

    `build` makes it easy to construct a component from a configuration.
    `build` automatically determines the component to construct by the `name` field in the configuration.
    So you could either call `registry.build(config)` or `registry.build(**config)`.
    Beyond this, `build` is just a syntax sugar for `registry.init(registry.lookup(name), *args, **kwargs)`.

    `lookup` is used to lookup for a component by its name.
    By default, `lookup` internally calls `NestedDict.get`, but you may override it to provide more functionalities.

    `init` is used to construct a component.
    By default, `init` internally calls `cls(*args, **kwargs)`, but you may override it to provide more functionalities.

    Notes:
        `Registry` inherits from `NestedDict`.

        Therefore, `Registry` comes in a nested structure by nature.
        You could create a sub-registry by simply calling `registry.sub_registry = Registry`,
        and access through `registry.sub_registry.register()`.

    See Also:
        [`ConfigRegistry`][chanfig.ConfigRegistry]: Optimised for components that can be initialised with a `config`.

    Examples:
        >>> registry = Registry()
        >>> @registry.register
        ... @registry.register("Module1")
        ... class Module:
        ...     def __init__(self, a, b):
        ...         self.a = a
        ...         self.b = b
        >>> module = registry.register(Module, "Module2")
        >>> registry
        Registry(
          ('Module1'): <class 'chanfig.registry.Module'>
          ('Module'): <class 'chanfig.registry.Module'>
          ('Module2'): <class 'chanfig.registry.Module'>
        )
        >>> module = registry.register(Module, "Module")
        Traceback (most recent call last):
        ValueError: Component with name Module already registered.
        >>> registry.lookup("Module")
        <class 'chanfig.registry.Module'>
        >>> config = {"module": {"name": "Module", "a": 1, "b": 2}}
        >>> # registry.register(Module)
        >>> module = registry.build(config["module"])
        >>> type(module)
        <class 'chanfig.registry.Module'>
        >>> module.a
        1
        >>> module.b
        2
    """

    override: bool = False

    def __init__(self, override: bool | None = None, key: str = "name", fallback: bool | None = None):
        super().__init__(fallback=fallback)
        self.setattr("key", key)
        if override is not None:
            self.setattr("override", override)

    def register(self, component: Any = None, name: Any | None = None, override: bool = False) -> Callable:
        r"""
        Register a new component.

        Args:
            component: The component to register.
            name: The name of the component.

        Returns:
            component: The registered component.
                Registered component are expected to be `Callable`.

        Raises:
            ValueError: If the component with the same name already registered and `Registry.override=False`.

        Examples:
            >>> registry = Registry()
            >>> @registry.register
            ... @registry.register("Module1")
            ... class Module:
            ...     def __init__(self, a, b):
            ...         self.a = a
            ...         self.b = b
            >>> module = registry.register(Module, "Module2")
            >>> registry
            Registry(
              ('Module1'): <class 'chanfig.registry.Module'>
              ('Module'): <class 'chanfig.registry.Module'>
              ('Module2'): <class 'chanfig.registry.Module'>
            )
        """

        if name in self and not (override or self.override):
            raise ValueError(f"Component with name {name} already registered.")

        # Registry.register()
        if name is not None:
            self.set(name, component)
            return component
        # @Registry.register
        if callable(component) and name is None:
            self.set(component.__name__, component)
            return component

        # @Registry.register()
        def decorator(name: Any | None = None):
            @wraps(self.register)
            def wrapper(component):
                if name is None:
                    self.set(component.__name__, component)
                else:
                    self.set(name, component)
                return component

            return wrapper

        return decorator(component)

    def lookup(self, name: str) -> Any:
        r"""
        Lookup for a component.

        Args:
            name:

        Returns:
            (Any): The component.

        Raises:
            KeyError: If the component is not registered.

        Examples:
            >>> registry = Registry()
            >>> @registry.register
            ... class Module:
            ...     def __init__(self, a, b):
            ...         self.a = a
            ...         self.b = b
            >>> registry.lookup("Module")
            <class 'chanfig.registry.Module'>
        """

        return self[name]

    @staticmethod
    def init(cls: Callable, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=W0211
        r"""
        Constructor of component.

        Args:
            cls: The component to construct.
            *args: The arguments to pass to the component.
            **kwargs: The keyword arguments to pass to the component.

        Returns:
            (Any):

        Examples:
            >>> class Module:
            ...     def __init__(self, a, b):
            ...         self.a = a
            ...         self.b = b
            >>> kwargs = {"a": 1, "b": 2}
            >>> module = Registry.init(Module, **kwargs)
            >>> type(module)
            <class 'chanfig.registry.Module'>
            >>> module.a
            1
            >>> module.b
            2
        """

        return cls(*args, **kwargs)

    def build(self, name: str | MutableMapping | None = None, *args: Any, **kwargs: Any) -> Any:
        r"""
        Build a component.

        Args:
            name (str | MutableMapping):
                If its a `MutableMapping`, it must contain `key` as a member, the rest will be treated as `**kwargs`.
                Note that values in `kwargs` will override values in `name` if its a `MutableMapping`.
            *args: The arguments to pass to the component.
            **kwargs: The keyword arguments to pass to the component.

        Returns:
            (Any):

        Raises:
            KeyError: If the component is not registered.

        Examples:
            >>> registry = Registry(key="model")
            >>> @registry.register
            ... class Module:
            ...     def __init__(self, a, b):
            ...         self.a = a
            ...         self.b = b
            >>> config = {"module": {"model": "Module", "a": 1, "b": 2}}
            >>> # registry.register(Module)
            >>> module = registry.build(**config["module"])
            >>> type(module)
            <class 'chanfig.registry.Module'>
            >>> module.a
            1
            >>> module.b
            2
            >>> module = registry.build(config["module"], a=2)
            >>> module.a
            2
        """

        if isinstance(name, MutableMapping):
            name = deepcopy(name)
            name, kwargs = name.pop(self.getattr("key", "name")), dict(name, **kwargs)  # type: ignore[arg-type]
        if name is None:
            name, kwargs = kwargs.pop(self.getattr("key")), dict(**kwargs)
        return self.init(self.lookup(name), *args, **kwargs)  # type: ignore[arg-type]


class ConfigRegistry(Registry):
    """
    `ConfigRegistry` for components that can be initialised with a `config`.

    `ConfigRegistry` is purcutularly useful when you want to construct a component from a configuration, such as a
    Hugginface Transformers model.

    See Also:
        [`Registry`][chanfig.Registry]: General purpose Registry.

    Examples:
        >>> from dataclasses import dataclass, field
        >>> @dataclass
        ... class Config:
        ...     a: int
        ...     b: int
        ...     mode: str = "proj"
        >>> registry = ConfigRegistry(key="mode")
        >>> @registry.register("proj")
        ... class Proj:
        ...     def __init__(self, config):
        ...         self.a = config.a
        ...         self.b = config.b
        >>> @registry.register("inv")
        ... class Inv:
        ...     def __init__(self, config):
        ...         self.a = config.b
        ...         self.b = config.a
        >>> registry
        ConfigRegistry(
          ('proj'): <class 'chanfig.registry.Proj'>
          ('inv'): <class 'chanfig.registry.Inv'>
        )
        >>> config = Config(a=0, b=1)
        >>> module = registry.build(config)
        >>> module.a, module.b
        (0, 1)
        >>> config = Config(a=0, b=1, mode="inv")
        >>> module = registry.build(config)
        >>> module.a, module.b
        (1, 0)
        >>> @dataclass
        ... class ModuleConfig:
        ...     a: int = 0
        ...     b: int = 1
        ...     mode: str = "proj"
        >>> @dataclass
        ... class NestedConfig:
        ...     module: ModuleConfig = field(default_factory=ModuleConfig)
        >>> nested_registry = ConfigRegistry(key="module.mode")
        >>> @nested_registry.register("proj")
        ... class Proj:
        ...     def __init__(self, config):
        ...         self.a = config.module.a
        ...         self.b = config.module.b
        >>> @nested_registry.register("inv")
        ... class Inv:
        ...     def __init__(self, config):
        ...         self.a = config.module.b
        ...         self.b = config.module.a
        >>> nested_config = NestedConfig()
        >>> module = nested_registry.build(nested_config)
        >>> module.a, module.b
        (0, 1)
    """

    def build(self, config) -> Any:  # type: ignore[override]
        r"""
        Build a component.

        Args:
            config

        Returns:
            (Any):

        Raises:
            KeyError: If the component is not registered.

        Examples:
            >>> from dataclasses import dataclass, field
            >>> registry = ConfigRegistry(key="module.mode")
            >>> @registry.register("proj")
            ... class Proj:
            ...     def __init__(self, config):
            ...         self.a = config.module.a
            ...         self.b = config.module.b
            >>> @registry.register("inv")
            ... class Inv:
            ...     def __init__(self, config):
            ...         self.a = config.module.b
            ...         self.b = config.module.a
            >>> @dataclass
            ... class ModuleConfig:
            ...     a: int = 0
            ...     b: int = 1
            ...     mode: str = "proj"
            >>> @dataclass
            ... class Config:
            ...     module: ModuleConfig = field(default_factory=ModuleConfig)
            >>> config = Config()
            >>> module = registry.build(config)
            >>> type(module)
            <class 'chanfig.registry.Proj'>
            >>> module.a, module.b
            (0, 1)
            >>> type(module)
            <class 'chanfig.registry.Proj'>
        """

        key = self.key
        config_ = deepcopy(config)

        while "." in key:
            key, rest = key.split(".", 1)
            config_, key = getattr(config_, key), rest
        name = getattr(config_, key)

        return self.init(self.lookup(name), config)  # type: ignore[arg-type]


GlobalRegistry = Registry()
