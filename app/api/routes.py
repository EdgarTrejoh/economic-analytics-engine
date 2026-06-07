from fastapi import APIRouter

from app.api.schemas import ReportCreateRequest, ReportResponse
from app.config import load_settings
from app.models import ReportRequest
from app.services.pipeline import run_pipeline


router = APIRouter()


@router.post("/reports", response_model=ReportResponse)
def create_report(payload: ReportCreateRequest):
    settings = load_settings(prompt_for_password=False)
    request = ReportRequest(
        recipient_email=payload.recipient_email,
        start_year=payload.start_year,
        end_year=payload.end_year,
        report_file_name=settings.report_file_name,
        nota_metodologica=payload.nota_metodologica,
    )
    result = run_pipeline(settings=settings, request=request)
    return ReportResponse(
        status=result.status,
        report_file_path=result.report_file_path,
        email_sent=result.email_sent,
        generated_at=result.generated_at,
        start_year=result.start_year,
        end_year=result.end_year,
    )
