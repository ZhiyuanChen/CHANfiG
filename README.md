# [CHANfiG](https://chanfig.danling.org)

## Introduction

CHANfiG aims to make your configuration easier.

There are tons of configurable parameters in training a Machine Learning model.
To configure all these parameters, researchers usually need to write gigantic config files, sometimes even thousands of lines.
Most of the configs are just replicates of the default arguments of certain functions, resulting in many unnecessary declarations.
It is also very hard to alter the configurations.
One needs to navigate and open the right configuration file, make changes, save and exit.
These had wasted an uncountable[^uncountable] amount of precious time ~~and are no doubt a crime~~.
Using `argparse` could relieve the burdens to some extent.
However, it takes a lot of work to make it compatible with existing config files, and its lack of nesting limits its potential.

CHANfiG would like to make a change.

You just type the alternations in the command line, and leave everything else to CHANfiG.

CHANfiG is highly inspired by [YACS](https://github.com/rbgirshick/yacs).
Different from the paradigm of YACS(
`your code + a YACS config for experiment E (+ external dependencies + hardware + other nuisance terms ...) = reproducible experiment E`),
The paradigm of CHANfiG is:

`your code + command line arguments (+ optional CHANfiG config + external dependencies + hardware + other nuisance terms ...) = reproducible experiment E (+ optional CHANfiG config for experiment E)`

## Components

A Config is basically a nested dict structure.

However, the default Python dict is hard to manipulate.

The only way to access a dict member is through `dict['name']`, which is obviously extremely complex.
Even worse, if the dict is nested like a config, member access could be something like `dict['parent']['children']['name']`.

Enough is enough, it is time to make a change.

We need attribute-style access, and we need it now.

Although there have been some other works that achieve a similar functionality of attribute-style access to dict members.
Their Config objects either use a separate dict to store information from attribute-style access (EasyDict), which may lead to inconsistency between attribute-style access and dict-style access;
or re-use the existing `__dict__` and redirect dict-style access (ml_collections), which may result in confliction between attributes and members of Config.

To overcome the aforementioned limitations, we inherit the Python built-in `dict` to create `FlatDict`, `NestedDict`, and `Config` objects.

### FlatDict

`FlatDict` improves the default `dict` in 3 aspects.

`FlatDict` also accepts `default_factory`, and can be easily used as `defaultdict`.

#### Dict Operations

`FlatDict` extends the `update` method of the original `dict`, allows passing another `Mapping`, `Iterable` or a path.

Moreover, `FlatDict` comes with `difference` and `intersection`, which makes it very easy to compare a `FlatDict` with other `Mapping`, `Iterable`, or a path.

#### ML Operations

`FlatDict` supports the `to` method similar to PyTorch Tensors.
You can simply convert all member values of `FlatDict` to a certain type or pass to a device in the same way.

`FlatDict` also integrates `cpu`, `gpu`, and `tpu` methods for easier access.

#### IO Operations

`FlatDict` provides `json`, `jsons`, `yaml` and `yamls` methods to dump `FlatDict` object to a file or string.
It also provides `from_json`, `from_jsons`, `from_yaml` and `from_yamls` methods to build a `FlatDict` object from a string or file.

`FlatDict` also includes `dump` and `load` methods which determines the type by its extension and dump/load `FlatDict` object to/from a file.

### NestedDict

Since most Configs are in a nested structure, we further propose a `NestedDict`.

Based on `FlatDict`, `NestedDict` provides `all_keys`, `all_values`, and `all_items` methods to allow iterating over the whole nested structure at once.

`NestedDict` also comes with `apply` method, which made it easier to manipulate nested structures.

### Config

`Config` extends the functionality by supporting `freeze` and `defrost` the dict, and by adding a built-in `ConfigParser` to pare command line arguments.

Note that `Config` also has `default_factory=Config()` by default for convenience.

### Variable

Have one value for multiple names at multiple places? We got you covered.

Just wrap the value with `Variable`, and one alteration will be reflected everywhere.

## Usage

CHANfiG has great backward compatibility with previous configs.

No matter if your old config is json or yaml, you could directly read from them.

And if you are using yacs, just replace `CfgNode` with `Config` and enjoy all the additional benefits that CHANfiG provides.

```python
from chanfig import Config, Variable


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
        dropout = Variable(0.1)
        self.data.batch_size = 64
        self.model.encoder.num_layers = 6
        self.model.decoder.num_layers = 6
        self.model.dropout = dropout
        self.model.encoder.dropout = dropout
        self.model.decoder.dropout = dropout
        self.activation = "GELU"
        self.optim.lr = 1e-3


if __name__ == '__main__':
    # config = Config.load('config.yaml')  # in case you want to read from a yaml
    # config = Config.load('config.json')  # in case you want to read from a json
    # existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # in case you have some config in dict to load
    config = TestConfig()
    config = config.parse()
    # config.update('dataset.yaml')  # in case you want to merge a yaml
    # config.update('dataset.json')  # in case you want to merge a json
    # note that the value of merge will override current values
    config.model.decoder.num_layers = 8
    config.freeze()
    print(config)
    # main(config)
    # config.yaml('config.yaml')  # in case you want to save a yaml
    # config.json('config.json')  # in case you want to save a json
```

All you need to do is just run a line:

```shell
python main.py --model.encoder.num_layers 8 --model.dropout=0.2
```

You could also load a default configure file and make changes based on it:

Note, you must specify `config.parse(default_config='config')` to correctly load the default config.

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8 --model.dropout=0.2
```

If you have made it dump current configurations, this should be in the written file:

```yaml
data:
  batch_size: 64
model:
  encoder:
    num_layers: 8
    dropout: 0.2
  decoder:
    num_layers: 8
    dropout: 0.2
  dropout: 0.2
  activation: GELU
```

```json
{
  "data": {
    "batch_size": 64
  },
  "model": {
    "encoder": {
      "num_layers": 8,
      "dropout": 0.2
    },
    "decoder": {
      "num_layers": 8,
      "dropout": 0.2
    },
    "dropout": 0.2,
    "activation": "GELU"
  }
}
```

Define the default arguments in function, put alterations in CLI, and leave the rest to CHANfiG.

## Installation

Install the most recent stable version on pypi:

```shell
pip install chanfig
```

Install the latest version from source:

```shell
pip install git+https://github.com/ZhiyuanChen/CHANfiG
```

It works the way it should have worked.

## License

CHANfiG is multi-licensed under the following licenses:

- Unlicense
- GNU GPL 2.0 (or any later version)
- MIT
- Apache 2.0
- BSD 2-Clause
- BSD 3-Clause

You can choose any (one or more) of them if you use this work.

`SPDX-License-Identifier: Unlicense OR GPL-2.0-or-later OR MIT OR Apache-2.0 OR BSD-2-Clause OR BSD-3-Clause`

[^uncountable]: fun fact: time is always uncountable.
