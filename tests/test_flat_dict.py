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
from argparse import ArgumentParser
from copy import copy, deepcopy
from typing import Dict, List, Optional, Tuple, Union

import pytest

from chanfig import FlatDict, Variable

# Variables moved from Test class to module level
dict_test = FlatDict()
dict_test[1] = 2
dict_test[3] = 4


def test_dict():
    assert dict_test == FlatDict({1: 2, 3: 4})


def test_list():
    assert dict_test == FlatDict([(1, 2), (3, 4)])


def test_args():
    dict = FlatDict([("1", 2), ("3", 4)])
    assert dict["1"] == 2
    assert dict["3"] == 4


def test_kwargs():
    dict = FlatDict(**{"1": 2, "3": 4})
    assert dict["1"] == 2
    assert dict["3"] == 4


def test_copy():
    assert copy(dict_test) == dict_test.copy()
    assert deepcopy(dict_test) == dict_test.deepcopy()


def test_deepcopy_self_reference():
    d = FlatDict()
    d.self = d
    cloned = deepcopy(d)
    assert cloned is not d
    assert cloned.self is cloned


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


def test_affinty():
    config = ConfigDict()
    assert id(config.a) == id(config.b.a) == id(config.c.a) == id(config.d.a)


def test_validate():
    config = ConfigDict(int_value="1", str_value=1.0, float_value=1)
    assert isinstance(config.int_value, int)
    assert isinstance(config.str_value, str)
    assert isinstance(config.float_value, float)
    config.int_value = "1"
    assert isinstance(config.int_value, int)
    config = ConfigDict(list_int=[1, "2", 3])
    assert all(isinstance(i, int) for i in config.list_int)
    config = ConfigDict(tuple_str=("1", "2", 3))
    assert all(isinstance(i, str) for i in config.tuple_str)
    config = ConfigDict(dict_float={"1": 1.0, "2": 2, "3": "3.0"})
    assert all(isinstance(i, float) for i in config.dict_float.values())
    ConfigDict(int_float=1)
    ConfigDict(int_float=0.5)
    config = ConfigDict(int_float="inf")
    assert config.int_float > 2**32
    ConfigDict(optional_str="1")
    ConfigDict(optional_str=None)
    config = ConfigDict(optional_str=1)
    assert config.optional_str == "1"


def test_construct_file():
    d = FlatDict("tests/test.json")
    assert d == FlatDict({"a": 1, "b": 2, "c": 3})


def test_construct_namespace():
    parser = ArgumentParser()
    parser.add_argument("--name", type=str)
    parser.add_argument("--seed", type=int)
    d = FlatDict(parser.parse_args(["--name", "chang", "--seed", "1016"]))
    assert d.name == "chang"
    assert d.seed == 1016


def test_conflicts():
    d = FlatDict(keys=0, values=1, items=2)
    p = {"keys": 0, "values": 1, "items": 2}
    assert d["keys"] == 0
    assert d["values"] == 1
    assert d["items"] == 2
    assert d.keys() == p.keys()
    assert list(d.values()) == list(p.values())  # dict_values can't be compared directly
    assert d.items() == p.items()


def test_merge_plain_mapping_respects_overwrite():
    d = FlatDict({"a": {"b": 1}})
    d.merge({"a": {"b": 2, "c": 3}}, overwrite=False)
    assert d.a == {"b": 1, "c": 3}

    d = FlatDict({"a": {"b": 1}})
    d.merge({"a": {"b": 2, "c": 3}}, overwrite=True)
    assert d.a == {"b": 2, "c": 3}


class AnnoDict(FlatDict):
    int_value: int
    str_value: str
    float_value: float
    list_int: list[int]
    tuple_str: tuple[str]
    dict_float: dict[str, float]
    union_int_float: Union[int, float]
    optional_str: Optional[str] = None
    nested: list[tuple[int, int]]


@pytest.mark.skipif(sys.version_info < (3, 9), reason="requires python3.9")
def test_anno_validate():
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
    anno_dict.nested = [["1", "2"]]
    assert isinstance(anno_dict.nested, list)
    assert isinstance(anno_dict.nested[0], tuple)
    assert isinstance(anno_dict.nested[0][0], int)
