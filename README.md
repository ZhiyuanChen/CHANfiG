# [CHANfiG](https://chanfig.danling.org)

## Introduction

In the world of machine learning, configuring models involves dealing with a plethora of parameters.
Researchers often face the daunting task of writing extensive config files, sometimes spanning thousands of lines.
Much of this work is repetitive, copying default arguments and resulting in unnecessary declarations.
Making even minor alterations becomes a challenge, requiring navigation through complex files, editing, saving, and exiting.
This process has consumed an uncountable[^uncountable] amount of valuable time.

CHANfiG would like to make a change.

With CHANfiG, you can make changes directly from the command line, leaving the rest to the system.

CHANfiG is highly inspired by [YACS](https://github.com/rbgirshick/yacs), but adopts a different paradigm:

`your code + command line arguments (+ optional CHANfiG config + external dependencies + hardware + other nuisance terms ...) = reproducible experiment E`

## Components

A Config is basically a nested `dict` structure.

However, working with default Python dictionaries can be cumbersome and complex.

The only way to access a `dict` member is through `dict['name']`, which is obviously extremely complex.
Even worse, if the dict is nested like a config, member access could be something like `dict['parent']['children']['name']`.
For example, accessing a nested member requires using expressions like `dict['parent']['children']['name']`, which can become unwieldy.

Enough is enough, we demand attribute-style access, and we demand it now.

`dict.parent.children.name` is all you need.

Although other solutions have aimed to provide attribute-style access, they often suffer from inconsistencies or conflicts between attribute and dictionary styles.
CHANfiG's components are designed to overcome these issues.

We extend the Python built-in dict to create specialized classes: `FlatDict`, `DefaultDict`, `NestedDict`, `Config`, and `Registry`. Additional components like `Variable` and `ConfigParser` enhance flexibility and ease of use.

### FlatDict

`FlatDict` improves the default `dict` in 3 aspects.

#### Dict Operations

`FlatDict` supports variable interpolation.
Set the value of a member to a string with `${}` and another member name inside, and call `interpolate` method.
The value will be automatically replaced with the value of another member.

`FlatDict` incorporates a `merge` method which allows you to merge a `Mapping`, an `Iterable`, or a path to a `FlatDict`.
Different to `update` method, `merge` assign value instead of replace values, which makes it work better with `DefaultDict`.

Besides, `FlatDict` comes with `difference` and `intersect`, which makes it very easy to compare a `FlatDict` with other `Mapping`, `Iterable`, or a path.

#### ML Operations

`FlatDict` supports `to` method similar to PyTorch Tensors.
You can simply convert all member values of `FlatDict` to a certain type or pass to a device in the same way.

`FlatDict` also integrates `cpu`, `gpu` (`cuda`), and `tpu` (`xla`) methods for easier access.

#### IO Operations

`FlatDict` provides `json`, `jsons`, `yaml` and `yamls` methods to dump `FlatDict` to a file or string.
It also provides `from_json`, `from_jsons`, `from_yaml` and `from_yamls` methods to build a `FlatDict` from a string or file.

`FlatDict` also includes `dump` and `load` methods which determines the type by its extension and dump/load `FlatDict` to/from a file.

`FlatDict` also comes with `apply` and `apply_` method, which made it easier to manipulate the dict structure.

### DefaultDict

To facilities the needs of default values, we incorporate `DefaultDict` which accepts `default_factory` and works just like a `collections.defaultdict`.

### NestedDict

Since most Configs are in a nested structure, we further propose a `NestedDict`.

Based on `DefaultDict`, `NestedDict` provides `all_keys`, `all_values`, and `all_items` methods to allow iterating over the whole nested structure at once.

### Config

`Config` extends the functionality by supporting `freeze` and `defrost`, and by adding a built-in `ConfigParser` to pare command line arguments.

Note that `Config` also has `default_factory=Config` by default for convenience.

### Registry

`Registry` extends `NestedDict` and supports `register`, `lookup`, and `build` to help you register constructors and build objects from a `Config`.

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

Moreover, if you find name in the config is too long for command-line, you could simply call `self.add_argument` with proper `dest` to use a shorter name in command-line, as you do with `argparse`.

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
    # config.merge('dataset.yaml')  # **in** case you want to merge a yaml
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

- Unlicense
- GNU Affero General Public License (3.0 or any later version)
- GNU General Public License (2.0 or any later version)
- MIT License
- BSD License
- Apache License (Version 2.0)

You can choose any (one or more) of these license if you use this work.

`SPDX-License-Identifier: Unlicense OR AGPL-3.0-or-later OR GPL-2.0-or-later OR MIT OR Apache-2.0 OR BSD-4-Clause`

[^uncountable]: fun fact: time is always uncountable.
