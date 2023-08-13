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

from pytest import raises

from chanfig import Variable


class Test:
    str_var = Variable("CHANFIG", str, validator=lambda x: x.isupper(), choices=["CHANFIG", "CHANG", "LIU"])
    int_var = Variable(0, int, validator=lambda x: x > 0, choices=[1, 2, 3])
    float_var = Variable(1e-2, float, validator=lambda x: 0.0 <= x < 1.0, choices=[1e-2, 3e-3, 5e-4])
    complex_var = Variable(1 + 2j, complex, validator=lambda x: x.real > 0.0, choices=[1 + 2j, 3 + 4j, 5 + 6j])
    bool_var = Variable(True, bool)
    required_var = Variable(required=True)

    def test_str(self):
        assert self.str_var.value == "CHANFIG"
        self.str_var.value = "CHANG"
        assert self.str_var.value == "CHANG"
        self.str_var.set("LIU")
        assert self.str_var.value == "LIU"
        with raises(TypeError):
            self.str_var.value = 0
        with raises(ValueError):
            self.str_var.value = "chang"
        with raises(ValueError):
            self.str_var.value = "FAIL"

    def test_int(self):
        assert self.int_var.value == 0
        self.int_var.value = 1
        assert self.int_var.value == 1
        self.int_var.set(2)
        assert self.int_var.value == 2
        with raises(TypeError):
            self.int_var.value = 1.0
        with raises(ValueError):
            self.int_var.value = 4
        with raises(ValueError):
            self.int_var.value = -1

    def test_float(self):
        assert self.float_var.value == 1e-2
        self.float_var.value = 3e-3
        assert self.float_var.value == 3e-3
        self.float_var.set(5e-4)
        assert self.float_var.value == 5e-4
        with raises(TypeError):
            self.float_var.value = 0
        with raises(ValueError):
            self.float_var.value = 0.4
        with raises(ValueError):
            self.float_var.value = -1.0

    def test_complex(self):
        assert self.complex_var.value == 1 + 2j
        self.complex_var.value = 3 + 4j
        assert self.complex_var.value == 3 + 4j
        self.complex_var.set(5 + 6j)
        assert self.complex_var.value == 5 + 6j
        with raises(TypeError):
            self.complex_var.value = 1
        with raises(ValueError):
            self.complex_var.value = 7 + 8j
        with raises(ValueError):
            self.complex_var.value = -1 + 2j

    def test_required(self):
        with raises(RuntimeError):
            self.required_var.validate()
        self.required_var.set("valid")
        self.required_var.validate()
