from dataclasses import dataclass

from app.config import DEFAULT_REPORT_FILE_NAME


@dataclass(frozen=True)
class ReportRequest:
    recipient_email: str | None
    start_year: int | None = None
    end_year: int | None = None
    report_file_name: str = DEFAULT_REPORT_FILE_NAME
    nota_metodologica: str | None = None


def report_request_from_settings(settings):
    return ReportRequest(
        recipient_email=settings.recipient_email,
        report_file_name=settings.report_file_name,
        nota_metodologica=getattr(settings, "nota_metodologica", None),
    )
