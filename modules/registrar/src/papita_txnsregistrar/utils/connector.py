import argparse
import sys
from typing import Self, Type

from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsregistrar.utils.cli import AbstractCLIUtils


class BaseCLIConnectorWrapper(AbstractCLIUtils):
    """
    A wrapper model for SQLDatabaseConnector to facilitate CLI integration.

    This model encapsulates a SQLDatabaseConnector instance, allowing it to be
    easily constructed and managed via command-line interfaces. It serves as
    a bridge between CLI utilities and the database connection logic.

    Attributes:
        connector (SQLDatabaseConnector): The database connector instance.
    """

    connector: Type[SQLDatabaseConnector]

    @classmethod
    def load(cls, **kwargs) -> Self:
        """
        Load the connector wrapper using Pydantic's model construction.

        This method constructs an instance of CLIConnectorWrapper by validating
        and parsing the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments required for constructing the connector.

        Returns:
            Self: An instance of CLIConnectorWrapper.
        """
        raise NotImplementedError("This method should be implemented in subclasses.")


class CLIURLConnectoryWrapper(BaseCLIConnectorWrapper):
    """
    A CLI wrapper for SQLDatabaseConnector that connects using a database URL.

    This wrapper allows users to specify a database connection via a URL
    string when using command-line interfaces. It constructs the underlying
    SQLDatabaseConnector based on the provided URL.

    Attributes:
        url (str): The database connection URL.
    """

    @classmethod
    def load(cls, **kwargs) -> Self:
        """
        Load the connector wrapper using the provided database URL.

        This method constructs an instance of CLIURLConnectorWrapper by
        creating a SQLDatabaseConnector with the specified URL.

        Args:
            **kwargs: Keyword arguments containing 'url' for the database connection.

        Returns:
            Self: An instance of CLIURLConnectorWrapper.
        """
        parser = argparse.ArgumentParser(cls.__doc__)
        parser.add_argument(
            "--connect-url",
            dest="connect_url",
            help="The database connection URL.",
            type=str,
            required=True,
        )
        parsed_args, _ = parser.parse_known_args(args=kwargs.pop("args") or sys.argv)

        return cls.model_validate(
            {"connector": SQLDatabaseConnector.establish(connection=getattr(parsed_args, "connect_url")), **kwargs}
        )
