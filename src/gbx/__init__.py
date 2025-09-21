from ._version import __version__

from .core import *

try:
    from . import lzo
except ImportError as e:
    raise ImportError("lzo not compiled. If you are a dev please run `pip install -e .`") from e
