# CHANfiG, Easier Configuration.
# Copyright (c) 2022-Present, CHANfiG Contributors

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


import os
from typing import List, Optional, Union

import pytest

from chanfig.functional import load
from chanfig.utils import (
    NULL,
    JsonEncoder,
    YamlDumper,
    YamlLoader,
    conform_annotation,
    find_circular_reference,
    find_placeholders,
    honor_annotation,
    parse_bool,
)


def test_honor_annotation():
    assert honor_annotation("42", int) == 42
    assert honor_annotation(42, str) == "42"
    assert honor_annotation("3.14", float) == 3.14
    assert honor_annotation(True, str) == "True"

    assert honor_annotation("name", Union[int, str]) == "name"
    assert honor_annotation(123, Union[int, str]) == 123
    assert honor_annotation("42", Union[int, str]) == "42"

    assert honor_annotation(None, Optional[int]) is None
    assert honor_annotation("42", Optional[int]) == 42

    assert honor_annotation(["1", "2", "3"], List[int]) == [1, 2, 3]

    assert honor_annotation("not_an_int", int) == "not_an_int"


def test_conform_annotation():
    assert conform_annotation(42, int)
    assert conform_annotation("hello", str)
    assert not conform_annotation("42", int)
    assert not conform_annotation(42, str)

    assert conform_annotation("name", Union[int, str])
    assert conform_annotation(123, Union[int, str])
    assert not conform_annotation([], Union[int, str])

    assert conform_annotation(None, Optional[int])
    assert conform_annotation(42, Optional[int])
    assert not conform_annotation("42", Optional[int])

    assert conform_annotation([1, 2, 3], List[int])
    assert not conform_annotation([1, "2", 3], List[int])


def test_find_placeholders():
    assert find_placeholders("Hello ${name}!") == ["name"]
    assert find_placeholders("${a} + ${b} = ${c}") == ["a", "b", "c"]
    assert find_placeholders("${outer.${inner}}") == ["outer.${inner}", "inner"]
    assert find_placeholders("Hello world!") == []
    assert find_placeholders("") == []
    assert find_placeholders("${x} and ${x}") == ["x", "x"]


def test_find_circular_reference():
    assert find_circular_reference({"a": ["b"], "b": ["c"], "c": []}) is None
    assert find_circular_reference({"a": ["b"], "b": ["a"]}) == ["a", "b", "a"]
    assert find_circular_reference({"a": ["b"], "b": ["c"], "c": ["a"]}) == ["a", "b", "c", "a"]
    assert find_circular_reference({"a": ["b"], "b": ["c"], "c": ["a"]}) == ["a", "b", "c", "a"]
    assert find_circular_reference({"a": ["a"]}) == ["a", "a"]
    assert find_circular_reference({}) is None
    result = find_circular_reference({"a": ["b"], "b": ["a"], "c": ["d"], "d": ["c"]})
    assert result in [["a", "b", "a"], ["c", "d", "c"]]


def test_parse_bool():
    assert parse_bool("true")
    assert parse_bool("True")
    assert parse_bool("yes")
    assert parse_bool("Yes")
    assert parse_bool("1")
    assert parse_bool(1)
    assert parse_bool(True)

    assert not parse_bool("false")
    assert not parse_bool("False")
    assert not parse_bool("no")
    assert not parse_bool("No")
    assert not parse_bool("0")
    assert not parse_bool(0)
    assert not parse_bool(False)

    with pytest.raises(ValueError):
        parse_bool("invalid")
    with pytest.raises(ValueError):
        parse_bool(42)


def test_null_singleton():
    null1 = NULL()
    null2 = NULL()
    assert null1 is null2

    assert bool(null1) is False
    assert len(null1) == 0
    assert list(null1) == []
    assert "anything" not in null1

    assert null1.anything is null1
    assert null1["anything"] is null1
    assert null1() is null1

    assert str(null1) == "Null"
    assert repr(null1) == "Null"


def test_json_encoder():
    encoder = JsonEncoder()

    assert encoder.encode([1, 2, 3]) == "[1, 2, 3]"
    assert encoder.encode({"a": 1}) == '{"a": 1}'
    assert encoder.encode(42) == "42"

    class DictLike:
        def __json__(self):
            return {"value": 42}

    assert encoder.encode(DictLike()) == '{"value": 42}'

    class DictObject:
        def to_dict(self):
            return {"value": 42}

    assert encoder.encode(DictObject()) == '{"value": 42}'

    with pytest.raises(TypeError):
        encoder.encode(complex(1, 2))


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
    with open("test_include.yaml", "w") as f:
        f.write(test_yaml)

    with open("test_include.yaml") as f:
        loader = YamlLoader(f)
    data = loader.get_data()

    assert data["env"] == os.environ["HOME"]
    assert data["include"] == load("tests/test.yaml")

    os.remove("test_include.yaml")
