import importlib.resources as importlib_resources
import logging
import logging.config
import os

import yaml

from papita_txnsmodel import LIB_NAME

DEFAULT_ENCODING = "utf-8"
LOGGER_NAME = LIB_NAME
DEFAULT_LOGGER_CONFIG_PATH = importlib_resources.files(f"{LIB_NAME}.configs").joinpath("logger.yaml").as_poxis()


def configure_logger(
    logger_name: str, config: os.PathLike | str = DEFAULT_LOGGER_CONFIG_PATH, level: int = logging.INFO
) -> None:
    with open(config, mode="r", encoding=DEFAULT_ENCODING) as freader:
        logger_config = yaml.load(freader, Loader=yaml.SafeLoader)
        logging.config.dictConfig(logger_config)

    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.debug("Logger '%s' setup with level '%s' from config '%s'", logger_name, level, logger_config)
