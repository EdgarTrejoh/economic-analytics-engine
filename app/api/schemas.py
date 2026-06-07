import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ReportCreateRequest(BaseModel):
    recipient_email: str = Field(..., min_length=3, max_length=254)
    start_year: int = Field(..., ge=1900, le=2100)
    end_year: int = Field(..., ge=1900, le=2100)
    nota_metodologica: str | None = None

    @field_validator("recipient_email")
    @classmethod
    def validate_email(cls, value):
        value = value.strip()
        if not EMAIL_PATTERN.match(value):
            raise ValueError("recipient_email debe tener formato de correo valido")
        return value

    @field_validator("nota_metodologica")
    @classmethod
    def normalize_note(cls, value):
        if value is None:
            return None
        value = value.strip()
        return value or None

    @model_validator(mode="after")
    def validate_period(self):
        if self.start_year > self.end_year:
            raise ValueError("start_year no puede ser mayor que end_year")
        return self


class ReportResponse(BaseModel):
    status: str
    report_file_path: str
    email_sent: bool
    generated_at: datetime
    start_year: int | None = None
    end_year: int | None = None
