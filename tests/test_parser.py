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

import sys
from argparse import ArgumentTypeError
from typing import Dict, List, Optional, Set, Tuple

import pytest

from chanfig import Config, ConfigParser


class TestConfig(Config):
    __test__ = False

    t: bool
    true: bool
    y: bool
    yes: Optional[bool]
    f: bool
    false: bool
    n: bool
    no: Optional[bool]
    not_recognized: List[bool]


class TestConfigPEP604(Config):
    __test__ = False

    true: bool | None
    false: bool | None
    not_recognized: list[bool]


def test_parse_bool():
    config = TestConfig()
    config.parse(
        [
            "--t",
            "t",
            "--true",
            "true",
            "--y",
            "y",
            "--yes",
            "yes",
            "--f",
            "f",
            "--false",
            "false",
            "--n",
            "n",
            "--no",
            "no",
        ]
    )
    assert config.t and config.true and config.y and config.yes
    assert not config.f and not config.false and not config.n and not config.no

    config = TestConfig()
    config.parse(
        [
            "--t",
            "T",
            "--true",
            "True",
            "--y",
            "Y",
            "--yes",
            "Yes",
            "--f",
            "F",
            "--false",
            "False",
            "--n",
            "N",
            "--no",
            "No",
        ]
    )
    assert config.t and config.true and config.y and config.yes
    assert not config.f and not config.false and not config.n and not config.no


def test_parse_negative_number():
    config = Config()
    config.parse(["--lr", "-0.1"])
    assert config.lr == -0.1
    config = Config()
    config.parse(["--wd", "-1e-4"])
    assert config.wd == -0.0001


@pytest.mark.skipif(sys.version_info < (3, 10), reason="PEP604 is available in Python 3.10+")
def test_parse_pep604():
    config = TestConfigPEP604()
    config.parse(
        [
            "--true",
            "true",
            "--false",
            "false",
        ]
    )
    assert config.true and not config.false

    config = TestConfigPEP604()
    config.parse(
        [
            "--true",
            "True",
            "--false",
            "False",
        ]
    )
    assert config.true and not config.false


def test_parse_config_requires_config():
    parser = ConfigParser()
    with pytest.raises(ValueError):
        parser.parse_config(["--a", "1"], config=None)


def test_parse_invalid_default_config_action():
    parser = ConfigParser()
    with pytest.raises(ValueError):
        parser.parse(["--a", "1"], default_config="config", no_default_config_action="invalid")


def test_parse_default_config_warn_and_ignore():
    parser = ConfigParser()
    with pytest.warns(RuntimeWarning):
        parser.merge_default_config(Config(), "config", no_default_config_action="warn")
    result = parser.merge_default_config(Config(), "config", no_default_config_action="ignore")
    assert isinstance(result, Config)


def test_parse_unknown_argument_suggests(capsys):
    parser = ConfigParser()
    parser.add_argument("--learning-rate")
    with pytest.raises(SystemExit):
        parser.parse_args(["--learnig-rate", "0.1"])
    stderr = capsys.readouterr().err
    assert "Did you mean" in stderr
    assert "--learning-rate" in stderr


def test_parse_warns_for_typos():
    cfg = Config({"lr": 0.1})
    parser = ConfigParser()
    with pytest.warns(RuntimeWarning):
        parser.parse(["--lrr", "0.2"], config=cfg)


def test_parser_contains_and_negative_normalize():
    parser = ConfigParser()
    parser.add_argument("--lr")
    args = parser.parse(["--lr", "-0.1"])
    assert parser.__contains__("--lr")
    assert args.lr == -0.1
    parser.add_argument("--val")
    args = parser.parse(["--val=-2"])
    assert args.val == -2


class ContainerConfig(Config):
    __test__ = False
    list_field: List[int]
    tuple_field: Tuple[int]
    set_field: Set[int]
    dict_field: Dict[str, int]


def test_container_arguments_and_conversion():
    parser = ConfigParser()
    cfg = ContainerConfig()
    parser.parse_config(
        [
            "--list_field",
            "1",
            "2",
            "--tuple_field",
            "3",
            "4",
            "--set_field",
            "5",
            "6",
            "--dict_field",
            "a=1",
            "b=2",
        ],
        config=cfg,
    )
    assert cfg.list_field == [1, 2]
    assert cfg.tuple_field == (3, 4)
    assert cfg.set_field == {5, 6}
    assert cfg.dict_field == {"a": 1, "b": 2}


def test_parse_heterogeneous_tuple_values():
    class MixedTupleConfig(Config):
        __test__ = False

        mixed: Tuple[int, bool, str]

    config = MixedTupleConfig()
    config.parse_config(["--mixed", "1", "false", "name"])
    assert config.mixed == (1, False, "name")


def test_convert_container_value_errors():
    parser = ConfigParser()
    meta = {"container_type": dict, "item_parser": parser.identity, "item_type": None}
    with pytest.raises(ArgumentTypeError):
        parser._convert_container_value("not-a-kv", meta)  # pylint: disable=protected-access


def test_parse_creates_default_config_when_none_provided():
    parser = ConfigParser()
    cfg = parser.parse(["--a", "1"])
    assert isinstance(cfg, Config)
    assert cfg.a == 1


def test_parse_args_no_eval_str():
    parser = ConfigParser()
    parser.add_argument("--val")
    parsed = parser.parse_args(["--val", "1"], eval_str=False)
    assert parsed.val == "1"


def test_infer_container_argument_none_for_scalar():
    parser = ConfigParser()
    assert parser._infer_container_argument(int) is None  # pylint: disable=protected-access


def test_merge_default_config_raise():
    parser = ConfigParser()
    with pytest.raises(RuntimeError):
        parser.merge_default_config(Config(), "config", no_default_config_action="raise")


def test_convert_container_value_non_iterable_tuple_set_paths():
    parser = ConfigParser()
    meta_tuple = {"container_type": tuple}
    meta_set = {"container_type": set}
    assert parser._convert_container_value(1, meta_tuple) == (1,)
    assert parser._convert_container_value(1, meta_set) == {1}


def test_parse_list_annotation_values():
    class ListConfig(Config):
        __test__ = False

        numbers: List[int]

    config = ListConfig()
    config.parse_config(["--numbers", "1", "2"])
    assert config.numbers == [1, 2]
    assert all(isinstance(v, int) for v in config.numbers)


def test_parse_list_from_default_preserves_flat_shape():
    config = Config()
    config.lst = [1, 2]
    config.parse(["--lst", "3", "4"])
    assert config.lst == [3, 4]
    assert all(isinstance(v, int) for v in config.lst)


def test_parse_dict_with_annotation():
    class DictConfig(Config):
        __test__ = False

        mapping: Dict[str, int]

    config = DictConfig()
    config.parse_config(["--mapping", "a=1", "b=2"])
    assert config.mapping == {"a": 1, "b": 2}
