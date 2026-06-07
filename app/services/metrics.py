import logging

from app.indicators import (
    INFLATION_COLUMN,
    INPC_COLUMN,
    MINIMUM_WAGE_COLUMN,
    NORMALIZED_REAL_MINIMUM_WAGE_COLUMN,
    NORMALIZED_REAL_UMA_COLUMN,
    PRICE_INDEX_COLUMN,
    REAL_MINIMUM_WAGE_COLUMN,
    REAL_UMA_COLUMN,
    UMA_COLUMN,
    YEAR_COLUMN,
    require_columns,
)


logger = logging.getLogger(__name__)


def calculate_cagr(start_value, end_value, num_years):
    if num_years == 0:
        return 0.0
    return (end_value / start_value) ** (1 / num_years) - 1


def calculate_financial_metrics(df):
    """Realiza todos los calculos financieros."""
    require_columns(df)
    df = df.copy()
    df[INFLATION_COLUMN] = (df[INPC_COLUMN] / df[INPC_COLUMN].shift(1) - 1) * 100
    df[INFLATION_COLUMN] = df[INFLATION_COLUMN].fillna(0)
    df[PRICE_INDEX_COLUMN] = (df[INPC_COLUMN] / df[INPC_COLUMN].iloc[0]) * 100
    df[REAL_MINIMUM_WAGE_COLUMN] = (
        df[MINIMUM_WAGE_COLUMN] / df[PRICE_INDEX_COLUMN]
    ) * 100
    df[REAL_UMA_COLUMN] = (df[UMA_COLUMN] / df[PRICE_INDEX_COLUMN]) * 100

    start_year = df[YEAR_COLUMN].min()
    end_year = df[YEAR_COLUMN].max()
    num_years = end_year - start_year

    start_row = df.loc[df[YEAR_COLUMN] == start_year].iloc[0]
    end_row = df.loc[df[YEAR_COLUMN] == end_year].iloc[0]

    nominal_salario_cagr = calculate_cagr(
        start_row[MINIMUM_WAGE_COLUMN],
        end_row[MINIMUM_WAGE_COLUMN],
        num_years,
    )
    real_salario_cagr = calculate_cagr(
        start_row[REAL_MINIMUM_WAGE_COLUMN],
        end_row[REAL_MINIMUM_WAGE_COLUMN],
        num_years,
    )
    nominal_uma_cagr = calculate_cagr(
        start_row[UMA_COLUMN],
        end_row[UMA_COLUMN],
        num_years,
    )
    real_uma_cagr = calculate_cagr(
        start_row[REAL_UMA_COLUMN],
        end_row[REAL_UMA_COLUMN],
        num_years,
    )

    base_year = start_year
    salario_real_base = df.loc[
        df[YEAR_COLUMN] == base_year,
        REAL_MINIMUM_WAGE_COLUMN,
    ].values[0]
    uma_real_base = df.loc[df[YEAR_COLUMN] == base_year, REAL_UMA_COLUMN].values[0]

    df[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN] = (
        df[REAL_MINIMUM_WAGE_COLUMN] / salario_real_base
    ) * 100
    df[NORMALIZED_REAL_UMA_COLUMN] = (df[REAL_UMA_COLUMN] / uma_real_base) * 100

    cagrs = {
        "nominal_salario": nominal_salario_cagr,
        "real_salario": real_salario_cagr,
        "nominal_uma": nominal_uma_cagr,
        "real_uma": real_uma_cagr,
    }

    logger.info("Calculos financieros (Real, UMA, CAGR) ejecutados con exito.")
    return df, cagrs, base_year, start_year, end_year
