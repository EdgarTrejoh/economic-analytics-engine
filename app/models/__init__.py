"""Modelos de dominio para etapas posteriores."""
from app.models.report_request import ReportRequest, report_request_from_settings
from app.models.report_result import ReportResult

__all__ = ["ReportRequest", "ReportResult", "report_request_from_settings"]
