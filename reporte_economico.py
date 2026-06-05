import logging

from app.data_sources.google_sheets import get_sheet_csv_url, load_and_clean_data
from app.services.email_sender import send_report_email
from app.services.metrics import calculate_cagr, calculate_financial_metrics
from app.services.pdf_report import PDFReport, create_pdf_report
from app.services.pipeline import execute_economic_pipeline, run_pipeline
from app.services.visualizations import generate_visualizations


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

__all__ = [
    "PDFReport",
    "calculate_cagr",
    "calculate_financial_metrics",
    "create_pdf_report",
    "execute_economic_pipeline",
    "generate_visualizations",
    "get_sheet_csv_url",
    "load_and_clean_data",
    "send_report_email",
    "run_pipeline",
]


if __name__ == "__main__":
    run_pipeline()
