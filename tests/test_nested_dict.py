from chanfig import NestedDict


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
