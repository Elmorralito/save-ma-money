from argparse import ArgumentParser


def build_parser() -> ArgumentParser:
    parser = ArgumentParser()
    parser.add_argument(
        "-p",
        "--plugin",
        dest="plugin",
        help="Something",
        type=str,
        required=True,
    )
    return parser
