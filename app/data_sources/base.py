from typing import Protocol

import pandas as pd


class DataSource(Protocol):
    def load_indicators(
        self,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> pd.DataFrame:
        ...
