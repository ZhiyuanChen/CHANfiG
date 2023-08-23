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

from copy import copy, deepcopy

from chanfig import FlatDict, Variable


class Test:
    dict = FlatDict()
    dict[1] = 2
    dict[3] = 4

    def test_dict(self):
        assert self.dict == FlatDict({1: 2, 3: 4})

    def test_list(self):
        assert self.dict == FlatDict([(1, 2), (3, 4)])

    def test_args(self):
        dict = FlatDict([("1", 2), ("3", 4)])
        assert dict["1"] == 2
        assert dict["3"] == 4

    def test_kwargs(self):
        dict = FlatDict(**{"1": 2, "3": 4})
        assert dict["1"] == 2
        assert dict["3"] == 4

    def test_copy(self):
        assert copy(self.dict) == self.dict.copy()
        assert deepcopy(self.dict) == self.dict.deepcopy()


class ConfigDict(FlatDict):
    def __init__(self):
        super().__init__()
        self.a = FlatDict()
        self.b = FlatDict({"a": self.a})
        self.c = Variable(FlatDict({"a": self.a}))
        self.d = FlatDict(a=self.a)


class TestConfigDict:
    dict = ConfigDict()

    def test_affinty(self):
        assert id(self.dict.a) == id(self.dict.b.a) == id(self.dict.c.a) == id(self.dict.d.a)
