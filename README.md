# [CHANfiG](https://chanfig.danling.org)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/75f2ee4ba5a64458afb488615e36adcb)](https://app.codacy.com/gh/ZhiyuanChen/CHANfiG/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/75f2ee4ba5a64458afb488615e36adcb)](https://app.codacy.com/gh/ZhiyuanChen/CHANfiG/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![CodeCov](https://codecov.io/gh/ZhiyuanChen/CHANfiG/graph/badge.svg?token=G9WGWCOFQE)](https://codecov.io/gh/ZhiyuanChen/CHANfiG)

[![PyPI - Version](https://img.shields.io/pypi/v/chanfig)](https://pypi.org/project/chanfig/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/chanfig)](https://pypi.org/project/chanfig/)
[![Downloads](https://static.pepy.tech/badge/chanfig/month)](https://chanfig.danling.org)

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](http://unlicense.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

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
`dict.name` and `dict.parent.children.name` is all you need.

Although there have been some other works that achieve a similar functionality of attribute-style access to dict members.
Their Config object either uses a separate dict to store information from attribute-style access (EasyDict), which may lead to inconsistency between attribute-style access and dict-style access;
or re-use the existing `__dict__` and redirect dict-style access (ml_collections), which may result in confliction between attributes and members of Config.

To overcome the aforementioned limitations, we inherit the Python built-in `dict` to create `FlatDict`, `DefaultDict`, `NestedDict`, `Config`, and `Registry`.
We also introduce `Variable` to allow sharing a value across multiple places, and `ConfigParser` to parse command line arguments.

### FlatDict

`FlatDict` improves the default `dict` in 3 aspects.

#### Dict Operations

`FlatDict` incorporates a `merge` method that allows you to merge a `Mapping`, an `Iterable`, or a path to the `FlatDict`.
Different from built-in `update`, `merge` assign values instead of replace, which makes it works better with `DefaultDict`.

Moreover, `FlatDict` comes with `difference` and `intersect`, which makes it very easy to compare a `FlatDict` with other `Mapping`, `Iterable`, or a path.

#### ML Operations

`FlatDict` supports `to` method similar to PyTorch Tensors.
You can simply convert all member values of `FlatDict` to a certain type or pass to a device in the same way.

`FlatDict` also integrates `cpu`, `gpu` (`cuda`), and `tpu` (`xla`) methods for easier access.

#### IO Operations

`FlatDict` provides `json`, `jsons`, `yaml` and `yamls` methods to dump `FlatDict` to a file or string.
It also provides `from_json`, `from_jsons`, `from_yaml` and `from_yamls` methods to build a `FlatDict` from a string or file.

`FlatDict` also includes `dump` and `load` methods which determines the type by its extension and dump/load `FlatDict` to/from a file.

### DefaultDict

To facility the needs of default values, we incorporate `DefaultDict` which accepts `default_factory` and works just like a `collections.defaultdict`.

### NestedDict

Since most Configs are in a nested structure, we further propose a `NestedDict`.

Based on `DefaultDict`, `NestedDict` provides `all_keys`, `all_values`, and `all_items` methods to allow iterating over the whole nested structure at once.

`NestedDict` also comes with `apply` method, which made it easier to manipulate the nested structure.

### Config

`Config` extends the functionality by supporting `freeze` and `defrost`, and by adding a built-in `ConfigParser` to pare command line arguments.

Note that `Config` also has `default_factory=Config()` by default for convenience.

### Registry

`Registry` extends the `NestedDict` and supports `register`, `lookup`, and `build` to help you register constructors and build objects from a `Config`.

### Variable

Have one value for multiple names at multiple places? We got you covered.

Just wrap the value with `Variable`, and one alteration will be reflected everywhere.

`Variable` also supports `type`, `choices`, `validator`, and `required` to ensure the correctness of the value.

To make it even easier, `Variable` also supports `help` to provide a description when using `ConfigParser`.

### ConfigParser

`ConfigParser` extends `ArgumentParser` and provides `parse` and `parse_config` to parse command line arguments.

## Usage

CHANfiG has great backward compatibility with previous configs.

No matter if your old config is json or yaml, you could directly read from them.

And if you are using yacs, just replace `CfgNode` with `Config` and enjoy all the additional benefits that CHANfiG provides.

Moreover, if you find a name in the config is too long for command-line, you could simply call `self.add_argument` with proper `dest` to use a shorter name in command-line, as you do with `argparse`.

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
        self.name = "CHANfiG"
        self.seed = 1013
        self.data.batch_size = 64
        self.model.encoder.num_layers = 6
        self.model.decoder.num_layers = 6
        self.model.dropout = dropout
        self.model.encoder.dropout = dropout
        self.model.decoder.dropout = dropout
        self.activation = "GELU"
        self.optim.lr = 1e-3
        self.add_argument("--batch_size", dest="data.batch_size")
        self.add_argument("--lr", dest="optim.lr")

    def post(self):
        self.id = f"{self.name}_{self.seed}"


if __name__ == '__main__':
    # config = Config.load('config.yaml')  # in case you want to read from a yaml
    # config = Config.load('config.json')  # in case you want to read from a json
    # existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # in case you have some config in dict to load
    config = TestConfig()
    config = config.parse()
    # config.merge('dataset.yaml')  # in case you want to merge a yaml
    # config.merge('dataset.json')  # in case you want to merge a json
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
python main.py --model.encoder.num_layers 8 --model.dropout=0.2 --lr 5e-3
```

You could also load a default configure file and make changes based on it:

Note, you must specify `config.parse(default_config='config')` to correctly load the default config.

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8 --model.dropout=0.2 --lr 5e-3
```

If you have made it dump current configurations, this should be in the written file:

```yaml
activation: GELU
data:
  batch_size: 64
id: CHANfiG_1013
model:
  decoder:
    dropout: 0.1
    num_layers: 6
  dropout: 0.1
  encoder:
    dropout: 0.1
    num_layers: 6
name: CHANfiG
optim:
  lr: 0.005
seed: 1013
```

```json
{
  "name": "CHANfiG",
  "seed": 1013,
  "data": {
    "batch_size": 64
  },
  "model": {
    "encoder": {
      "num_layers": 6,
      "dropout": 0.1
    },
    "decoder": {
      "num_layers": 6,
      "dropout": 0.1
    },
    "dropout": 0.1
  },
  "activation": "GELU",
  "optim": {
    "lr": 0.005
  },
  "id": "CHANfiG_1013"
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

- The Unlicense
- GNU Affero General Public License v3.0 or later
- GNU General Public License v2.0 or later
- BSD 4-Clause "Original" or "Old" License
- MIT License
- Apache License 2.0

You can choose any (one or more) of these licenses if you use this work.

`SPDX-License-Identifier: Unlicense OR AGPL-3.0-or-later OR GPL-2.0-or-later OR BSD-4-Clause OR MIT OR Apache-2.0`

[^uncountable]: fun fact: time is always uncountable.
