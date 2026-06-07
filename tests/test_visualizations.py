import matplotlib.axes
import pandas as pd

from app.schema import YEAR_COLUMN
from app.services.visualizations import generate_visualizations


def test_generate_visualizations_excludes_base_year_from_inflation_plots(monkeypatch, tmp_path):
    df = pd.DataFrame(
        {
            YEAR_COLUMN: [2016, 2017, 2018],
            "Salario_Minimo_Real": [70.0, 73.3, 76.8],
            "UMA_Real": [70.0, 70.0, 70.0],
            "Salario_Minimo_Diario": [70.0, 77.0, 84.7],
            "UMA_diario": [70.0, 73.5, 77.175],
            "Salario_Minimo_Real_Normalizado": [100.0, 104.7, 109.8],
            "UMA_Real_Normalizado": [100.0, 100.0, 100.0],
            "inflacion": [0.0, 5.0, 5.0],
            "Tasa_Referencia_Banxico": [4.0, 5.0, 6.0],
        }
    )
    cagrs = {
        "nominal_salario": 0.1,
        "real_salario": 0.047,
        "nominal_uma": 0.05,
        "real_uma": 0.0,
    }

    plotted_years = []
    original_plot = matplotlib.axes.Axes.plot

    def capture_inflation_plot(self, x, y, *args, **kwargs):
        label = kwargs.get("label")
        if label in {"Inflacion Anual (%)", "Tasa de Referencia Banxico (%)"}:
            plotted_years.append(list(x))
        return original_plot(self, x, y, *args, **kwargs)

    monkeypatch.setattr(matplotlib.axes.Axes, "plot", capture_inflation_plot)

    original_columns = df.columns.tolist()
    generate_visualizations(df, cagrs, 2016, 2016, 2018, tmp_path)

    assert df.columns.tolist() == original_columns
    assert plotted_years
    assert all(years == [2017, 2018] for years in plotted_years)
