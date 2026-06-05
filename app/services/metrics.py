import logging


logger = logging.getLogger(__name__)
YEAR_COLUMN = "Año"


def calculate_cagr(start_value, end_value, num_years):
    if num_years == 0:
        return 0.0
    return (end_value / start_value) ** (1 / num_years) - 1


def calculate_financial_metrics(df):
    """Realiza todos los calculos financieros."""
    df = df.copy()
    df["inflacion"] = (df["INPC"] / df["INPC"].shift(1) - 1) * 100
    df["inflacion"] = df["inflacion"].fillna(0)
    df["Indice_de_Precios"] = (df["INPC"] / df["INPC"].iloc[0]) * 100
    df["Salario_Minimo_Real"] = (
        df["Salario_Minimo_Diario"] / df["Indice_de_Precios"]
    ) * 100
    df["UMA_Real"] = (df["UMA_diario"] / df["Indice_de_Precios"]) * 100

    start_year = df[YEAR_COLUMN].min()
    end_year = df[YEAR_COLUMN].max()
    num_years = end_year - start_year

    start_row = df.loc[df[YEAR_COLUMN] == start_year].iloc[0]
    end_row = df.loc[df[YEAR_COLUMN] == end_year].iloc[0]

    nominal_salario_cagr = calculate_cagr(
        start_row["Salario_Minimo_Diario"],
        end_row["Salario_Minimo_Diario"],
        num_years,
    )
    real_salario_cagr = calculate_cagr(
        start_row["Salario_Minimo_Real"],
        end_row["Salario_Minimo_Real"],
        num_years,
    )
    nominal_uma_cagr = calculate_cagr(
        start_row["UMA_diario"],
        end_row["UMA_diario"],
        num_years,
    )
    real_uma_cagr = calculate_cagr(
        start_row["UMA_Real"],
        end_row["UMA_Real"],
        num_years,
    )

    base_year = start_year
    salario_real_base = df.loc[
        df[YEAR_COLUMN] == base_year,
        "Salario_Minimo_Real",
    ].values[0]
    uma_real_base = df.loc[df[YEAR_COLUMN] == base_year, "UMA_Real"].values[0]

    df["Salario_Minimo_Real_Normalizado"] = (
        df["Salario_Minimo_Real"] / salario_real_base
    ) * 100
    df["UMA_Real_Normalizado"] = (df["UMA_Real"] / uma_real_base) * 100

    cagrs = {
        "nominal_salario": nominal_salario_cagr,
        "real_salario": real_salario_cagr,
        "nominal_uma": nominal_uma_cagr,
        "real_uma": real_uma_cagr,
    }

    logger.info("Calculos financieros (Real, UMA, CAGR) ejecutados con exito.")
    return df, cagrs, base_year, start_year, end_year
