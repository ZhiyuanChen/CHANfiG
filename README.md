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
Using [`argparse`][argparse] could relieve the burdens to some extent.
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
or reuse the existing `__dict__` and redirect dict-style access (ml_collections), which may result in confliction between attributes and members of Config.

To overcome the aforementioned limitations, we inherit the Python built-in [`dict`][dict] to create [`FlatDict`][chanfig.FlatDict], [`DefaultDict`][chanfig.DefaultDict], [`NestedDict`][chanfig.NestedDict], [`Config`][chanfig.Config], and [`Registry`][chanfig.Registry].
We also introduce [`Variable`][chanfig.Variable] to allow sharing a value across multiple places, and [`ConfigParser`][chanfig.ConfigParser] to parse command line arguments.

### FlatDict

[`FlatDict`][chanfig.FlatDict] improves the default [`dict`][dict] in 3 aspects.

#### Dict Operations

[`FlatDict`][chanfig.FlatDict] supports variable interpolation.
Set a member's value to another member's name wrapped in `${}`, then call [`interpolate`][chanfig.FlatDict.interpolate] method. The value of this member will be automatically replaced with the value of another member.

[`dict`][dict] in Python is ordered since Python 3.7, but there isn't a built-in method to help you sort a [`dict`][dict]. [`FlatDict`][chanfig.FlatDict]supports [`sort`][chanfig.FlatDict.sort] to help you manage your dict.

[`FlatDict`][chanfig.FlatDict] incorporates a [`merge`][chanfig.FlatDict.merge] method that allows you to merge a `Mapping`, an `Iterable`, or a path to the [`FlatDict`][chanfig.FlatDict].
Different from built-in [`update`][dict.update], [`merge`][chanfig.FlatDict.merge] assign values instead of replace, which makes it work better with [`DefaultDict`][chanfig.DefaultDict].

Moreover, [`FlatDict`][chanfig.FlatDict] comes with [`difference`][chanfig.FlatDict.difference] and [`intersect`][chanfig.FlatDict.intersect], which makes it very easy to compare a [`FlatDict`][chanfig.FlatDict] with other `Mapping`, `Iterable`, or a path.

#### ML Operations

[`FlatDict`][chanfig.FlatDict] supports [`to`][chanfig.FlatDict.to] method similar to PyTorch Tensor.
You can simply convert all member values of [`FlatDict`][chanfig.FlatDict] to a certain type or pass to a device in the same way.

[`FlatDict`][chanfig.FlatDict] also integrates [`cpu`][chanfig.FlatDict.cpu], [`gpu`][chanfig.FlatDict.gpu] ([`cuda`][chanfig.FlatDict.cuda]), and [`tpu`][chanfig.FlatDict.tpu] ([`xla`][chanfig.FlatDict.xla]) methods for easier access.

#### IO Operations

[`FlatDict`][chanfig.FlatDict] provides [`json`][chanfig.FlatDict.json], [`jsons`][chanfig.FlatDict.jsons], [`yaml`][chanfig.FlatDict.yaml] and [`yamls`][chanfig.FlatDict.yamls] methods to dump [`FlatDict`][chanfig.FlatDict] to a file or string.
It also provides [`from_json`][chanfig.FlatDict.from_json], [`from_jsons`][chanfig.FlatDict.from_jsons], [`from_yaml`][chanfig.FlatDict.from_yaml] and [`from_yamls`][chanfig.FlatDict.from_yamls] methods to build a [`FlatDict`][chanfig.FlatDict] from a string or file.

[`FlatDict`][chanfig.FlatDict] also includes `dump` and `load` methods which determine the type by their extension and dump/load [`FlatDict`][chanfig.FlatDict] to/from a file.

### DefaultDict

To facilitate the needs of default values, we incorporate [`DefaultDict`][chanfig.DefaultDict] which accepts `default_factory` and works just like a [`collections.defaultdict`][collections.defaultdict].

### NestedDict

Since most Configs are in a nested structure, we further propose a [`NestedDict`][chanfig.NestedDict].

Based on [`DefaultDict`][chanfig.DefaultDict], [`NestedDict`][chanfig.NestedDict] provides [`all_keys`][chanfig.NestedDict.all_keys], [`all_values`][chanfig.NestedDict.all_values], and [`all_items`][chanfig.NestedDict.all_items] methods to allow iterating over the whole nested structure at once.

[`NestedDict`][chanfig.NestedDict] also comes with [`apply`][chanfig.NestedDict.apply] and [`apply_`][chanfig.NestedDict.apply_] methods, which make it easier to manipulate the nested structure.

### Config

[`Config`][chanfig.Config] extends the functionality by supporting [`freeze`][chanfig.Config.freeze] and [`defrost`][chanfig.Config.defrost], and by adding a built-in [`ConfigParser`][chanfig.ConfigParser] to pare command line arguments.

Note that [`Config`][chanfig.Config] also has `default_factory=Config()` by default for convenience.

### Registry

[`Registry`][chanfig.Registry] extends the [`NestedDict`][chanfig.NestedDict] and supports [`register`][chanfig.Registry.register], [`lookup`][chanfig.Registry.lookup], and [`build`][chanfig.Registry.build] to help you register constructors and build objects from a [`Config`][chanfig.Config].

### Variable

Have one value for multiple names at multiple places? We got you covered.

Just wrap the value with [`Variable`][chanfig.Variable], and one alteration will be reflected everywhere.

[`Variable`][chanfig.Variable] supports `type`, `choices`, `validator`, and `required` to ensure the correctness of the value.

To make it even easier, [`Variable`][chanfig.Variable] also support `help` to provide a description when using [`ConfigParser`][chanfig.ConfigParser].

### ConfigParser

[`ConfigParser`][chanfig.ConfigParser] extends [`ArgumentParser`][argparse.ArgumentParser] and provides [`parse`][chanfig.ConfigParser.parse] and [`parse_config`][chanfig.ConfigParser.parse_config] to parse command line arguments.

## Usage

CHANfiG has great backward compatibility with previous configs.

No matter if your old config is json or yaml, you could directly read from them.

And if you are using yacs, just replace `CfgNode` with [`Config`][chanfig.Config] and enjoy all the additional benefits that CHANfiG provides.

Moreover, if you find a name in the config is too long for command-line, you could simply call [`self.add_argument`][chanfig.Config.add_argument] with proper `dest` to use a shorter name in command-line, as you do with `argparse`.

```python
--8<-- "demo/config.py"
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

=== "yaml"

    ``` yaml
    --8<-- "demo/config.yaml"
    ```

=== "json"

    ``` json
    --8<-- "demo/config.json"
    ```

Define the default arguments in function, put alterations in CLI, and leave the rest to CHANfiG.

## Installation

=== "Install the most recent stable version on pypi"

    ```shell
    pip install chanfig
    ```

=== "Install the latest version from source"

    ```shell
    pip install git+https://github.com/ZhiyuanChen/CHANfiG
    ```

It works the way it should have worked.

## License

CHANfiG is multi-licensed under the following licenses:

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

You can choose any (one or more) of these licenses if you use this work.

`SPDX-License-Identifier: Unlicense OR AGPL-3.0-or-later OR GPL-2.0-or-later OR BSD-4-Clause OR MIT OR Apache-2.0`

[^uncountable]: fun fact: time is always uncountable.
