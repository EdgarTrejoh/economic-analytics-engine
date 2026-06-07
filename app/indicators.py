from dataclasses import dataclass


@dataclass(frozen=True)
class IndicatorSpec:
    column: str
    label: str
    aliases: tuple[str, ...] = ()
    required: bool = True
    unit: str = ""
    role: str = "source"


YEAR_COLUMN = "Año"
INPC_COLUMN = "INPC"
MINIMUM_WAGE_COLUMN = "Salario_Minimo_Diario"
UMA_COLUMN = "UMA_diario"
BANXICO_RATE_COLUMN = "Tasa_Referencia_Banxico"

INFLATION_COLUMN = "inflacion"
PRICE_INDEX_COLUMN = "Indice_de_Precios"
REAL_MINIMUM_WAGE_COLUMN = "Salario_Minimo_Real"
REAL_UMA_COLUMN = "UMA_Real"
NORMALIZED_REAL_MINIMUM_WAGE_COLUMN = "Salario_Minimo_Real_Normalizado"
NORMALIZED_REAL_UMA_COLUMN = "UMA_Real_Normalizado"

SOURCE_INDICATORS = (
    IndicatorSpec(
        column=YEAR_COLUMN,
        label="Año",
        aliases=("Ano", "Anio", "Year", "Ejercicio"),
        unit="year",
    ),
    IndicatorSpec(column=INPC_COLUMN, label="INPC", unit="index"),
    IndicatorSpec(
        column=MINIMUM_WAGE_COLUMN,
        label="Salario minimo diario",
        unit="MXN diarios",
    ),
    IndicatorSpec(column=UMA_COLUMN, label="UMA diaria", unit="MXN diarios"),
    IndicatorSpec(
        column=BANXICO_RATE_COLUMN,
        label="Tasa de referencia Banxico",
        unit="%",
    ),
)

DERIVED_INDICATORS = (
    IndicatorSpec(column=INFLATION_COLUMN, label="Inflacion anual", unit="%", role="derived"),
    IndicatorSpec(
        column=PRICE_INDEX_COLUMN,
        label="Indice de precios",
        unit="index",
        role="derived",
    ),
    IndicatorSpec(
        column=REAL_MINIMUM_WAGE_COLUMN,
        label="Salario minimo real",
        unit="MXN reales",
        role="derived",
    ),
    IndicatorSpec(
        column=REAL_UMA_COLUMN,
        label="UMA real",
        unit="MXN reales",
        role="derived",
    ),
    IndicatorSpec(
        column=NORMALIZED_REAL_MINIMUM_WAGE_COLUMN,
        label="Salario real normalizado",
        unit="index",
        role="derived",
    ),
    IndicatorSpec(
        column=NORMALIZED_REAL_UMA_COLUMN,
        label="UMA real normalizada",
        unit="index",
        role="derived",
    ),
)

ALL_INDICATORS = SOURCE_INDICATORS + DERIVED_INDICATORS

COLUMN_ALIASES = {
    alias: indicator.column
    for indicator in SOURCE_INDICATORS
    for alias in (indicator.column, *indicator.aliases)
}

REQUIRED_SOURCE_COLUMNS = tuple(
    indicator.column for indicator in SOURCE_INDICATORS if indicator.required
)


def indicator_by_column(column):
    return {indicator.column: indicator for indicator in ALL_INDICATORS}.get(column)


def require_columns(df, columns=REQUIRED_SOURCE_COLUMNS):
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        raise KeyError(", ".join(missing_columns))
