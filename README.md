---
title: CHANfiG
summary: Easy Configuration
authors:
    - Zhiyuan Chen
date: 2022-05-04 00:00:00
categories:
    - README
tags:
    - README
---

## Introduction

CHANfiG aims to make your confuration easier.

There are tons of configurable parameters in training a Machine Learning model.
To configure all these parameters, researchers usually need to write giant config files, somtimes even thousdands of lines.
Most of the configs are just replicates of the default arguments of certain functions, resuling many unnessary declarations.
It is also very hard to alter the configurations, one needs to navigade and open the right configuration file, make changes, save and exit.
These had wasted an incountable[^incountable] amount of precisious time ~~and is no doubt a crime~~.
Using `argparse` could relief the burdens to some extent, however, it takes a lot of works to make it compatible with existing config files, and it's lack of nesting limits it's potentials.
CHANfiG would like to make a change.

You just run your experiment, with arguments.

[^incountable]: fun fact: time is always incountable.

CHANfiG is highly inspired by [YACS](https://github.com/rbgirshick/yacs).
Different to the paradigm of YACS(
`your code + a YACS config for experiment E (+ external dependencies + hardware + other nuisance terms ...) = reproducible experiment E`),
The paradigm of CHANfiG is:

`your code + command line arguments (+ optional CHANfiG config + external dependencies + hardware + other nuisance terms ...) = reproducible experiment E (+ optional CHANfiG config for experiment E)`

## Usage

Existing code:

```python
from chanfig import Config, ConfigParser


class Model:
    def __init__(self, encoder, dropout=0.1, activation='ReLU'):
        self.encoder = Encoder(**encoder)
        self.dropout = Dropout(dropout)
        self.activation = getattr(Activation, activation)

def main(config):
    model = Model(**config.model.dict())
    optimizer = Optimizer(**config.optimizer.dict())
    scheduler = Scheduler(**config.scheduler.dict())
    dataset = Dataset(**config.dataset.dict())
    dataloader = Dataloader(**config.dataloader.dict())


if __name__ == '__main__':
    # config = Config.read('config.yaml')  # in case you want to read from a yaml
    # config = Config.read('config.json')  # in case you want to read from a json
    existing_configs = {'a': 1, 'b.c': 2}
    config = Config(**existing_configs)
    parser = ConfigParser()
    config = parser.parse_config(config=config)
    # config.merge('dataset.yaml')
    config.activation = 'GELU'
    # config['meow.is.good'] = True
    main(config)
    # config.yaml('config.yaml')  # in case you want to save a yaml
    # config.json('config.json')  # in case you want to save a json
```

All you needs to do is just run a line:

```shell
python main.py --model.encoder.num_layers 6 --model.dropout 0.2
```

You could also load a default configure file and make changs based on it:

```shell
python main.py --config meow.yaml --model.encoder.num_layers 6 --model.dropout 0.2
```

If you have made it dump current configurations, this should be in the written file:

```yaml
a: 1
b:
  c: 2
model:                                                                                                                                dropout: 0.2
  encoder:
    num_layers: 6
  activation: GELU
```

```json
{
  "a": 1,
  "b": {
    "c": 2
  },
  "model": {
    "encoder": {
      "num_layers": 6
    },
  "dropout": 0.2,
  "activation": "GELU"
  }
}
```

Defing the default arguments in function, put alteration in CLI, and leave the rest to CHANfiG.

It works the way it should have worked.
