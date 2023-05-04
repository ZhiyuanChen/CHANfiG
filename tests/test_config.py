from copy import copy, deepcopy
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
        self.seed = Variable(1013)
        data_factory = partial(DataConfig, name="CIFAR10")
        self.datasets = Config(default_factory=data_factory)
        self.datasets.a.num_classes = num_classes
        self.datasets.b.num_classes = num_classes
        self.network.name = "ResNet18"
        self.network.num_classes = num_classes

    def post(self):
        self.name = self.name.lower()
        self.id = f"{self.name}_{self.seed}"


class Test:
    config = TestConfig()

    def test_value(self):
        assert self.config.name == "CHANfiG"

    def test_post(self):
        self.config.boot()
        assert self.config.name == "chanfig"
        assert self.config.id == "chanfig_1013"
        assert self.config.datasets.a.name == "cifar10"

    def test_parse(self):
        self.config.parse(["--name", "Test", "--seed", "1014"])
        assert self.config.name == "test"
        assert self.config.id == "test_1014"

    def test_nested(self):
        assert self.config.network.name == "ResNet18"
        self.config.network.nested.value = 1

    def test_variable(self):
        assert self.config.network.num_classes == 10
        self.config.network.num_classes += 1
        assert self.config.datasets.a.num_classes == 11

    def test_fstring(self):
        assert f"seed{self.config.seed}" == "seed1014"

    def test_load(self):
        self.config.name = "Test"
        self.config.datasets.a.num_classes = 12
        self.config.dump("tests/test_config.json")
        self.config = self.config.load("tests/test_config.json")
        assert self.config.name == "Test"
        assert self.config.network.name == "ResNet18"
        assert self.config.network.num_classes == 12
        assert self.config.datasets.a.num_classes == 12

    def test_copy(self):
        assert self.config.copy() == copy(self.config)
        assert self.config.deepcopy() == deepcopy(self.config)
