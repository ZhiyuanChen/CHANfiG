from .nested_dict import NestedDict
from .utils import PathStr


def load(file: PathStr, *args, **kwargs) -> NestedDict:
    r"""
    Load a file into a `NestedDict`.

    This function simply calls `NestedDict.load`.

    Args:
        file: The file to load.
        *args: The arguments to pass to `NestedDict.load`.
        **kwargs: The keyword arguments to pass to `NestedDict.load`.

    See Also:
        [`chanfig.NestedDict.load`][chanfig.NestedDict.load]

    Examples:
        >>> from chanfig import load
        >>> config = load("example.yaml")
        >>> config
        NestedDict(
          ('a'): 1
          ('b'): 2
          ('c'): 3
        )
    """

    return NestedDict.load(file, *args, **kwargs)  # type: ignore
