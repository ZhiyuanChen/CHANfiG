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
