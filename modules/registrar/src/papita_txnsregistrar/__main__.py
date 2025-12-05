import sys
import warnings

from papita_txnsregistrar.utils.main import MainCLIUtils


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
    warnings.warn(
        "Running 'python -m papita_txnsregistrar' is not recommended. "
        "Please use the command 'papita-txnsregistrar' instead.",
        UserWarning,
        stacklevel=2,
    )


def main() -> None:
    """
    The main entry point for the registrar CLI.

    This function initializes and runs the registrar CLI utility. It loads the
    configuration and executes the main workflow.
    """
    MainCLIUtils.load().run()
