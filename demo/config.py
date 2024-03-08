import os

from chanfig import Config, Variable, configclass


@configclass
class DataloaderConfig:
    batch_size: int = 64
    num_workers: int = 4
    pin_memory: bool = True


class TestConfig(Config):
    def __init__(self):
        super().__init__()
        dropout = Variable(0.1)
        self.name = "CHANfiG"
        self.seed = 1013
        self.activation = "GELU"
        self.optim.lr = 1e-3
        self.dataloader = DataloaderConfig()
        self.model.encoder.num_layers = 6
        self.model.decoder.num_layers = 6
        self.model.dropout = dropout
        self.model.encoder.dropout = dropout
        self.model.decoder.dropout = dropout
        self.add_argument("--batch_size", dest="data.batch_size")
        self.add_argument("--lr", dest="optim.lr")

    def post(self):
        self.id = f"{self.name}_{self.seed}"


if __name__ == "__main__":
    # config = Config.load('config.yaml')  # read config from a yaml
    # config = Config.load('config.json')  # read config from a json
    existing_config = {"model.encoder.num_layers": 8}
    config = TestConfig()
    config.merge(existing_config)
    # config.merge('dataset.yaml')  # merge config from a yaml
    # config.merge('dataset.json', overwrite=False)  # merge config from a json
    config = config.parse()
    config.model.decoder.num_layers = 8
    config.freeze()
    print(config)
    # main(config)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    print(dir_path)
    config.save(os.path.join(dir_path, "config.yaml"))  # save config to a yaml
    config.save(os.path.join(dir_path, "config.json"))  # save config to a json
