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

from __future__ import annotations

import os

import chanfig


def test_list():
    list = [1, 2, 3]
    chanfig.save(list, "test.yaml")
    assert chanfig.load("test.yaml") == list
    os.remove("test.yaml")


def test_list_dict():
    list = [{"a": 1, "b": 2}, {"c": 3, "d": 4}]
    chanfig.save(list, "test.yaml")
    assert chanfig.load("test.yaml") == list
    os.remove("test.yaml")
