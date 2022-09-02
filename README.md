# CHANfiG

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
    model = Model(**config.model)
    optimizer = Optimizer(**config.optimizer)
    scheduler = Scheduler(**config.scheduler)
    dataset = Dataset(**config.dataset)
    dataloader = Dataloader(**config.dataloader)


if __name__ == '__main__':
    # config = Config.read('config.yaml')  # in case you want to read from a yaml
    # config = Config.read('config.json')  # in case you want to read from a json
    existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    config = Config(**existing_configs)
    config = config.parse()
    # CLI arguments: python xxx.py --activation GELU
    # config.merge('dataset.yaml')
    config.model.decoder.num_layers = 8
    main(config)
    # config.yaml('config.yaml')  # in case you want to save a yaml
    # config.json('config.json')  # in case you want to save a json
```

All you needs to do is just run a line:

```shell
python main.py --model.decoder.num_layers 8
```

You could also load a default configure file and make changs based on it:

```shell
python main.py --config meow.yaml --model.decoder.num_layers 8
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

Defing the default arguments in function, put alteration in CLI, and leave the rest to CHANfiG.

It works the way it should have worked.

[^incountable]: fun fact: time is always incountable.
