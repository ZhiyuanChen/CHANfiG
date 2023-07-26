from functools import partial

from torch import nn

from chanfig import Config, Variable


class Model:
    def __init__(self, encoder, decoder, dropout=0.1, activation="ReLU"):
        # self.encoder = Encoder(**encoder)
        # self.decoder = Decoder(**decoder)
        self.dropout = nn.Dropout(dropout)
        self.activation = getattr(nn, activation)


class DatasetConfig(Config):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.truncation = True
        self.num_classes = 10

    def post(self):
        self.name = self.name.lower()


class ModelConfig(Config):
    def __init__(self):
        super().__init__()
        dropout = Variable(0.1)
        self.encoder.num_layers = 6
        self.decoder.num_layers = 6
        self.dropout = dropout
        self.encoder.dropout = dropout
        self.decoder.dropout = dropout
        self.activation = "GELU"


class TestConfig(Config):
    def __init__(self):
        super().__init__()
        self.name = "CHANfiG"
        self.seed = 1013
        data_factory = partial(DatasetConfig, name="CIFAR10")
        self.datasets = Config(default_factory=data_factory)
        self.dataloader.num_workers = 4
        self.model = ModelConfig()
        self.optim.lr = 1e-3
        self.add_argument("--batch_size", dest="dataloader.batch_size", default=64)
        self.add_argument("--lr", dest="optim.lr")

    @property
    def dataset(self):
        return next(iter(self.datasets.values())) if self.datasets else self.datasets.default

    def post(self):
        self.id = f"{self.name}_{self.seed}"

        def update_layers(config, num_layers):
            if "num_layers" in config:
                config.num_layers = num_layers

        if "num_layers" in self:
            self.apply(update_layers, num_layers=self.num_layers)


def main(config: Config):
    model = Model(**config.model)
    # optimizer = Optimizer(**config.optim)
    # dataset = data.Dataset(**config.datasets)
    # dataloader = data.Dataloader(**config.dataloader)
    print(f"dropout: {model.dropout}")
    assert config.dataset is config.datasets.default
    print(config)


if __name__ == "__main__":
    # config = Config.load('config.yaml')  # in case you want to read from a yaml
    # config = Config.load('config.json')  # in case you want to read from a json
    # existing_configs = {'dataloader.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # in case you have some config in dict to load
    config = TestConfig()
    config = config.parse()
    # config.merge('dataset.yaml')  # in case you want to merge a yaml
    # config.merge('dataset.json')  # in case you want to merge a json
    # note that the value of merge will override current values
    print(config)
    main(config)
    # config.yaml('config.yaml')  # in case you want to save a yaml
    # config.json('config.json')  # in case you want to save a json
