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

from collections.abc import Callable, MutableMapping
from copy import deepcopy
from functools import wraps
from inspect import signature
from typing import Any
from warnings import warn

from .nested_dict import NestedDict
from .utils import NULL, Null


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
        ... @registry.register("Module1", default=True)
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
        >>> config = {"module": {"type": "Module", "a": 0, "b": 1}}
        >>> # registry.register(Module)
        >>> module = registry.build(config["module"])
        >>> type(module)
        <class 'chanfig.registry.Module'>
        >>> module.a, module.b
        (0, 1)
        >>> config = {"module": {"type": "NE", "a": 1, "b": 0}}
        >>> module = registry.build(config["module"])
        >>> module.a, module.b
        (1, 0)
        >>> registry = Registry(case_sensitive=False)
        >>> module = registry.register(Module)
        >>> registry
        Registry(
          ('module'): <class 'chanfig.registry.Module'>
        )
        >>> registry.lookup("module")
        <class 'chanfig.registry.Module'>
    """

    override = False
    key = "type"
    default = Null
    case_sensitive = True

    def __init__(
        self,
        override: bool | None = None,
        key: str | None = None,
        fallback: bool | None = None,
        default: Any = None,
        default_factory: Callable | NULL = Null,
        case_sensitive: bool | None = None,
    ):
        super().__init__(default_factory=default_factory, fallback=fallback)
        if override is not None:
            self.setattr("override", override)
        if key is not None:
            self.setattr("key", key)
        if default is not None:
            self.setdefault(default)
        if case_sensitive is not None:
            self.setattr("case_sensitive", case_sensitive)

    def register(
        self, component: Any = Null, name: Any = Null, override: bool = False, default: bool = False
    ) -> Callable:
        r"""
        Register a new component.

        Args:
            component: The component to register.
            name: The name of the component.

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

        override_allowed = override or self.override

        def normalize_name(key: Any) -> Any:
            if isinstance(key, str) and not self.getattr("case_sensitive", False):
                return key.lower()
            return key

        def ensure_available(key: Any) -> None:
            normalized = normalize_name(key)
            if normalized in self and not override_allowed:
                raise ValueError(f"Component with name {key} already registered.")

        def register_component(component_: Any, name_: Any) -> Any:
            ensure_available(name_)
            self.set(name_, component_)
            if default:
                self.setdefault(component_)
            return component_

        # Registry.register(component) / Registry.register(component, name=...)
        if component is not Null and callable(component):
            resolved_name = component.__name__ if name is Null else name
            return register_component(component, resolved_name)

        # Registry.register(component, name=...) for non-callable component
        if component is not Null and name is not Null:
            return register_component(component, name)

        # @Registry.register("Name")
        if component is not Null and name is Null:
            name = component

        # @Registry.register()
        def decorator(component_: Any):
            @wraps(self.register)
            def wrapper():
                resolved_name = component_.__name__ if name is Null else name
                return register_component(component_, resolved_name)

            return wrapper()

        return decorator

    def set(self, name: Any, component: Any) -> None:  # type: ignore[override]
        if isinstance(name, str) and not self.getattr("case_sensitive", False):
            name = name.lower()
        super().set(name, component)

    def lookup(self, name: str, default: Any = Null) -> Any:
        r"""
        Lookup for a component.

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

        if default is Null:
            default = self.getattr("default", Null)
            if default is Null:
                default = None
        if isinstance(name, str) and not self.getattr("case_sensitive", False):
            name = name.lower()
        component = self.get(name, default)
        if isinstance(component, Registry):
            is_fallback = not component
            component = component.getattr("default")
            if is_fallback:
                warn(f"Component {name} is not registered, falling back to {component}.", stacklevel=2)
        if component in (Null, None):
            raise ValueError(f"Component {name} is not registered.")
        return component

    @staticmethod
    def init(cls: Callable, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=W0211
        r"""
        Constructor of component.

        Args:
            cls: The component to construct.
            *args: The arguments to pass to the component.
            **kwargs: The keyword arguments to pass to the component.

        Examples:
            >>> class Module:
            ...     def __init__(self, a, b):
            ...         self.a = a
            ...         self.b = b
            >>> kwargs = {"a": 0, "b": 1}
            >>> module = Registry.init(Module, **kwargs)
            >>> type(module)
            <class 'chanfig.registry.Module'>
            >>> module.a, module.b
            (0, 1)
            >>> kwargs = {"a": 1, "b": 0, "enabled": True}
            >>> if kwargs.get("enabled"):
            ...     module = Registry.init(Module, **kwargs)
            >>> type(module)
            <class 'chanfig.registry.Module'>
            >>> module.a, module.b
            (1, 0)
        """

        sig = signature(cls)
        ignored_kwargs, passing_kwargs = {}, {}
        for k, v in kwargs.items():
            if k in sig.parameters:
                passing_kwargs[k] = v
            else:
                ignored_kwargs[k] = v
        if ignored_kwargs:
            warn(
                f"The following kwargs do not match the signature of {cls.__name__} and will be ignored: {ignored_kwargs}",  # noqa: E501
                stacklevel=2,
            )
        return cls(*args, **passing_kwargs)

    def build(self, name: str | MutableMapping | NULL = Null, *args: Any, **kwargs: Any) -> Any:
        r"""
        Build a component.

        Args:
            name (str | MutableMapping):
                If its a `MutableMapping`, it must contain `key` as a member, the rest will be treated as `**kwargs`.
                Note that values in `kwargs` will override values in `name` if its a `MutableMapping`.
            *args: The arguments to pass to the component.
            **kwargs: The keyword arguments to pass to the component.

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

        key = self.getattr("key", "type")

        if isinstance(name, MutableMapping):
            kwargs_ = deepcopy(name)
            name, kwargs = kwargs_.pop(key), dict(kwargs_, **kwargs)
        elif key in kwargs:
            if name is not Null:
                args = (name,) + args
            name = kwargs.pop(key)

        return self.init(self.lookup(name), *args, **kwargs)  # type: ignore[arg-type]

    def setdefault(self, component: Any) -> Any:  # type: ignore[override]
        self.setattr("default", component)
        return component


class ConfigRegistry(Registry):
    """
    `ConfigRegistry` for components that can be initialised with a `config`.

    `ConfigRegistry` is particularly useful when you want to construct a component from a configuration, such as a
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

    @staticmethod
    def init(cls: Callable, config, *args: Any, **kwargs: Any) -> Any:  # pylint: disable=W0211
        r"""
        Constructor of component.

        Args:
            cls: The component to construct.
            *args: The arguments to pass to the component.
            **kwargs: The keyword arguments to pass to the component.

        Examples:
            >>> class Module:
            ...     def __init__(self, config, a=None, b=None):
            ...         self.config = config
            ...         self.a = config.a if a is None else a
            ...         self.b = config.b if b is None else b
            >>> config = NestedDict({"a": 0, "b": 1})
            >>> module = ConfigRegistry.init(Module, config, b=2)
            >>> module.a, module.b
            (0, 2)
        """

        return cls(config, *args, **kwargs)

    def build(self, config, *args, **kwargs) -> Any:  # type: ignore[override]
        r"""
        Build a component.

        Args:
            config

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

        key = self.getattr("key")
        config_ = deepcopy(config)

        while "." in key:
            key, rest = key.split(".", 1)
            config_, key = getattr(config_, key), rest
        name = getattr(config_, key, None)

        return self.init(self.lookup(name), config, *args, **kwargs)  # type: ignore[arg-type]


GlobalRegistry = Registry()
