"""Public package surface for ``papita_txnsapi``.

Re-exports version metadata, author information, and Poetry-derived configuration
from :mod:`papita_txnsapi.__meta__`. Import :data:`LIB_NAME` when a stable logger or
diagnostic label for the API package is required.
"""

from .__meta__ import __authors__, __configs__, __version__

LIB_NAME = __name__

__all__ = ["__authors__", "__configs__", "__version__", "LIB_NAME"]
