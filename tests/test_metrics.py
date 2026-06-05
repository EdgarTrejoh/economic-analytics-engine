import pandas as pd
import pytest

from app.services.metrics import calculate_cagr, calculate_financial_metrics


def test_calculate_cagr():
    assert calculate_cagr(100, 200, 1) == 1.0
    assert calculate_cagr(100, 121, 2) == pytest.approx(0.1, 0.0001)
    assert calculate_cagr(100, 150, 0) == 0.0


def test_calculate_financial_metrics_does_not_mutate_input_dataframe():
    df = pd.DataFrame(
        {
            "Año": [2016, 2017, 2018],
            "INPC": [100.0, 105.0, 110.25],
            "Salario_Minimo_Diario": [70.0, 77.0, 84.7],
            "UMA_diario": [70.0, 73.5, 77.175],
            "Tasa_Referencia_Banxico": [4.0, 5.0, 6.0],
        }
    )
    original_columns = df.columns.tolist()

    df_calc, cagrs, base_year, start_year, end_year = calculate_financial_metrics(df)

    assert df.columns.tolist() == original_columns
    assert base_year == 2016
    assert start_year == 2016
    assert end_year == 2018
    assert df_calc["Indice_de_Precios"].iloc[2] == pytest.approx(110.25, 0.01)
    assert df_calc["inflacion"].iloc[1] == pytest.approx(5.0, 0.001)
    assert cagrs["nominal_salario"] == pytest.approx(0.10, 0.001)
    assert cagrs["nominal_uma"] == pytest.approx(0.05, 0.001)


@pytest.mark.parametrize(
    "missing_column",
    ["INPC", "Salario_Minimo_Diario", "UMA_diario"],
)
def test_calculate_financial_metrics_missing_required_columns_raises_key_error(missing_column):
    data = {
        "Año": [2016, 2017, 2018],
        "INPC": [100.0, 105.0, 110.25],
        "Salario_Minimo_Diario": [70.0, 77.0, 84.7],
        "UMA_diario": [70.0, 73.5, 77.175],
        "Tasa_Referencia_Banxico": [4.0, 5.0, 6.0],
    }
    data.pop(missing_column)

    with pytest.raises(KeyError, match=missing_column):
        calculate_financial_metrics(pd.DataFrame(data))
