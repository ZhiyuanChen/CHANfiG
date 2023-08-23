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

from copy import copy, deepcopy
from typing import Dict, List, Tuple

from pytest import raises

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
    int_value: int
    str_value: str
    float_value: float
    list_int: List[int]
    tuple_str: Tuple[str]
    dict_float: Dict[str, float]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.a = FlatDict()
        self.b = FlatDict({"a": self.a})
        self.c = Variable(FlatDict({"a": self.a}))
        self.d = FlatDict(a=self.a)


class TestConfigDict:
    dict = ConfigDict()

    def test_affinty(self):
        assert id(self.dict.a) == id(self.dict.b.a) == id(self.dict.c.a) == id(self.dict.d.a)

    def test_validate(self):
        ConfigDict(int_value=1, str_value="1", float_value=1.0)
        with raises(TypeError):
            ConfigDict(int_value="1", str_value="1", float_value=1.0)
        with raises(TypeError):
            self.dict.int_value = "1"
            self.dict.validate()
        ConfigDict(list_int=[1, 2, 3])
        with raises(TypeError):
            ConfigDict(list_int=[1, "2", 3])
        ConfigDict(tuple_str=("1", "2", "3"))
        with raises(TypeError):
            ConfigDict(tuple_str=["1", "2", 3])
        ConfigDict(dict_float={"1": 1.0, "2": 2.0, "3": 3.0})
        with raises(TypeError):
            ConfigDict(dict_float={"1": 1.0, "2": 2.0, "3": "3.0"})
