from argparse import Namespace
from ast import literal_eval
from collections import OrderedDict
from json import dump, dumps
from os import PathLike
from typing import Any


class Config(Namespace):
    """
    Basic Config
    """

    delimiter: str = '.'

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

    def __contains__(self, name: str) -> bool:
        return hasattr(self, name)

    def __eq__(self, other) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self.dict() == other.dict()

    def dict(self) -> OrderedDict:
        dict = OrderedDict()
        for k, v in self.__dict__.items():
            if isinstance(v, Config):
                dict[k] = v.dict()
            else:
                dict[k] = v
        return dict

    def dump(self, fp):
        if isinstance(fp, (str, bytes, PathLike)):
            fp = open(fp)
        dump(self.dict(), fp)
        fp.close()

    def dumps(self) -> str:
        return dumps(self.dict())
