from papita_txnsregistrar.utils.main import MainCLIUtils


def main() -> None:
    """
    The main entry point for the registrar CLI.

    This function initializes and runs the registrar CLI utility. It loads the
    configuration and executes the main workflow.
    """
    MainCLIUtils.load().run()
