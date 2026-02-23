# CHANfiG
# Copyright (C) 2022-Present, DanLing Team

# This file is part of CHANfiG.

# CHANfiG is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0

# CHANfiG is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

from pathlib import Path

import chanfig

TESTS_DIR = Path(__file__).resolve().parent


def test_interpolate():
    config = chanfig.load(TESTS_DIR / "interpolate.yaml").interpolate()
    assert config.data.root == "localhost:80"
    assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
    assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
    assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
    assert config.model.num_heads == config.model.num_channels // 64
    assert config.model.num_hidden_size == config.model.num_channels // 64 * config.model.multiple


def test_interpolate_eval():
    config = chanfig.load(TESTS_DIR / "interpolate.yaml").interpolate()
    assert config.data.root == "localhost:80"
    assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
    assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
    assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
    assert config.model.num_heads == config.model.num_channels // 64
    assert config.model.num_hidden_size == config.model.num_channels // 64 * config.model.multiple


def test_interpolate_eval_updates():
    d = chanfig.FlatDict(a=1, b="${a}", c="${a}.${b}").interpolate()
    assert d.resolved()["c"] == 1.1
    d.a += 1
    assert d.resolved()["c"] == 2.2
    assert d.dict()["c"] == "${a}.${b}"


def test_interpolate_preserve_placeholders():
    config = chanfig.load(TESTS_DIR / "interpolate.yaml").interpolate()

    placeholder_dict = config.dict()
    assert placeholder_dict["data"]["root"] == "${host}:${port}"
    assert placeholder_dict["data"]["imagenet"]["data_dirs"][0] == "${data.root}/X-A"
    assert placeholder_dict["model"]["num_heads"] == "${model.num_channels} // 64"
    assert placeholder_dict["model"]["num_hidden_size"] == "${model.num_heads} * ${model.multiple}"
    resolved = config.resolved()
    assert resolved["data"]["root"] == "localhost:80"
    assert resolved["model"]["num_heads"] == 512 // 64
    assert resolved["model"]["num_hidden_size"] == 512 // 64 * 256

    dumped = config.yamls()
    assert "${host}:${port}" in dumped
    assert "${data.root}/X-A" in dumped


def test_include():
    config = chanfig.load(TESTS_DIR / "parent.yaml")
    model = chanfig.load(TESTS_DIR / "model.yaml")
    assert config.model == model
    assert config.port == 80
