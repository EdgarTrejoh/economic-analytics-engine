from unittest.mock import MagicMock

import matplotlib.pyplot as plt

from app.services import pdf_report
from app.services.ai_insights import SECTION_IDS, get_fallback_insights


def test_create_pdf_report_builds_expected_pdf_sections(monkeypatch, tmp_path):
    pdf_instance = MagicMock()
    pdf_class = MagicMock(return_value=pdf_instance)
    monkeypatch.setattr(pdf_report, "PDFReport", pdf_class)
    monkeypatch.setattr(pdf_report, "METHODOLOGICAL_NOTE_PATH", tmp_path / "missing-note.txt")

    create_args = {
        "df": MagicMock(),
        "cagrs": {"nominal_salario": 0.1, "real_salario": 0.05},
        "base_year": 2016,
        "start_year": 2016,
        "end_year": 2018,
        "image_paths": [f"plot{i}.png" for i in range(1, 6)],
        "report_file_name": "reporte.pdf",
    }

    pdf_report.create_pdf_report(**create_args)

    pdf_class.assert_called_once_with()
    pdf_instance.add_cover.assert_called_once()
    assert pdf_instance.add_page.call_count == 5
    assert pdf_instance.add_section.call_count == 5
    assert pdf_instance.image.call_count == 5
    assert pdf_instance.multi_cell.call_count >= 20
    cell_texts = [call.args[2] for call in pdf_instance.multi_cell.call_args_list]
    assert "Lectura ejecutiva:" in cell_texts
    assert pdf_report._safe_pdf_text("Implicación:") in cell_texts
    pdf_instance.output.assert_called_once_with("reporte.pdf")


def test_create_pdf_report_adds_methodological_note_when_file_exists(monkeypatch, tmp_path):
    pdf_instance = MagicMock()
    pdf_class = MagicMock(return_value=pdf_instance)
    note_path = tmp_path / "nota_metodologica.txt"
    note_path.write_text("Contenido metodologico de prueba.", encoding="utf-8")

    monkeypatch.setattr(pdf_report, "PDFReport", pdf_class)
    monkeypatch.setattr(pdf_report, "METHODOLOGICAL_NOTE_PATH", note_path)

    pdf_report.create_pdf_report(
        df=MagicMock(),
        cagrs={"nominal_salario": 0.1, "real_salario": 0.05},
        base_year=2016,
        start_year=2016,
        end_year=2018,
        image_paths=[f"plot{i}.png" for i in range(1, 6)],
        report_file_name="reporte.pdf",
    )

    cell_texts = [call.args[2] for call in pdf_instance.multi_cell.call_args_list]
    assert pdf_report._safe_pdf_text(pdf_report.METHODOLOGICAL_NOTE_TITLE) in cell_texts
    assert "Contenido metodologico de prueba." in cell_texts
    assert "Anexo" not in cell_texts
    assert pdf_instance.add_page.call_count == 6
    pdf_instance.output.assert_called_once_with("reporte.pdf")


def test_create_pdf_report_continues_when_methodological_note_is_missing(monkeypatch, tmp_path, caplog):
    pdf_instance = MagicMock()
    pdf_class = MagicMock(return_value=pdf_instance)

    monkeypatch.setattr(pdf_report, "PDFReport", pdf_class)
    monkeypatch.setattr(pdf_report, "METHODOLOGICAL_NOTE_PATH", tmp_path / "missing.txt")

    pdf_report.create_pdf_report(
        df=MagicMock(),
        cagrs={"nominal_salario": 0.1, "real_salario": 0.05},
        base_year=2016,
        start_year=2016,
        end_year=2018,
        image_paths=[f"plot{i}.png" for i in range(1, 6)],
        report_file_name="reporte.pdf",
    )

    assert "Nota metodologica no encontrada" in caplog.text
    assert pdf_instance.add_page.call_count == 5
    pdf_instance.output.assert_called_once_with("reporte.pdf")


def test_trim_text_does_not_cut_normal_executive_implication():
    text = "El entorno conserva presion sobre costo financiero, credito y consumo financiado."

    assert pdf_report._trim_text(text, 220) == text


def test_create_pdf_report_keeps_dashboard_on_sixth_page(monkeypatch, tmp_path):
    captured = {}
    original_pdf_report = pdf_report.PDFReport

    class CapturingPDFReport(original_pdf_report):
        def __init__(self):
            super().__init__()
            captured["pdf"] = self

    monkeypatch.setattr(pdf_report, "PDFReport", CapturingPDFReport)
    monkeypatch.setattr(pdf_report, "METHODOLOGICAL_NOTE_PATH", tmp_path / "missing-note.txt")

    image_paths = []
    for index, figsize in enumerate([(12, 7), (12, 6), (10, 6), (12, 7), (12, 15)], start=1):
        image_path = tmp_path / f"plot{index}.png"
        plt.figure(figsize=figsize)
        plt.plot([2016, 2017, 2018], [1, 2, 3])
        plt.savefig(image_path, format="png", bbox_inches="tight")
        plt.close()
        image_paths.append(str(image_path))

    insights = get_fallback_insights()
    for insight in insights:
        insight["comentario"] = (
            "Texto ejecutivo con suficiente longitud para validar que el bloque se "
            "mantiene compacto dentro de la pagina del reporte y no abre una pagina residual."
        )
        insight["implicacion"] = (
            "Condiciones financieras restrictivas con recuperacion salarial real."
        )

    pdf_report.create_pdf_report(
        df=MagicMock(),
        cagrs={"nominal_salario": 0.1574, "real_salario": 0.1037},
        base_year=2016,
        start_year=2016,
        end_year=2026,
        image_paths=image_paths,
        report_file_name=str(tmp_path / "reporte.pdf"),
        insights=insights,
    )

    assert captured["pdf"].page_no() == 6
    assert [insight["section_id"] for insight in insights] == SECTION_IDS
