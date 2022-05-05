from __future__ import annotations

from argparse import Namespace
from ast import literal_eval
from collections import OrderedDict
from contextlib import contextmanager
from json import dump as json_dump
from json import dumps as json_dumps
from json import load as json_load
from os import PathLike as _PathLike
from typing import IO, Any, Callable, Iterable, MutableMapping, Union

from yaml import SafeDumper, SafeLoader
from yaml import dump as yaml_dump
from yaml import load as yaml_load

PathLike = Union[str, _PathLike]
File = Union[PathLike, IO]

YAML_EXTENSIONS = ('.yml', '.yaml')
JSON_EXTENSIONS = ('.json')
PYTHON_EXTENSIONS = ('.py')


class Dumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


class FileExtensionError(ValueError):
    pass


class Config(Namespace):
    """
    Basic Config
    """

    delimiter: str = '.'
    indent: int = 2

    def __setattr__(self, name: str, value: Any) -> None:
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            if not hasattr(self, name):
                setattr(self, name, type(self)())
            setattr(getattr(self, name), rest, value)
        elif isinstance(value, dict):
            setattr(self, name, type(self)(**value))
        else:
            if isinstance(value, str):
                try:
                    value = literal_eval(value)
                except (ValueError, SyntaxError):
                    pass
            super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        if self.delimiter in name:
            name, rest = name.split(self.delimiter, 1)
            return getattr(self[name], rest)
        else:
            return super().__getattribute__(name)

    __setitem__ = __setattr__
    __getitem__ = __getattr__

    def __len__(self) -> int:
        return len(self.__dict__)

    def __iter__(self, prefix=''):
        for key, value in self.__dict__.items():
            if prefix:
                key = prefix + self.delimiter + key
            if isinstance(value, Config):
                yield from value.__iter__(key)
            else:
                yield key

    def __contains__(self, name: str) -> bool:
        return hasattr(self, name)

    def __eq__(self, other: Config) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.dict() == other.dict()

    def __str__(self) -> str:
        return self.yamls()

    def dict(self, cls: Callable = OrderedDict) -> MutableMapping:
        dict = cls()
        for k, v in self.__dict__.items():
            if isinstance(v, Config):
                dict[k] = v.dict(cls)
            else:
                dict[k] = v
        return dict

    def json(self, file: File, *args, **kwargs):
        if 'indent' not in kwargs:
            kwargs['indent'] = self.indent
        with self.open(file, mode='w') as fp:
            json_dump(self.dict(), fp, *args, **kwargs)

    def jsons(self, *args, **kwargs):
        if 'indent' not in kwargs:
            kwargs['indent'] = self.indent
        return json_dumps(self.dict(), *args, **kwargs)

    def yaml(self, file: File, *args, **kwargs):
        with self.open(file, mode='w') as fp:
            self.yamls(fp, *args, **kwargs)

    def yamls(self, *args, **kwargs):
        if 'Dumper' not in kwargs:
            kwargs['Dumper'] = Dumper
        if 'indent' not in kwargs:
            kwargs['indent'] = self.indent
        return yaml_dump(self.dict(dict), *args, **kwargs)

    def merge(self, other: Union[Config, dict, str], reverse: bool = False):
        if isinstance(other, dict):
            other = type(self)(**other)
        elif isinstance(other, str):
            other = self.read(other)
        if reverse:
            self, other = other, self
        for key, value in other.items():
            self[key] = value
        return self

    def items(self, prefix: str = ''):
        for key, value in self.__dict__.items():
            if prefix:
                key = prefix + self.delimiter + key
            if isinstance(value, Config):
                yield from value.items(key)
            else:
                yield key, value

    keys = __iter__

    def values(self):
        for value in self.__dict__.values():
            if isinstance(value, Config):
                yield from value.values()
            else:
                yield value

    @classmethod
    def read(cls, path: str, **kwargs) -> Config:
        path = path.lower()
        with cls.open(path) as fp:
            if path.endswith(JSON_EXTENSIONS):
                config = cls(**json_load(fp, **kwargs))
            elif path.endswith(YAML_EXTENSIONS):
                config = cls.load(fp.read(), **kwargs)
            else:
                raise FileExtensionError(f"path {path} should have extensions {JSON_EXTENSIONS} or {YAML_EXTENSIONS}")
        return config

    @classmethod
    def load(cls, yaml: str, **kwargs) -> Config:
        if 'Loader' not in kwargs:
            kwargs['Loader'] = SafeLoader
        return cls(**yaml_load(yaml, **kwargs))

    @staticmethod
    @contextmanager
    def open(file: File, *args, **kwargs):
        if isinstance(file, (str, _PathLike )):
            file = open(file, *args, **kwargs)
            try:
                yield file
            finally:
                file.close()
        elif isinstance(file, (IO, )):
            yield file
        else:
            raise ValueError(f"file {file} should be of type (str, os.PathLike) or (io.IOBase), but got {type(file)}")
