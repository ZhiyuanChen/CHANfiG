---
summary: Easier Configuration
authors:
  - Zhiyuan Chen
date: 2022-05-04
---

# CHANfiG

## 介绍

CHANfiG 希望能让你的配置更加简单。

训练一个机器学习模型有无数个可调节的参数。
为了调节所有参数，研究员们常常需要撰写巨大的配置文件，有时甚至长达数千行。
大多数参数只是方法默认参数的简单重复，这导致了很多不必要的声明。
此外，调节这些参数同样很繁琐，需要定位并打开配置文件，作出修改，然后保存关闭。
这个过程浪费了无数的宝贵时间 ~~甚至是一种犯罪~~ 。
使用 `argparse`可以在一定程度上缓解调参的不变，但是，要让他和配置文件适配依然需要很多工作，并且缺乏嵌套也限制了他的潜力。
CHANfiG 旨在带来改变。

你只需要在命令行中运行你的实验。

CHANfiG 启发自[YACS](https://github.com/rbgirshick/yacs)。
不同于 YACS 的范式（`代码 + 实验E的YACS配置文件 (+ 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E`），
CHANfiG 的范式是：

`代码 + 命令行参数 (+ 可选的CHANfiG配置文件 + 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E (+ 可选的CHANfiG配置文件)`

## 特性

CHANfiG 包括一个功能完全的`FlatDict`和`NestedDict`，他们具有完善的 IO 操作（`load`、`dump`、`jsons`、`yamls`等），协作能力（`difference`、`intersection`、`update`）和简单易用的 APIs（`all_items`、`all_keys`、`all_values`）。

与`ConfigParser`相配合，你可以简单的从命令行参数创建`Config`对象。

有一个值在多个地方以多个名字出现？我们给你提供掩护。

只要将值以`Variable`包装，然后每处更改都会在处处体现。

## 使用

CHANfiG 有着强大的前向兼容能力，能够良好的兼容以往基于 yaml 和 json 的配置文件。

如果你此前使用 yacs，只需简单将`CfgNode`替换为`Config`便可以享受所有 CHANfiG 所提供的便利。

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
    # config = Config.load('config.yaml')  # 如果你想读取一个 yaml
    # config = Config.load('config.json')  # 如果你想读取一个 json
    # existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # 如果你有些config需要读取
    config = TestConfig()
    config = config.parse()
    # config.update('dataset.yaml')  # 如果你想合并一个 yaml
    # config.update('dataset.json')  # 如果你想合并一个 json
    # 注意被合并的值具有更高的优先级
    config.model.decoder.num_layers = 8
    config.freeze()
    print(config)
    # main(config)
    # config.yaml('config.yaml')  # 如果你想保存一个 yaml
    # config.json('config.json')  # 如果你想保存一个 json
```

所有你需要做的仅仅是运行一行：

```shell
python main.py --model.encoder.num_layers 8 --model.dropout=0.2
```

当然，你也可以读取一个默认配置文件然后在他基础上修改：

注意，你必须指定`config.parse(default_config='config')`来正确读取默认配置文件。

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8 --model.dropout=0.2
```

如果你保存了配置文件，那他应该看起来像这样：

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

在方法中定义默认参数，在命令行中修改，然后将剩下的交给 CHANfiG。

## 安装

安装 pypi 上最近的稳定版本：

```shell
pip install chanfig
```

从源码安装最新的版本：

```shell
pip install git+https://github.com/ZhiyuanChen/CHANfiG
```

他本该如此工作。
