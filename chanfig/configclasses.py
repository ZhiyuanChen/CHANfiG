# CHANfiG, Easier Configuration.
# Copyright (c) 2022-Present, CHANfiG Contributors

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

from typing import Any, Type
from warnings import warn

from .config import Config


def configclass(cls=None):
    """
    Construct a Config in [`dataclass`][dataclasses.dataclass] style.

    This decorator creates a Config instance with the provided class attributes.

    See Also:
        [`dataclass`][dataclasses.dataclass]

    Args:
        cls (Type[Any]): The class to be enhanced, provided directly if no parentheses are used.

    Returns:
        A modified class with Config functionalities or a decorator with bound parameters.

    Examples:
        >>> @configclass
        ... class DataloaderConfig:
        ...     batch_size: int = 64
        ...     num_workers: int = 4
        ...     pin_memory: bool = True
        >>> config = DataloaderConfig()
        >>> print(config)
        DataloaderConfig(<class 'chanfig.config.Config'>,
          ('batch_size'): 64
          ('num_workers'): 4
          ('pin_memory'): True
        )
    """

    warn(
        "This decorator is deprecated and may be removed in the future release. "
        "All chanfig classes will copy variable identified in `__annotations__` by default."
        "This decorator is equivalent to inheriting from `Config`.",
        PendingDeprecationWarning,
    )

    def decorator(cls: Type[Any]):
        if not issubclass(cls, Config):
            config_cls = type(cls.__name__, (Config, cls), dict(cls.__dict__))
            cls = config_cls

        return cls

    if cls is None:
        return decorator
    return decorator(cls)
