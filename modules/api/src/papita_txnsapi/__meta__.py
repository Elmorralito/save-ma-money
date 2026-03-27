from papita_txnsmodel.__meta__ import get_poetry_configs

__configs__ = get_poetry_configs(module_path=__file__)

__authors__ = __configs__.get("authors", {})

__version__ = __configs__.get("version", "0.0.1").replace("v", "")
