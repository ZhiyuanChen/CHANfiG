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

from functools import partial

from chanfig import Config, Variable


class DataConfig(Config):
    __test__ = False

    def __init__(self, name):
        super().__init__()
        self.name = name

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

    def post(self):
        self.name = self.name.lower()
        self.id = f"{self.name}_{self.seed}"

    @property
    def data(self):
        return next(iter(self.datas.values())) if self.datas else self.datas["default"]
