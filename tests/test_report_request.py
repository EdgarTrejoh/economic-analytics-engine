from app.config import Settings
from app.models import ReportRequest, report_request_from_settings


def test_report_request_from_settings_maps_runtime_fields():
    settings = Settings(
        sheet_url="https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing",
        sender_email="sender@gmail.com",
        recipient_email="recipient@example.com",
        app_password="",
        report_file_name="output/test.pdf",
        nota_metodologica="Nota en memoria.",
    )

    request = report_request_from_settings(settings)

    assert isinstance(request, ReportRequest)
    assert request.recipient_email == "recipient@example.com"
    assert request.report_file_name == "output/test.pdf"
    assert request.nota_metodologica == "Nota en memoria."
    assert request.start_year is None
    assert request.end_year is None
