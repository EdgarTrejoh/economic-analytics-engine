import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


logger = logging.getLogger(__name__)


def send_report_email(sender_email, app_password, recipient_email, report_file_name):
    """Envia el PDF generado por correo electronico."""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = (
        "Reporte Economico Ejecutivo - Analisis de Poder Adquisitivo "
        f"({os.path.basename(report_file_name)})"
    )

    body = "Adjunto el Reporte Economico Ejecutivo completo, generado automaticamente por el pipeline de Python."
    msg.attach(MIMEText(body, "plain"))

    try:
        with open(report_file_name, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {report_file_name}")
            msg.attach(part)
    except FileNotFoundError:
        logger.error(f"No se pudo encontrar el archivo adjunto: {report_file_name}")
        return

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info(f"Correo electronico enviado exitosamente a {recipient_email}.")
    except smtplib.SMTPAuthenticationError:
        logger.error("ERROR DE AUTENTICACION SMTP: La contraseña o el correo no son correctos.")
    except Exception as e:
        logger.error(f"Fallo al enviar el correo: {e}")
    finally:
        if "server" in locals() and server:
            server.quit()
