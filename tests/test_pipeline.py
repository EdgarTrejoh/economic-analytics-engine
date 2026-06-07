from dataclasses import replace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.config import Settings
from app.data_sources.google_sheets import GoogleSheetsConnectionError
from app.models import ReportRequest, ReportResult
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


def _data_source(df):
    data_source = MagicMock()
    data_source.load_indicators.return_value = df
    return data_source


def test_run_pipeline_orchestrates_report_without_email(monkeypatch):
    raw_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    calc_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    metrics_result = (calc_df, {"nominal_salario": 0.1}, 2016, 2016, 2016)

    calc_metrics = MagicMock(return_value=metrics_result)
    generate_images = MagicMock(return_value=["p1", "p2", "p3", "p4", "p5"])
    generate_insights = MagicMock(return_value=["insight-1", "insight-2", "insight-3", "insight-4", "insight-5"])
    create_pdf = MagicMock()
    send_email = MagicMock()

    monkeypatch.setattr(pipeline, "calculate_financial_metrics", calc_metrics)
    monkeypatch.setattr(pipeline, "generate_report_insights", generate_insights)
    monkeypatch.setattr(pipeline, "generate_visualizations", generate_images)
    monkeypatch.setattr(pipeline, "create_pdf_report", create_pdf)
    monkeypatch.setattr(pipeline, "send_report_email", send_email)

    settings = _settings(app_password="", nota_metodologica="Nota desde settings.")
    data_source = _data_source(raw_df)
    result = pipeline.run_pipeline(settings, data_source=data_source)

    data_source.load_indicators.assert_called_once_with(None, None)
    calc_metrics.assert_called_once_with(raw_df)
    generate_insights.assert_called_once_with(calc_df, metrics_result[1], 2016, 2016, 2016, settings)
    generate_images.assert_called_once()
    create_pdf.assert_called_once()
    assert create_pdf.call_args.args[-2] == ["insight-1", "insight-2", "insight-3", "insight-4", "insight-5"]
    assert create_pdf.call_args.args[-1] == "Nota desde settings."
    assert result.email_sent is False
    assert result.report_file_path == "reporte.pdf"
    assert result.status == "completed"
    assert isinstance(result, ReportResult)
    send_email.assert_not_called()


def test_run_pipeline_uses_explicit_report_request(monkeypatch):
    settings = _settings(app_password="")
    request = ReportRequest(
        recipient_email="custom@example.com",
        start_year=2018,
        end_year=2020,
        report_file_name="custom.pdf",
        nota_metodologica="Nota custom.",
    )
    raw_df = pd.DataFrame({YEAR_COLUMN: [2018], "INPC": [100.0]})
    metrics_result = (raw_df, {"nominal_salario": 0.1}, 2018, 2018, 2020)
    data_source = _data_source(raw_df)

    monkeypatch.setattr(pipeline, "calculate_financial_metrics", MagicMock(return_value=metrics_result))
    monkeypatch.setattr(pipeline, "generate_report_insights", MagicMock(return_value=["i1", "i2", "i3", "i4", "i5"]))
    monkeypatch.setattr(pipeline, "generate_visualizations", MagicMock(return_value=["p1", "p2", "p3", "p4", "p5"]))
    create_pdf = MagicMock()
    monkeypatch.setattr(pipeline, "create_pdf_report", create_pdf)
    monkeypatch.setattr(pipeline, "send_report_email", MagicMock())

    result = pipeline.run_pipeline(settings, request=request, data_source=data_source)

    data_source.load_indicators.assert_called_once_with(2018, 2020)
    assert create_pdf.call_args.args[-3] == "custom.pdf"
    assert create_pdf.call_args.args[-1] == "Nota custom."
    assert result.report_file_path == "custom.pdf"
    assert result.start_year == 2018
    assert result.end_year == 2020


def test_run_pipeline_sends_email_when_password_is_present(monkeypatch):
    settings = _settings(app_password="abcdefghijklmnop")
    raw_df = pd.DataFrame({YEAR_COLUMN: [2016], "INPC": [100.0]})
    metrics_result = (raw_df, {"nominal_salario": 0.1}, 2016, 2016, 2016)

    monkeypatch.setattr(pipeline, "calculate_financial_metrics", MagicMock(return_value=metrics_result))
    monkeypatch.setattr(pipeline, "generate_report_insights", MagicMock(return_value=["i1", "i2", "i3", "i4", "i5"]))
    monkeypatch.setattr(pipeline, "generate_visualizations", MagicMock(return_value=["p1", "p2", "p3", "p4", "p5"]))
    monkeypatch.setattr(pipeline, "create_pdf_report", MagicMock())
    send_email = MagicMock()
    monkeypatch.setattr(pipeline, "send_report_email", send_email)

    result = pipeline.run_pipeline(settings, data_source=_data_source(raw_df))

    send_email.assert_called_once_with(
        settings.sender_email,
        settings.app_password,
        settings.recipient_email,
        settings.report_file_name,
    )
    assert result.email_sent is True


def test_run_pipeline_logs_and_reraises_failures(caplog):
    data_source = MagicMock()
    data_source.load_indicators.side_effect = GoogleSheetsConnectionError("No se pudo conectar a Google Sheets.")

    with pytest.raises(GoogleSheetsConnectionError, match="No se pudo conectar a Google Sheets"):
        pipeline.run_pipeline(_settings(app_password=""), data_source=data_source)

    data_source.load_indicators.assert_called_once_with(None, None)
    assert "El pipeline fallo en la ejecucion" in caplog.text


def test_execute_economic_pipeline_is_compatibility_alias(monkeypatch):
    run_pipeline = MagicMock()
    monkeypatch.setattr(pipeline, "run_pipeline", run_pipeline)

    settings = replace(_settings(), app_password="")
    pipeline.execute_economic_pipeline(settings)

    run_pipeline.assert_called_once_with(settings)
