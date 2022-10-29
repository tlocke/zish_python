from zish.core import ZishException, ZishLocationException, dump, dumps, load, loads

__all__ = ["ZishException", "ZishLocationException", "dump", "dumps", "load", "loads"]

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version

__version__ = version("zish")
