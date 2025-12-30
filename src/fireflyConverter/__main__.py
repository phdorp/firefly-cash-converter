import logging
import sys
from argparse import ArgumentParser, Namespace

from fireflyConverter import cli

# Configure logging for the package
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


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
    log = logging.getLogger(__name__)

    try:
        main()
    except KeyboardInterrupt:
        log.info("Exiting...")
        sys.exit(130)
    except Exception as e:
        log.fatal(e)
        raise
