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
from typing import List, Optional

import pytest

from chanfig import Config


class TestConfig(Config):
    __test__ = False

    t: bool
    true: bool
    y: bool
    yes: Optional[bool]
    f: bool
    false: bool
    n: bool
    no: Optional[bool]
    not_recognized: List[bool]


class TestConfigPEP604(Config):
    __test__ = False

    true: bool | None
    false: bool | None
    not_recognized: list[bool]


def test_parse_bool():
    config = TestConfig()
    config.parse(
        [
            "--t",
            "t",
            "--true",
            "true",
            "--y",
            "y",
            "--yes",
            "yes",
            "--f",
            "f",
            "--false",
            "false",
            "--n",
            "n",
            "--no",
            "no",
        ]
    )
    assert config.t and config.true and config.y and config.yes
    assert not config.f and not config.false and not config.n and not config.no

    config = TestConfig()
    config.parse(
        [
            "--t",
            "T",
            "--true",
            "True",
            "--y",
            "Y",
            "--yes",
            "Yes",
            "--f",
            "F",
            "--false",
            "False",
            "--n",
            "N",
            "--no",
            "No",
        ]
    )
    assert config.t and config.true and config.y and config.yes
    assert not config.f and not config.false and not config.n and not config.no


def test_parse_negative_number():
    config = Config()
    config.parse(["--lr", "-0.1"])
    assert config.lr == -0.1
    config = Config()
    config.parse(["--wd", "-1e-4"])
    assert config.wd == -0.0001


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP604 is available in Python 3.10+")
def test_parse_pep604():
    config = TestConfigPEP604()
    config.parse(
        [
            "--true",
            "true",
            "--false",
            "false",
        ]
    )
    assert config.true and not config.false

    config = TestConfigPEP604()
    config.parse(
        [
            "--true",
            "True",
            "--false",
            "False",
        ]
    )
    assert config.true and not config.false


def test_parse_list_annotation_values():
    class ListConfig(Config):
        __test__ = False

        numbers: list[int]

    config = ListConfig()
    config.parse_config(["--numbers", "1", "2"])
    assert config.numbers == [1, 2]
    assert all(isinstance(v, int) for v in config.numbers)


def test_parse_list_from_default_preserves_flat_shape():
    config = Config()
    config.lst = [1, 2]
    config.parse(["--lst", "3", "4"])
    assert config.lst == [3, 4]
    assert all(isinstance(v, int) for v in config.lst)


def test_parse_dict_with_annotation():
    class DictConfig(Config):
        __test__ = False

        mapping: dict[str, int]

    config = DictConfig()
    config.parse_config(["--mapping", "a=1", "b=2"])
    assert config.mapping == {"a": 1, "b": 2}
