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

from chanfig.utils.null import NULL


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
