# CHANfiG, Easier Configuration.
# Copyright (c) 2022-2023, CHANfiG Contributors
# This program is free software: you can redistribute it and/or modify
# it under the terms of the following licenses:
# - Unlicense
# - GNU GPL 2.0 (or any later version)
# - MIT
# - Apache 2.0
# - BSD 2-Clause
# - BSD 3-Clause
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

# pylint: disable=C0302

from __future__ import annotations

from ast import literal_eval
from contextlib import contextmanager
from copy import copy, deepcopy
from json import dumps as json_dumps
from json import loads as json_loads
from os import PathLike
from os.path import splitext
from typing import IO, Any, Callable, Iterable, Mapping, Optional, Union
from warnings import warn

from yaml import dump as yaml_dump
from yaml import load as yaml_load

from .utils import FileError, JsonEncoder, Null, YamlDumper, YamlLoader
from .variable import Variable

try:
    from torch import Tensor as TorchTensor
    from torch import device as TorchDevice
    from torch import dtype as TorchDtype

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

PathStr = Union[PathLike, str, bytes]
File = Union[PathStr, IO]

YAML = ("yml", "yaml")
JSON = ("json",)
PYTHON = ("py",)


class FlatDict(dict):
    r"""
    `FlatDict` with attribute-style access.

    `FlatDict` inherits from built-in `dict`.

    It comes with many easy to use helper function, such as `difference`, `intersection`.

    It also has full support for  IO operations, such as `json` and `yaml`.

    Even better, `FlatDict` has pytorch support built-in.
    You can directly call `FlatDict.cpu()` or `FlatDict.to("cpu")` to move all `torch.Tensor` objects across devices.

    `FlatDict` works best with `Variable` objects.
    Just simply call ``FlatDict.a = Variable(1); FlatDict.b = FlatDict.a``, and their values will be sync.

    Attributes:
        indent: Indentation level in printing and dumping to json or yaml.
        default_factory: Default factory for defaultdict behavior.

    Notes:
        `FlatDict` rewrite `__getattribute__` and `__getattr__` to supports attribute-style access to its members.
        Therefore, all internal attributes should be set and get through `FlatDict.setattr` and `FlatDict.getattr`.

        Although it is possible to override other internal methods, it is not recommended to do so.

        `__class__`, `__dict__`, and `getattr` are reserved and cannot be override in any manner.

    Examples:
    ```python
    >>> d = FlatDict()
    >>> d.d = 1013
    >>> d['d']
    1013
    >>> d['i'] = 1013
    >>> d.i
    1013
    >>> d.a = Variable(1)
    >>> d.b = d.a
    >>> d.a, d.b
    (1, 1)
    >>> d.a += 1
    >>> d.a, d.b
    (2, 2)
    >>> d.a = 3
    >>> d.a, d.b
    (3, 3)
    >>> d.a = Variable('hello')
    >>> f"{d.a}, world!"
    'hello, world!'
    >>> d.a = d.a + ', world!'
    >>> d.b
    'hello, world!'

    ```
    """

    # pylint: disable=R0904

    indent: int = 2
    default_factory: Optional[Callable]

    def __init__(self, *args, default_factory: Optional[Callable] = None, **kwargs) -> None:
        super().__init__()
        if default_factory is not None:
            if callable(default_factory):
                self.setattr("default_factory", default_factory)
            else:
                raise TypeError(
                    f"default_factory={default_factory} should be of type Callable, but got {type(default_factory)}."
                )
        self._init(*args, **kwargs)

    def _init(self, *args, **kwargs) -> None:
        r"""
        Initialise values from arguments for `FlatDict`.

        This method is called in `__init__`.
        """

        for key, value in args:
            self.set(key, value)
        for key, value in kwargs.items():
            self.set(key, value)

    def __getattribute__(self, name) -> Any:
        if name not in ("__class__", "__dict__", "getattr") and name in self:
            return self[name]
        return super().__getattribute__(name)

    def get(self, name: str, default: Any = Null) -> Any:
        r"""
        Get value from `FlatDict`.

        Note that `default` has higher priority than `default_factory`.

        Args:
            name:
            default:

        Returns:
            value:
                If name does not exist, return `default`.
                If `default` is not specified, return `default_factory()`.

        Raises:
            KeyError: If name does not exist and `default`/`default_factory` is not specified.

        **Alias**:

        + `__getitem__`
        + `__getattr__`

        Examples:
        ```python
        >>> d = FlatDict(d=1013)
        >>> d.get('d')
        1013
        >>> d['d']
        1013
        >>> d.d
        1013
        >>> d.get('f', 2)
        2
        >>> d.get('f')
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain f.'

        ```
        """

        return super().__getitem__(name) if default is Null else self.__missing__(name, default)

    __getitem__ = get
    __getattr__ = get

    def set(self, name: str, value: Any) -> None:
        r"""
        Set value of `FlatDict`.

        Args:
            name:
            value:

        **Alias**:

        + `__setitem__`
        + `__setattr__`

        Examples:
        ```python
        >>> d = FlatDict()
        >>> d.set('d', 1013)
        >>> d.get('d')
        1013
        >>> d['n'] = 'chang'
        >>> d.n
        'chang'
        >>> d.n = 'liu'
        >>> d['n']
        'liu'

        ```
        """

        if isinstance(value, str):
            try:
                value = literal_eval(value)
            except (TypeError, ValueError, SyntaxError):
                pass
        if name in self and isinstance(self[name], Variable):
            self[name].set(value)
        else:
            super().__setitem__(name, value)

    __setitem__ = set
    __setattr__ = set

    def delete(self, name: str) -> None:
        r"""
        Delete value from `FlatDict`.

        Args:
            name:

        **Alias**:

        + `__delitem__`
        + `__delattr__`

        Examples:
        ```python
        >>> d = FlatDict(d=1016, n='chang')
        >>> d.d
        1016
        >>> d.n
        'chang'
        >>> d.delete('d')
        >>> d.d
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain d.'
        >>> del d.n
        >>> d.n
        Traceback (most recent call last):
        KeyError: 'FlatDict does not contain n.'
        >>> del d.f
        Traceback (most recent call last):
        KeyError: 'f'

        ```
        """

        super().__delitem__(name)

    __delitem__ = delete
    __delattr__ = delete

    def getattr(self, name: str, default: Any = Null) -> Any:
        r"""
        Get attribute of `FlatDict`.

        Note that it won't retrieve value in `FlatDict`,
        nor will it create new `default_factory` even if it is assigned.

        Args:
            name:
            default:

        Returns:
            value: If name does not exist, return `default`.

        Examples:
        ```python
        >>> d = FlatDict(a=1, default_factory=list)
        >>> d.getattr('default_factory')
        <class 'list'>
        >>> d.getattr('b', 2)
        2
        >>> d.getattr('a')
        Traceback (most recent call last):
        AttributeError: FlatDict has no attribute a.

        ```
        """

        try:
            if name in self.__dict__:
                return self.__dict__[name]
            if name in self.__class__.__dict__:
                return self.__class__.__dict__[name]
            return super().getattr(name, default)  # type: ignore
        except AttributeError:
            if default is not Null:
                return default
            raise AttributeError(f"{self.__class__.__name__} has no attribute {name}.") from None

    def setattr(self, name: str, value: Any) -> None:
        r"""
        Set attribute of `FlatDict`.

        Note that it won't alter values in `FlatDict`.

        Args:
            name:
            value:

        Warns:
            RuntimeWarning: If name already exists in `FlatDict`.

        Examples:
        ```python
        >>> d = FlatDict()
        >>> d.setattr('attr', 'value')
        >>> d.getattr('attr')
        'value'
        >>> d.set('d', 1013)
        >>> d.setattr('d', 1031)  # RuntimeWarning: d already exists in FlatDict.
        >>> d.get('d')
        1013
        >>> d.d
        1013
        >>> d.getattr('d')
        1031

        ```
        """

        if name in self:
            warn(
                f"{name} already exists in {self.__class__.__name__}.\n"
                "Users must call `{self.__class__.__name__}.getattr()` to retrieve conflicting attribute value.",
                RuntimeWarning,
            )
        self.__dict__[name] = value

    def delattr(self, name: str) -> None:
        r"""
        Delete attribute of `FlatDict`.

        Note that it won't delete values in `FlatDict`.

        Args:
            name:

        Examples:
        ```python
        >>> d = FlatDict()
        >>> d.setattr('name', 'chang')
        >>> d.getattr('name')
        'chang'
        >>> d.delattr('name')
        >>> d.getattr('name')
        Traceback (most recent call last):
        AttributeError: FlatDict has no attribute name.

        ```
        """

        del self.__dict__[name]

    def hasattr(self, name: str) -> bool:
        r"""
        Determine if an attribute exists in `FlatDict`.

        Args:
            name:

        Returns:
            (bool):

        Examples:
        ```python
        >>> d = FlatDict()
        >>> d.setattr('name', 'chang')
        >>> d.hasattr('name')
        True
        >>> d.delattr('name')
        >>> d.hasattr('name')
        False

        ```
        """

        try:
            if name in self.__dict__ or name in self.__class__.__dict__:
                return True
            return super().hasattr(name)  # type: ignore
        except AttributeError:
            return False

    def __missing__(self, name: str, default: Any = Null) -> Any:  # pylint: disable=R1710
        if name == "_ipython_canary_method_should_not_exist_":
            return
        if default is Null:
            # default_factory might not in __dict__ and cannot be replaced with if self.getattr("default_factory")
            if "default_factory" not in self.__dict__:
                raise KeyError(f"{self.__class__.__name__} does not contain {name}.")
            default_factory = self.getattr("default_factory")
            default = default_factory()
            if isinstance(default, FlatDict):
                default.__dict__.update(self.__dict__)
            super().__setitem__(name, default)
        return default

    def dict(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert `FlatDict` to other `Mapping`.

        Args:
            cls: Target class to be converted to.

        Returns:
            (Mapping):

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        return cls({k: v.value if isinstance(v, Variable) else v for k, v in self.items()})

    def update(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:  # type: ignore
        r"""
        Update `FlatDict` values w.r.t. `other`.

        Args:
            other:

        Returns:
            self:

        **Alias**:

        + `merge`
        + `merge_from_file`
        + `union`

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.update(n).dict()
        {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.update(l).dict()
        {'a': 1, 'b': 'b', 'c': 3, 'd': 4}

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            for key, value in other.items():
                if key in self and isinstance(self[key], (Mapping,)) and isinstance(value, (Mapping,)):
                    self[key].update(value)
                else:
                    self[key] = value
        elif isinstance(other, Iterable):
            for key, value in other:  # type: ignore
                self[key] = value
        return self

    merge = update
    merge_from_file = update
    union = update

    def difference(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:
        r"""
        Difference between `FlatDict` values and `other`.

        Args:
            other:

        Returns:
            (FlatDict):

        **Alias**:

        + `diff`

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.difference(n).dict()
        {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.difference(l).dict()
        {'d': 4}
        >>> d.difference(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>.

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}.")

        return self.empty_like(
            **{key: value for key, value in other if key not in self or self[key] != value}  # type: ignore
        )

    diff = difference

    def intersection(self, other: Union[Mapping, Iterable, PathStr]) -> FlatDict:
        r"""
        Intersection between `FlatDict` values and `other`.

        Args:
            other (Mapping | Iterable | PathStr):

        Returns:
            (FlatDict):

        **Alias**:

        + `inter`

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
        >>> d.intersection(n).dict()
        {}
        >>> l = [('c', 3), ('d', 4)]
        >>> d.intersection(l).dict()
        {'c': 3}
        >>> d.intersection(1)
        Traceback (most recent call last):
        TypeError: other=1 should be of type Mapping, Iterable or PathStr, but got <class 'int'>.

        ```
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = other.items()
        if not isinstance(other, Iterable):
            raise TypeError(f"other={other} should be of type Mapping, Iterable or PathStr, but got {type(other)}.")
        return self.empty_like(
            **{key: value for key, value in other if key in self and self[key] == value}  # type: ignore
        )

    inter = intersection

    def to(self, cls: Union[str, TorchDevice, TorchDtype]) -> FlatDict:
        r"""
        Convert values of `FlatDict` to target `cls`.

        Args:
            cls (str | torch.device | torch.dtype):

        Returns:
            self:

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        # pylint: disable=C0103

        if isinstance(cls, str):
            if cls in ("cpu", "gpu", "cuda", "tpu", "xla"):
                return getattr(self, cls)()
        if TORCH_AVAILABLE and isinstance(cls, (TorchDevice, TorchDtype)):
            for k, v in self.items():
                if isinstance(v, TorchTensor):
                    self[k] = v.to(cls)
            return self

        raise TypeError(f"to() only support torch.dtype and torch.device, but got {cls}.")

    def cpu(self) -> FlatDict:  # pylint: disable=C0103
        r"""
        Move all tensors to cpu.

        Returns:
            self:

        Examples:
        ```python
        >>> import torch
        >>> d = FlatDict(a=torch.tensor(1))
        >>> d.cpu().dict()  # doctest: +SKIP
        {'a': tensor(1, device='cpu')}

        ```
        """

        return self.to(TorchDevice("cpu"))

    def gpu(self) -> FlatDict:  # pylint: disable=C0103
        r"""
        Move all tensors to gpu.

        Returns:
            self:

        **Alias**:

        + `cuda`

        Examples:
        ```python
        >>> import torch
        >>> d = FlatDict(a=torch.tensor(1))
        >>> d.gpu().dict()  # doctest: +SKIP
        {'a': tensor(1, device='cuda:0')}

        ```
        """

        return self.to(TorchDevice("cuda"))

    cuda = gpu

    def tpu(self) -> FlatDict:
        r"""
        Move all tensors to tpu.

        Returns:
            self:

        **Alias**:

        + `xla`

        Examples:
        ```python
        >>> import torch
        >>> d = FlatDict(a=torch.tensor(1))
        >>> d.tpu().dict()  # doctest: +SKIP
        {'a': tensor(1, device='xla:0')}

        ```
        """

        return self.to(TorchDevice("xla"))

    xla = tpu

    def copy(self) -> FlatDict:
        r"""
        Create a shallow copy of `FlatDict`.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.copy()
        >>> c.dict()
        {'a': []}
        >>> d.a.append(1)
        >>> c.dict()
        {'a': [1]}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        return copy(self)

    def deepcopy(self, memo: Optional[Mapping] = None) -> FlatDict:
        r"""
        Create a deep copy of `FlatDict`.

        Returns:
            (FlatDict):

        **Alias**:

        + `clone`
        + `__deepcopy__`

        Examples:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.deepcopy()
        >>> c.dict()
        {'a': []}
        >>> d.a.append(1)
        >>> c.dict()
        {'a': []}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        # pylint: disable=C0103

        if memo is not None and id(self) in memo:
            return memo[id(self)]
        ret = self.empty_like()
        for k, v in self.items():
            if isinstance(v, FlatDict):
                ret[k] = v.deepcopy(memo=memo)
            else:
                ret[k] = deepcopy(v)
        return ret

    __deepcopy__ = deepcopy

    clone = deepcopy

    def dump(self, file: File, method: Optional[str] = None, *args, **kwargs) -> None:  # pylint: disable=W1113
        r"""
        Dump `FlatDict` to file.

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.dump("example.yaml")

        ```
        """

        if method is None:
            if isinstance(file, IO):
                raise ValueError("method must be specified when dumping to file-like object.")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in YAML:
            return self.yaml(file=file, *args, **kwargs)  # type: ignore
        if extension in JSON:
            return self.json(file=file, *args, **kwargs)  # type: ignore
        raise FileError(f"file {file} should be in {JSON} or {YAML}, but got {extension}")  # type: ignore

    @classmethod
    def load(cls, file: File, method: Optional[str] = None, *args, **kwargs) -> FlatDict:  # pylint: disable=W1113
        """
        Load `FlatDict` from file.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict.load("example.yaml")
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        if method is None:
            if isinstance(file, IO):
                raise ValueError("method must be specified when loading from file-like object.")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in JSON:
            return cls.from_json(file, *args, **kwargs)
        if extension in YAML:
            return cls.from_yaml(file, *args, **kwargs)
        raise FileError("file {file} should be in {JSON} or {YAML}, but got {extension}.")

    def json(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump `FlatDict` to json file.

        This function calls `self.jsons()` to generate json string.
        You may overwrite `jsons` in case something is not json serializable.

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.json("example.json")

        ```
        """

        with self.open(file, mode="w") as fp:  # pylint: disable=C0103
            fp.write(self.jsons(*args, **kwargs))

    @classmethod
    def from_json(cls, file: File, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from json file.

        This function calls `self.from_jsons()` to construct object from json string.
        You may overwrite `from_jsons` in case something is not json serializable.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict.from_json('example.json')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            return cls.from_jsons(fp.read(), *args, **kwargs)

    def jsons(self, *args, **kwargs) -> str:
        r"""
        Dump `FlatDict` to json string.

        Returns:
            (str):

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.jsons()
        '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}'

        ```
        """

        if "cls" not in kwargs:
            kwargs["cls"] = JsonEncoder
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent", 2)
        return json_dumps(self.dict(), *args, **kwargs)

    @classmethod
    def from_jsons(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from json string.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict.from_jsons('{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        config = cls()
        config.update(json_loads(string, *args, **kwargs))
        return config

    def yaml(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump `FlatDict` to yaml file.

        This function calls `self.yamls()` to generate yaml string.
        You may overwrite `yamls` in case something is not yaml serializable.

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.yaml("example.yaml")

        ```
        """

        with self.open(file, mode="w") as fp:  # pylint: disable=C0103
            self.yamls(fp, *args, **kwargs)

    @classmethod
    def from_yaml(cls, file: File, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from yaml file.

        This function calls `self.from_yamls()` to construct object from yaml string.
        You may overwrite `from_yamls` in case something is not yaml serializable.

        Returns:
            (FlatDict):

        ```python
        >>> d = FlatDict.from_yaml('example.yaml')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            return cls.from_yamls(fp.read(), *args, **kwargs)

    def yamls(self, *args, **kwargs) -> str:
        r"""
        Dump `FlatDict` to yaml string.

        Returns:
            (str):

        Examples:
        ```python
        >>> d = FlatDict(a=1, b=2, c=3)
        >>> d.yamls()
        'a: 1\nb: 2\nc: 3\n'

        ```
        """

        if "Dumper" not in kwargs:
            kwargs["Dumper"] = YamlDumper
        if "indent" not in kwargs:
            kwargs["indent"] = self.getattr("indent", 2)
        return yaml_dump(self.dict(), *args, **kwargs)  # type: ignore

    @classmethod
    def from_yamls(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from yaml string.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict.from_yamls('a: 1\nb: 2\nc: 3\n')
        >>> d.dict()
        {'a': 1, 'b': 2, 'c': 3}

        ```
        """

        if "Loader" not in kwargs:
            kwargs["Loader"] = YamlLoader

        config = cls()
        config.update(yaml_load(string, *args, **kwargs))
        return config

    @staticmethod
    @contextmanager
    def open(file: File, *args, **kwargs):
        """
        Open file IO from file path or file-like object.

        This methods extends the ability of built-in `open` by allowing it to accept an `IO` object.

        Args:
            file: File path or file-like object.
            *args: Additional arguments passed to `open`.
                Defaults to ().
            **kwargs: Any
                Additional keyword arguments passed to `open`.
                Defaults to ().

        Yields:
            (FileIO):

        Examples:
        ```python
        >>> with FlatDict.open("example.yaml") as fp:
        ...     print(fp.read())
        a: 1
        b: 2
        c: 3
        <BLANKLINE>

        ```
        """

        if isinstance(file, (PathLike, str)):
            file = open(file, *args, **kwargs)  # pylint: disable=W1514
            try:
                yield file
            finally:
                file.close()  # type: ignore
        elif isinstance(file, (IO,)):
            yield file
        else:
            raise TypeError(f"file={file!r} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}.")

    @classmethod
    def empty(cls, *args, **kwargs) -> FlatDict:
        r"""
        Initialise an empty `FlatDict`.

        This method is helpful when you inheriting `FlatDict` with default values defined in `__init__()`.
        As use `type(self)()` in this case would copy all the default values, which might not be desired.

        This method will preserve everything in `FlatDict.__class__.__dict__`.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict(a=[])
        >>> c = d.empty()
        >>> c.dict()
        {}

        ```
        """

        empty = cls()
        empty.clear()
        empty._init(*args, **kwargs)
        return empty

    def empty_like(self, *args, **kwargs) -> FlatDict:
        r"""
        Initialise an empty copy of `FlatDict`.

        This method will preserve everything in `FlatDict.__class__.__dict__` and `FlatDict.__dict__`.

        Returns:
            (FlatDict):

        Examples:
        ```python
        >>> d = FlatDict(a=[])
        >>> d.setattr("name", "Chang")
        >>> c = d.empty_like()
        >>> c.dict()
        {}
        >>> c.getattr("name")
        'Chang'

        ```
        """

        empty = self.empty(*args, **kwargs)
        empty.__dict__.update(self.__dict__)
        return empty

    @staticmethod
    def extra_repr() -> str:  # pylint: disable=C0116
        return ""

    def __repr__(self) -> str:
        extra_lines = []
        extra_repr = self.extra_repr()
        # empty string will be split into list ['']
        if extra_repr:
            extra_lines = extra_repr.split("\n")
        child_lines = []
        for key, value in self.items():
            key_repr = repr(key)
            value_repr = repr(value)
            value_repr = self._add_indent(value_repr)
            child_lines.append("(" + key_repr + "): " + value_repr)
        lines = extra_lines + child_lines

        main_repr = self.__class__.__name__ + "("
        if lines:
            # simple one-liner info, which most builtin Modules will use
            if len(extra_lines) == 1 and not child_lines:
                main_repr += extra_lines[0]
            else:
                main_repr += "\n  " + "\n  ".join(lines) + "\n"

        main_repr += ")"
        return main_repr

    def _add_indent(self, text: str) -> str:
        lines = text.split("\n")
        # don't do anything for single-line stuff
        if len(lines) == 1:
            return text
        first = lines.pop(0)
        lines = [(self.getattr("indent", 2) * " ") + line for line in lines]
        text = "\n".join(lines)
        text = first + "\n" + text
        return text

    def __getstate__(self, *args, **kwargs):
        return self.__dict__

    def __setstate__(self, states, *args, **kwargs):
        for name, value in states.items():
            self.setattr(name, value)
