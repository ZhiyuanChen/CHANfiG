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
from pathlib import Path

from pytest import raises

from chanfig import FlatDict
from chanfig.io import JsonEncoder, YamlDumper, YamlLoader, load, save

TESTS_DIR = Path(__file__).resolve().parent


def _toml_writer_available():
    try:
        import tomli_w  # noqa: F401
    except ImportError:
        try:
            import toml  # noqa: F401
        except ImportError:
            return False
    return True


def test_yaml_dumper():
    dumper = YamlDumper(None)

    assert dumper.increase_indent(flow=True, indentless=False) == super(YamlDumper, dumper).increase_indent(
        flow=True, indentless=False
    )
    assert dumper.increase_indent(flow=False, indentless=True) == super(YamlDumper, dumper).increase_indent(
        flow=False, indentless=True
    )


def test_yaml_loader(tmp_path):
    include_path = TESTS_DIR / "test.yaml"
    parent_path = TESTS_DIR / "parent.yaml"
    child_path = TESTS_DIR / "child.yaml"

    test_yaml = f"""
    include: !include "{include_path}"
    includes: !includes ["{parent_path}", "{child_path}"]
    env: !env HOME
    """
    include_output = tmp_path / "test_include.yaml"
    save(FlatDict.from_yamls(test_yaml), include_output)

    with include_output.open() as f:
        loader = YamlLoader(f)
    data = loader.get_data()

    assert data["env"] == os.environ["HOME"]
    assert data["include"] == load(include_path)


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


def test_list(tmp_path):
    data = [1, 2, 3]
    output = tmp_path / "test.yaml"
    save(data, output)
    assert load(output) == data


def test_list_dict(tmp_path):
    data = [{"a": 1, "b": 2}, {"c": 3, "d": 4}]
    output = tmp_path / "test.yaml"
    save(data, output)
    assert load(output) == data


def test_toml_save_and_load(tmp_path):
    data = {"a": 1, "b": 2}
    output = tmp_path / "test.toml"
    if _toml_writer_available():
        save(data, output)
        assert load(output) == data
    else:
        with raises(TypeError, match="TOML"):
            save(data, output)
