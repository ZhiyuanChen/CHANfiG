# CHANfiG, Easier Configuration.
# Copyright (c) 2022-2023, CHANfiG Contributors
# This program is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - The Unlicense
# - GNU Affero General Public License v3.0 or later
# - GNU General Public License v2.0 or later
# - BSD 4-Clause "Original" or "Old" License
# - MIT License
# - Apache License 2.0
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

import chanfig


class Test:
    def test_interpolate(self):
        config = chanfig.load("tests/interpolate.yaml").interpolate()
        assert config.data.root == "localhost:80"
        assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
        assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
        assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
        assert config.model.num_heads == f"{config.model.num_channels} // 64"
        assert config.model.num_hidden_size == f"{config.model.num_channels} // 64 * {config.model.multiple}"

    def test_interpolate_eval(self):
        config = chanfig.load("tests/interpolate.yaml").interpolate(unsafe_eval=True)
        assert config.data.root == "localhost:80"
        assert config.data.imagenet.data_dirs[0] == "localhost:80/X-A"
        assert config.data.imagenet.data_dirs[1] == "localhost:80/X-B"
        assert config.data.imagenet.data_dirs[2] == "localhost:80/X-C"
        assert config.model.num_heads == config.model.num_channels // 64
        assert config.model.num_hidden_size == config.model.num_channels // 64 * config.model.multiple
