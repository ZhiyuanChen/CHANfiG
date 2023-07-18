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
# - BSD 4-Clause
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the LICENSE file for more details.

# pylint: disable=C0302

from __future__ import annotations

from contextlib import contextmanager
from copy import copy, deepcopy
from io import BytesIO, IOBase, StringIO
from json import dumps as json_dumps
from json import loads as json_loads
from os import PathLike
from os.path import splitext
from typing import Any, Callable, Iterable, Mapping, Sequence
from warnings import warn

from yaml import dump as yaml_dump
from yaml import load as yaml_load

from .utils import _K, _V, JSON, YAML, File, JsonEncoder, Null, PathStr, YamlDumper, YamlLoader
from .variable import Variable

try:
    from torch import device as TorchDevice
    from torch import dtype as TorchDType

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


def to_dict(obj: Any) -> Mapping[str, Any]:  # pylint: disable=R0911
    r"""
    Convert an object to a dict.

    Note that when converting a `set` object, it may be converted to a `tuple` object if its values is not hashable.

    Args:
        obj: Object to be converted.

    Returns:
        A dict.

    Examples:
        >>> to_dict(1)
        1
        >>> to_dict([1, 2, 3])
        [1, 2, 3]
        >>> to_dict((1, 2, 3))
        (1, 2, 3)
        >>> to_dict({1, 2, 3})
        {1, 2, 3}
        >>> to_dict({'a': 1, 'b': 2})
        {'a': 1, 'b': 2}
        >>> to_dict(Variable(1))
        1
        >>> to_dict(FlatDict(a=[[[[[FlatDict(b=1)]]]]]))
        {'a': [[[[[{'b': 1}]]]]]}
        >>> to_dict(FlatDict(a={FlatDict(b=1)}))
        {'a': ({'b': 1},)}
    """

    if isinstance(obj, Mapping):
        return {k: to_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]  # type: ignore
    if isinstance(obj, tuple):
        return tuple(to_dict(v) for v in obj)  # type: ignore
    if isinstance(obj, set):
        try:
            return {to_dict(v) for v in obj}  # type: ignore
        except TypeError:
            return tuple(to_dict(v) for v in obj)  # type: ignore
    if isinstance(obj, Variable):
        return obj.value
    return obj


