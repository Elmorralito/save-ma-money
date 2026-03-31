from .__meta__ import __authors__, __version__

LIB_NAME = __name__.split(".", maxsplit=1)[0]
API_VERSION = __version__.replace("v", "").split(".")[0]
AUTHORS = __authors__
