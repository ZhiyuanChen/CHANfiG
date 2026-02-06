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

from collections.abc import Mapping
from typing import Any


def find_placeholders(text: str) -> list[str]:
    r"""Find all placeholders in text, including nested ones.

    This function searches for placeholders in the format ${name} and returns a list
    of all placeholder names found, including those that are nested within other placeholders.

    Examples:
        >>> find_placeholders("Hello ${name}")
        ['name']
        >>> find_placeholders("Hello ${user.${type}}")
        ['user.${type}', 'type']
        >>> find_placeholders("${outer${inner}}")
        ['outer${inner}', 'inner']
    """
    if not isinstance(text, str):
        return []

    results = []
    stack = []
    i = 0

    while i < len(text):
        if text[i : i + 2] == "${":  # noqa: E203
            stack.append(i)
            i += 2
        elif text[i] == "}" and stack:
            start = stack.pop()
            placeholder = text[start + 2 : i]  # noqa: E203
            if not stack:
                results.append(placeholder)
            i += 1
        else:
            i += 1

    nested_results = []
    for placeholder in results:
        nested_results.extend(find_placeholders(placeholder))

    return results + nested_results


def find_circular_reference(graph: Mapping) -> list[str] | None:
    r"""
    Find circular references in a dependency graph.

    This function performs a depth-first search to detect any circular references
    in a graph represented as a mapping of nodes to their dependencies.
    """

    visited: set[Any] = set()
    path: list[Any] = []
    path_indices: dict[Any, int] = {}

    def dfs(node):
        if node in path_indices:
            cycle_start = path_indices[node]
            return path[cycle_start:] + [node]
        if node in visited:
            return None

        path_indices[node] = len(path)
        path.append(node)

        for child in graph.get(node, []):
            result = dfs(child)
            if result is not None:
                return result

        path.pop()
        path_indices.pop(node, None)
        visited.add(node)
        return None

    for key in graph:
        if key in visited:
            continue
        result = dfs(key)
        if result is not None:
            return result

    return None
