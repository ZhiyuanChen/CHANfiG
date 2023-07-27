from pytest import raises

from chanfig import NestedDict, Variable


class Test:
    dict = NestedDict({"i.d": 1013, "f.n": "chang"})

    def test_dict(self):
        assert self.dict == NestedDict({"i.d": 1013, "f.n": "chang"})
        assert self.dict == NestedDict(**{"i.d": 1013, "f.n": "chang"})

    def test_list(self):
        assert self.dict == NestedDict([("i.d", 1013), ("f.n", "chang")])
        assert self.dict == NestedDict(*[("i.d", 1013), ("f.n", "chang")])

    def test_contains(self):
        assert "f" in self.dict
        assert "f.n" in self.dict
        assert "n.f" not in self.dict
        assert "f.n.a" not in self.dict

    def test_sub_dict(self):
        self.dict["n"] = {}
        self.dict["n.l"] = "liu"
        assert self.dict["n.l"] == "liu"

    def test_interpolate(self):
        d = NestedDict({"i.d": 1013, "i.i.d": "${i.d}"})
        d.interpolate()
        assert d.i.d is d.i.i.d

    def test_merge(self):
        d = NestedDict()
        d["a.b.c"] = {"d": 3, "e": {"f": 4}}
        assert d.merge(NestedDict({"a.b.c.d": 3, "a.b.c.e.f": 4})).dict() == {
            "a": {"b": {"c": {"d": 3, "e": {"f": 4}}}}
        }
        d = NestedDict({"a": 1, "b.c": 2, "b.d": 3, "c.d.e": 4, "c.d.f": 5, "c.e": 6})
        n = {"b": {"c": 3, "d": 5}, "c.d.e": 4, "c.d": {"f": 5}, "d": 0}
        assert d.merge(n).dict() == {"a": 1, "b": {"c": 3, "d": 5}, "c": {"d": {"e": 4, "f": 5}, "e": 6}, "d": 0}
        assert NestedDict(a=1, b=1, c=1).union(NestedDict(b="b", c="c", d="d")).dict() == {
            "a": 1,
            "b": "b",
            "c": "c",
            "d": "d",
        }
        d = NestedDict()
        d.c = {"b": {"d": 3, "e": {"f": 4}}}
        assert d.merge(n).dict() == {"c": {"b": {"d": 3, "e": {"f": 4}}, "d": {"f": 5}}, "b": {"c": 3, "d": 5}, "d": 0}
        d = NestedDict()
        assert d.merge(a={1: 1}, b={2: 2}, c={3: 3}).dict() == {"a": {1: 1}, "b": {2: 2}, "c": {3: 3}}
        assert d.merge(d.clone()).dict() == {"a": {1: 1}, "b": {2: 2}, "c": {3: 3}}
        d = NestedDict()
        d["a.b.c"] = {"d": 3, "e": {"f": 4}}
        assert d.merge(NestedDict({"a.b.c.d": 5, "a.b.c.h": 6}), overwrite=False).dict() == {
            "a": {"b": {"c": {"d": 3, "e": {"f": 4}, "h": 6}}}
        }

    def test_validate(self):
        assert NestedDict({"i.d": Variable(1016, type=int, validator=lambda x: x > 0)}).validate() is None
        with raises(TypeError):
            NestedDict({"i.d": Variable(1016, type=str, validator=lambda x: x > 0)}).validate()
        with raises(ValueError):
            NestedDict({"i.d": Variable(-1, type=int, validator=lambda x: x > 0)}).validate()

    def test_dropnull(self):
        from chanfig.utils import Null

        d = NestedDict({"a.b": Null, "b.c.d": Null, "b.c.e.f": Null, "c.d.e.f": Null, "h.j": 1})
        assert d.dict() == {
            "a": {"b": Null},
            "b": {"c": {"d": Null, "e": {"f": Null}}},
            "c": {"d": {"e": {"f": Null}}},
            "h": {"j": 1},
        }
        assert d.dropnull().dict() == {"h": {"j": 1}}
