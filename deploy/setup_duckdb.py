"""DuckDB database setup and schema initialization utility.

This module provides functionality to validate DuckDB database URLs, parse file paths
from various URL formats, and set up database schemas. It supports multiple URL
formats including DuckDB-specific protocols (duckdb:// and duckdb:///) and standard
POSIX file paths.

Key Functions:
    validate_duckdb_url: Validates if a string matches a valid DuckDB URL pattern.
    is_in_memory_url: Checks if a URL represents an in-memory database.
    extract_file_path: Extracts file path from DuckDB URL formats.
    parse_db_path: Parses and validates database path, creating directories if needed.
    parse_schema: Validates schema name format.
    setup_schema: Creates a schema in the specified DuckDB database.
    main: Command-line entry point for schema setup operations.
"""

import argparse
import re
import sys
from pathlib import Path

import duckdb

# Regex pattern to validate DuckDB database URLs
# Matches:
# - duckdb:///path/to/file.db or duckdb:///path/to/file.duckdb (3 slashes, absolute or relative path)
# - duckdb:///:memory: (in-memory database with 3 slashes)
# - duckdb://path/to/file.db or duckdb://path/to/file.duckdb (2 slashes, relative path)
# - :memory: (standalone in-memory database)
# - POSIX paths: /absolute/path/to/file.db, ./relative/path.db, ../relative/path.db, or path/to/file.db
DUCKDB_URL_PATTERN = re.compile(
    r"^(?:"
    r"duckdb:///(?::memory:|.+\.(?:db|duckdb))"  # duckdb:/// with :memory: or file path (3 slashes)
    r"|"
    r"duckdb://.+\.(?:db|duckdb)"  # duckdb:// with file path (2 slashes)
    r"|"
    r":memory:"  # standalone in-memory
    r"|"
    r"(?:/|\./|\.\./)?[^:]+\.(?:db|duckdb)"  # POSIX paths (absolute, relative, or plain)
    r")$",
    re.IGNORECASE,
)


def validate_duckdb_url(db_url: str) -> bool:
    """Validate if the provided string is a valid DuckDB database URL.

    Checks if the input string matches any of the supported DuckDB URL formats:
    duckdb:///path, duckdb://path, :memory:, or POSIX file paths ending in .db
    or .duckdb.

    Args:
        db_url: The database URL string to validate. Supports DuckDB protocol
            formats (duckdb:/// and duckdb://), in-memory databases (:memory:),
            and POSIX paths (absolute, relative with ./ or ../, or plain relative).

    Returns:
        True if the URL matches a valid DuckDB URL pattern, False otherwise.
    """
    return bool(DUCKDB_URL_PATTERN.match(db_url.strip()))


def is_in_memory_url(db_url: str) -> bool:
    """Check if the URL represents an in-memory database.

    Determines whether the provided URL string corresponds to an in-memory DuckDB
    database, which does not persist data to disk.

    Args:
        db_url: The database URL string to check. Accepts both standalone
            ':memory:' format and 'duckdb:///:memory:' protocol format.

    Returns:
        True if the URL represents an in-memory database, False otherwise.
    """
    url = db_url.strip()
    return url.lower() == ":memory:" or url.lower() == "duckdb:///:memory:"


