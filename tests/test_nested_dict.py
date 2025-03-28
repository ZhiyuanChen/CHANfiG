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

from chanfig import NestedDict, Variable

dict_test = NestedDict({"i.d": 1016, "f.n": "chang"})


def test_dict():
    assert dict_test == NestedDict({"i.d": 1016, "f.n": "chang"})
    assert dict_test == NestedDict(**{"i.d": 1016, "f.n": "chang"})


def test_list():
    assert dict_test == NestedDict([("i.d", 1016), ("f.n", "chang")])
    assert dict_test == NestedDict(*[("i.d", 1016), ("f.n", "chang")])


def test_contains():
    assert "f" in dict_test
    assert "f.n" in dict_test
    assert "n.f" not in dict_test
    assert "f.n.a" not in dict_test


def test_sub_dict():
    dict_test["n"] = {}
    dict_test["n.l"] = "liu"
    assert dict_test["n.l"] == "liu"


def test_interpolate():
    d = NestedDict({"i.d": 1016, "i.i.d": "${i.d}"})
    d.interpolate()
    assert d.i.d is d.i.i.d


def test_merge():
    d = NestedDict()
    d["a.b.c"] = {"d": 3, "e": {"f": 4}}
    assert d.merge(NestedDict({"a.b.c.d": 3, "a.b.c.e.f": 4})).dict() == {"a": {"b": {"c": {"d": 3, "e": {"f": 4}}}}}
    d = NestedDict({"a": 1, "b.c": 2, "b.d": 3, "c.d.e": 4, "c.d.f": 5, "c.e": 6})
    m = {"b": {"c": 3, "d": 5}, "c.d.e": 4, "c.d": {"f": 5}, "d": 0}
    assert d.merge(m).dict() == {"a": 1, "b": {"c": 3, "d": 5}, "c": {"d": {"e": 4, "f": 5}, "e": 6}, "d": 0}
    assert NestedDict(a=1, b=1, c=1).union(NestedDict(b="b", c="c", d="d")).dict() == {
        "a": 1,
        "b": "b",
        "c": "c",
        "d": "d",
    }
    n = {"b": 2, "c.d.e": 4, "c.d": {"f": 5}, "d": 0}
    assert d.merge(n).dict() == {"a": 1, "b": 2, "c": {"d": {"e": 4, "f": 5}, "e": 6}, "d": 0}
    d = NestedDict()
    d.c = {"b": {"d": 3, "e": {"f": 4}}}
    assert d.merge(m).dict() == {"c": {"b": {"d": 3, "e": {"f": 4}}, "d": {"f": 5}}, "b": {"c": 3, "d": 5}, "d": 0}
    d = NestedDict()
    assert d.merge(a={1: 1}, b={2: 2}, c={3: 3}).dict() == {"a": {1: 1}, "b": {2: 2}, "c": {3: 3}}
    assert d.merge(d.clone()).dict() == {"a": {1: 1}, "b": {2: 2}, "c": {3: 3}}
    d = NestedDict()
    d["a.b.c"] = {"d": 3, "e": {"f": 4}}
    assert d.merge(NestedDict({"a.b.c.d": 5, "a.b.c.h": 6}), overwrite=False).dict() == {
        "a": {"b": {"c": {"d": 3, "e": {"f": 4}, "h": 6}}}
    }


def test_dropnull():
    from chanfig.utils import Null

    d = NestedDict({"a.b": Null, "b.c.d": Null, "b.c.e.f": Null, "c.d.e.f": Null, "h.j": 1})
    assert d.dict() == {
        "a": {"b": Null},
        "b": {"c": {"d": Null, "e": {"f": Null}}},
        "c": {"d": {"e": {"f": Null}}},
        "h": {"j": 1},
    }
    assert d.dropnull().dict() == {"h": {"j": 1}}


def test_fallback():
    d = NestedDict({"n.d": 0.5, "n.a.d": 0.1, "n.b.l": 6})
    assert d.get("n.a.d", fallback=True) == 0.1
    assert d.get("n.b.d", fallback=True) == 0.5


def test_to_dict():
    d = NestedDict({"i.d": 1016, "f.n": "chang"})
    assert d.dict() == {"i": {"d": 1016}, "f": {"n": "chang"}}
    assert d.dict(flatten=True) == {"i.d": 1016, "f.n": "chang"}


class ConfigDict(NestedDict):
    def __init__(self):
        super().__init__()
        self.a = NestedDict()
        self.b = NestedDict({"a": self.a})
        self.c = Variable(NestedDict({"a": self.a}))
        self.d = NestedDict(a=self.a)


config_dict = ConfigDict()


def test_affinty():
    assert id(config_dict.a) == id(config_dict.b.a) == id(config_dict.c.a) == id(config_dict.d.a)
