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


from enum import auto

from chanfig import NestedDict

try:
    from enum import StrEnum
except ImportError:
    from strenum import LowercaseStrEnum as StrEnum  # type: ignore[no-redef]


class Task(StrEnum):
    __test__ = False
    Regression = auto()
    Binary = auto()
    MultiClass = auto()
    MultiLabel = auto()


class TaskConfig(NestedDict):
    __test__ = False
    task: Task = "regression"


class TestDump:
    def test_yamls(self):
        config = TaskConfig()
        s = config.yamls()
        assert s == "task: regression\n"
