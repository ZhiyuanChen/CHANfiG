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

from chanfig import Variable, configclass


@configclass
class AncestorConfig:
    __test__ = False
    name: str = "Chang"
    seed: int = Variable(1013, help="random seed")


@configclass(recursive=True)
class ChildConfig(AncestorConfig):
    __test__ = False
    name: str = "CHANfiG"


@configclass
class TestConfig(AncestorConfig):
    __test__ = False
    name: str = "CHANfiG"


class Test:
    def test_configclass(self):
        config = TestConfig()
        assert config.name == "CHANfiG"
        assert "seed" not in config

    def test_configclass_recursive(self):
        config = ChildConfig()
        assert config.name == "CHANfiG"
        assert "seed" in config
