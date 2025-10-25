"""
File Loader Implementation Module.

This module provides concrete implementations of file loaders for specific file formats:
- CSVFileLoader: For loading data from CSV (Comma-Separated Values) files
- ExcelFileLoader: For loading data from Excel spreadsheet files

These loaders extend the FileLoader base class and implement the file-specific
loading logic while maintaining a consistent interface for data access through the
result property.
"""

from typing import Self

import pandas as pd
from pydantic import Field

from papita_txnsregistrar.loaders.abstract import AbstractLoader

from .abstract import FileLoader


class CSVFileLoader(FileLoader, AbstractLoader):
    """
    Loader for CSV (Comma-Separated Values) files.

    This loader provides functionality to read data from CSV files into pandas DataFrames.
    It implements the FileLoader interface and specializes in handling CSV format
    using pandas' read_csv functionality.

    Attributes:
        _result: Internal storage for the loaded DataFrame.

    Examples:
        ```python
        loader = CSVFileLoader(path="data.csv")
        df = loader.load().result

        # With custom CSV parameters
        loader = CSVFileLoader(path="data.csv")
        df = loader.load(sep="|", header=None).result
        ```
    """

    _result: pd.DataFrame = pd.DataFrame([])

    @property
    def result(self) -> pd.DataFrame:
        """
        Get the loaded CSV data.

        Returns:
            pd.DataFrame: The data loaded from the CSV file as a pandas DataFrame.
        """
        return self._result

    def load(self, **kwargs) -> Self:
        """
        Load data from the CSV file.

        This method reads the CSV file at the specified path into a pandas DataFrame.
        All keyword arguments are passed directly to pandas' read_csv function,
        allowing for customization of how the CSV is parsed.

        Args:
            **kwargs: Keyword arguments passed to pandas.read_csv(), such as:
                        - sep: Delimiter to use (default ',')
                        - header: Row number to use as column names
                        - names: List of column names
                        - dtype: Data types for columns
                        - encoding: File encoding

        Returns:
            Self: The loader instance for method chaining.
        """
        self._result = pd.read_csv(self.path, **kwargs)
        return self

    def unload(self, **kwargs) -> Self:
        del self._result
        self._result = pd.DataFrame([])
        return self


class ExcelFileLoader(FileLoader, AbstractLoader):
    """
    Loader for Excel spreadsheet files.

    This loader provides functionality to read data from Excel files (.xls, .xlsx)
    into pandas DataFrames. It implements the FileLoader interface and
    specializes in handling Excel formats using pandas' ExcelFile functionality.

    Unlike the CSVFileLoader which returns a single DataFrame, this loader returns
    a dictionary mapping sheet names to their respective DataFrames.

    Attributes:
        _result: Dictionary mapping sheet names to pandas DataFrames.

    Examples:
        ```python
        # Load all sheets
        loader = ExcelFileLoader(path="data.xlsx")
        sheets_dict = loader.load().result

        # Load a specific sheet
        loader = ExcelFileLoader(path="data.xlsx")
        sheets_dict = loader.load(sheet="Sheet1").result
        ```
    """

    _result: dict[str, pd.DataFrame] = Field(default_factory=dict)

    @property
    def result(self) -> dict[str, pd.DataFrame]:
        """
        Get the loaded Excel data.

        Returns:
            dict[str, pd.DataFrame]: Dictionary mapping sheet names to pandas DataFrames.
        """
        return self._result

    def load(self, **kwargs) -> Self:
        """
        Load data from the Excel file.

        This method reads the Excel file at the specified path, creating a dictionary
        that maps sheet names to pandas DataFrames. By default, it loads all sheets,
        but can be configured to load only a specific sheet.

        Args:
            **kwargs: Keyword arguments to customize loading behavior, including:
                        - sheet: Specific sheet name to load
                        - sheet_name: Alternative parameter name for sheet
                        Additional arguments are passed to pandas.read_excel()

        Returns:
            Self: The loader instance for method chaining.
        """
        sheet = kwargs.get("sheet", kwargs.get("sheet_name"))
        with open(self.path, mode="r", encoding=kwargs.get("encoding", "utf-8")) as freader:
            excel_file = pd.ExcelFile(freader)
            sheets = excel_file.sheet_names
            if sheet and sheet in sheets:
                sheets = [sheet]

            self.result = {sheet_: excel_file.parse(sheet_, **kwargs) for sheet_ in sheets}
            excel_file.close()

        return self

    def unload(self, **kwargs) -> Self:
        del self._result
        self._result = {}.copy()
        return self
