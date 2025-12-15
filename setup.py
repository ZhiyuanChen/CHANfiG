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

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

ext_modules = [
    Extension(
        "chanfig._cext",
        sources=["chanfig/_cext.c"],
    )
]


class BuildExtOptional(build_ext):
    """Allow building without a C compiler; ignore failures."""

    def run(self):
        try:
            super().run()
        except Exception as exc:  # pragma: no cover - fallback when no compiler
            self.announce(f"WARNING: building C extension failed ({exc}); falling back to pure Python", level=3)

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as exc:  # pragma: no cover - fallback when no compiler
            self.announce(f"WARNING: building extension {ext.name} failed ({exc}); skipping C extension", level=3)


setup(ext_modules=ext_modules, cmdclass={"build_ext": BuildExtOptional})
