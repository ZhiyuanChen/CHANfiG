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

import os
from typing import Any

from chanfig import Config, Variable


class DataloaderConfig(Config):
    # You must set the type annotation, or they will not be accessible as a CHANfiG member
    batch_size: int = 64
    num_workers: int = 4
    pin_memory: bool = True
    # If no type annotation is suitable, use `Any`
    unknown: Any = None
    # Attribute without type annotation are used to maintain the internal state of CHANfiG
    attribute = "None"


class TestConfig(Config):
    name: str = "CHANfiG"
    seed: int = 1016
    activation: str = "GELU"
    dataloader: DataloaderConfig = DataloaderConfig()

    def __init__(self):
        super().__init__()
        dropout = Variable(0.1)
        self.optim.lr = 1e-3
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
