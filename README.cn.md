# CHANfiG

Read this in other language: [English](README.md)

在其他语言中阅读本文：[简体中文](README.cn.md)

## 介绍

CHANfiG希望能让你的配置更加简单。

训练一个机器学习模型有无数个可调节的参数。
为了调节所有参数，研究员们常常需要撰写巨大的配置文件，有时甚至长达数千行。
大多数参数只是方法默认参数的简单重复，这导致了很多不必要的声明。
此外，调节这些参数同样很繁琐，需要定位并打开配置文件，作出修改，然后保存关闭。
这个过程浪费了无数的宝贵时间~~甚至是一种犯罪~~。
使用 `argparse`可以在一定程度上缓解调参的不变，但是，要让他和配置文件适配依然需要很多工作，并且缺乏嵌套也限制了他的潜力。
CHANfiG旨在带来改变。

你只需要在命令行中运行你的实验。

CHANfiG启发自[YACS](https://github.com/rbgirshick/yacs)。
不同于YACS的范式（`代码 + 实验E的YACS配置文件 (+ 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E`），
CHANfiG的范式是：

`代码 + 命令行参数 (+ 可选的CHANfiG配置文件 + 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E (+ 可选的CHANfiG配置文件)`

## 使用

CHANfiG 有着强大的前向兼容能力，能够良好的兼容以往基于yaml和json的配置文件。

如果你此前使用yacs，只需简单将`CfgNode`替换为`Config`便可以享受所有CHANfiG所提供的便利。

现有代码：

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
    # config = Config.read('config.yaml')  # 如果你想读取一个 yaml
    # config = Config.read('config.json')  # 如果你想读取一个 json
    # existing_configs = {'data.batch_size': 64, 'model.encoder.num_layers': 8}
    # config = Config(**existing_configs)  # 如果你有些config需要读取
    config = TestConfig()
    config = config.parse()
    # config.merge('dataset.yaml')  # 如果你想合并一个 yaml
    # config.merge('dataset.json')  # 如果你想合并一个 json
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
python main.py --model.encoder.num_layers 8
```

当然，你也可以读取一个默认配置文件然后在他基础上修改：

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8
```

如果你保存了配置文件，那他应该看起来像这样：

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

在方法中定义默认参数，在命令行中修改，然后将剩下的交给CHANfiG。

## 安装

安装 pypi 上最近的稳定版本：

```shell
pip install chanfig
```

从源码安装最新的版本：

```shell
pip install git+https://github.com/ZhiyuanChen/chanfig
```



他本该如此工作。
