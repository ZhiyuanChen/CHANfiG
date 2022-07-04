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

## 介绍

CHANfiG希望能让你的配置更加简单。

训练一个机器学习模型有无数个可调节的参数。
为了调节所有参数，研究员们常常需要撰写巨大的配置文件，有时甚至长达数千行。
大多数参数只是方法默认参数的简单重复，这导致了很多不必要的声明。
此外，调节这些参数同样很繁琐，需要定位并打开配置文件，作出修改，然后保存关闭。
这个过程浪费了无数的宝贵时间~~甚至是一种犯罪~~。
使用`argparse`可以在一定程度上缓解调参的不变，但是，要让他和配置文件适配依然需要很多工作，并且缺乏嵌套也限制了他的潜力。
CHANfiG旨在减轻带来改变。

你只需要在命令行中运行你的实验。

CHANfiG启发自[YACS](https://github.com/rbgirshick/yacs)。
不同于YACS的范式（`代码 + 实验E的YACS配置文件 (+ 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E`），
CHANfiG的范式是：

`代码 + 命令行参数 (+ 可选的CHANfiG配置文件 + 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E (+ 可选的CHANfiG配置文件)`

## 使用

现有代码：

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
    # config = Config.read('config.yaml')  # 如果你想读取一个yaml
    # config = Config.read('config.json')  # 如果你想读取一个json
    existing_configs = {'a': 1, 'b.c': 2}
    config = Config(**existing_configs)
    config = config.parse()
    # config.merge('dataset.yaml')
    config.activation = 'GELU'
    # config['meow.is.good'] = True
    main(config)
    # config.yaml('config.yaml')  # 如果你想保存一个yaml
    # config.json('config.json')  # 如果你想保存一个json
```

所有你需要做的仅仅是运行一行：

```shell
python main.py --model.encoder.num_layers 6 --model.dropout 0.2
```

当然，你也可以读取一个默认配置文件然后在他基础上修改：

```shell
python main.py --config meow.yaml --model.encoder.num_layers 6 --model.dropout 0.2
```

如果你保存了配置文件，那他应该看起来像这样：

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

在方法中定义默认参数，在命令行中修改，然后将剩下的交给CHANfiG。

他本该如此工作。
