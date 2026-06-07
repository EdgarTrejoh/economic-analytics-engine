from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.data_sources.google_sheets import (
    GoogleSheetsConnectionError,
    get_sheet_csv_url,
    load_and_clean_data,
)
from app.schema import YEAR_COLUMN


@pytest.mark.parametrize(
    ("sheet_url", "expected_csv_url"),
    [
        (
            "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing",
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv",
        ),
        (
            "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing#gid=987",
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=987",
        ),
    ],
)
def test_get_sheet_csv_url(sheet_url, expected_csv_url):
    assert get_sheet_csv_url(sheet_url) == expected_csv_url


def test_get_sheet_csv_url_invalid_url_raises_value_error():
    with pytest.raises(ValueError, match="URL de Google Sheets"):
        get_sheet_csv_url("https://example.com/not-a-google-sheet")


def test_load_and_clean_data_converts_types_and_drops_rows_without_year(monkeypatch):
    raw_df = pd.DataFrame(
        {
            "Año": ["2016", None, "2018"],
            "INPC": ["100.0", "105.0", "110.25"],
            "Salario_Minimo_Diario": ["70.0", "77.0", "84.7"],
            "UMA_diario": ["70.0", "73.5", "77.175"],
            "Tasa_Referencia_Banxico": ["4.0", "5.0", "6.0"],
        }
    )
    read_csv = MagicMock(return_value=raw_df)
    monkeypatch.setattr("app.data_sources.google_sheets.pd.read_csv", read_csv)

    cleaned_df = load_and_clean_data("https://docs.google.com/sheet.csv")

    read_csv.assert_called_once_with(
        "https://docs.google.com/sheet.csv",
        skipinitialspace=True,
    )
    assert len(cleaned_df) == 2
    assert cleaned_df[YEAR_COLUMN].tolist() == [2016, 2018]
    assert str(cleaned_df[YEAR_COLUMN].dtype) == "Int64"
    assert cleaned_df["INPC"].dtype == "float64"


def test_load_and_clean_data_preserves_extra_numeric_indicators(monkeypatch):
    raw_df = pd.DataFrame(
        {
            "Año": ["2016", "2018"],
            "INPC": ["100.0", "110.25"],
            "Salario_Minimo_Diario": ["70.0", "84.7"],
            "UMA_diario": ["70.0", "77.175"],
            "Tasa_Referencia_Banxico": ["4.0", "6.0"],
            "Nuevo_Indicador": ["1.5", "2.5"],
        }
    )
    monkeypatch.setattr(
        "app.data_sources.google_sheets.pd.read_csv",
        MagicMock(return_value=raw_df),
    )

    cleaned_df = load_and_clean_data("https://docs.google.com/sheet.csv")

    assert "Nuevo_Indicador" in cleaned_df.columns
    assert cleaned_df["Nuevo_Indicador"].tolist() == [1.5, 2.5]


@pytest.mark.parametrize("year_alias", ["Ano", "Anio", "Year", "Ejercicio"])
def test_load_and_clean_data_normalizes_year_column_aliases(monkeypatch, year_alias):
    raw_df = pd.DataFrame(
        {
            year_alias: ["2016", "2018"],
            "INPC": ["100.0", "110.25"],
            "Salario_Minimo_Diario": ["70.0", "84.7"],
            "UMA_diario": ["70.0", "77.175"],
            "Tasa_Referencia_Banxico": ["4.0", "6.0"],
        }
    )
    monkeypatch.setattr(
        "app.data_sources.google_sheets.pd.read_csv",
        MagicMock(return_value=raw_df),
    )

    cleaned_df = load_and_clean_data("https://docs.google.com/sheet.csv")

    assert YEAR_COLUMN in cleaned_df.columns
    assert year_alias not in cleaned_df.columns
    assert cleaned_df[YEAR_COLUMN].tolist() == [2016, 2018]


def test_load_and_clean_data_read_csv_error_is_raised(monkeypatch):
    original_error = ConnectionError("network unavailable")
    monkeypatch.setattr(
        "app.data_sources.google_sheets.pd.read_csv",
        MagicMock(side_effect=original_error),
    )

    with pytest.raises(GoogleSheetsConnectionError, match="No se pudo conectar a Google Sheets") as exc_info:
        load_and_clean_data("https://docs.google.com/sheet.csv")

    assert exc_info.value.__cause__ is original_error
