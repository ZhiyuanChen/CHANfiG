# [CHANfiG](https://chanfig.danling.org/zh)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/75f2ee4ba5a64458afb488615e36adcb)](https://app.codacy.com/gh/ZhiyuanChen/CHANfiG/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Codacy Badge](https://app.codacy.com/project/badge/Coverage/75f2ee4ba5a64458afb488615e36adcb)](https://app.codacy.com/gh/ZhiyuanChen/CHANfiG/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![CodeCov](https://codecov.io/gh/ZhiyuanChen/CHANfiG/graph/badge.svg?token=G9WGWCOFQE)](https://codecov.io/gh/ZhiyuanChen/CHANfiG)

[![PyPI - Version](https://img.shields.io/pypi/v/chanfig)](https://pypi.org/project/chanfig/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/chanfig)](https://pypi.org/project/chanfig/)
[![Downloads](https://static.pepy.tech/badge/chanfig/month)](https://chanfig.danling.org)

[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-blue.svg)](http://unlicense.org/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## 介绍

CHANfiG 希望能让你的配置更加简单。

训练一个机器学习模型有无数个可调节的参数。
为了调节所有参数，研究员们常常需要撰写巨大的配置文件，有时甚至长达数千行。
大多数参数只是方法默认参数的简单重复，这导致了很多不必要的声明。
此外，调节这些参数同样很繁琐，需要定位并打开配置文件，作出修改，然后保存关闭。
这个过程浪费了无数的宝贵时间 ~~这无疑是一种犯罪~~ 。
使用[`argparse`][argparse]可以在一定程度上缓解调参的不变，但是，要让他和配置文件适配依然需要很多工作，并且缺乏嵌套也限制了他的潜力。

CHANfiG 旨在带来改变。

你只需要在命令行中输入你的修改，然后把剩下的交给 CHANfiG。

CHANfiG 很大程度上启发自[YACS](https://github.com/rbgirshick/yacs)。
不同于 YACS 的范式（`代码 + 实验E的YACS配置文件 (+ 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E`），
CHANfiG 的范式是：

`代码 + 命令行参数 (+ 可选的CHANfiG配置文件 + 外部依赖 + 硬件 + 其他令人讨厌的术语 ...) = 可重复的实验E (+ 可选的CHANfiG配置文件)`

## 组件

一个配置文件可以被看作一个嵌套的字典结构。

但是，默认的 Python 字典十分难以操作。

访问字典成员的唯一方式是`dict['name']`，这无疑是极其繁琐的。
更糟糕的，如果这个字典和配置一样是一个嵌套结构，访问成员将会变成类似于`dict['parent']['children']['name']`的样子。

够了就是够了，是时候做出改变了。

我们需要属性方式的访问，并且我们现在就需要。
`dict.name`和`dict.parent.children.name`是所有你需要的。

尽管此前已经有工作来实现类似的对字典成员的属性方式访问。但是他们的 Config 对象要么使用一个独立的字典来存储属性方式访问的信息（EasyDict），而这可能导致属性方式访问和字典方式访问的不一致；要么重新使用既有的`__dict__`然后对字典方式访问进行重定向（ml_collections），而这可能导致属性和字典成员存在冲突。

为了解决上述限制，我们继承了 Python 内置的`dict`来创建[`FlatDict`][chanfig.FlatDict]、[`DefaultDict`][chanfig.DefaultDict]、[`NestedDict`][chanfig.NestedDict]、[`Config`][chanfig.Config]和[`Registry`][chanfig.Registry]。
我们同时介绍了[`Variable`][chanfig.Variable]来在多个位置共享值，和[`ConfigParser`][chanfig.ConfigParser]来解析命令行参数。

### FlatDict

[`FlatDict`][chanfig.FlatDict]在三个方面对默认的`dict`做出改进。

#### 字典操作

[`FlatDict`][chanfig.FlatDict]支持变量插值。
将一个成员的值设置为`${}`包裹的另一个成员名，然后调用[`interpolate`][chanfig.FlatDict.interpolate]方法。
这个成员的值将会自动替换为另一个成员的值。

Python 的`dict`自 Python 3.7 之后就是有序的，但是并没有一个内置的方法来帮助你对一个`dict`进行排序。[`FlatDict`][chanfig.FlatDict]支持[`sort`][chanfig.FlatDict.sort]来帮助你管理你的字典。

[`FlatDict`][chanfig.FlatDict]包括了一个[`merge`][chanfig.FlatDict.merge]方法，他使你能将一个`Mapping`、`Iterable`或者一个路径合并进入一个[`FlatDict`][chanfig.FlatDict]。
与[`update`][dict.update]方法不同，[`merge`][chanfig.FlatDict.merge]方法是赋值而不是替换，这使得他能更好的与[`DefaultDict`][chanfig.DefaultDict]配合使用。

此外，[`FlatDict`][chanfig.FlatDict]引入了[`difference`][chanfig.FlatDict.difference]和[`intersect`][chanfig.FlatDict.intersect]，这些使其可以非常简单的将[`FlatDict`][chanfig.FlatDict]和其他`Mapping`、`Iterable`或者一个路径进行对比。

#### 机器学习操作

[`FlatDict`][chanfig.FlatDict]支持与 Pytorch Tensor 类似的[`to`][chanfig.FlatDict.to]方法。
你可以很简单的通过相同的方式将所有[`FlatDict`][chanfig.FlatDict]的成员值转换为某种类型或者转移到某个设备上。

[`FlatDict`][chanfig.FlatDict]同时集成了[`cpu`][chanfig.FlatDict.cpu]、[`gpu`][chanfig.FlatDict.gpu] ([`cuda`][chanfig.FlatDict.cuda])、[`tpu`][chanfig.FlatDict.tpu] ([`xla`][chanfig.FlatDict.xla])方法来提供更便捷的访问。

#### IO 操作

[`FlatDict`][chanfig.FlatDict]支持[`json`][chanfig.FlatDict.json]、[`jsons`][chanfig.FlatDict.jsons]、[`yaml`][chanfig.FlatDict.yaml]和[`yamls`][chanfig.FlatDict.yamls]方法来将[`FlatDict`][chanfig.FlatDict]存储到文件或者转换成字符串。
它还提供了[`from_json`][chanfig.FlatDict.from_json]、[`from_jsons`][chanfig.FlatDict.from_jsons]、[`from_yaml`][chanfig.FlatDict.from_yaml]和[`from_yamls`][chanfig.FlatDict.from_yamls]来从一个字符串或者文件中构建[`FlatDict`][chanfig.FlatDict]。

[`FlatDict`][chanfig.FlatDict]也包括了`dump`和`load`方法，他们可以从文件扩展名中自动推断类型然后将[`FlatDict`][chanfig.FlatDict]存储到文件中/从文件中加载[`FlatDict`][chanfig.FlatDict]。

### DefaultDict

为了满足默认值的需要，我们包括了一个[`DefaultDict`][chanfig.DefaultDict]，他接受`default_factory`参数，并和[`collections.defaultdict`][collections.defaultdict]一样工作。

### NestedDict

由于大多数配置都是一个嵌套的结构，我们进一步提出了[`NestedDict`][chanfig.NestedDict]。

基于[`DefaultDict`][chanfig.DefaultDict]，[`NestedDict`][chanfig.NestedDict]提供了[`all_keys`][chanfig.NestedDict.all_keys]、[`all_values`][chanfig.NestedDict.all_values]、[`all_items`][chanfig.NestedDict.all_items]方法来允许一次性遍历整个嵌套结构。

[`NestedDict`][chanfig.NestedDict]同时提供了[`apply`][chanfig.NestedDict.apply]和[`apply_`][chanfig.NestedDict.apply_]方法，它可以使操纵嵌套结构更加容易。

### Config

[`Config`][chanfig.Config]通过两个方面来进一步提升功能性：
支持[`freeze`][chanfig.Config.freeze]来冻结和[`defrost`][chanfig.Config.defrost]解冻字典和
加入内置的[`ConfigParser`][chanfig.ConfigParser]来解析命令行语句。

注意[`Config`][chanfig.Config]默认设置`default_factory=Config()`来提供便利。

### Registry

[`Registry`][chanfig.Registry]继承自[`NestedDict`][chanfig.NestedDict]，并且提供[`register`][chanfig.Registry.register]、[`lookup`][chanfig.Registry.lookup]和[`build`][chanfig.Registry.build]来帮助你注册构造函数并从[`Config`][chanfig.Config]来创建对象。

### Variable

有一个值在多个地方以多个名字出现？我们给你提供掩护。

只要将值以[`Variable`][chanfig.Variable]包装，然后每处更改都会在处处体现。

[`Variable`][chanfig.Variable]支持`type`、`choices`、`validator`、`required`来确保值的正确性。

为了更加简单，[`Variable`][chanfig.Variable]还支持`help`来在使用[`ConfigParser`][chanfig.ConfigParser]时提供描述。

### ConfigParser

[`ConfigParser`][chanfig.ConfigParser]在[`ArgumentParser`][argparse.ArgumentParser]的基础之上，提供了[`parse`][chanfig.ConfigParser.parse]和[`parse_config`][chanfig.ConfigParser.parse_config]来解析命令行参数并创建/更新[`Config`][chanfig.Config]。

## 使用

CHANfiG 有着强大的前向兼容能力，能够良好的兼容以往基于 yaml 和 json 的配置文件。

如果你此前使用 yacs，只需简单将`CfgNode`替换为[`Config`][chanfig.Config]便可以享受所有 CHANfiG 所提供的便利。

更进一步的，如果你发现[`Config`][chanfig.Config]中的名字对于命令行来说过长，你可以简单的调用[`self.add_argument`][chanfig.Config.add_argument]并设置恰当的`dest`来在命令行中使用更短的名字，正如`argparse`所做的那样。

```shell
--8<-- "demo/config.py"
```

所有你需要做的仅仅是运行一行：

```shell
python main.py --model.encoder.num_layers 8 --model.dropout=0.2 --lr 5e-3
```

当然，你也可以读取一个默认配置文件然后在他基础上修改：

注意，你必须指定`config.parse(default_config='config')`来正确读取默认配置文件。

```shell
python main.py --config meow.yaml --model.encoder.num_layers 8 --model.dropout=0.2 --lr 5e-3
```

如果你保存了配置文件，那他应该看起来像这样：

=== "yaml"

    ``` yaml
    --8<-- "demo/config.yaml"
    ```

=== "json"

    ``` json
    --8<-- "demo/config.json"
    ```

在方法中定义默认参数，在命令行中修改，然后将剩下的交给 CHANfiG。

## 安装

=== "安装 pypi 上最近的稳定版本"

    ```shell
    pip install chanfig
    ```

=== "从源码安装最新的版本"

    ```shell
    pip install git+https://github.com/ZhiyuanChen/CHANfiG
    ```

他本该如此工作。

## 授权

CHANfiG 依据下列许可证进行多重授权：

=== "The Unlicense"

    ```
    --8<-- "LICENSES/LICENSE.Unlicense"
    ```

=== "GNU Affero General Public License v3.0 or later"

    ```
    --8<-- "LICENSES/LICENSE.AGPL"
    ```

=== "GNU General Public License v2.0 or later"

    ```
    --8<-- "LICENSES/LICENSE.GPLv2"
    ```

=== "BSD 4-Clause "Original" or "Old" License"

    ```
    --8<-- "LICENSES/LICENSE.BSD"
    ```

=== "MIT License"

    ```
    --8<-- "LICENSES/LICENSE.MIT"
    ```

=== "Apache License 2.0"

    ```
    --8<-- "LICENSES/LICENSE.Apache"
    ```

如果你使用本工作，你可以从中任选（一个或者多个）许可证。

`SPDX-License-Identifier: Unlicense OR AGPL-3.0-or-later OR GPL-2.0-or-later OR BSD-4-Clause OR MIT OR Apache-2.0`
