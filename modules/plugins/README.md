# Papita Transaction Plugins

Welcome to the **Implementation Layer** of the Papita ecosystem. The `papita-txnsplugins` library provides a collection of concrete, production-ready plugins that bridge the gap between various financial data formats and the [papita-txnsmodel](../model/README.md).

These plugins are designed to be used seamlessly with the [papita-txnsregistrar](../registrar/README.md), enabling flexible and automated data ingestion.

## Core Plugins

The library currently ships with two mission-critical plugins that handle universal data formats:

### 1. CSV File Plugin

A robust loader for comma-separated values.

- **Features**: Automatic header detection, type validation via Pydantic, and support for custom delimiters.
- **Usage**: Best for simple, single-table bank exports.
- **CLI Command**:
  ```bash
  papita-txnsregistrar "CSV File Plugin" --path ./my_data.csv --sheet "Transactions"
  ```

### 2. Excel File Plugin

A powerful, multi-sheet ingestion engine.

- **Features**: Processes complex workbooks with multiple sheets in a single pass.
- **Orchestration**: Uses the `ExcelContractBuilder` to dynamically map different sheets to their corresponding handlers (e.g., "Expenses" vs "Income").
- **CLI Command**:
  ```bash
  papita-txnsregistrar "Excel File Loader Plugin" --path ./finances_2024.xlsx
  ```

---

## Architectural Deep Dive: The Excel Builder

One of the most advanced features of this module is the `ExcelContractBuilder`. Unlike simple loaders, this builder:

1.  **Scans the Workbook**: Reads all available sheets.
2.  **Generic Mapping**: Uses the `HandlerFactory` from the model library to find handlers registered with names matching the sheet titles.
3.  **Parallel Assembly**: Constructs a unique service/handler pair for every relevant sheet, allowing for heterogeneous data processing within a single file.

## Bank-Specific Extensions (Roadmap)

The library is pre-structured to support native parsers for specific financial institutions:

- `papita_txnsplugins.bancolombia`: Targeted for Bancolombia PDF/CSV exports.
- `papita_txnsplugins.nu`: Targeted for Nubank data structures.

> [!NOTE]
> These modules currently serve as structural placeholders. Contributions for high-precision parsers are welcome!

---

## Developer Guide: Creating a New Plugin

Extending the system is straightforward. To create a new plugin, follow these steps:

### 1. Define the Plugin Class

Inherit from `PluginContract` and specify your Loader and Builder types.

### 2. Register with Metadata

Use the `@plugin` decorator to make your plugin discoverable by the Registrar.

```python
from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.plugin import PluginContract
from papita_txnsregistrar.loaders.file.impl import CSVFileLoader
from papita_txnsplugins.core.builders import ExcelContractBuilder

@plugin(
    meta={
        "name": "My Custom Provider",
        "version": "1.0.0",
        "feature_tags": ["custom_bank", "high_priority"]
    }
)
class MyCustomPlugin(PluginContract[CSVFileLoader, ExcelContractBuilder]):
    def start(self, **kwargs):
        # Add custom pre-processing logic here
        return super().start(**kwargs)
```

### 3. CLI Support

To enable CLI usage, inherit from `AbstractCLIUtils` and implement `parse_cli_args`.

## Relationship with Other Modules

- **`papita-txnsmodel`**: Provides the data structures (DAOs/DTOs) and business logic (Services).
- **`papita-txnsregistrar`**: Provides the orchestration framework that discovers and executes these plugins.
