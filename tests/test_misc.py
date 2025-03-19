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

import chanfig


def test_interpolate():
    config = chanfig.load("tests/interpolate.yaml").interpolate()
    assert config.data.root == "localhost:80"
    assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
    assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
    assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
    assert config.model.num_heads == f"{config.model.num_channels} // 64"
    assert config.model.num_hidden_size == f"{config.model.num_channels} // 64 * {config.model.multiple}"


def test_interpolate_eval():
    config = chanfig.load("tests/interpolate.yaml").interpolate(unsafe_eval=True)
    assert config.data.root == "localhost:80"
    assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
    assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
    assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
    assert config.model.num_heads == config.model.num_channels // 64
    assert config.model.num_hidden_size == config.model.num_channels // 64 * config.model.multiple


def test_include():
    config = chanfig.load("tests/parent.yaml")
    model = chanfig.load("tests/model.yaml")
    assert config.model == model
    assert config.port == 80
