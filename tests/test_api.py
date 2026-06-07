from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.api.main import app
from app.models import ReportResult


client = TestClient(app)


def _settings():
    return SimpleNamespace(report_file_name="output/test.pdf")


def test_create_report_calls_pipeline_with_report_request(monkeypatch):
    load_settings = MagicMock(return_value=_settings())
    run_pipeline = MagicMock(
        return_value=ReportResult(
            report_file_path="output/test.pdf",
            email_sent=False,
            generated_at=datetime(2026, 6, 7, 12, 0, 0),
            status="completed",
            start_year=2018,
            end_year=2020,
        )
    )
    monkeypatch.setattr("app.api.routes.load_settings", load_settings)
    monkeypatch.setattr("app.api.routes.run_pipeline", run_pipeline)

    response = client.post(
        "/reports",
        json={
            "recipient_email": "cliente@example.com",
            "start_year": 2018,
            "end_year": 2020,
            "nota_metodologica": " Nota API. ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "completed",
        "report_file_path": "output/test.pdf",
        "email_sent": False,
        "generated_at": "2026-06-07T12:00:00",
        "start_year": 2018,
        "end_year": 2020,
    }
    load_settings.assert_called_once_with(prompt_for_password=False)
    run_pipeline.assert_called_once()

    _, kwargs = run_pipeline.call_args
    request = kwargs["request"]
    assert kwargs["settings"] == load_settings.return_value
    assert request.recipient_email == "cliente@example.com"
    assert request.start_year == 2018
    assert request.end_year == 2020
    assert request.report_file_name == "output/test.pdf"
    assert request.nota_metodologica == "Nota API."


def test_create_report_rejects_invalid_email(monkeypatch):
    run_pipeline = MagicMock()
    monkeypatch.setattr("app.api.routes.run_pipeline", run_pipeline)

    response = client.post(
        "/reports",
        json={
            "recipient_email": "correo-invalido",
            "start_year": 2018,
            "end_year": 2020,
        },
    )

    assert response.status_code == 422
    run_pipeline.assert_not_called()


def test_create_report_rejects_invalid_period(monkeypatch):
    run_pipeline = MagicMock()
    monkeypatch.setattr("app.api.routes.run_pipeline", run_pipeline)

    response = client.post(
        "/reports",
        json={
            "recipient_email": "cliente@example.com",
            "start_year": 2021,
            "end_year": 2020,
        },
    )

    assert response.status_code == 422
    run_pipeline.assert_not_called()
