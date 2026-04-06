"""Market asset dictionaries: YAML models and singleton loading.

This module defines validated shapes for grouped trading symbols (pairs, codes, precision,
icons, sources) and a ``MarketAssetsLoader`` that reads YAML from the filesystem or from
packaged resources under ``papita_txnsmodel.configs.dictionaries``. The loader is a
singleton (via ``MetaSingleton``) so configuration is parsed once and reused for lookups.

Key types:
    Symbol: One tradable instrument entry.
    MarketGroup: Named group containing one or more ``Symbol`` rows.
    MarketAssets: Root document with one or more ``MarketGroup`` instances.
    MarketAssetsLoader: Load, merge, and resolve symbols by keyword or enum value.
"""

import importlib.resources as pkg_resources
from enum import Enum
from pathlib import Path
from typing import Annotated, List, Self

import yaml
from pydantic import BaseModel, Field

from papita_txnsmodel.utils.classutils import MetaSingleton
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING
from papita_txnsmodel.utils.modelutils import URLStr


class Symbol(BaseModel):
    """Single market symbol entry from YAML configuration.

    Attributes:
        base: Base asset identifier (e.g. currency or commodity code).
        quote: Quote asset identifier for the pair.
        description: Human-readable description of the instrument.
        symbol: Short display symbol for the pair.
        code: Internal or canonical short code for the instrument.
        precision: Decimal places supported for amounts (0-18).
        icon: URL of an icon image for the instrument.
        source: URL of the data or definition source.
    """

    base: Annotated[str, Field(min_length=1, max_length=10)]
    quote: Annotated[str, Field(min_length=1, max_length=10)]
    description: Annotated[str, Field(min_length=1, max_length=255)]
    symbol: Annotated[str, Field(min_length=1, max_length=10)]
    code: Annotated[str, Field(min_length=1, max_length=10)]
    precision: Annotated[int, Field(ge=0, le=18)]
    icon: URLStr
    source: URLStr

    def __str__(self) -> str:
        return self.symbol


class MarketGroup(BaseModel):
    """A named collection of ``Symbol`` rows (e.g. one exchange or asset class).

    Attributes:
        name: Group name.
        description: Group description.
        items: Non-empty list of symbols belonging to this group.
    """

    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(min_length=1, max_length=255)]
    items: Annotated[List[Symbol], Field(min_items=1)]

    def __str__(self) -> str:
        return f"{self.name} [{len(self.items)} assets]: {self.description}"


class MarketAssets(BaseModel):
    """Root document for market configuration: one or more ``MarketGroup`` instances.

    Attributes:
        groups: Non-empty list of groups; each group holds ``Symbol`` items.
    """

    groups: Annotated[List[MarketGroup], Field(min_items=1)]

    def __str__(self) -> str:
        return "\n".join(str(group) for group in self.groups)


