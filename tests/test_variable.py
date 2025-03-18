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

from copy import copy, deepcopy

import torch
from pytest import raises

from chanfig import Variable

str_var = Variable("CHANFIG", str, validator=lambda x: x.isupper(), choices=["CHANFIG", "CHANG", "LIU"])
int_var = Variable(0, int, validator=lambda x: x > 0, choices=[1, 2, 3])
float_var = Variable(1e-2, float, validator=lambda x: 0.0 <= x < 1.0, choices=[1e-2, 3e-3, 5e-4])
complex_var = Variable(1 + 2j, complex, validator=lambda x: x.real > 0.0, choices=[1 + 2j, 3 + 4j, 5 + 6j])
bool_var = Variable(True, bool)
required_var = Variable(required=True)


def test_str():
    assert str_var.value == "CHANFIG"
    str_var.value = "CHANG"
    assert str_var.value == "CHANG"
    str_var.set("LIU")
    assert str_var.value == "LIU"
    with raises(TypeError):
        str_var.value = 0
    with raises(ValueError):
        str_var.value = "chang"
    with raises(ValueError):
        str_var.value = "FAIL"


def test_int():
    assert int_var.value == 0
    int_var.value = 1
    assert int_var.value == 1
    int_var.set(2)
    assert int_var.value == 2
    with raises(TypeError):
        int_var.value = 1.0
    with raises(ValueError):
        int_var.value = 4
    with raises(ValueError):
        int_var.value = -1


def test_float():
    assert float_var.value == 1e-2
    float_var.value = 3e-3
    assert float_var.value == 3e-3
    float_var.set(5e-4)
    assert float_var.value == 5e-4
    with raises(TypeError):
        float_var.value = 0
    with raises(ValueError):
        float_var.value = 0.4
    with raises(ValueError):
        float_var.value = -1.0


def test_complex():
    assert complex_var.value == 1 + 2j
    complex_var.value = 3 + 4j
    assert complex_var.value == 3 + 4j
    complex_var.set(5 + 6j)
    assert complex_var.value == 5 + 6j
    with raises(TypeError):
        complex_var.value = 1
    with raises(ValueError):
        complex_var.value = 7 + 8j
    with raises(ValueError):
        complex_var.value = -1 + 2j


def test_required():
    with raises(RuntimeError):
        required_var.validate()
    required_var.set("valid")
    required_var.validate()


def test_math_operations():
    v = Variable(5)
    assert v + 3 == 8
    assert 3 + v == 8
    v += 2
    assert v == 7

    v = Variable(10)
    assert v - 3 == 7
    assert 15 - v == 5
    v -= 2
    assert v == 8

    v = Variable(4)
    assert v * 3 == 12
    assert 3 * v == 12
    v *= 2
    assert v == 8

    v = Variable(15)
    assert v / 3 == 5
    assert 30 / v == 2
    v /= 3
    assert v == 5

    v = Variable(17)
    assert v // 5 == 3
    assert 50 // v == 2
    v //= 4
    assert v == 4

    v = Variable(17)
    assert v % 5 == 2
    assert 5 % v == 5
    v %= 5
    assert v == 2

    v = Variable(2)
    assert v**3 == 8
    assert 2**v == 4
    v **= 2
    assert v == 4

    v = Variable(torch.tensor([1, 2]))
    w = Variable(torch.tensor([3, 4]))
    assert (v @ w) == 11
    v @= w
    assert v == 11


def test_comparison_operations():
    v = Variable(5)
    w = Variable(10)

    assert v < w
    assert v <= w
    assert v <= 5
    assert v == 5
    assert v != w
    assert v >= 5
    assert w > v


def test_container_operations():
    v = Variable([1, 2, 3])
    assert 2 in v
    assert 4 not in v
    assert list(v) == [1, 2, 3]

    items = []
    for item in v:
        items.append(item)
    assert items == [1, 2, 3]


def test_copy_operations():
    v = Variable([1, 2, 3])

    v_copy = copy(v)
    assert v_copy.value == v.value
    v.value.append(4)
    assert v_copy.value == [1, 2, 3, 4]

    v = Variable([1, 2, 3])
    v_deepcopy = deepcopy(v)
    assert v_deepcopy.value == v.value
    v.value.append(4)
    assert v_deepcopy.value == [1, 2, 3]


def test_format_operations():
    v = Variable(42)
    assert str(v) == "42"
    assert repr(v) == "42"
    assert f"{v:03d}" == "042"

    v = Variable(3.14159)
    assert f"{v:.2f}" == "3.14"


def test_type_conversion():
    v = Variable("42")
    assert v.int() == 42
    assert isinstance(v.value, int)

    v = Variable("3.14")
    assert v.float() == 3.14
    assert isinstance(v.value, float)

    v = Variable(42)
    assert v.str() == "42"
    assert isinstance(v.value, str)


def test_wrapping():
    v = Variable(42)
    assert isinstance(v, int)

    with v.unwrapped():
        assert not isinstance(v, int)
        assert isinstance(v, Variable)

    assert isinstance(v, int)

    v.unwrap()
    assert not isinstance(v, int)
    assert isinstance(v, Variable)

    v.wrap()
    assert isinstance(v, int)
