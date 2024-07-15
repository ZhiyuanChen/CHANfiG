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

from copy import copy, deepcopy
from functools import partial
from io import StringIO

from chanfig import Config, Variable


class DataConfig(Config):
    __test__ = False

    def __init__(self, name, *args, **kwargs):
        super().__init__()
        self.name = name
        self.max_length = 1024
        self.merge(*args, **kwargs)

    def post(self):
        self.name = self.name.lower()


class TestConfig(Config):
    __test__ = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        num_classes = Variable(10)
        self.name = "CHANfiG"
        self.seed = Variable(1013, help="random seed")
        data_factory = partial(DataConfig, name="CIFAR10")
        self.datasets = Config(default_factory=data_factory)
        self.datas = Config(default_factory=data_factory)
        self.datasets.a.num_classes = num_classes
        self.datasets.b.num_classes = num_classes
        self.network.name = "ResNet18"
        self.network.num_classes = num_classes
        self.checkpoint = None

    def post(self):
        self.name = self.name.lower()
        self.id = f"{self.name}_{self.seed}"

    @property
    def data(self):
        return next(iter(self.datas.values())) if self.datas else self.datas["default"]


class Test:

    def test_value(self):
        config = TestConfig()
        assert config.name == "CHANfiG"

    def test_post(self):
        config = TestConfig()
        config.boot()
        assert config.name == "chanfig"
        assert config.id == "chanfig_1013"
        assert config.datasets.a.name == "cifar10"

    def test_parse(self):
        config = TestConfig()
        config.parse(
            [
                "--name",
                "Test",
                "--seed",
                "1014",
                "--datas.a.root",
                "dataset/a",
                "--datas.a.feature_cols",
                "a",
                "b",
                "c",
                "--datas.b.root",
                "dataset/b",
                "--datas.b.label_cols",
                "d",
                "e",
                "f",
                "--checkpoint",
                "path/to/checkpoint.pth",
            ]
        )
        assert config.name == "test"
        assert config.id == "test_1014"
        assert config.checkpoint == "path/to/checkpoint.pth"
        assert config.data.name == "cifar10"
        assert config.datas.a.feature_cols == ["a", "b", "c"]
        assert config.datas.b.label_cols == ["d", "e", "f"]
        assert config.data.max_length == 1024

    def test_nested(self):
        config = TestConfig()
        assert config.network.name == "ResNet18"
        config.network.nested.value = 1

    def test_contains(self):
        config = TestConfig()
        assert "name" in config
        assert "seed" in config
        assert "a.b.c" not in config
        assert "a.b" not in config

    def test_variable(self):
        config = TestConfig()
        assert config.network.num_classes == 10
        config.network.num_classes += 1
        assert config.datasets.a.num_classes == 11

    def test_fstring(self):
        config = TestConfig()
        assert f"seed{config.seed}" == "seed1013"

    def test_load(self):
        config = TestConfig()
        config.name = "Test"
        config.datasets.a.num_classes = 12
        buffer = StringIO()
        config.dump(buffer, method="json")
        assert config == Config.load(buffer, method="json")
        assert config.name == "Test"
        assert config.network.name == "ResNet18"
        assert config.network.num_classes == 12
        assert config.datasets.a.num_classes == 12

    def test_copy(self):
        config = TestConfig()
        assert config.copy() == copy(config)
        assert config.deepcopy() == deepcopy(config)


class Ancestor(Config):
    ancestor = 1


class Parent(Ancestor):
    parent = 2


class ConfigDict(Parent):
    child = 3

    def __init__(self):
        super().__init__()
        self.a = Config()
        self.b = Config({"a": self.a})
        self.c = Variable(Config({"a": self.a}))
        self.d = Config(a=self.a)


class TestConfigDict:
    dict = ConfigDict()

    def test_affinty(self):
        assert id(self.dict.a) == id(self.dict.b.a) == id(self.dict.c.a) == id(self.dict.d.a)

    def test_copy_class_attributes(self):
        config = self.dict.copy_class_attributes(recursive=False)
        assert config.child == 3
        assert "ancestor" not in config
        config = self.dict.copy_class_attributes()
        assert config.ancestor == 1
