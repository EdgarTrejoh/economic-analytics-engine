import getpass
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1JiB0WJPRTcq5yE1Zy3jW7n7K2hgfdRNcwXhiS8P1XTI/edit?usp=sharing"
)
DEFAULT_REPORT_FILE_NAME = str(Path("output") / "Reporte_Economico_Ejecutivo.pdf")
APP_PASSWORD_PLACEHOLDER = "TU_CONTRASEÑA_DE_APLICACION_AQUI"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


@dataclass
class Settings:
    sheet_url: str
    sender_email: str | None
    recipient_email: str | None
    app_password: str
    report_file_name: str = DEFAULT_REPORT_FILE_NAME
    ai_insights_enabled: bool = False
    openai_api_key: str | None = None
    openai_model: str = DEFAULT_OPENAI_MODEL
    nota_metodologica: str | None = None


def load_settings(prompt_for_password: bool = True) -> Settings:
    """Carga configuracion desde variables de entorno y opcionalmente solicita password."""
    load_dotenv()

    app_password = os.getenv("APP_PASSWORD", "")
    if not app_password or app_password == APP_PASSWORD_PLACEHOLDER:
        if prompt_for_password:
            try:
                app_password = getpass.getpass(
                    "Ingresa la Contraseña de Aplicación de Google (16 dígitos) "
                    "o presiona Enter para omitir el correo: "
                )
            except EOFError:
                app_password = ""
        else:
            app_password = ""

    return Settings(
        sheet_url=os.getenv("SHEET_URL", DEFAULT_SHEET_URL),
        sender_email=os.getenv("SENDER_EMAIL"),
        recipient_email=os.getenv("RECIPIENT_EMAIL"),
        app_password=app_password,
        ai_insights_enabled=_env_flag("AI_INSIGHTS_ENABLED"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
    )


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
