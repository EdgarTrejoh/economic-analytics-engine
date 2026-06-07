from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ReportResult:
    report_file_path: str
    email_sent: bool
    generated_at: datetime
    status: str
    start_year: int | None = None
    end_year: int | None = None