def extract_file_path(db_url: str) -> str:
    """Extract the file path from a DuckDB URL.

    Parses various DuckDB URL formats and extracts the underlying file system path.
    Supports duckdb:///path, duckdb://path, and POSIX path formats. In-memory
    database URLs are not supported and will raise an exception.

    Args:
        db_url: The database URL string in any supported format (duckdb:///path,
            duckdb://path, or POSIX paths like /absolute/path.db, ./relative.db,
            ../relative.db, or path/to/file.db).

    Returns:
        The extracted file path as a string, with any URL protocol prefixes
        removed.

    Raises:
        ValueError: If the URL represents an in-memory database or if the URL
            format cannot be parsed to extract a valid file path.
    """
    url = db_url.strip()

    # Check if it's in-memory
    if is_in_memory_url(url):
        raise ValueError("In-memory database URLs are not supported. Please provide a file path.")

    # Extract path from duckdb:///path/to/file.db or duckdb:///path/to/file.duckdb
    match = re.match(r"^duckdb:///(.+)$", url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Extract path from duckdb://path/to/file.db or duckdb://path/to/file.duckdb
    match = re.match(r"^duckdb://(.+)$", url, re.IGNORECASE)
    if match:
        return match.group(1)

    # Extract POSIX paths: /absolute/path.db, ./relative/path.db, ../relative/path.db, or path/to/file.db
    match = re.match(r"^(?:/|\./|\.\./)?[^:]+\.(?:db|duckdb)$", url, re.IGNORECASE)
    if match:
        return url

    raise ValueError(f"Could not extract file path from URL: {db_url}")


def parse_db_path(db_path: str) -> Path:
    """Parse and validate a database path, creating directories if necessary.

    Validates the provided database path, extracts the file path from URL formats,
    and ensures the parent directory exists. If the path points to an existing
    directory, appends 'store.duckdb' as the default database filename.

    Args:
        db_path: The database path or URL string to parse. Must be a valid DuckDB
            URL format as validated by validate_duckdb_url.

    Returns:
        A Path object representing the database file location. If the path
        exists as a file, returns it directly. If it exists as a directory,
        returns a Path to 'store.duckdb' within that directory. Otherwise,
        creates the parent directory structure and returns the file path.

    Raises:
        ValueError: If the database path is not a valid DuckDB URL format or if
            it represents an in-memory database.
    """
    if not validate_duckdb_url(db_path):
        raise ValueError(f"Invalid DuckDB database URL: {db_path}")

    if is_in_memory_url(db_path):
        raise ValueError("In-memory database URLs are not supported. Please provide a file path.")

    file_path = Path(extract_file_path(db_path))
    print(f"Database File path: {file_path}")
    if file_path.exists() and file_path.is_file():
        return file_path

    if file_path.is_dir():
        file_path = file_path.joinpath("store.duckdb")

    print(f"Creating database folder at: {file_path.parent}")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def parse_schema(schema: str):
    """Validate and return a schema name.

    Ensures the schema name contains only alphanumeric characters and underscores,
    which are valid identifiers in SQL databases.

    Args:
        schema: The schema name string to validate. Must contain only letters,
            numbers, and underscores.

    Returns:
        The validated schema name string if it matches the required pattern.

    Raises:
        ValueError: If the schema name contains invalid characters or is empty.
    """
    if re.match(r"^[a-zA-Z0-9_]+$", schema):
        return schema

    raise ValueError(f"Invalid schema: {schema}")


def setup_schema(db_path: Path, schema: str):
    """Create a schema in the specified DuckDB database.

    Connects to the DuckDB database at the given path and creates the specified
    schema if it does not already exist. The operation is committed to the
    database.

    Args:
        db_path: A Path object pointing to the DuckDB database file. The path
            is converted to an absolute POSIX path for the connection.
        schema: The name of the schema to create. Should be a valid SQL
            identifier (alphanumeric and underscores only).

    Note:
        This function uses 'CREATE SCHEMA IF NOT EXISTS', so it is safe to
        call multiple times. The schema will only be created if it doesn't
        already exist.
    """
    uri = db_path.absolute().as_posix()
    print(f"Connecting to database: {uri}")
    with duckdb.connect(uri) as conn:
        print(f"Setting up schema: {schema}")
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        print(f"Schema {schema} setup successfully")
        conn.commit()

    print(f"Schema {schema} setup successfully in {db_path}")


def parse_args():
    """Parse command-line arguments for database setup.

    Creates an argument parser and defines the required command-line arguments
    for setting up a DuckDB database schema.

    Returns:
        An argparse.Namespace object containing the parsed arguments:
            - duckdb_db_path: Path to the DuckDB database (required).
            - schema: Name of the schema to create (required).
    """
    parser = argparse.ArgumentParser(description="Setup DuckDB database")
    parser.add_argument("-p", "-path", "--duckdb-db-path", type=str, required=True, help="Path to the DuckDB database")
    parser.add_argument("-s", "-schema", "--schema", type=str, required=True, help="Schema to setup")
    return parser.parse_args()


def main():
    """Main entry point for the DuckDB schema setup script.

    Parses command-line arguments, validates the database path and schema name,
    and creates the specified schema in the database. Handles errors with
    appropriate exit codes.

    Exit Codes:
        0: Success - Schema was created or already exists.
        1: General error - Unexpected exception occurred.
        2: Validation error - Invalid input (database path or schema name).

    Raises:
        SystemExit: Always exits with code 0 on success, 1 on general errors,
            or 2 on validation errors.
    """
    args = parse_args()
    try:
        db_path = parse_db_path(args.duckdb_db_path)
        schema = parse_schema(args.schema)
        setup_schema(db_path, schema)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
