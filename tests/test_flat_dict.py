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

import sys
from argparse import ArgumentParser
from copy import copy, deepcopy
from typing import Dict, List, Optional, Tuple, Union

import pytest
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
    int_float: Union[int, float]
    optional_str: Optional[str]

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
        self.dict.int_value = "1"
        assert isinstance(self.dict.int_value, int)
        ConfigDict(list_int=[1, 2, 3])
        with raises(TypeError):
            ConfigDict(list_int=[1, "2", 3])
        ConfigDict(tuple_str=("1", "2", "3"))
        with raises(TypeError):
            ConfigDict(tuple_str=["1", "2", 3])
        ConfigDict(dict_float={"1": 1.0, "2": 2.0, "3": 3.0})
        with raises(TypeError):
            ConfigDict(dict_float={"1": 1.0, "2": 2.0, "3": "3.0"})
        ConfigDict(int_float=1)
        ConfigDict(int_float=0.5)
        with raises(TypeError):
            ConfigDict(int_float="inf")
        ConfigDict(optional_str="1")
        ConfigDict(optional_str=None)
        with raises(TypeError):
            ConfigDict(optional_str=1)

    def test_construct_file(self):
        d = FlatDict("tests/test.json")
        assert d == FlatDict({"a": 1, "b": 2, "c": 3})

    def test_construct_namespace(self):
        parser = ArgumentParser()
        parser.add_argument("--name", type=str)
        parser.add_argument("--seed", type=int)
        d = FlatDict(parser.parse_args(["--name", "chang", "--seed", "1016"]))
        assert d.name == "chang"
        assert d.seed == 1016

    def test_conflicts(self):
        d = FlatDict(keys=0, values=1, items=2)
        p = {"keys": 0, "values": 1, "items": 2}
        assert d["keys"] == 0
        assert d["values"] == 1
        assert d["items"] == 2
        assert d.keys() == p.keys()
        assert list(d.values()) == list(p.values())  # dict_values can't be compared directly
        assert d.items() == p.items()


class AnnoDict(FlatDict):
    int_value: int
    str_value: str
    float_value: float
    list_int: list[int]
    tuple_str: tuple[str]
    dict_float: dict[str, float]
    union_int_float: Union[int, float]
    optional_str: Optional[str] = None
    wont_convert: list[tuple[int, int]]


class TestAnnoDict:

    @pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9")
    def test_validate(self):
        anno_dict = AnnoDict()
        anno_dict.int_value = "1"
        assert isinstance(anno_dict.int_value, int)
        anno_dict.str_value = 1
        assert isinstance(anno_dict.str_value, str)
        anno_dict.float_value = 1
        assert isinstance(anno_dict.float_value, float)
        anno_dict.list_int = ("1", "2", "3")
        assert isinstance(anno_dict.list_int, list)
        anno_dict.tuple_str = [1, 2, 3]
        assert isinstance(anno_dict.tuple_str, tuple)
        anno_dict.dict_float = [("a", 1), ("b", 2)]
        assert isinstance(anno_dict.dict_float, dict)
        assert isinstance(anno_dict.dict_float["a"], int)
        anno_dict.union_int_float = "1"
        assert isinstance(anno_dict.union_int_float, int)
        assert anno_dict.optional_str is None
        anno_dict.optional_str = 1
        assert isinstance(anno_dict.optional_str, str)
        anno_dict.wont_convert = [("1", "2")]
        assert isinstance(anno_dict.wont_convert, list)
        assert isinstance(anno_dict.wont_convert[0][0], str)
