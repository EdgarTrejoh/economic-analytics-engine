import pytest
import pandas as pd
import smtplib
from email import message_from_string
from email.header import decode_header, make_header
from unittest.mock import MagicMock

from reporte_economico import (
    calculate_cagr,
    calculate_financial_metrics,
    get_sheet_csv_url,
    load_and_clean_data,
    send_report_email,
)

def test_calculate_cagr():
    # start_value = 100, end_value = 200, num_years = 1 -> (200/100)^(1/1) - 1 = 1.0 (100%)
    assert calculate_cagr(100, 200, 1) == 1.0
    
    # start_value = 100, end_value = 121, num_years = 2 -> (121/100)^(1/2) - 1 = 1.1 - 1 = 0.1 (10%)
    assert calculate_cagr(100, 121, 2) == pytest.approx(0.1, 0.0001)

    # num_years = 0
    assert calculate_cagr(100, 150, 0) == 0.0

def test_calculate_financial_metrics():
    # DataFrame ficticio similar a los datos de la fuente original
    data = {
        'Año': [2016, 2017, 2018],
        'INPC': [100.0, 105.0, 110.25], # Inflación constante del 5% anual
        'Salario_Minimo_Diario': [70.0, 77.0, 84.7], # Incremento nominal constante del 10% anual
        'UMA_diario': [70.0, 73.5, 77.175], # Incremento nominal constante del 5% anual (igual a inflación)
        'Tasa_Referencia_Banxico': [4.0, 5.0, 6.0]
    }
    df = pd.DataFrame(data)

    df_calc, cagrs, base_year, start_year, end_year = calculate_financial_metrics(df)

    # Aserciones sobre fechas
    assert base_year == 2016
    assert start_year == 2016
    assert end_year == 2018

    # Aserciones sobre Índice de Precios (Base 100)
    assert df_calc['Indice_de_Precios'].iloc[0] == 100.0
    assert df_calc['Indice_de_Precios'].iloc[1] == 105.0
    assert df_calc['Indice_de_Precios'].iloc[2] == pytest.approx(110.25, 0.01)

    # Aserciones sobre Inflación
    assert df_calc['inflacion'].iloc[0] == 0.0
    assert df_calc['inflacion'].iloc[1] == pytest.approx(5.0, 0.001)
    assert df_calc['inflacion'].iloc[2] == pytest.approx(5.0, 0.001)

    # Aserciones sobre Salario y UMA reales
    # UMA Crece 5% y la inflación es 5%, por ende el crecimiento real de la UMA debe ser 0% (se mantiene el poder adquisitivo)
    assert df_calc['UMA_Real'].iloc[0] == 70.0
    assert df_calc['UMA_Real'].iloc[2] == 70.0
    assert cagrs['real_uma'] == pytest.approx(0.0, 0.001)

    # Salario Crece 10% pero la inflación es 5%. Crecimiento real debe ser positivo.
    assert df_calc['Salario_Minimo_Real'].iloc[2] > 70.0
    assert cagrs['real_salario'] > 0.0

    # Aserciones sobre CAGR Nominales
    assert cagrs['nominal_salario'] == pytest.approx(0.10, 0.001)
    assert cagrs['nominal_uma'] == pytest.approx(0.05, 0.001)

def test_send_report_email_smtp_flow(monkeypatch, tmp_path):
    report_file = tmp_path / "reporte.pdf"
    report_file.write_bytes(b"%PDF-1.4 test content")

    smtp_instance = MagicMock()
    smtp_class = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr("reporte_economico.smtplib.SMTP", smtp_class)

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
    assert sendmail_args[0] == "sender@gmail.com"
    assert sendmail_args[1] == "recipient@example.com"

    sent_message = message_from_string(sendmail_args[2])
    subject = str(make_header(decode_header(sent_message["Subject"])))
    assert "Reporte Econ" in subject
    assert "reporte.pdf" in subject
    assert sent_message["From"] == "sender@gmail.com"
    assert sent_message["To"] == "recipient@example.com"

def test_send_report_email_missing_attachment_does_not_connect(monkeypatch, tmp_path, caplog):
    smtp_class = MagicMock()
    monkeypatch.setattr("reporte_economico.smtplib.SMTP", smtp_class)

    missing_report = tmp_path / "no_existe.pdf"
    send_report_email(
        sender_email="sender@gmail.com",
        app_password="abcdefghijklmnop",
        recipient_email="recipient@example.com",
        report_file_name=str(missing_report),
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
    monkeypatch.setattr("reporte_economico.smtplib.SMTP", smtp_class)

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
    assert "ERROR DE AUTENTICACI" in caplog.text

@pytest.mark.parametrize(
    ("sheet_url", "expected_csv_url"),
    [
        (
            "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing",
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv",
        ),
        (
            "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing#gid=987",
            "https://docs.google.com/spreadsheets/d/abc123/export?format=csv&gid=987",
        ),
    ],
)
def test_get_sheet_csv_url(sheet_url, expected_csv_url):
    assert get_sheet_csv_url(sheet_url) == expected_csv_url

def test_get_sheet_csv_url_invalid_url_raises_value_error():
    with pytest.raises(ValueError, match="URL de Google Sheets"):
        get_sheet_csv_url("https://example.com/not-a-google-sheet")

def test_load_and_clean_data_converts_types_and_drops_rows_without_year(monkeypatch):
    raw_df = pd.DataFrame(
        {
            'Año': ["2016", None, "2018"],
            'INPC': ["100.0", "105.0", "110.25"],
            'Salario_Minimo_Diario': ["70.0", "77.0", "84.7"],
            'UMA_diario': ["70.0", "73.5", "77.175"],
            'Tasa_Referencia_Banxico': ["4.0", "5.0", "6.0"],
        }
    )
    read_csv = MagicMock(return_value=raw_df)
    monkeypatch.setattr("reporte_economico.pd.read_csv", read_csv)

    cleaned_df = load_and_clean_data("https://docs.google.com/sheet.csv")

    read_csv.assert_called_once_with(
        "https://docs.google.com/sheet.csv",
        skipinitialspace=True,
    )
    assert len(cleaned_df) == 2
    assert cleaned_df['Año'].tolist() == [2016, 2018]
    assert str(cleaned_df['Año'].dtype) == "Int64"
    assert cleaned_df['INPC'].dtype == "float64"
    assert cleaned_df['Salario_Minimo_Diario'].dtype == "float64"
    assert cleaned_df['UMA_diario'].dtype == "float64"
    assert cleaned_df['Tasa_Referencia_Banxico'].dtype == "float64"

def test_load_and_clean_data_read_csv_error_is_raised(monkeypatch):
    monkeypatch.setattr(
        "reporte_economico.pd.read_csv",
        MagicMock(side_effect=ConnectionError("network unavailable")),
    )

    with pytest.raises(ConnectionError, match="network unavailable"):
        load_and_clean_data("https://docs.google.com/sheet.csv")

@pytest.mark.parametrize(
    "missing_column",
    ["INPC", "Salario_Minimo_Diario", "UMA_diario"],
)
def test_calculate_financial_metrics_missing_required_columns_raises_key_error(missing_column):
    data = {
        'Año': [2016, 2017, 2018],
        'INPC': [100.0, 105.0, 110.25],
        'Salario_Minimo_Diario': [70.0, 77.0, 84.7],
        'UMA_diario': [70.0, 73.5, 77.175],
        'Tasa_Referencia_Banxico': [4.0, 5.0, 6.0],
    }
    data.pop(missing_column)
    df = pd.DataFrame(data)

    with pytest.raises(KeyError, match=missing_column):
        calculate_financial_metrics(df)
