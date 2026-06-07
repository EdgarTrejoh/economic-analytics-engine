import smtplib
from email import message_from_string
from email.header import decode_header, make_header
from unittest.mock import MagicMock

from app.services.email_sender import send_report_email


def test_send_report_email_smtp_flow(monkeypatch, tmp_path):
    report_file = tmp_path / "reporte.pdf"
    report_file.write_bytes(b"%PDF-1.4 test content")

    smtp_instance = MagicMock()
    smtp_class = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_class)

    send_report_email(
        sender_email="sender@gmail.com",
        app_password="abcdefghijklmnop",
        recipient_email="recipient@example.com",
        report_file_name=str(report_file),
    )

    smtp_class.assert_called_once_with("smtp.gmail.com", 587)
    smtp_instance.starttls.assert_called_once_with()
    smtp_instance.login.assert_called_once_with("sender@gmail.com", "abcdefghijklmnop")
    smtp_instance.sendmail.assert_called_once()
    smtp_instance.quit.assert_called_once_with()

    sendmail_args = smtp_instance.sendmail.call_args.args
    sent_message = message_from_string(sendmail_args[2])
    subject = str(make_header(decode_header(sent_message["Subject"])))
    assert sendmail_args[:2] == ("sender@gmail.com", "recipient@example.com")
    assert "Reporte Economico" in subject
    assert "reporte.pdf" in subject
    assert sent_message["From"] == "sender@gmail.com"
    assert sent_message["To"] == "recipient@example.com"


def test_send_report_email_missing_attachment_does_not_connect(monkeypatch, tmp_path, caplog):
    smtp_class = MagicMock()
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_class)

    send_report_email(
        sender_email="sender@gmail.com",
        app_password="abcdefghijklmnop",
        recipient_email="recipient@example.com",
        report_file_name=str(tmp_path / "no_existe.pdf"),
    )

    smtp_class.assert_not_called()
    assert "No se pudo encontrar el archivo adjunto" in caplog.text


def test_send_report_email_authentication_error_logs_and_quits(monkeypatch, tmp_path, caplog):
    report_file = tmp_path / "reporte.pdf"
    report_file.write_bytes(b"%PDF-1.4 test content")

    smtp_instance = MagicMock()
    smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(
        535,
        b"Authentication failed",
    )
    smtp_class = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_class)

    send_report_email(
        sender_email="sender@gmail.com",
        app_password="wrong-password",
        recipient_email="recipient@example.com",
        report_file_name=str(report_file),
    )

    smtp_instance.starttls.assert_called_once_with()
    smtp_instance.login.assert_called_once_with("sender@gmail.com", "wrong-password")
    smtp_instance.sendmail.assert_not_called()
    smtp_instance.quit.assert_called_once_with()
    assert "ERROR DE AUTENTICACION" in caplog.text


def test_send_report_email_smtp_connection_error_does_not_call_quit(monkeypatch, tmp_path, caplog):
    report_file = tmp_path / "reporte.pdf"
    report_file.write_bytes(b"%PDF-1.4 test content")

    smtp_class = MagicMock(side_effect=OSError("connection refused"))
    monkeypatch.setattr("app.services.email_sender.smtplib.SMTP", smtp_class)

    send_report_email(
        sender_email="sender@gmail.com",
        app_password="abcdefghijklmnop",
        recipient_email="recipient@example.com",
        report_file_name=str(report_file),
    )

    smtp_class.assert_called_once_with("smtp.gmail.com", 587)
    assert "Fallo al enviar el correo: connection refused" in caplog.text
