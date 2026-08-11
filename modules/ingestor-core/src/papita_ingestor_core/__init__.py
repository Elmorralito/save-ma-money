"""papita-ingestor-core — source-agnostic ingestion contracts (scaffold).

Business rules stay in ``papita_txnsmodel``. Concrete sources (email, bank-api)
live in plugin packages under ``modules/ingestors/`` and must not be imported
here.
"""

from __future__ import annotations

from papita_ingestor_core.__meta__ import __version__

__all__ = ["__version__"]
