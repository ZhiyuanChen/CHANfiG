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

import pytest

from chanfig import Config, FlatDict
from chanfig.io import JsonEncoder
from chanfig.utils.functional import parse_bool


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


def test_keyerror_suggests_close_match():
    config = FlatDict(alpha=1, beta=2)
    with pytest.raises(KeyError, match="Did you mean 'alpha'"):
        _ = config["alpa"]


def test_attributeerror_suggests_nested_key():
    config = Config()
    config.model.hidden = 128
    config.freeze()
    with pytest.raises(AttributeError, match="Did you mean 'hidden'"):
        _ = config.model.hiden
