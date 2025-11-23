
import importlib.resources as pkg_resources
import logging
import logging.config
import os
import yaml

from papita_txnsregistrar import LIB_NAME


DEFAULT_LOGGING_CONFIG = pkg_resources.read_text(f"{LIB_NAME}.defaults", "logging.yml")

def setup_logger(name: str, config: os.PathLike | str = DEFAULT_LOGGING_CONFIG, level: int = logging.INFO) -> None:
    with open(config, mode="r", encoding="utf-8") as freader:
        config = yaml.load(freader)
    
    logging.config.dictConfig(config)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.debug("Logger '%s' setup with level '%s'", name, level)
