"""Package metadata loaded from Poetry configuration.

Reads ``pyproject.toml`` adjacent to the API module via
:func:`papita_txnsmodel.__meta__.get_poetry_configs` and exposes version, author,
and dependency metadata for runtime introspection and logging.
"""

from papita_txnsmodel.__meta__ import get_poetry_configs

__configs__ = get_poetry_configs(module_path=__file__)

__authors__ = __configs__.get("authors", {})

__version__ = __configs__.get("version", "0.0.1").replace("v", "")
