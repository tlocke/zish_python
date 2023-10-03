from importlib.metadata import version

from zish.core import ZishException, ZishLocationException, dump, dumps, load, loads

__all__ = ["ZishException", "ZishLocationException", "dump", "dumps", "load", "loads"]

__version__ = version("zish")
