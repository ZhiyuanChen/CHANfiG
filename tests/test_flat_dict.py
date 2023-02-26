import copy

from chanfig import FlatDict


class Test:
    dict = FlatDict()
    dict[1] = 2
    dict[3] = 4

    def test_dict(self):
        assert self.dict == FlatDict({1: 2, 3: 4})

    def test_list(self):
        assert self.dict == FlatDict([(1, 2), (3, 4)])
        assert self.dict == FlatDict(*[(1, 2), (3, 4)])

    def test_args(self):
        dict = FlatDict(*[("1", 2), ("3", 4)])
        assert dict["1"] == 2
        assert dict["3"] == 4

    def test_kwargs(self):
        dict = FlatDict(**{"1": 2, "3": 4})
        assert dict["1"] == 2
        assert dict["3"] == 4

    def test_copy(self):
        assert copy.copy(self.dict) == self.dict.copy()
        assert copy.deepcopy(self.dict) == self.dict.deepcopy()
