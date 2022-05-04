import sys
from argparse import ArgumentParser

from .config import Config


class ConfigParser(ArgumentParser):
    def parse_config(self, args=None, namespace=None):
        if args is None:
            args = sys.argv[1:]
        for arg in args:
            if arg.startswith('--') and args != '--' and arg not in self._option_string_actions:
                self.add_argument(arg)
        if namespace is None:
            namespace = Config()
        namespace, _ = self.parse_known_args(args, namespace)
        return namespace
    parse_all_args = parse_config
