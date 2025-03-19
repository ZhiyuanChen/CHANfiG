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

from chanfig import Variable, configclass


@configclass
class AncestorConfig:
    __test__ = False
    name: str = "Chang"
    seed: int = Variable(1016, help="random seed")


@configclass
class ChildConfig(AncestorConfig):
    __test__ = False
    name: str = "CHANfiG"


@configclass
class TestConfig(AncestorConfig):
    __test__ = False
    name: str = "CHANfiG"


def test_configclass():
    config = TestConfig()
    assert config.name == "CHANfiG"
    assert "seed" in config
