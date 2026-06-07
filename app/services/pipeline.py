import logging
import tempfile
from datetime import datetime

from app.config import load_settings
from app.data_sources.google_sheets import GoogleSheetsDataSource
from app.models import ReportResult, report_request_from_settings
from app.services.ai_insights import generate_report_insights
from app.services.email_sender import send_report_email
from app.services.metrics import calculate_financial_metrics
from app.services.pdf_report import create_pdf_report
from app.services.visualizations import generate_visualizations


logger = logging.getLogger(__name__)


def run_pipeline(settings=None, request=None, data_source=None):
    """Ejecucion central del pipeline."""
    if settings is None:
        settings = load_settings()
    if request is None:
        request = report_request_from_settings(settings)
    if data_source is None:
        data_source = GoogleSheetsDataSource(settings.sheet_url)

    try:
        df_raw = data_source.load_indicators(request.start_year, request.end_year)
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
                request.report_file_name,
                insights,
                request.nota_metodologica,
            )

            email_sent = False
            if settings.app_password:
                send_report_email(
                    settings.sender_email,
                    settings.app_password,
                    request.recipient_email,
                    request.report_file_name,
                )
                email_sent = True
            else:
                logger.info(
                    "No se proporciono password. El correo no fue enviado, "
                    "pero el reporte se conservo localmente."
                )

            return ReportResult(
                report_file_path=request.report_file_name,
                email_sent=email_sent,
                generated_at=datetime.now(),
                status="completed",
                start_year=int(start_year),
                end_year=int(end_year),
            )
    except Exception:
        logger.exception("El pipeline fallo en la ejecucion")
        raise


def execute_economic_pipeline(settings=None):
    """Alias de compatibilidad con la version previa del script."""
    return run_pipeline(settings)
