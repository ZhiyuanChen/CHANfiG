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

from typing import Any


class Dict(type(dict)):  # type: ignore[misc]
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        # if hasattr(cls, '__before_init__'):
        #     cls.__before_init__()
        instance = super().__call__(*args, **kwargs)
        instance.__post_init__()
        instance.validate()
        return instance
