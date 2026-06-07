import pandas as pd
import pytest

from app.indicators import (
    COLUMN_ALIASES,
    REQUIRED_SOURCE_COLUMNS,
    SOURCE_INDICATORS,
    YEAR_COLUMN,
    indicator_by_column,
    require_columns,
)


def test_indicator_catalog_defines_required_source_columns_and_aliases():
    assert YEAR_COLUMN in REQUIRED_SOURCE_COLUMNS
    assert COLUMN_ALIASES["Ano"] == YEAR_COLUMN
    assert COLUMN_ALIASES["Anio"] == YEAR_COLUMN
    assert COLUMN_ALIASES["Year"] == YEAR_COLUMN
    assert COLUMN_ALIASES["Ejercicio"] == YEAR_COLUMN
    assert len(REQUIRED_SOURCE_COLUMNS) == len(SOURCE_INDICATORS)


def test_indicator_by_column_returns_metadata():
    indicator = indicator_by_column(YEAR_COLUMN)

    assert indicator is not None
    assert indicator.column == YEAR_COLUMN
    assert indicator.required is True


def test_require_columns_raises_key_error_with_missing_columns():
    df = pd.DataFrame({YEAR_COLUMN: [2024]})

    with pytest.raises(KeyError, match="INPC"):
        require_columns(df)
