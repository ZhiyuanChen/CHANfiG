import sys
from argparse import ArgumentParser
from typing import List

from .config import Config


class ConfigParser(ArgumentParser):
    def parse_config(self, args: List[str] = None, config: Config = None, config_name: str = 'config') -> Config:
        if args is None:
            args = sys.argv[1:]
        for arg in args:
            if arg.startswith('--') and args != '--' and arg not in self._option_string_actions:
                self.add_argument(arg)
        if config is None:
            config = Config()
        if (path := getattr(config, config_name, None)) is not None:
            raise ValueError(f"--{config_name} is reserved for auto loading config file, but got {path}")
        config, _ = self.parse_known_args(args, config)
        if (path := getattr(config, config_name, None)) is not None:
            config = config.update(path)
        return config
    parse_all_args = parse_config
