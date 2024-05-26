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

from __future__ import annotations

from typing import List, Optional

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
    no: bool | None
    not_recognized: List[bool]


class Test:

    def test_parse_bool(self):
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
