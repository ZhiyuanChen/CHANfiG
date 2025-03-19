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

from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import pytest

from chanfig.utils.annotation import conform_annotation, get_annotations, honor_annotation


class TestClass:
    a: int
    b: str
    c: List[int]


def example_function(a: int, b: str, c: List[int]) -> None:
    pass


def test_get_annotations_class():
    result = get_annotations(TestClass)
    assert "a" in result
    assert "b" in result
    assert "c" in result
    assert result["a"] == int
    assert result["b"] == str
    assert result["c"] == List[int]


def test_get_annotations_function():
    result = get_annotations(example_function)
    assert "a" in result
    assert "b" in result
    assert "c" in result
    assert "return" in result
    assert result["a"] == int
    assert result["b"] == str
    assert result["c"] == List[int]
    assert result["return"] is None


def test_get_annotations_instance():
    instance = TestClass()
    result = get_annotations(instance)
    assert "a" in result
    assert "b" in result
    assert "c" in result
    assert result["a"] == int
    assert result["b"] == str
    assert result["c"] == List[int]


def test_get_annotations_with_module():
    import sys

    this_module = sys.modules[__name__]
    result = get_annotations(this_module)
    assert isinstance(result, dict)


def test_get_annotations_without_annotations():
    class NoAnnotations:
        pass

    result = get_annotations(NoAnnotations)
    assert result == {}

    instance = NoAnnotations()
    result = get_annotations(instance)
    assert result == {}


def test_get_annotations_invalid_annotations():
    class InvalidAnnotations:
        __annotations__ = "not_a_dict"

    with pytest.raises(ValueError):
        get_annotations(InvalidAnnotations)


def test_get_annotations_wrapped_function():
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @decorator
    def func(a: int, b: str) -> None:
        pass

    result = get_annotations(func)
    assert "a" in result
    assert "b" in result
    assert result["a"] == int
    assert result["b"] == str


def test_get_annotations_partial_function():
    from functools import partial

    def func(a: int, b: str) -> None:
        pass

    partial_func = partial(func, a=10)
    result = get_annotations(partial_func)
    assert isinstance(result, dict)


def test_honor_annotation_basic_types():
    assert honor_annotation("42", int) == 42
    assert honor_annotation(42, str) == "42"
    assert honor_annotation("3.14", float) == 3.14
    assert honor_annotation(True, str) == "True"
    assert honor_annotation("not_an_int", int) == "not_an_int"


def test_honor_annotation_union_types():
    assert honor_annotation("name", Union[int, str]) == "name"
    assert honor_annotation(123, Union[int, str]) == 123
    assert honor_annotation("42", Union[int, str]) == "42"


def test_honor_annotation_optional_types():
    assert honor_annotation(None, Optional[int]) is None
    assert honor_annotation("42", Optional[int]) == 42
    assert honor_annotation(42, Optional[str]) == "42"


def test_honor_annotation_list_types():
    assert honor_annotation(["1", "2", "3"], List[int]) == [1, 2, 3]
    assert honor_annotation([1, 2, 3], List[str]) == ["1", "2", "3"]
    assert honor_annotation([], List[int]) == []


def test_honor_annotation_nested_list_types():
    assert honor_annotation([["1", "2"], ["3", "4"]], List[List[int]]) == [[1, 2], [3, 4]]


def test_honor_annotation_tuple_types():
    assert honor_annotation(("1", 2), Tuple[int, int]) == (1, 2)
    assert honor_annotation((1, 2), Tuple[str, str]) == ("1", "2")
    assert honor_annotation(("1", "2", "3"), Tuple[int, ...]) == (1, 2, 3)


def test_honor_annotation_dict_types():
    assert honor_annotation({"a": "1", "b": "2"}, Dict[str, int]) == {"a": 1, "b": 2}
    assert honor_annotation({1: 2, 3: 4}, Dict[str, str]) == {"1": "2", "3": "4"}
    assert honor_annotation({}, Dict[str, int]) == {}


def test_honor_annotation_set_types():
    assert honor_annotation({"1", "2", "3"}, Set[int]) == {1, 2, 3}
    assert honor_annotation({1, 2, 3}, Set[str]) == {"1", "2", "3"}
    assert honor_annotation(set(), Set[int]) == set()


def test_honor_annotation_any_type():
    assert honor_annotation(42, Any) == 42
    assert honor_annotation("test", Any) == "test"
    assert honor_annotation([1, 2, 3], Any) == [1, 2, 3]


def test_conform_annotation_basic_types():
    assert conform_annotation(42, int)
    assert conform_annotation("hello", str)
    assert not conform_annotation("42", int)
    assert not conform_annotation(42, str)


def test_conform_annotation_union_types():
    assert conform_annotation("name", Union[int, str])
    assert conform_annotation(123, Union[int, str])
    assert not conform_annotation([], Union[int, str])
    assert not conform_annotation({}, Union[int, str])


def test_conform_annotation_optional_types():
    assert conform_annotation(None, Optional[int])
    assert conform_annotation(42, Optional[int])
    assert not conform_annotation("42", Optional[int])
    assert not conform_annotation([], Optional[int])


def test_conform_annotation_list_types():
    assert conform_annotation([1, 2, 3], List[int])
    assert not conform_annotation([1, "2", 3], List[int])
    assert conform_annotation([], List[int])
    assert not conform_annotation("not_a_list", List[int])
    assert not conform_annotation(42, List[int])


def test_conform_annotation_tuple_types():
    assert conform_annotation((1, 2), Tuple[int, int])
    assert not conform_annotation((1, "2"), Tuple[int, int])
    assert not conform_annotation((1, 2, 3), Tuple[int, int])
    assert conform_annotation((1, 2, 3), Tuple[int, ...])
    assert not conform_annotation((1, "2", 3), Tuple[int, ...])


def test_conform_annotation_dict_types():
    assert conform_annotation({"a": 1, "b": 2}, Dict[str, int])
    assert not conform_annotation({"a": 1, "b": "2"}, Dict[str, int])
    assert not conform_annotation({1: 1, 2: 2}, Dict[str, int])
    assert conform_annotation({}, Dict[str, int])


def test_conform_annotation_set_types():
    assert conform_annotation({1, 2, 3}, Set[int])
    assert not conform_annotation({1, "2", 3}, Set[int])
    assert conform_annotation(set(), Set[int])


def test_conform_annotation_callable_type():
    def func():
        pass

    assert conform_annotation(func, Callable)
    assert conform_annotation(lambda x: x, Callable)
    assert not conform_annotation("not_callable", Callable)
    assert not conform_annotation(42, Callable)


def test_conform_annotation_any_type():
    assert conform_annotation(42, Any)
    assert conform_annotation("test", Any)
    assert conform_annotation([1, 2, 3], Any)
    assert conform_annotation(None, Any)
