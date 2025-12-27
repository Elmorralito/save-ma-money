"""
Main entry point for the papita-txnsregistrar CLI.

This module provides the command-line interface entry point for the registrar
package. It handles script initialization, configuration loading, and CLI execution,
including warnings when run as a module.
"""

import contextlib
import logging
import sys
import warnings

from papita_txnsregistrar import LIB_NAME, __configs__
from papita_txnsregistrar.utils.cli.main import MainCLIUtils

logger = logging.getLogger(LIB_NAME)


def _is_running_as_module() -> bool:
    """
    Check if the script is being run as a module (python -m papita_txnsregistrar)
    instead of as a command (papita-txnsregistrar).

    Returns:
        True if running as module, False otherwise.
    """
    argv0 = sys.argv[0]
    if len(sys.argv) > 1 and sys.argv[1] == "-m":
        return True
    if "__main__.py" in argv0:
        return True
    if "papita-txnsregistrar" not in argv0:
        if argv0.endswith(".py") or ("papita_txnsregistrar" in argv0 and "__main__" in argv0):
            return True

    return False


if _is_running_as_module():
    command = next(iter(__configs__.get("tool", {}).get("poetry", {}).get("scripts", {})), "papita-txnsregistrar")
    warnings.warn(
        "Running 'python -m papita_txnsregistrar' is not recommended. " f"Please use the command '{command}' instead.",
        UserWarning,
        stacklevel=2,
    )


def main() -> None:
    """
    The main entry point for the registrar CLI.

    This function initializes and runs the registrar CLI utility. It loads the
    configuration and executes the main workflow.
    """
    cli_utils = None
    try:
        logger.debug("Loading CLI utilities...")
        cli_utils = MainCLIUtils.load()
        logger.debug("CLI utilities loaded successfully.")
    except Exception as err:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Error loading CLI utilities: %s", err)
        else:
            logger.error("Error loading CLI utilities: %s", err)

        logger.error("Please check the configuration and try again.")
        sys.exit(1)

    try:
        logger.debug("Running CLI utilities...")
        cli_utils.run()
        logger.debug("CLI utilities completed successfully.")
    except Exception as err:
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Error running CLI utilities: %s", err)
        else:
            logger.error("Error running CLI utilities: %s", err)

        logger.error("Please check the configuration and try again.")
        sys.exit(1)
    finally:
        if cli_utils is not None:
            with contextlib.suppress(Exception):
                cli_utils.stop()