class FlatDict(dict, Mapping[_K, _V]):  # for python 3.7 compatible
    r"""
    `FlatDict` with attribute-style access.

    `FlatDict` inherits from built-in `dict`.

    It comes with many easy to use helper function, such as `difference`, `intersect`.

    It also has full support for IO operations, such as `json` and `yaml`.

    Even better, `FlatDict` has pytorch support built-in.
    You can directly call `FlatDict.cpu()` or `FlatDict.to("cpu")` to move all `torch.Tensor` objects across devices.

    `FlatDict` works best with `Variable` objects.
    Just simply call ``FlatDict.a = Variable(1); FlatDict.b = FlatDict.a``, and their values will be synced.

    Attributes:
        indent: Indentation level in printing and dumping to json or yaml.

    Notes:
        `FlatDict` rewrite `__getattribute__` and `__getattr__` to supports attribute-style access to its members.
        Therefore, all internal attributes should be set and get through `FlatDict.setattr` and `FlatDict.getattr`.

        Although it is possible to override other internal methods, it is not recommended to do so.

        `__class__`, `__dict__`, and `getattr` are reserved and cannot be overrode in any manner.

    Examples:
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
    """

    # pylint: disable=R0904

    indent: int = 2

    def __getattribute__(self, name: Any) -> Any:
        if name not in ("__class__", "__dict__", "getattr") and name in self:
            return self.get(name)
        return super().__getattribute__(name)

    def get(self, name: Any, default: Any = None) -> Any:
        r"""
        Get value from `FlatDict`.

        Args:
            name:
            default:

        Returns:
            value:
                If `FlatDict` does not contain `name`, return `default`.

        Raises:
            KeyError: If `FlatDict` does not contain `name` and `default` is not specified.

        Examples:
            >>> d = FlatDict(d=1013)
            >>> d.get('d')
            1013
            >>> d['d']
            1013
            >>> d.d
            1013
            >>> d.get('d', None)
            1013
            >>> d.get('f', 2)
            2
            >>> d.get('f')
            >>> d.get('f', Null)
            Traceback (most recent call last):
            KeyError: 'f'
        """

        if name in self:
            return dict.__getitem__(self, name)
        if default is not Null:
            return default
        return self.__missing__(name)

    def __getitem__(self, name: Any) -> Any:
        return self.get(name, default=Null)

    def __getattr__(self, name: Any) -> Any:
        try:
            return self.get(name, default=Null)
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'") from None

    def set(self, name: Any, value: Any) -> None:
        r"""
        Set value of `FlatDict`.

        Args:
            name:
            value:

        Examples:
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
        """

        if name in self and isinstance(self.get(name), Variable):
            self.get(name).set(value)
        else:
            dict.__setitem__(self, name, value)

    def __setitem__(self, name: Any, value: Any) -> None:
        self.set(name, value)

    def __setattr__(self, name: Any, value: Any) -> None:
        self.set(name, value)

    def delete(self, name: Any) -> None:
        r"""
        Delete value from `FlatDict`.

        Args:
            name:

        Examples:
            >>> d = FlatDict(d=1016, n='chang')
            >>> d.d
            1016
            >>> d.n
            'chang'
            >>> d.delete('d')
            >>> d.d
            Traceback (most recent call last):
            AttributeError: 'FlatDict' object has no attribute 'd'
            >>> del d.n
            >>> d.n
            Traceback (most recent call last):
            AttributeError: 'FlatDict' object has no attribute 'n'
            >>> del d.f
            Traceback (most recent call last):
            AttributeError: 'FlatDict' object has no attribute 'f'
        """

        dict.__delitem__(self, name)

    def __delitem__(self, name: Any) -> None:
        return self.delete(name)

    def __delattr__(self, name: Any) -> None:
        try:
            self.delete(name)
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'") from None

    def __missing__(self, name: Any) -> Any:  # pylint: disable=R1710
        raise KeyError(name)

    def validate(self) -> None:
        r"""
        Validate if all `Variable` in `FlatDict` are valid.

        Raises:
            TypeError: If `Variable` has invalid type.
            ValueError: If `Variable` has invalid value.

        Examples:
            >>> d = FlatDict(d=Variable(1016, type=int), n=Variable('chang', validator=lambda x: x.islower()))
            >>> d.validate()
            >>> d = FlatDict(d=Variable(1016, type=str), n=Variable('chang', validator=lambda x: x.islower()))
            >>> d.validate()
            Traceback (most recent call last):
            TypeError: 'd' has invalid type. Value 1016 is not of type <class 'str'>.
            >>> d = FlatDict(d=Variable(1016, type=int), n=Variable('chang', validator=lambda x: x.isupper()))
            >>> d.validate()
            Traceback (most recent call last):
            ValueError: 'n' has invalid value. Value chang is not valid.
        """

        for name, value in self.items():
            if isinstance(value, Variable):
                try:
                    value.validate()
                except TypeError as exc:
                    raise TypeError(f"'{name}' has invalid type. {exc}") from None
                except ValueError as exc:
                    raise ValueError(f"'{name}' has invalid value. {exc}") from None

    def getattr(self, name: str, default: Any = Null) -> Any:
        r"""
        Get attribute of `FlatDict`.

        Note that it won't retrieve value in `FlatDict`,

        Args:
            name:
            default:

        Returns:
            value: If `FlatDict` does not contain `name`, return `default`.

        Raises:
            AttributeError: If `FlatDict` does not contain `name` and `default` is not specified.

        Examples:
            >>> d = FlatDict(a=1)
            >>> d.get('a')
            1
            >>> d.getattr('a')
            Traceback (most recent call last):
            AttributeError: 'FlatDict' object has no attribute 'a'
            >>> d.getattr('b', 2)
            2
            >>> d.setattr('b', 3)
            >>> d.getattr('b')
            3
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
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'") from None

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
        """

        if name in self:
            warn(
                f"{name} already exists in {self.__class__.__name__}.\n"
                f"Users must call `{self.__class__.__name__}.getattr()` to retrieve conflicting attribute value.",
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
            >>> d = FlatDict()
            >>> d.setattr('name', 'chang')
            >>> d.getattr('name')
            'chang'
            >>> d.delattr('name')
            >>> d.getattr('name')
            Traceback (most recent call last):
            AttributeError: 'FlatDict' object has no attribute 'name'
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
            >>> d = FlatDict()
            >>> d.setattr('name', 'chang')
            >>> d.hasattr('name')
            True
            >>> d.delattr('name')
            >>> d.hasattr('name')
            False
        """

        try:
            if name in self.__dict__ or name in self.__class__.__dict__:
                return True
            return super().hasattr(name)  # type: ignore
        except AttributeError:
            return False

    def dict(self, cls: Callable = dict) -> Mapping:
        r"""
        Convert `FlatDict` to other `Mapping`.

        Args:
            cls: Target class to be converted to.

        Returns:
            (Mapping):

        See Also:
            [`to_dict`][chanfig.flat_dict.to_dict]: implementation of `dict` method.

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        return cls(to_dict(self))

    @classmethod
    def from_dict(cls, obj: Mapping | Sequence) -> Any:  # pylint: disable=R0911
        r"""
        Convert `Mapping` or `Sequence` to `FlatDict`.

        Examples:
            >>> FlatDict.from_dict({'a': 1, 'b': 2, 'c': 3})
            FlatDict(
              ('a'): 1
              ('b'): 2
              ('c'): 3
            )
            >>> FlatDict.from_dict([('a', 1), ('b', 2), ('c', 3)])
            FlatDict(
              ('a'): 1
              ('b'): 2
              ('c'): 3
            )
            >>> FlatDict.from_dict([{'a': 1}, {'b': 2}, {'c': 3}])
            [FlatDict(('a'): 1), FlatDict(('b'): 2), FlatDict(('c'): 3)]
        """

        if isinstance(obj, Mapping):
            return cls(obj)
        elif isinstance(obj, Sequence):
            try:
                return cls(obj)
            except ValueError:
                return [cls(json) for json in obj]
        raise TypeError(f"Expected Mapping or Sequence, but got {type(obj)}.")

    def merge(self, *args, overwrite: bool = True, **kwargs) -> FlatDict:
        r"""
        Merge `other` into `FlatDict`.

        Args:
            other:

        Returns:
            self:

        **Alias**:

        + `union`

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
            >>> d.merge(n).dict()
            {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
            >>> l = [('c', 3), ('d', 4)]
            >>> d.merge(l).dict()
            {'a': 1, 'b': 'b', 'c': 3, 'd': 4}
            >>> FlatDict(a=1, b=1, c=1).union(FlatDict(b='b', c='c', d='d')).dict()  # alias
            {'a': 1, 'b': 'b', 'c': 'c', 'd': 'd'}
            >>> d = FlatDict()
            >>> d.merge({1: 1, 2: 2, 3:3}).dict()
            {1: 1, 2: 2, 3: 3}
            >>> d.merge(d.clone()).dict()
            {1: 1, 2: 2, 3: 3}
            >>> d.merge({1:3, 2:1, 3: 2, 4: 4, 5: 5}, overwrite=False).dict()
            {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}
        """

        if not args and not kwargs:
            return self

        if len(args) == 1:
            args = args[0]
            if isinstance(args, (PathLike, str, bytes)):
                args = self.load(args)  # type: ignore
                warn(
                    "merge file is deprecated and maybe removed in a future release. Use `merge_from_file` instead.",
                    PendingDeprecationWarning,
                )
            self._merge(self, args, overwrite=overwrite)
        else:
            self._merge(self, args, overwrite=overwrite)
        self._merge(self, kwargs, overwrite=overwrite)
        return self

    @staticmethod
    def _merge(this: FlatDict, that: Iterable, overwrite: bool = True) -> Mapping:
        if isinstance(that, Mapping):
            that = that.items()
        for key, value in that:
            if key in this and isinstance(this[key], Mapping):
                if isinstance(value, Mapping):
                    FlatDict._merge(this[key], value)
                elif overwrite:
                    if isinstance(value, FlatDict):
                        this.set(key, value)
                    else:
                        this[key] = value
            elif overwrite or key not in this:
                this.set(key, value)
        return this

    def union(self, *args, **kwargs) -> FlatDict:
        r"""
        Alias of [`merge`][chanfig.FlatDict.merge].
        """
        return self.merge(*args, **kwargs)

    def merge_from_file(self, file: File, *args, **kwargs) -> FlatDict:
        r"""
        Merge content of `file` into `FlatDict`.

        Args:
            file (File):
            *args: Passed to [`load`][chanfig.FlatDict.load].
            **kwargs: Passed to [`load`][chanfig.FlatDict.load].

        Returns:
            self:

        Examples:
            >>> d = FlatDict(a=1, b=1)
            >>> d.merge_from_file("example.yaml").dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        return self.merge(self.load(file, *args, **kwargs))

    def intersect(self, other: Mapping | Iterable | PathStr) -> FlatDict:
        r"""
        Intersection of `FlatDict` and `other`.

        Args:
            other (Mapping | Iterable | PathStr):

        Returns:
            (FlatDict):

        **Alias**:

        + `inter`

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
            >>> d.intersect(n).dict()
            {}
            >>> l = [('c', 3), ('d', 4)]
            >>> d.intersect(l).dict()
            {'c': 3}
            >>> d.merge(l).intersect("example.yaml").dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> d.intersect(1)
            Traceback (most recent call last):
            TypeError: `other=1` should be of type Mapping, Iterable or PathStr, but got <class 'int'>.
            >>> d.inter(FlatDict(b='b', c='c', d='d')).dict()  # alias
            {}
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")
        return self.empty_like(
            **{key: value for key, value in other if key in self and self[key] == value}  # type: ignore
        )

    def inter(self, other: Mapping | Iterable | PathStr, *args, **kwargs) -> FlatDict:
        r"""
        Alias of [`intersect`][chanfig.FlatDict.intersect].
        """
        return self.intersect(other, *args, **kwargs)

    def difference(self, other: Mapping | Iterable | PathStr) -> FlatDict:
        r"""
        Difference between `FlatDict` and `other`.

        Args:
            other:

        Returns:
            (FlatDict):

        **Alias**:

        + `diff`

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> n = {'b': 'b', 'c': 'c', 'd': 'd'}
            >>> d.difference(n).dict()
            {'b': 'b', 'c': 'c', 'd': 'd'}
            >>> l = [('c', 3), ('d', 4)]
            >>> d.difference(l).dict()
            {'d': 4}
            >>> d.merge(l).difference("example.yaml").dict()
            {}
            >>> d.difference(1)
            Traceback (most recent call last):
            TypeError: `other=1` should be of type Mapping, Iterable or PathStr, but got <class 'int'>.
            >>> FlatDict(a=1, b=1, c=1).diff(FlatDict(b='b', c='c', d='d')).dict()  # alias
            {'b': 'b', 'c': 'c', 'd': 'd'}
        """

        if isinstance(other, (PathLike, str, bytes)):
            other = self.load(other)
        if isinstance(other, (Mapping,)):
            other = self.empty_like(other).items()
        if not isinstance(other, Iterable):
            raise TypeError(f"`other={other}` should be of type Mapping, Iterable or PathStr, but got {type(other)}.")
        return self.empty_like(
            **{key: value for key, value in other if key not in self or self[key] != value}  # type: ignore
        )

    def diff(self, other: Mapping | Iterable | PathStr, *args, **kwargs) -> FlatDict:
        r"""
        Alias of [`difference`][chanfig.FlatDict.difference].
        """
        return self.difference(other, *args, **kwargs)

    def to(self, cls: str | TorchDevice | TorchDType) -> FlatDict:
        r"""
        Convert values of `FlatDict` to target `cls`.

        Args:
            cls (str | torch.device | torch.dtype):

        Returns:
            self:

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.to(int)
            Traceback (most recent call last):
            TypeError: to() only support torch.dtype and torch.device, but got <class 'int'>.
        """

        # pylint: disable=C0103

        if isinstance(cls, (str, TorchDevice, TorchDType)):
            for k, v in self.items():
                if hasattr(v, "to"):
                    self[k] = v.to(cls)
            return self

        raise TypeError(f"to() only support torch.dtype and torch.device, but got {cls}.")

    def cpu(self) -> FlatDict:  # pylint: disable=C0103
        r"""
        Move all tensors to cpu.

        Returns:
            self:

        Examples:
            >>> import torch
            >>> d = FlatDict(a=torch.tensor(1))
            >>> d.cpu().dict()  # doctest: +SKIP
            {'a': tensor(1, device='cpu')}
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
            >>> import torch
            >>> d = FlatDict(a=torch.tensor(1))
            >>> d.gpu().dict()  # doctest: +SKIP
            {'a': tensor(1, device='cuda:0')}
            >>> d.cuda().dict()  # alias  # doctest: +SKIP
            {'a': tensor(1, device='cuda:0')}
        """

        return self.to(TorchDevice("cuda"))

    def cuda(self) -> FlatDict:
        r"""
        Alias of [`gpu`][chanfig.FlatDict.gpu].
        """
        return self.gpu()

    def tpu(self) -> FlatDict:
        r"""
        Move all tensors to tpu.

        Returns:
            self:

        **Alias**:

        + `xla`

        Examples:
            >>> import torch
            >>> d = FlatDict(a=torch.tensor(1))
            >>> d.tpu().dict()  # doctest: +SKIP
            {'a': tensor(1, device='xla:0')}
            >>> d.xla().dict()  # alias  # doctest: +SKIP
            {'a': tensor(1, device='xla:0')}
        """

        return self.to(TorchDevice("xla"))

    def xla(self) -> FlatDict:
        r"""
        Alias of [`tpu`][chanfig.FlatDict.tpu].
        """
        return self.tpu()

    def copy(self) -> FlatDict:
        r"""
        Create a shallow copy of `FlatDict`.

        Returns:
            (FlatDict):

        Examples:
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
        """

        return copy(self)

    def __deepcopy__(self, memo: Mapping | None = None) -> FlatDict:
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

    def deepcopy(self, memo: Mapping | None = None) -> FlatDict:  # pylint: disable=W0613
        r"""
        Create a deep copy of `FlatDict`.

        Returns:
            (FlatDict):

        **Alias**:

        + `clone`

        Examples:
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
            >>> d == d.clone()  # alias
            True
        """

        return deepcopy(self)

    def clone(self, memo: Mapping | None = None) -> FlatDict:
        r"""
        Alias of [`deepcopy`][chanfig.FlatDict.deepcopy].
        """
        return self.deepcopy(memo=memo)

    def dump(self, file: File, method: str | None = None, *args, **kwargs) -> None:  # pylint: disable=W1113
        r"""
        Dump `FlatDict` to file.

        Raises:
            ValueError: If dump to `IO` and `method` is not specified.
            TypeError: If dump to unsupported extension.

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.dump("example.yaml")
            >>> d.dump("example.conf")
            Traceback (most recent call last):
            TypeError: `file='example.conf'` should be in ('json',) or ('yml', 'yaml'), but got conf.
            >>> with open("test.yaml", "w") as f:
            ...     d.dump(f)
            Traceback (most recent call last):
            ValueError: `method` must be specified when dumping to IO.
        """

        if method is None:
            if isinstance(file, IOBase):
                raise ValueError("`method` must be specified when dumping to IO.")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in YAML:
            return self.yaml(file=file, *args, **kwargs)  # type: ignore
        if extension in JSON:
            return self.json(file=file, *args, **kwargs)  # type: ignore
        raise TypeError(f"`file={file!r}` should be in {JSON} or {YAML}, but got {extension}.")  # type: ignore

    @classmethod
    def load(cls, file: File, method: str | None = None, *args, **kwargs) -> FlatDict:  # pylint: disable=W1113
        """
        Load `FlatDict` from file.

        Args:
            file: File to load from.
            method: File type, should be in `JSON` or `YAML`.

        Returns:
            (FlatDict):

        Raises:
            ValueError: If load from `IO` and `method` is not specified.
            TypeError: If dump to unsupported extension.

        Examples:
            >>> d = FlatDict.load("example.yaml")
            >>> d.dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> d.load("example.conf")
            Traceback (most recent call last):
            TypeError: `file='example.conf'` should be in ('json',) or ('yml', 'yaml'), but got conf.
            >>> with open("test.yaml") as f:
            ...     d.load(f)
            Traceback (most recent call last):
            ValueError: `method` must be specified when loading from IO.
        """

        if method is None:
            if isinstance(file, IOBase):
                raise ValueError("`method` must be specified when loading from IO.")
            method = splitext(file)[-1][1:]  # type: ignore
        extension = method.lower()  # type: ignore
        if extension in JSON:
            return cls.from_json(file, *args, **kwargs)
        if extension in YAML:
            return cls.from_yaml(file, *args, **kwargs)
        raise TypeError(f"`file={file!r}` should be in {JSON} or {YAML}, but got {extension}.")

    def json(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump `FlatDict` to json file.

        This function calls `self.jsons()` to generate json string.
        You may overwrite `jsons` in case something is not json serializable.

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.json("example.json")
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
            >>> d = FlatDict.from_json('example.json')
            >>> d.dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            if isinstance(fp, (StringIO, BytesIO)):
                return cls.from_jsons(fp.getvalue(), *args, **kwargs)  # type: ignore
            return cls.from_jsons(fp.read(), *args, **kwargs)

    def jsons(self, *args, **kwargs) -> str:
        r"""
        Dump `FlatDict` to json string.

        Returns:
            (str):

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.jsons()
            '{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}'
        """

        kwargs.setdefault("cls", JsonEncoder)
        kwargs.setdefault("indent", self.getattr("indent", 2))
        return json_dumps(self.dict(), *args, **kwargs)

    @classmethod
    def from_jsons(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from json string.

        Returns:
            (FlatDict):

        Examples:
            >>> FlatDict.from_jsons('{\n  "a": 1,\n  "b": 2,\n  "c": 3\n}').dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> FlatDict.from_jsons('[["a", 1], ["b", 2], ["c", 3]]').dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> FlatDict.from_jsons('[{"a": 1}, {"b": 2}, {"c": 3}]')
            [FlatDict(('a'): 1), FlatDict(('b'): 2), FlatDict(('c'): 3)]
        """

        return cls.from_dict(json_loads(string, *args, **kwargs))

    def yaml(self, file: File, *args, **kwargs) -> None:
        r"""
        Dump `FlatDict` to yaml file.

        This function calls `self.yamls()` to generate yaml string.
        You may overwrite `yamls` in case something is not yaml serializable.

        Examples:
            >>> d = FlatDict(a=1, b=2, c=3)
            >>> d.yaml("example.yaml")
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

        Examples:
            >>> FlatDict.from_yaml('example.yaml').dict()
            {'a': 1, 'b': 2, 'c': 3}
        """

        with cls.open(file) as fp:  # pylint: disable=C0103
            if isinstance(fp, (StringIO, BytesIO)):
                return cls.from_yamls(fp.getvalue(), *args, **kwargs)  # type: ignore
            return cls.from_yamls(fp.read(), *args, **kwargs)

    def yamls(self, *args, **kwargs) -> str:
        r"""
        Dump `FlatDict` to yaml string.

        Returns:
            (str):

        Examples:
            >>> FlatDict(a=1, b=2, c=3).yamls()
            'a: 1\nb: 2\nc: 3\n'
        """

        kwargs.setdefault("Dumper", YamlDumper)
        kwargs.setdefault("indent", self.getattr("indent", 2))
        return yaml_dump(self.dict(), *args, **kwargs)  # type: ignore

    @classmethod
    def from_yamls(cls, string: str, *args, **kwargs) -> FlatDict:
        r"""
        Construct `FlatDict` from yaml string.

        Returns:
            (FlatDict):

        Examples:
            >>> FlatDict.from_yamls('a: 1\nb: 2\nc: 3\n').dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> FlatDict.from_yamls('- - a\n  - 1\n- - b\n  - 2\n- - c\n  - 3\n').dict()
            {'a': 1, 'b': 2, 'c': 3}
            >>> FlatDict.from_yamls('- a: 1\n- b: 2\n- c: 3\n')
            [FlatDict(('a'): 1), FlatDict(('b'): 2), FlatDict(('c'): 3)]
        """

        kwargs.setdefault("Loader", YamlLoader)
        return cls.from_dict(yaml_load(string, *args, **kwargs))

    @staticmethod
    @contextmanager
    def open(file: File, *args, **kwargs):
        r"""
        Open file IO from file path or IO.

        This methods extends the ability of built-in `open` by allowing it to accept an `IOBase` object.

        Args:
            file: File path or IO.
            *args: Additional arguments passed to `open`.
                Defaults to ().
            **kwargs: Any
                Additional keyword arguments passed to `open`.
                Defaults to {}.

        Yields:
            (FileIO):

        Examples:
            >>> with FlatDict.open("example.yaml") as fp:
            ...     print(fp.read())
            a: 1
            b: 2
            c: 3
            <BLANKLINE>
            >>> io = open("example.yaml")
            >>> with FlatDict.open(io) as fp:
            ...     print(fp.read())
            a: 1
            b: 2
            c: 3
            <BLANKLINE>
            >>> with FlatDict.open(123, mode="w") as fp:
            ...     print(fp.read())
            Traceback (most recent call last):
            TypeError: 'file=123' should be of type (str, os.PathLike) or (io.IOBase), but got <class 'int'>.
        """

        if isinstance(file, (PathLike, str)):
            file = open(file, *args, **kwargs)  # pylint: disable=W1514 # noqa: SIM115
            try:
                yield file
            finally:
                file.close()  # type: ignore
        elif isinstance(file, (IOBase,)):
            yield file
        else:
            raise TypeError(
                f"'file={file!r}' should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}."
            )

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
            >>> d = FlatDict(a=[])
            >>> c = d.empty()
            >>> c.dict()
            {}
        """

        empty = cls.__new__(cls)
        empty.merge(*args, **kwargs)  # pylint: disable=W0212
        return empty

    def empty_like(self, *args, **kwargs) -> FlatDict:
        r"""
        Initialise an empty copy of `FlatDict`.

        This method will preserve everything in `FlatDict.__class__.__dict__` and `FlatDict.__dict__`.

        Returns:
            (FlatDict):

        Examples:
            >>> d = FlatDict(a=[])
            >>> d.setattr("name", "Chang")
            >>> c = d.empty_like()
            >>> c.dict()
            {}
            >>> c.getattr("name")
            'Chang'
        """

        empty = self.empty(*args, **kwargs)
        empty.__dict__.update(self.__dict__)
        return empty

    def dropnull(self) -> FlatDict:
        r"""
        Drop key-value pairs with `Null` value.

        Returns:
            (FlatDict):

        **Alias**:

        + `dropna`

        Examples:
            >>> d = FlatDict(a=Null, b=Null, c=3)
            >>> d.dict()
            {'a': Null, 'b': Null, 'c': 3}
            >>> d.dropnull().dict()
            {'c': 3}
            >>> d.dropna().dict()  # alias
            {'c': 3}
        """

        return self.empty_like({k: v for k, v in self.items() if v is not Null})

    def dropna(self) -> FlatDict:
        r"""
        Alias of [`dropnull`][chanfig.FlatDict.dropnull].
        """
        return self.dropnull()

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
            child_lines.append(f"({key_repr}): {value_repr}")
            # child_lines.append(f"{key_repr}: {value_repr}")
        lines = extra_lines + child_lines

        main_repr = self.__class__.__name__ + "("
        if lines:
            # simple one-liner info, which most builtin Modules will use
            if len(extra_lines) == 1 and not child_lines:
                main_repr += extra_lines[0]
            elif len(child_lines) == 1 and not extra_lines and len(child_lines[0]) < 10:
                main_repr += child_lines[0]
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

    def __hash__(self):
        return hash(frozenset(self.items()))

    def __getstate__(self, *args, **kwargs):
        return self.__dict__

    def __setstate__(self, states, *args, **kwargs):
        for name, value in states.items():
            self.setattr(name, value)

    def __wrapped__(self, *args, **kwargs):
        pass

    def _ipython_display_(self):
        return repr(self)

    def _ipython_canary_method_should_not_exist_(self):
        return None

    def aihwerij235234ljsdnp34ksodfipwoe234234jlskjdf(self):
        return None

    def __rich__(self):
        return self.__repr__()