class MarketAssetsLoader(metaclass=MetaSingleton):
    """Singleton loader for ``MarketAssets`` from YAML files or package resources.

    After ``load()``, ``market_assets`` holds the merged model. Use ``get_symbol`` to
    resolve a symbol by string or enum value.

    Attributes:
        market_assets: Parsed and merged assets after ``load()``; ``None`` until loaded.
        file_path: Optional explicit path to a YAML file, directory of ``*.yml`` files, or
            ``None`` to use packaged dictionaries.
        encoding: Text encoding used when reading files (defaults to project default).
    """

    def __init__(self, file_path: str | Path | None = None, encoding: str = DEFAULT_ENCODING):
        self.market_assets: MarketAssets | None = None
        self.file_path: str | Path | None = file_path
        self.encoding: str = encoding

    @property
    def symbols(self) -> List[str]:
        """Return every ``Symbol`` instance across all groups (flattened order).

        Returns:
            Each ``Symbol`` from every group in nested iteration order.

        Raises:
            AttributeError: If ``market_assets`` has not been set (call ``load()`` first).

        Note:
            The return annotation is ``List[str]`` but the implementation returns
            ``Symbol`` instances; use ``str(symbol)`` for the short symbol string.
        """
        return [symbol for group in self.market_assets.groups for symbol in group.items]

    def get_symbol(self, keyword: str | Enum) -> Symbol:
        """Resolve a symbol using a string or an enum whose value is the lookup key.

        Comparison is case-insensitive against ``internal_code``, ``external_code``, and
        ``symbol`` on each ``Symbol``.

        Args:
            keyword: Search string, or an ``Enum`` member (``keyword.value`` is used).

        Returns:
            The first ``Symbol`` that matches the keyword.

        Raises:
            ValueError: If no matching symbol exists.
            AttributeError: If ``Symbol`` rows lack ``internal_code`` or ``external_code``
                attributes expected by this method.
            AttributeError: If ``market_assets`` is unset.
        """
        if isinstance(keyword, Enum):
            return self.get_symbol(keyword.value)

        for group in self.market_assets.groups:
            for item in group.items:
                if (
                    item.internal_code == keyword.lower()
                    or item.external_code == keyword.lower()
                    or item.symbol == keyword.lower()
                ):
                    return item

        raise ValueError(f"Keyword matching '{keyword}' not found")

    def load_file(self, file_path: str, encoding: str = DEFAULT_ENCODING) -> MarketAssets:
        """Parse one YAML file into a ``MarketAssets`` model.

        Expects a mapping with a ``groups`` key holding a list of group objects compatible
        with ``MarketGroup``.

        Args:
            file_path: Path to the YAML file (string accepted by ``open``).
            encoding: File text encoding.

        Returns:
            Validated ``MarketAssets`` instance.

        Raises:
            ValueError: If the document is not a mapping, or ``groups`` is missing or not a
                list, or group rows fail validation.
            OSError: If the file cannot be read.
            yaml.YAMLError: If the file is not valid YAML.
        """
        with open(file_path, "r", encoding=encoding) as file:
            raw_data = yaml.safe_load(file)

        if not isinstance(raw_data, dict):
            raise ValueError("Invalid market assets data")

        groups = raw_data.get("groups", [])
        if not isinstance(groups, list):
            raise ValueError("Invalid market assets data")

        return MarketAssets(groups=[MarketGroup.model_validate(group) for group in groups])

    def load_dictionaries(
        self, file_path: str | Path | None = None, encoding: str = DEFAULT_ENCODING
    ) -> List[MarketAssets]:
        """Load from a file path, directory of YAML files, or packaged defaults.

        If ``file_path`` is ``None``, uses ``importlib.resources`` for
        ``papita_txnsmodel.configs.dictionaries``. If it is a file, loads that file. If it
        is a directory, loads each ``*.yml`` file and returns the aggregate as a list of
        ``MarketAssets`` (one per file).

        Args:
            file_path: ``Path``, path string, or ``None`` for package resources.
            encoding: Encoding for file reads.

        Returns:
            A single ``MarketAssets`` when loading one file; a list of ``MarketAssets`` when
            loading from a directory.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
            ValueError: If the path is neither a file nor a directory.

        Note:
            Return type varies by input shape; callers merging results should normalize to
            ``List[MarketAssets]`` before ``build_market_assets``.
        """
        match file_path:
            case Path():
                files = file_path
            case str():
                files = Path(file_path)
            case _:
                files = pkg_resources.files("papita_txnsmodel.configs.dictionaries").as_posix()
                files = Path(files)

        if not files.exists():
            raise FileNotFoundError(f"Given path or package {files} does not exist")

        if files.is_file():
            return [self.load_file(files.as_posix(), encoding=encoding)]

        if files.is_dir():
            return [
                self.load_dictionaries(file_path.as_posix(), encoding=encoding) for file_path in files.glob("*.yml")
            ]

        raise ValueError(f"Given path or package {files} is not a valid file or directory")

    def build_market_assets(self, market_assets: List[MarketAssets]) -> MarketAssets:
        """Merge multiple ``MarketAssets`` documents into one by concatenating all groups.

        Args:
            market_assets: One or more loaded documents.

        Returns:
            A new ``MarketAssets`` whose ``groups`` list is the concatenation of every input
            document’s groups in order.
        """
        return MarketAssets(groups=[group for market_asset in market_assets for group in market_asset.groups])

    def load(self) -> Self:
        """Load using ``file_path`` and ``encoding``, then set ``market_assets``.

        Delegates to ``load_dictionaries`` and ``build_market_assets``.

        Returns:
            ``self`` for chaining.

        Raises:
            Propagates exceptions from ``load_dictionaries`` or ``build_market_assets`` when
            inputs are not compatible (e.g. type mismatch between a single document and a
            list).

        Note:
            Ensure ``load_dictionaries`` returns a ``List[MarketAssets]`` when calling
            ``build_market_assets``, or normalize the result first.
        """
        markets = self.load_dictionaries(self.file_path, encoding=self.encoding)
        self.market_assets = self.build_market_assets(markets)
        return self
