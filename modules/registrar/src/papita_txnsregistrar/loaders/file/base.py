import os
from pathlib import Path
from typing import Iterable, Self

import pandas as pd

from papita_txnsregistrar.loaders.abstract import AbstractLoader


class FileBaseLoader(AbstractLoader):

    path: str | Path

    @property
    def result(self) -> pd.DataFrame | Iterable:
        return pd.DataFrame([])

    def check_source(self, **kwargs) -> Self:
        path = Path(self.path) if isinstance(self.path, str) else self.path
        if not (path.is_file() and path.exists() and os.access(path.as_posix(), os.R_OK)):
            raise OSError("The path does not correspond to a file or does not exist.")

        self.path = path
        return self

    def load(self, **kwargs) -> Self:
        return self
