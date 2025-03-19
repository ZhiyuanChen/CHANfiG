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

import json
import os

from pytest import raises

from chanfig import FlatDict
from chanfig.utils.io import JsonEncoder, YamlDumper, YamlLoader, load, save


def test_yaml_dumper():
    dumper = YamlDumper(None)

    assert dumper.increase_indent(flow=True, indentless=False) == super(YamlDumper, dumper).increase_indent(
        flow=True, indentless=False
    )
    assert dumper.increase_indent(flow=False, indentless=True) == super(YamlDumper, dumper).increase_indent(
        flow=False, indentless=True
    )


def test_yaml_loader():
    test_yaml = """
    include: !include tests/test.yaml
    includes: !includes [tests/parent.yaml, tests/child.yaml]
    env: !env HOME
    """
    save(FlatDict.from_yamls(test_yaml), "test_include.yaml")

    with open("test_include.yaml") as f:
        loader = YamlLoader(f)
    data = loader.get_data()

    assert data["env"] == os.environ["HOME"]
    assert data["include"] == load("tests/test.yaml")

    os.remove("test_include.yaml")


def test_json_encoder():
    class JsonObject:
        def __json__(self):
            return {"type": "json_object"}

    class DictObject:
        def to_dict(self):
            return {"type": "dict_object"}

    class RegularObject:
        pass

    json_obj = JsonObject()
    assert json.dumps(json_obj, cls=JsonEncoder) == '{"type": "json_object"}'

    dict_obj = DictObject()
    assert json.dumps(dict_obj, cls=JsonEncoder) == '{"type": "dict_object"}'

    reg_obj = RegularObject()
    with raises(TypeError):
        json.dumps(reg_obj, cls=JsonEncoder)
