import reporte_economico


def test_legacy_facade_exports_public_api():
    expected_exports = {
        "PDFReport",
        "calculate_cagr",
        "calculate_financial_metrics",
        "create_pdf_report",
        "execute_economic_pipeline",
        "generate_visualizations",
        "get_sheet_csv_url",
        "load_and_clean_data",
        "send_report_email",
        "run_pipeline",
    }

    assert set(reporte_economico.__all__) == expected_exports
    for name in expected_exports:
        assert hasattr(reporte_economico, name)
