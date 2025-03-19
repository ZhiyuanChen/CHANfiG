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

from chanfig.utils.placeholder import find_circular_reference, find_placeholders


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
