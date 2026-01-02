# Papita Transactions Registrar

Welcome to the **Orchestration Layer** of the Papita financial ecosystem. The `papita-txnsregistrar` library is a sophisticated, plugin-based framework designed to manage the high-fidelity ingestion of financial transaction data from a vast array of sources.

It provides the necessary infrastructure to discover, load, and execute data pipelines that transform heterogeneous "raw signals" (CSVs, Excel files, API responses) into the structured entities defined in the [papita-txnsmodel](../model/README.md).

![](../../docs/registrar_architecture_placeholder.png)

## Overview

In a complex financial environment, data is never uniform. The Registrar solves this by implementing a **Strict Contract Pattern**, ensuring that regardless of where the data comes from, it arrives at the database with 100% integrity.

### Key Mission

- **Extensibility**: Add support for new banks or platforms in minutes by implementing a simple Plugin.
- **Dynamic Discovery**: Automatically find and register new capabilities without changing the core codebase.
- **Unified Interface**: Provide a single, consistent CLI and API for all data ingestion tasks.

## The Contract Pattern

The Registrar's power lies in its tripartite architectural pattern. Every ingestion flow is governed by a **Contract** that binds three specialized components:

### 1. The Plugin (`PluginContract`)

The entry point. It defines the "Identity" of the ingestion logic.

- **Metadata**: Name, version, and capability tags (e.g., `csv`, `bank-a`, `credit-card`).
- **Lifecycle Management**: Handles the `init()`, `start()`, and `stop()` phases of the ingestion process.

### 2. The Loader (`AbstractDataLoader`)

The "Input" specialist. It knows how to reach out to a source and bring data into memory.

- Supports **File Loaders** (CSV, Excel) and **Memory Loaders**.
- Implements `check_source()` to fail fast if data is missing or corrupt.

### 3. The Builder (`AbstractContractBuilder`)

The "Architect". It manages the dependency injection and assembly of the entire pipeline.

- Orchestrates the creation of the **Service** and **Handler** (from the Model library) needed to process the loader's output.

---

## Core Components

### Registry & Discovery

The `Registry` is a singleton "Phonebook" of all available capabilities.

- **ClassDiscovery**: Uses advanced Python introspection to find every `PluginContract` in your environment.
- **Fuzzy Matching**: Allows you to load plugins using human-readable tags rather than rigid class names.
- **Metadata Validation**: Every plugin is strictly validated against a `PluginMetadata` schema using Pydantic.

### CLI Integration

The Registrar isn't just a library; it's a powerful command-line utility.

- **Automated Parameter Mapping**: Plugins can define their own CLI arguments, which are automatically parsed and injected.
- **Unified Entry Point**: Run any ingestion task via a single command: `papita-txnsregistrar -p "Bank A CSV" --path ./data/exports.csv`.

## Integration with `papita-txnsmodel`

The Registrar acts as the bridge between the outside world and the Model library:

1.  **Registrar** identifies the correct **Plugin**.
2.  **Plugin** uses a **Loader** to get raw data.
3.  **Registrar** uses a **Builder** to instantiate the relevant **Service** and **Handler** from `papita-txnsmodel`.
4.  Data is passed through the **Handler** for transformation.
5.  **Service** performs the final ACID-compliant upsert into the database.

---

## Usage Examples

### 1. Dynamic Plugin Retrieval

```python
from papita_txnsregistrar.contracts.loader import load_plugin

# Dynamically find the best plugin for a task
plugin_cls = load_plugin(
    plugin_name="csv",
    modules=["papita_txnsplugins.core"]
)

# Initialize and run
plugin = plugin_cls(path="transfers.csv").init(connector=my_db_connector)
plugin.start()
```

### 2. Implementing a Custom Plugin

```python
from papita_txnsregistrar.contracts.loader import plugin
from papita_txnsregistrar.contracts.plugin import PluginContract
from my_module.loaders import MyCustomLoader
from my_module.builders import MyCustomBuilder

@plugin(meta={"name": "My Custom Bank", "version": "1.0.0"})
class MyBankPlugin(PluginContract[MyCustomLoader, MyCustomBuilder]):
    def start(self, **kwargs):
        # Specific orchestration logic...
        return super().start(**kwargs)
```

## Getting Started

To begin using the registrar, ensure you have your backend database configured via the `papita-txnsmodel` and explore the available plugins in the `modules/plugins` directory.
