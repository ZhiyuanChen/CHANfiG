# CHANfiG

Read this in other language: [English](README.md)

在其他语言中阅读本文：[简体中文](README.cn.md)

## Introduction

CHANfiG aims to make your configuration easier.

There are tons of configurable parameters in training a Machine Learning model.
To configure all these parameters, researchers usually need to write gigantic config files, sometimes even thousands of lines.
Most of the configs are just replicates of the default arguments of certain functions, resulting in many unnecessary declarations.
It is also very hard to alter the configurations.
One needs to navigate and open the right configuration file, make changes, save and exit.
These had wasted an incountable[^incountable] amount of precious time ~~and is no doubt a crime~~.
Using `argparse` could relieve the burdens to some extent, however, it takes a lot of work to make it compatible with existing config files, and its lack of nesting limits its potential.
CHANfiG would like to make a change.

You just run your experiment with arguments, and leave everything else to CHANfiG.

CHANfiG is highly inspired by [YACS](https://github.com/rbgirshick/yacs).
Different to the paradigm of YACS(
`your code + a YACS config for experiment E (+ external dependencies + hardware + other nuisance terms ...) = reproducible experiment E`),
The paradigm of CHANfiG is:

`your code + command line arguments (+ optional CHANfiG config + external dependencies + hardware + other nuisance terms ...) = reproducible experiment E (+ optional CHANfiG config for experiment E)`

## Usage

CHANfiG has great backward compatibility with previous configs.

No matter your old config is json or yaml, you could directly read from them.

And if you are using yacs, just replace `CfgNode` with `Config` and enjoy all the additional benefits that CHANfiG provides.

```python
from chanfig import Config


class Model:
    def __init__(self, encoder, dropout=0.1, activation='ReLU'):
        self.encoder = Encoder(**encoder)
        self.dropout = Dropout(dropout)
        self.activation = getattr(Activation, activation)

def main(config):
    model = Model(**config.model)
    optimizer = Optimizer(**config.optimizer)
    scheduler = Scheduler(**config.scheduler)
    dataset = Dataset(**config.dataset)
    dataloader = Dataloader(**config.dataloader)


class TestConfig(Config):
    def __init__(self):
        super().__init__()
        self.data.batch_size = 64
        self.model.encoder.num_layers = 6
        self.model.decoder.num_layers = 6
        self.activation = "GELU"
        self.optim.lr = 1e-3


if __name__ == '__main__':
    # config = Config.read('config.yaml')  # in case you want to read from a yaml
    # config = Config.read('config.json')  # in case you want to read from a json
    # existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # in case you have some config in dict to load
    config = TestConfig()
    config = config.parse()
    # config.merge('dataset.yaml')  # in case you want to merge a yaml
    # config.merge('dataset.json')  # in case you want to merge a json
    # note that the value of merge will surpass current values
    config.model.decoder.num_layers = 8
    config.freeze()
    print(config)
    # main(config)
    # config.yaml('config.yaml')  # in case you want to save a yaml
    # config.json('config.json')  # in case you want to save a json
```

All you needs to do is just run a line:

```shell
python main.py --model.encoder.num_layers 8
```

You could also load a default configure file and make changes based on it:

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8
```

If you have made it dump current configurations, this should be in the written file:

```yaml
data:
  batch_size: 64
model:
  encoder:
    num_layers: 8
  decoder:
    num_layers: 8
  activation: GELU
```

```json
{
  "data": {
    "batch_size": 64
  },
  "model": {
    "encoder": {
      "num_layers": 8
    },
    "decoder": {
      "num_layers": 8
    },
  "activation": "GELU"
  }
}
```

Define the default arguments in function, put alteration in CLI, and leave the rest to CHANfiG.

## Installation

Install most recent stable version on pypi:

```shell
pip install chanfig
```

Install the latest version from source:

```shell
pip install git+https://github.com/ZhiyuanChen/chanfig
```



It works the way it should have worked.

[^incountable]: fun fact: time is always incountable.
