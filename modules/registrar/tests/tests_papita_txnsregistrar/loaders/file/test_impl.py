"""
Unit tests for file loader implementations (CSVFileLoader and ExcelFileLoader).

This module contains comprehensive tests for CSV and Excel file loaders, verifying
data loading functionality, file path handling, error conditions, and resource cleanup.
Tests use mocking to isolate file I/O operations and ensure deterministic behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

from papita_txnsmodel.utils.classutils import FallbackAction
from papita_txnsregistrar.loaders.file.impl import CSVFileLoader, ExcelFileLoader


@pytest.fixture
def sample_csv_content():
    """Provide sample CSV content for testing CSV file loading operations."""
    return "name,age,city\nJohn,30,New York\nJane,25,Los Angeles\n"


@pytest.fixture
def sample_csv_file(sample_csv_content):
    """Provide a temporary CSV file with sample data for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp_file:
        tmp_file.write(sample_csv_content)
        tmp_path = tmp_file.name
    yield Path(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def sample_excel_file():
    """Provide a temporary Excel file with sample data for testing."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        tmp_path = tmp_file.name
    df1 = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    df2 = pd.DataFrame({"col3": [5, 6], "col4": [7, 8]})
    with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Sheet1", index=False)
        df2.to_excel(writer, sheet_name="Sheet2", index=False)
    yield Path(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)


class TestCSVFileLoader:
    """Test suite for CSVFileLoader class functionality."""

    @pytest.mark.parametrize(
        "path_input,error_handler",
        [
            ("/path/to/file.csv", FallbackAction.RAISE),
            (Path("/path/to/file.csv"), FallbackAction.LOG),
        ],
    )
    def test_csv_loader_initialization_with_various_paths(self, path_input, error_handler):
        """Test that CSVFileLoader initializes correctly with string or Path object file paths."""
        # Act
        loader = CSVFileLoader(path=path_input, error_handler=error_handler)

        # Assert
        assert loader.path == path_input
        assert loader.error_handler == error_handler
        assert loader._result.empty

    def test_csv_loader_result_property_returns_dataframe(self):
        """Test that result property returns pandas DataFrame containing loaded CSV data."""
        # Arrange
        loader = CSVFileLoader(path="/path/to/file.csv", error_handler=FallbackAction.RAISE)
        expected_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        loader._result = expected_df

        # Act
        result = loader.result

        # Assert
        assert isinstance(result, pd.DataFrame)
        pd.testing.assert_frame_equal(result, expected_df)

    @patch("pandas.read_csv")
    def test_csv_loader_load_reads_file_successfully(self, mock_read_csv, sample_csv_file):
        """Test that load method successfully reads CSV file and stores result in DataFrame."""
        # Arrange
        expected_df = pd.DataFrame({"name": ["John", "Jane"], "age": [30, 25]})
        mock_read_csv.return_value = expected_df
        loader = CSVFileLoader(path=sample_csv_file, error_handler=FallbackAction.RAISE)

        # Act
        result = loader.load()

        # Assert
        assert result is loader
        mock_read_csv.assert_called_once_with(sample_csv_file, **{})
        pd.testing.assert_frame_equal(loader._result, expected_df)

    @patch("pandas.read_csv")
    def test_csv_loader_load_with_custom_parameters(self, mock_read_csv, sample_csv_file):
        """Test that load method passes custom parameters to pandas read_csv function."""
        # Arrange
        expected_df = pd.DataFrame({"col1": [1, 2]})
        mock_read_csv.return_value = expected_df
        loader = CSVFileLoader(path=sample_csv_file, error_handler=FallbackAction.RAISE)
        custom_params = {"sep": "|", "header": None, "names": ["col1", "col2"]}

        # Act
        loader.load(**custom_params)

        # Assert
        mock_read_csv.assert_called_once_with(sample_csv_file, **custom_params)

    def test_csv_loader_unload_clears_dataframe(self):
        """Test that unload method clears loaded DataFrame and resets to empty DataFrame."""
        # Arrange
        loader = CSVFileLoader(path="/path/to/file.csv", error_handler=FallbackAction.RAISE)
        loader._result = pd.DataFrame({"col1": [1, 2, 3]})

        # Act
        result = loader.unload()

        # Assert
        assert result is loader
        assert loader._result.empty
        assert isinstance(loader._result, pd.DataFrame)

    @patch("pandas.read_csv")
    def test_csv_loader_load_handles_file_not_found_error(self, mock_read_csv):
        """Test that load method propagates FileNotFoundError when CSV file does not exist."""
        # Arrange
        nonexistent_path = Path("/nonexistent/file.csv")
        loader = CSVFileLoader(path=nonexistent_path, error_handler=FallbackAction.RAISE)
        mock_read_csv.side_effect = FileNotFoundError("File not found")

        # Act & Assert
        with pytest.raises(FileNotFoundError, match="File not found"):
            loader.load()

    def test_csv_loader_check_source_inherited_from_file_loader(self, sample_csv_file):
        """Test that CSVFileLoader inherits check_source method from FileLoader base class."""
        # Arrange
        loader = CSVFileLoader(path=sample_csv_file, error_handler=FallbackAction.RAISE)

        # Act
        result = loader.check_source()

        # Assert
        assert result is loader
        assert isinstance(loader.path, Path)


class TestExcelFileLoader:
    """Test suite for ExcelFileLoader class functionality."""

    @pytest.mark.parametrize(
        "sheet_name,expected_sheet,error_handler",
        [(None, None, FallbackAction.RAISE), ("Sheet1", "Sheet1", FallbackAction.LOG)],
    )
    def test_excel_loader_initialization_with_sheet_options(self, sheet_name, expected_sheet, error_handler):
        """Test that ExcelFileLoader initializes correctly with default or specified sheet parameter."""
        # Arrange
        path = "/path/to/file.xlsx"

        # Act
        loader = ExcelFileLoader(path=path, sheet=sheet_name, error_handler=error_handler)

        # Assert
        assert loader.path == path
        assert loader.error_handler == error_handler
        assert loader.sheet == expected_sheet
        if expected_sheet is None:
            assert loader.result == {}

    def test_excel_loader_result_property_returns_dictionary(self):
        """Test that result property returns dictionary mapping sheet names to DataFrames."""
        # Arrange
        loader = ExcelFileLoader(path="/path/to/file.xlsx", error_handler=FallbackAction.RAISE)
        expected_result = {"Sheet1": pd.DataFrame({"col1": [1, 2]})}
        loader._result = expected_result

        # Act
        result = loader.result

        # Assert
        assert isinstance(result, dict)
        assert result == expected_result

    @patch("pandas.ExcelFile")
    @patch("builtins.open", new_callable=mock_open)
    def test_excel_loader_load_reads_all_sheets(self, mock_file_open, mock_excel_file, sample_excel_file):
        """Test that load method reads all sheets from Excel file when no sheet specified."""
        # Arrange
        mock_excel_instance = MagicMock()
        mock_excel_instance.sheet_names = ["Sheet1", "Sheet2"]
        df1 = pd.DataFrame({"col1": [1, 2]})
        df2 = pd.DataFrame({"col3": [5, 6]})
        mock_excel_instance.parse.side_effect = [df1, df2]
        mock_excel_file.return_value = mock_excel_instance
        loader = ExcelFileLoader(path=sample_excel_file, error_handler=FallbackAction.RAISE)

        # Act
        result = loader.load()

        # Assert
        assert result is loader
        assert len(loader.result) == 2
        assert "Sheet1" in loader.result
        assert "Sheet2" in loader.result
        pd.testing.assert_frame_equal(loader.result["Sheet1"], df1)
        pd.testing.assert_frame_equal(loader.result["Sheet2"], df2)
        mock_excel_instance.close.assert_called_once()

    @patch("pandas.ExcelFile")
    @patch("builtins.open", new_callable=mock_open)
    def test_excel_loader_load_reads_specific_sheet(self, mock_file_open, mock_excel_file, sample_excel_file):
        """Test that load method reads only specified sheet when sheet parameter provided."""
        # Arrange
        mock_excel_instance = MagicMock()
        mock_excel_instance.sheet_names = ["Sheet1", "Sheet2"]
        mock_excel_instance.parse.return_value = pd.DataFrame({"col1": [1, 2]})
        mock_excel_file.return_value = mock_excel_instance
        loader = ExcelFileLoader(path=sample_excel_file, sheet="Sheet1", error_handler=FallbackAction.RAISE)

        # Act
        result = loader.load()

        # Assert
        assert result is loader
        assert len(loader.result) == 1
        assert "Sheet1" in loader.result
        mock_excel_instance.parse.assert_called_once_with("Sheet1", **{})

    @patch("pandas.ExcelFile")
    @patch("builtins.open", new_callable=mock_open)
    @pytest.mark.parametrize("sheet_param,expected_sheet", [("sheet", "Sheet2"), ("sheet_name", "Sheet2")])
    def test_excel_loader_load_with_sheet_parameters(
        self, mock_file_open, mock_excel_file, sample_excel_file, sheet_param, expected_sheet
    ):
        """Test that load method accepts sheet or sheet_name parameter via kwargs to override instance sheet."""
        # Arrange
        mock_excel_instance = MagicMock()
        mock_excel_instance.sheet_names = ["Sheet1", "Sheet2"]
        mock_excel_instance.parse.return_value = pd.DataFrame({"col1": [1, 2]})
        mock_excel_file.return_value = mock_excel_instance
        loader = ExcelFileLoader(path=sample_excel_file, error_handler=FallbackAction.RAISE)

        # Act
        loader.load(**{sheet_param: expected_sheet})

        # Assert
        mock_excel_instance.parse.assert_called_once_with(expected_sheet, **{})

    @patch("pandas.ExcelFile")
    @patch("builtins.open", new_callable=mock_open)
    def test_excel_loader_load_passes_kwargs_to_parse(self, mock_file_open, mock_excel_file, sample_excel_file):
        """Test that load method passes additional kwargs to ExcelFile.parse method."""
        # Arrange
        mock_excel_instance = MagicMock()
        mock_excel_instance.sheet_names = ["Sheet1"]
        mock_excel_instance.parse.return_value = pd.DataFrame({"col1": [1, 2]})
        mock_excel_file.return_value = mock_excel_instance
        loader = ExcelFileLoader(path=sample_excel_file, error_handler=FallbackAction.RAISE)
        parse_kwargs = {"header": 0, "skiprows": 1}

        # Act
        loader.load(**parse_kwargs)

        # Assert
        mock_excel_instance.parse.assert_called_once_with("Sheet1", **parse_kwargs)

    @patch("pandas.ExcelFile")
    @patch("builtins.open", new_callable=mock_open)
    def test_excel_loader_load_uses_default_encoding(self, mock_file_open, mock_excel_file, sample_excel_file):
        """Test that load method uses DEFAULT_ENCODING when encoding not specified in kwargs."""
        # Arrange
        mock_excel_instance = MagicMock()
        mock_excel_instance.sheet_names = ["Sheet1"]
        mock_excel_instance.parse.return_value = pd.DataFrame()
        mock_excel_file.return_value = mock_excel_instance
        loader = ExcelFileLoader(path=sample_excel_file, error_handler=FallbackAction.RAISE)

        # Act
        loader.load()

        # Assert
        mock_file_open.assert_called_once_with(sample_excel_file, mode="r", encoding="utf-8")

    def test_excel_loader_unload_clears_result_dictionary(self):
        """Test that unload method clears loaded result dictionary and resets to empty dict."""
        # Arrange
        loader = ExcelFileLoader(path="/path/to/file.xlsx", error_handler=FallbackAction.RAISE)
        loader._result = {"Sheet1": pd.DataFrame({"col1": [1, 2]})}

        # Act
        result = loader.unload()

        # Assert
        assert result is loader
        assert loader.result == {}
