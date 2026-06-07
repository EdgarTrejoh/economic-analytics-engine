import datetime
import logging
from pathlib import Path

from fpdf import FPDF

from app.services.ai_insights import SECTION_IDS, get_fallback_insights


logger = logging.getLogger(__name__)
METHODOLOGICAL_NOTE_PATH = Path("data") / "nota_metodologica.txt"
METHODOLOGICAL_NOTE_TITLE = "Notas metodológicas y supuestos de cierre 2026"


class PDFReport(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_y(10)
            self.set_font("Arial", "B", 12)
            self.cell(0, 5, "Reporte Ejecutivo", 0, 1, "C")

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Pagina {self.page_no()}", 0, 0, "C")

    def add_cover(self, titulo, subtitulo, autor, fecha):
        self.add_page()
        self.set_font("Arial", "B", 24)
        self.ln(50)
        self.multi_cell(0, 10, titulo, align="C")
        self.set_font("Arial", "I", 16)
        self.ln(10)
        self.multi_cell(0, 10, subtitulo, align="C")
        self.ln(40)
        self.set_font("Arial", "", 14)
        self.cell(0, 10, f"Autor: {autor}", align="C")
        self.ln(10)
        self.cell(0, 10, f"Fecha: {fecha.strftime('%Y-%m-%d')}", align="C")
        self.ln(10)

    def add_section(self, title):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(5)

    def add_paragraph(self, text):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 5, text)
        self.ln(5)


def create_pdf_report(
    df,
    cagrs,
    base_year,
    start_year,
    end_year,
    image_paths,
    report_file_name,
    insights=None,
    nota_metodologica=None,
):
    """Genera el PDF combinando analisis de texto, imagenes e insights ejecutivos."""
    insights_by_section = _insights_by_section(insights)
    pdf = PDFReport()
    pdf.add_cover(
        titulo="Reporte Ejecutivo: El Poder Adquisitivo",
        subtitulo=f"Analisis de Salario Minimo, UMA e Inflacion en Mexico ({start_year}-{end_year})",
        autor="Pipeline Analitico Automatizado",
        fecha=datetime.date.today(),
    )

    pdf.add_page()
    pdf.add_section("1. Evolucion del Poder Adquisitivo: Salario vs. UMA")
    pdf.image(image_paths[0], x=20, w=170)
    _add_executive_insight(pdf, insights_by_section["poder_adquisitivo"])

    pdf.add_page()
    pdf.add_section(f"2. Salario Minimo vs. UMA (Base {base_year} = 100)")
    pdf.image(image_paths[1], x=20, w=170)
    _add_executive_insight(pdf, insights_by_section["base_2016"])

    pdf.add_page()
    pdf.add_section(f"3. Crecimiento Anual Compuesto (CAGR {start_year}-{end_year})")
    pdf.image(image_paths[2], x=20, w=170)
    _add_executive_insight(pdf, insights_by_section["cagr"])

    pdf.add_page()
    pdf.add_section("4. Inflacion Anual y Politica Monetaria")
    pdf.image(image_paths[3], x=20, w=170)
    _add_executive_insight(pdf, insights_by_section["inflacion_banxico"])

    pdf.add_page()
    pdf.add_section("5. Dashboard (Resumen Ejecutivo)")
    pdf.image(image_paths[4], x=20, w=170)
    _add_executive_insight(pdf, insights_by_section["dashboard"])

    _add_methodological_note_page(pdf, nota_metodologica)

    report_path = Path(report_file_name)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(report_file_name)
    logger.info(f"Reporte '{report_file_name}' generado exitosamente.")


def _insights_by_section(insights):
    selected_insights = insights or get_fallback_insights()
    mapped = {insight.get("section_id"): insight for insight in selected_insights}
    if set(mapped) != set(SECTION_IDS):
        mapped = {insight["section_id"]: insight for insight in get_fallback_insights()}
    return mapped


def _add_executive_insight(pdf, insight):
    comentario = _safe_pdf_text(_trim_text(insight["comentario"], 420))
    implicacion = _safe_pdf_text(_trim_text(insight["implicacion"], 220))
    current_y = pdf.get_y()
    compact = isinstance(current_y, (int, float)) and current_y > 235
    title_size = 8 if compact else 9
    body_size = 8 if compact else 8.5
    line_height = 3.4 if compact else 3.7

    pdf.ln(1)
    pdf.set_font("Arial", "B", title_size)
    pdf.multi_cell(0, line_height, "Lectura ejecutiva:")
    pdf.set_font("Arial", "", body_size)
    pdf.multi_cell(0, line_height, comentario)
    pdf.set_font("Arial", "B", title_size)
    pdf.multi_cell(0, line_height, _safe_pdf_text("Implicación:"))
    pdf.set_font("Arial", "", body_size)
    pdf.multi_cell(0, line_height, implicacion)


def _add_methodological_note_page(pdf, nota_text: str | None = None):
    note_text = nota_text.strip() if isinstance(nota_text, str) else None
    if note_text is None:
        note_text = _read_methodological_note()
    if not note_text:
        return

    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.multi_cell(0, 6, _safe_pdf_text(METHODOLOGICAL_NOTE_TITLE))
    pdf.ln(4)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 5, _safe_pdf_text(note_text))


def _read_methodological_note():
    if not METHODOLOGICAL_NOTE_PATH.exists():
        logger.warning("Nota metodologica no encontrada: %s", METHODOLOGICAL_NOTE_PATH)
        return None

    try:
        return METHODOLOGICAL_NOTE_PATH.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError:
        return METHODOLOGICAL_NOTE_PATH.read_text(encoding="cp1252").strip()


def _safe_pdf_text(text):
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _trim_text(text, max_length):
    text = " ".join(str(text).split())
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip(" .,;:") + "."
