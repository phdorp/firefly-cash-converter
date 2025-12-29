import logging
import sys
from argparse import ArgumentParser, Namespace

from gnucashConverter import cli


def main():
    """Parse CLI arguments and dispatch the selected subcommand.

    Creates the argument parser, registers subcommands, parses user input, and
    invokes the mapped command handler.

    Raises:
        KeyError: If the provided command does not have a registered handler.
    """
    parser = ArgumentParser("cash")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for defineParser in cli.PARSER_DEFINITIONS:
        defineParser(subparsers)

    arguments: Namespace = parser.parse_args()
    cli.COMMAND_EXECUTION[cli.CommandType(arguments.command)](arguments)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log = logging.getLogger(__name__)
        log.info("Exiting...")
        sys.exit()
    except Exception as e:
        log = logging.getLogger(__name__)
        log.fatal(e)
        raise
