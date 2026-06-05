import logging
import tempfile

from app.config import load_settings
from app.data_sources.google_sheets import get_sheet_csv_url, load_and_clean_data
from app.services.ai_insights import generate_report_insights
from app.services.email_sender import send_report_email
from app.services.metrics import calculate_financial_metrics
from app.services.pdf_report import create_pdf_report
from app.services.visualizations import generate_visualizations


logger = logging.getLogger(__name__)


def run_pipeline(settings=None):
    """Ejecucion central del pipeline."""
    if settings is None:
        settings = load_settings()

    try:
        url_csv_export = get_sheet_csv_url(settings.sheet_url)
        df_raw = load_and_clean_data(url_csv_export)
        df_calc, cagrs, base_year, start_year, end_year = calculate_financial_metrics(df_raw)
        insights = generate_report_insights(df_calc, cagrs, base_year, start_year, end_year, settings)

        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = generate_visualizations(
                df_calc,
                cagrs,
                base_year,
                start_year,
                end_year,
                temp_dir,
            )
            create_pdf_report(
                df_calc,
                cagrs,
                base_year,
                start_year,
                end_year,
                image_paths,
                settings.report_file_name,
                insights,
            )

            if settings.app_password:
                send_report_email(
                    settings.sender_email,
                    settings.app_password,
                    settings.recipient_email,
                    settings.report_file_name,
                )
            else:
                logger.info(
                    "No se proporciono contraseña. El correo no fue enviado, "
                    "pero el reporte se conservo localmente."
                )
    except Exception as e:
        logger.error(f"El pipeline fallo en la ejecucion: {e}")


def execute_economic_pipeline(settings=None):
    """Alias de compatibilidad con la version previa del script."""
    return run_pipeline(settings)
