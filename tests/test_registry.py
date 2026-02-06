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


import pytest

from chanfig import ConfigRegistry as Registry_


class Registry(Registry_):
    key = "level"


def test_registry():
    registry = Registry()
    assert registry.getattr("key") == "level"


def test_register_case_insensitive_duplicate_explicit():
    registry = Registry(case_sensitive=False)

    class Module:
        pass

    registry.register(Module, "Foo")
    with pytest.raises(ValueError):
        registry.register(Module, "FOO")


def test_register_case_insensitive_duplicate_auto_name():
    registry = Registry(case_sensitive=False)

    class Foo:
        pass

    class FOO:
        pass

    registry.register(Foo)
    with pytest.raises(ValueError):
        registry.register(FOO)


def test_register_named_decorator():
    registry = Registry()

    @registry.register(name="NamedModule")
    class Module:
        pass

    assert Module is registry.lookup("NamedModule")
