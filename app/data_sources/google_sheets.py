import logging
from urllib.parse import parse_qs, urlparse

import pandas as pd


logger = logging.getLogger(__name__)
YEAR_COLUMN = "Año"


def get_sheet_csv_url(sheet_url):
    """Extrae el Document ID y el GID de una URL de Google Sheets y arma la URL CSV."""
    try:
        doc_id = sheet_url.split("/d/")[1].split("/edit")[0]
        parsed_url = urlparse(sheet_url)
        fragment_dict = parse_qs(parsed_url.fragment)
        gid = fragment_dict.get("gid", ["0"])[0]

        if gid == "0":
            return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
        return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
    except Exception as e:
        logger.error(f"Error al procesar la URL de Google Sheets: {e}")
        raise ValueError("URL de Google Sheets inválida.")


def load_and_clean_data(url_csv_export):
    """Descarga el CSV y limpia los formatos."""
    try:
        df = pd.read_csv(url_csv_export, skipinitialspace=True)
        logger.info("Datos cargados correctamente desde Google Sheets.")
    except Exception as e:
        logger.error(f"Fallo en la conexión a Google Sheets. Error: {e}")
        raise

    try:
        df[YEAR_COLUMN] = pd.to_numeric(df[YEAR_COLUMN], errors="coerce").astype("Int64")
        cols_to_float = [col for col in df.columns if col != YEAR_COLUMN]
        df[cols_to_float] = df[cols_to_float].astype(float)
        df = df.dropna(subset=[YEAR_COLUMN])
        logger.info("Tipos de datos convertidos a flotante y entero.")
        return df
    except Exception as e:
        logger.error(f"Error al convertir tipos de datos: {e}")
        raise
