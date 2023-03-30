# [CHANfiG](https://chanfig.danling.org/zh)

## 介绍

CHANfiG 希望能让你的配置更加简单。

训练一个机器学习模型有无数个可调节的参数。
为了调节所有参数，研究员们常常需要撰写巨大的配置文件，有时甚至长达数千行。
大多数参数只是方法默认参数的简单重复，这导致了很多不必要的声明。
此外，调节这些参数同样很繁琐，需要定位并打开配置文件，作出修改，然后保存关闭。
这个过程浪费了无数的宝贵时间 ~~这无疑是一种犯罪~~ 。
使用`argparse`可以在一定程度上缓解调参的不变，但是，要让他和配置文件适配依然需要很多工作，并且缺乏嵌套也限制了他的潜力。

CHANfiG 旨在带来改变。

你只需要在命令行中输入你的修改，然后把剩下的交给 CHANfiG。

CHANfiG 很大程度上启发自[YACS](https://github.com/rbgirshick/yacs)。
不同于 YACS 的范式（`代码 + 实验E的YACS配置文件 (+ 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E`），
CHANfiG 的范式是：

`代码 + 命令行参数 (+ 可选的CHANfiG配置文件 + 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E (+ 可选的CHANfiG配置文件)`

## 组件

一个配置文件可以被看作一个嵌套的字典结构。

但是，默认的 Python 字典十分难以操作。

访问字典成员的唯一方式是 `dict['name']` ，这无疑是极其繁琐的。
更糟糕的，如果这个字典和配置一样是一个嵌套结构，访问成员将会变成类似于`dict['parent']['children']['name']`的样子。

够了就是够了，是时候做出改变了。

我们需要属性方式的访问，并且我们现在就需要。
`dict.name`和`dict.parent.children.name`是所有你需要的。

尽管此前已经有工作来实现类似的对字典成员的属性方式访问。但是他们要么使用一个独立的字典来存储属性方式访问的信息（EasyDict），而这可能导致属性方式访问和字典方式访问的不一致；要么重新使用既有的`__dict__`然后对字典方式访问进行重定向（ml_collections），而这可能导致属性可字典成员的冲突。

为了解决上述限制，我们继承了 Python 内置的`dict`来创建`FlatDict`、`DefaultDict`、`NestedDict`、`Config`和`Registry`对象。

### FlatDict

`FlatDict`在三个方面对默认的`dict`做出改进。

#### 字典操作

`FlatDict`扩充原始的`dict`的`update`方法，使其支持传递另一个`Mapping`、`Iterable`或者一个路径。

更进一步的，`FlatDict`引入了`difference`和`intersection`，这些使其可以非常简单的对比`FlatDict`和其他`Mapping`、`Iterable`或者一个路径进行对比。

#### 机器学习操作

`FlatDict`支持与 Pytorch Tensor 类似的`to`方法。
你可以很简单的通过相同的方式将所有`FlatDict`的成员值转换为某种类型或者转一道某个设备上。

`FlatDict`同时集成了`cpu`、`gpu` (`cuda`)、`tpu`方法来提供更便捷的访问。

#### IO 操作

`FlatDict`支持`json`、`jsons`、`yaml`和`yamls`方法来将`FlatDict`对象存储到文件或者转换成字符串。
它还提供了`from_json`、`from_jsons`、`from_yaml`和`from_yamls`来从一个字符串或者文件中构建`FlatDict`对象。

`FlatDict`也包括了`dump`和`load`方法，他们可以从文件扩展名中自动推断类型然后将`FlatDict`对象存储到文件中/从文件中加载`FlatDict`对象。

### DefaultDict

为了满足默认值的需要，我们包括了一个`DefaultDict`，他接受`default_factory`参数，并和`collections.defaultdict`一样工作。

### NestedDict

由于大多数配置都是一个嵌套的结构，我们进一步提出了`NestedDict`。

基于`FlatDict`，`NestedDict`提供了`all_keys`、`all_values`、`all_items`方法来允许一次性遍历整个嵌套结构。

`NestedDict`同时提供了一个`apply`方法，它可以使操纵嵌套结构更加容易。

### Config

`Config`通过两个方面来进一步提升功能性：
支持`freeze`来冻结和`defrost`解冻字典和
加入内置的`ConfigParser`来解析命令行语句。

注意`Config`默认设置`default_factory=Config()`来提供便利。

### Registry

`Registry`继承自`NestedDict`，并且提供`register`、`lookup`和`build`来帮助你注册构造函数并从`Config`来创建对象。

### Variable

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

    def post(self):
        self.id = f"{self.name}_{self.seed}"


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
  lr: 0.001
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
    "lr": 0.001
  },
  "id": "CHANfiG_1013"
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

## 授权

CHANfiG 依据下列许可证进行多重授权：

- Unlicense
- GPL 2.0 (or any later version)
- MIT
- Apache 2.0
- BSD 2-Clause
- BSD 3-Clause
- BSD 4-Clause

如果你使用本工作，你可以从中任选（一个或者多个）许可证。

`SPDX-License-Identifier: Unlicense OR GPL-2.0-or-later OR MIT OR Apache-2.0 OR BSD-2-Clause OR BSD-3-Clause OR BSD-4-Clause`
