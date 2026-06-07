from dataclasses import replace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.config import Settings
from app.data_sources.google_sheets import GoogleSheetsConnectionError
from app.schema import YEAR_COLUMN
from app.services import pipeline


def _settings(app_password="", nota_metodologica=None):
    return Settings(
        sheet_url="https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing",
        sender_email="sender@gmail.com",
        recipient_email="recipient@example.com",
        app_password=app_password,
        report_file_name="reporte.pdf",
        nota_metodologica=nota_metodologica,
    )


def test_run_pipeline_orchestrates_report_without_email(monkeypatch):
    raw_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    calc_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    metrics_result = (calc_df, {"nominal_salario": 0.1}, 2016, 2016, 2016)

    get_url = MagicMock(return_value="csv-url")
    load_data = MagicMock(return_value=raw_df)
    calc_metrics = MagicMock(return_value=metrics_result)
    generate_images = MagicMock(return_value=["p1", "p2", "p3", "p4", "p5"])
    generate_insights = MagicMock(return_value=["insight-1", "insight-2", "insight-3", "insight-4", "insight-5"])
    create_pdf = MagicMock()
    send_email = MagicMock()

    monkeypatch.setattr(pipeline, "get_sheet_csv_url", get_url)
    monkeypatch.setattr(pipeline, "load_and_clean_data", load_data)
    monkeypatch.setattr(pipeline, "calculate_financial_metrics", calc_metrics)
    monkeypatch.setattr(pipeline, "generate_report_insights", generate_insights)
    monkeypatch.setattr(pipeline, "generate_visualizations", generate_images)
    monkeypatch.setattr(pipeline, "create_pdf_report", create_pdf)
    monkeypatch.setattr(pipeline, "send_report_email", send_email)

    settings = _settings(app_password="", nota_metodologica="Nota desde settings.")
    pipeline.run_pipeline(settings)

    get_url.assert_called_once_with(_settings().sheet_url)
    load_data.assert_called_once_with("csv-url")
    calc_metrics.assert_called_once_with(raw_df)
    generate_insights.assert_called_once_with(calc_df, metrics_result[1], 2016, 2016, 2016, settings)
    generate_images.assert_called_once()
    create_pdf.assert_called_once()
    assert create_pdf.call_args.args[-2] == ["insight-1", "insight-2", "insight-3", "insight-4", "insight-5"]
    assert create_pdf.call_args.args[-1] == "Nota desde settings."
    send_email.assert_not_called()


def test_run_pipeline_sends_email_when_password_is_present(monkeypatch):
    settings = _settings(app_password="abcdefghijklmnop")
    raw_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    metrics_result = (raw_df, {"nominal_salario": 0.1}, 2016, 2016, 2016)

    monkeypatch.setattr(pipeline, "get_sheet_csv_url", MagicMock(return_value="csv-url"))
    monkeypatch.setattr(pipeline, "load_and_clean_data", MagicMock(return_value=raw_df))
    monkeypatch.setattr(pipeline, "calculate_financial_metrics", MagicMock(return_value=metrics_result))
    monkeypatch.setattr(pipeline, "generate_report_insights", MagicMock(return_value=["i1", "i2", "i3", "i4", "i5"]))
    monkeypatch.setattr(pipeline, "generate_visualizations", MagicMock(return_value=["p1", "p2", "p3", "p4", "p5"]))
    monkeypatch.setattr(pipeline, "create_pdf_report", MagicMock())
    send_email = MagicMock()
    monkeypatch.setattr(pipeline, "send_report_email", send_email)

    pipeline.run_pipeline(settings)

    send_email.assert_called_once_with(
        settings.sender_email,
        settings.app_password,
        settings.recipient_email,
        settings.report_file_name,
    )


def test_run_pipeline_logs_and_reraises_failures(monkeypatch, caplog):
    get_url = MagicMock(return_value="csv-url")
    load_data = MagicMock(side_effect=GoogleSheetsConnectionError("No se pudo conectar a Google Sheets."))

    monkeypatch.setattr(pipeline, "get_sheet_csv_url", get_url)
    monkeypatch.setattr(pipeline, "load_and_clean_data", load_data)

    with pytest.raises(GoogleSheetsConnectionError, match="No se pudo conectar a Google Sheets"):
        pipeline.run_pipeline(_settings(app_password=""))

    get_url.assert_called_once_with(_settings().sheet_url)
    load_data.assert_called_once_with("csv-url")
    assert "El pipeline fallo en la ejecucion" in caplog.text


def test_execute_economic_pipeline_is_compatibility_alias(monkeypatch):
    run_pipeline = MagicMock()
    monkeypatch.setattr(pipeline, "run_pipeline", run_pipeline)

    settings = replace(_settings(), app_password="")
    pipeline.execute_economic_pipeline(settings)

    run_pipeline.assert_called_once_with(settings)
