from argparse import ArgumentParser


def build_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "-p",
        "--plugin",
        dest="plugin",
        help="Specify the name of the plugin to be used.",
        type=str,
        required=True,
    )
    parser.add_argument(
        "-m",
        "--mod",
        "--module",
        dest="modules",
        help="Specify the module(s) to be used. This can include multiple modules separated by commas.",
        type=str,
        required=False,
        nargs="*",
        default=["papita_txnsregistrar_plugins"],
    )
    return parser
