import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from app.services import ai_insights


def _settings(enabled=False, api_key=None):
    return SimpleNamespace(
        ai_insights_enabled=enabled,
        openai_api_key=api_key,
        openai_model="test-model",
    )


def _df():
    return pd.DataFrame(
        {
            "Año": [2016, 2017, 2018],
            "Salario_Minimo_Real": [70.0, 73.3, 76.8],
            "UMA_Real": [70.0, 70.0, 70.0],
            "Salario_Minimo_Real_Normalizado": [100.0, 104.7, 109.8],
            "UMA_Real_Normalizado": [100.0, 100.0, 100.0],
            "inflacion": [0.0, 5.0, 5.0],
            "Tasa_Referencia_Banxico": [4.0, 5.0, 6.0],
        }
    )


def _cagrs():
    return {
        "nominal_salario": 0.1,
        "real_salario": 0.047,
        "nominal_uma": 0.05,
        "real_uma": 0.0,
    }


def _valid_ai_json():
    return json.dumps(
        {
            "insights": [
                {
                    "section_id": section_id,
                    "titulo": f"Titulo {section_id}",
                    "comentario": f"Comentario {section_id}.",
                    "implicacion": f"Implicacion {section_id}.",
                }
                for section_id in ai_insights.SECTION_IDS
            ]
        }
    )


def test_generate_report_insights_uses_fallback_without_api_key():
    insights = ai_insights.generate_report_insights(
        _df(),
        _cagrs(),
        2016,
        2016,
        2018,
        _settings(enabled=True, api_key=None),
    )

    assert len(insights) == 5
    assert [insight["section_id"] for insight in insights] == ai_insights.SECTION_IDS
    assert "76.80" in insights[0]["comentario"]


def test_build_insight_payload_includes_sections_assumptions_and_derived_metrics():
    payload = ai_insights.build_insight_payload(_df(), _cagrs(), 2016, 2016, 2018)
    sections = {section["section_id"]: section for section in payload["secciones"]}

    assert [section["section_id"] for section in payload["secciones"]] == ai_insights.SECTION_IDS
    assert payload["supuestos_2026"] == {
        "inflacion_2026": "estimado de Banxico al mes de diciembre",
        "tasa_banxico": "ultima tasa de referencia publicada disponible",
        "nota_interpretacion": "No tratar 2026 como cierre observado definitivo si corresponde a estimacion.",
    }
    assert sections["poder_adquisitivo"]["brecha_salario_uma_real_final"] == pytest.approx(6.8)
    assert sections["base_2016"]["brecha_normalizada_final"] == pytest.approx(9.8)
    assert sections["base_2016"]["relacion_salario_vs_uma_final"] == pytest.approx(1.098)
    assert sections["inflacion_banxico"]["diferencial_tasa_vs_inflacion_final"] == pytest.approx(1.0)


def test_parse_ai_insights_accepts_expected_json():
    insights = ai_insights.parse_ai_insights(_valid_ai_json())

    assert len(insights) == 5
    assert [insight["section_id"] for insight in insights] == ai_insights.SECTION_IDS
    assert insights[0]["titulo"] == "Titulo poder_adquisitivo"


def test_parse_ai_insights_fills_missing_title_from_section_fallback():
    response = {
        "insights": [
            {
                "section_id": section_id,
                "comentario": f"Comentario {section_id}.",
                "implicacion": f"Implicacion {section_id}.",
            }
            for section_id in ai_insights.SECTION_IDS
        ]
    }

    insights = ai_insights.parse_ai_insights(json.dumps(response))
    fallback = ai_insights.get_fallback_insights()

    assert len(insights) == 5
    assert insights[0]["titulo"] == fallback[0]["titulo"]
    assert insights[0]["comentario"] == "Comentario poder_adquisitivo."


def test_parse_ai_insights_fills_empty_text_fields_from_section_fallback():
    response = json.loads(_valid_ai_json())
    response["insights"][0]["comentario"] = " "
    response["insights"][1]["implicacion"] = ""

    insights = ai_insights.parse_ai_insights(json.dumps(response))
    fallback = ai_insights.get_fallback_insights()

    assert insights[0]["comentario"] == fallback[0]["comentario"]
    assert insights[1]["implicacion"] == fallback[1]["implicacion"]


def test_parse_ai_insights_replaces_weak_editorial_terms_with_fallback():
    response = json.loads(_valid_ai_json())
    response["insights"][0]["implicacion"] = "Esto puede impulsar el consumo."
    response["insights"][1]["comentario"] = "La grafica sugiere una posible presion."
    response["insights"][2]["comentario"] = "Hay inflacion controlada."
    response["insights"][3]["implicacion"] = "Puede afectar el costo financiero."

    insights = ai_insights.parse_ai_insights(json.dumps(response))
    fallback = ai_insights.get_fallback_insights()

    assert insights[0]["implicacion"] == fallback[0]["implicacion"]
    assert insights[1]["comentario"] == fallback[1]["comentario"]
    assert insights[2]["comentario"] == fallback[2]["comentario"]
    assert insights[3]["implicacion"] == fallback[3]["implicacion"]


def test_generate_report_insights_uses_fallback_when_ai_returns_invalid_json(monkeypatch):
    request_ai = MagicMock(return_value="{invalid-json")
    monkeypatch.setattr(ai_insights, "request_ai_insights", request_ai)

    insights = ai_insights.generate_report_insights(
        _df(),
        _cagrs(),
        2016,
        2016,
        2018,
        _settings(enabled=True, api_key="test-key"),
    )

    request_ai.assert_called_once()
    assert len(insights) == 5
    assert "76.80" in insights[0]["comentario"]


def test_generate_report_insights_uses_dynamic_fallback_when_disabled():
    insights = ai_insights.generate_report_insights(
        _df(),
        _cagrs(),
        2016,
        2016,
        2018,
        _settings(enabled=False, api_key="test-key"),
    )

    assert len(insights) == 5
    assert "76.80" in insights[0]["comentario"]


def test_dynamic_fallback_avoids_forbidden_editorial_terms():
    payload = ai_insights.build_insight_payload(_df(), _cagrs(), 2016, 2016, 2018)
    insights = ai_insights.get_fallback_insights(payload)
    full_text = " ".join(
        f"{insight['titulo']} {insight['comentario']} {insight['implicacion']}"
        for insight in insights
    ).lower()

    forbidden_terms = [
        "deterioro",
        "impacta negativamente",
        "desigualdad",
        "podria influir",
        "podría influir",
        "decisiones de politica monetaria",
        "decisiones de política monetaria",
    ]
    assert all(term not in full_text for term in forbidden_terms)
    assert insights[0]["implicacion"] == (
        "La mejora relativa del salario minimo fortalece la capacidad de compra medida contra la UMA."
    )
    assert insights[1]["implicacion"] == (
        "La brecha indexada confirma un fortalecimiento relativo del salario minimo frente a la UMA."
    )


def test_get_fallback_insights_returns_exactly_five_insights():
    insights = ai_insights.get_fallback_insights()

    assert len(insights) == 5
    assert [insight["section_id"] for insight in insights] == ai_insights.SECTION_IDS

def test_fmt_percent_uses_percentage_points():
    from app.services.ai_insights import _fmt_percent

    assert _fmt_percent(0.1037) == "10.37%"
    assert _fmt_percent(10.37) == "10.37%"
    assert _fmt_percent(15.74) == "15.74%"
    assert _fmt_percent(-0.02) == "-0.02%"
