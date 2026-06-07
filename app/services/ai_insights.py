import json
import logging
import re
import urllib.error
import urllib.request
from pathlib import Path

from app.indicators import (
    BANXICO_RATE_COLUMN,
    INFLATION_COLUMN,
    NORMALIZED_REAL_MINIMUM_WAGE_COLUMN,
    NORMALIZED_REAL_UMA_COLUMN,
    REAL_MINIMUM_WAGE_COLUMN,
    REAL_UMA_COLUMN,
    YEAR_COLUMN,
)


logger = logging.getLogger(__name__)
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "ai_insights_system_v1.md"

SECTION_IDS = [
    "poder_adquisitivo",
    "base_2016",
    "cagr",
    "inflacion_banxico",
    "dashboard",
]

FORBIDDEN_EDITORIAL_TERMS = [
    "puede impulsar",
    "puede favorecer",
    "puede influir",
    "puede afectar",
    "posible presion",
    "posible presión",
    "sugiere",
    "inflacion controlada",
    "inflación controlada",
    "deterioro",
    "impacta negativamente",
    "desigualdad",
    "decisiones de politica monetaria",
    "decisiones de política monetaria",
    "favorece el ahorro",
]

UNSUPPORTED_INFERENCE_TERMS = [
    "ahorro",
]


def get_fallback_insights(payload=None):
    if payload:
        try:
            return _build_dynamic_fallback_insights(payload)
        except Exception as exc:
            logger.warning("No se pudo construir fallback dinamico; se usara fallback estatico. Error: %s", exc)

    return [
        {
            "section_id": "poder_adquisitivo",
            "titulo": "Divergencia real entre indicadores",
            "comentario": "El salario minimo real muestra una trayectoria distinta frente a la UMA, con mayor sensibilidad al periodo reciente. La comparacion permite separar aumentos nominales de cambios efectivos en poder adquisitivo.",
            "implicacion": "La lectura ejecutiva debe centrarse en la evolucion real, no solo en los incrementos nominales.",
        },
        {
            "section_id": "base_2016",
            "titulo": "Base comun para comparar avance",
            "comentario": "El indice base 2016 permite observar con claridad la distancia acumulada entre salario minimo real y UMA real. La normalizacion reduce ruido de escala y facilita comparar trayectorias.",
            "implicacion": "La brecha indexada resume el cambio relativo del periodo con mayor claridad.",
        },
        {
            "section_id": "cagr",
            "titulo": "Crecimiento compuesto del periodo",
            "comentario": "Las tasas compuestas sintetizan el ritmo promedio anual de los indicadores nominales y reales. La comparacion entre salario y UMA ayuda a identificar donde se concentro el mayor avance relativo.",
            "implicacion": "El CAGR facilita comunicar el desempeño del periodo en una sola metrica comparable.",
        },
        {
            "section_id": "inflacion_banxico",
            "titulo": "Inflacion y referencia monetaria",
            "comentario": "La inflacion anual se interpreta desde el primer año con variacion disponible, evitando atribuir significado al año base. La tasa de referencia aporta contexto monetario sin asumir causalidad directa.",
            "implicacion": "La lectura debe distinguir contexto macroeconomico de relaciones causales no probadas.",
        },
        {
            "section_id": "dashboard",
            "titulo": "Sintesis ejecutiva del periodo",
            "comentario": "El tablero integra poder adquisitivo, crecimiento compuesto e inflacion para una lectura conjunta del periodo. La combinacion de metricas permite identificar consistencias y tensiones entre indicadores.",
            "implicacion": "La decision ejecutiva debe apoyarse en la convergencia de señales, no en una sola grafica.",
        },
    ]


def generate_report_insights(df, cagrs, base_year, start_year, end_year, settings):
    payload = None
    try:
        payload = build_insight_payload(df, cagrs, base_year, start_year, end_year)
    except Exception as exc:
        logger.warning("No se pudo construir payload de insights; se usara fallback estatico. Error: %s", exc)

    if payload is None:
        return get_fallback_insights()

    if not getattr(settings, "ai_insights_enabled", False):
        return get_fallback_insights(payload)

    api_key = getattr(settings, "openai_api_key", None)
    if not api_key:
        return get_fallback_insights(payload)

    try:
        raw_response = request_ai_insights(
            payload,
            api_key,
            getattr(settings, "openai_model", "gpt-4o-mini"),
        )
        return parse_ai_insights(raw_response, get_fallback_insights(payload), payload)
    except Exception as exc:
        logger.warning("No se pudieron generar insights con IA; se usara fallback. Error: %s", exc)
        return get_fallback_insights(payload)


def build_insight_payload(df, cagrs, base_year, start_year, end_year):
    inflation_df = df.loc[df[YEAR_COLUMN] > start_year].copy()
    last_row = df.loc[df[YEAR_COLUMN] == end_year].iloc[0]
    first_row = df.loc[df[YEAR_COLUMN] == start_year].iloc[0]
    closing_assumptions = _closing_assumptions(end_year)

    return {
        "periodo": {"inicio": int(start_year), "fin": int(end_year), "base": int(base_year)},
        "supuestos_cierre": {
            "inflacion": closing_assumptions["inflacion"],
            "tasa_banxico": "ultima tasa de referencia publicada disponible",
            "nota_interpretacion": closing_assumptions["nota_interpretacion"],
        },
        "secciones": [
            {
                "section_id": "poder_adquisitivo",
                "nombre": "Evolucion del Poder Adquisitivo: Salario vs. UMA",
                "salario_real_inicial": float(first_row[REAL_MINIMUM_WAGE_COLUMN]),
                "salario_real_inicial_texto": _fmt_number(first_row[REAL_MINIMUM_WAGE_COLUMN]),
                "salario_real_final": float(last_row[REAL_MINIMUM_WAGE_COLUMN]),
                "salario_real_final_texto": _fmt_number(last_row[REAL_MINIMUM_WAGE_COLUMN]),
                "uma_real_inicial": float(first_row[REAL_UMA_COLUMN]),
                "uma_real_inicial_texto": _fmt_number(first_row[REAL_UMA_COLUMN]),
                "uma_real_final": float(last_row[REAL_UMA_COLUMN]),
                "uma_real_final_texto": _fmt_number(last_row[REAL_UMA_COLUMN]),
                "brecha_salario_uma_real_final": float(last_row[REAL_MINIMUM_WAGE_COLUMN] - last_row[REAL_UMA_COLUMN]),
                "brecha_salario_uma_real_final_texto": _fmt_number(
                    last_row[REAL_MINIMUM_WAGE_COLUMN] - last_row[REAL_UMA_COLUMN]
                ),
                "crecimiento_salario_real_periodo": float(last_row[REAL_MINIMUM_WAGE_COLUMN] - first_row[REAL_MINIMUM_WAGE_COLUMN]),
                "crecimiento_salario_real_periodo_texto": _fmt_number(
                    last_row[REAL_MINIMUM_WAGE_COLUMN] - first_row[REAL_MINIMUM_WAGE_COLUMN]
                ),
                "crecimiento_uma_real_periodo": float(last_row[REAL_UMA_COLUMN] - first_row[REAL_UMA_COLUMN]),
                "crecimiento_uma_real_periodo_texto": _fmt_number(last_row[REAL_UMA_COLUMN] - first_row[REAL_UMA_COLUMN]),
                "crecimiento_relativo_salario_real_periodo": _safe_ratio_change(
                    first_row[REAL_MINIMUM_WAGE_COLUMN],
                    last_row[REAL_MINIMUM_WAGE_COLUMN],
                ),
                "crecimiento_relativo_salario_real_periodo_texto": _fmt_percent(
                    _safe_ratio_change(first_row[REAL_MINIMUM_WAGE_COLUMN], last_row[REAL_MINIMUM_WAGE_COLUMN])
                ),
                "crecimiento_relativo_uma_real_periodo": _safe_ratio_change(
                    first_row[REAL_UMA_COLUMN],
                    last_row[REAL_UMA_COLUMN],
                ),
                "crecimiento_relativo_uma_real_periodo_texto": _fmt_percent(
                    _safe_ratio_change(first_row[REAL_UMA_COLUMN], last_row[REAL_UMA_COLUMN])
                ),
                "lectura_esperada": "Comparar salario minimo real contra UMA real sin atribuir causalidades no soportadas.",
            },
            {
                "section_id": "base_2016",
                "nombre": f"Salario Minimo vs. UMA (Base {base_year} = 100)",
                "salario_real_normalizado_final": float(last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN]),
                "salario_real_normalizado_final_texto": _fmt_number(last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN]),
                "uma_real_normalizado_final": float(last_row[NORMALIZED_REAL_UMA_COLUMN]),
                "uma_real_normalizado_final_texto": _fmt_number(last_row[NORMALIZED_REAL_UMA_COLUMN]),
                "brecha_normalizada_final": float(
                    last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN] - last_row[NORMALIZED_REAL_UMA_COLUMN]
                ),
                "brecha_normalizada_final_texto": _fmt_number(
                    last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN] - last_row[NORMALIZED_REAL_UMA_COLUMN]
                ),
                "relacion_salario_vs_uma_final": _safe_ratio(
                    last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN],
                    last_row[NORMALIZED_REAL_UMA_COLUMN],
                ),
                "relacion_salario_vs_uma_final_texto": _fmt_number(
                    _safe_ratio(last_row[NORMALIZED_REAL_MINIMUM_WAGE_COLUMN], last_row[NORMALIZED_REAL_UMA_COLUMN])
                ),
                "lectura_esperada": "Explicar la brecha indexada acumulada desde el año base.",
            },
            {
                "section_id": "cagr",
                "nombre": f"Crecimiento Anual Compuesto (CAGR {start_year}-{end_year})",
                "cagr_nominal_salario": float(cagrs["nominal_salario"]),
                "cagr_nominal_salario_texto": _fmt_percent(cagrs["nominal_salario"]),
                "cagr_real_salario": float(cagrs["real_salario"]),
                "cagr_real_salario_texto": _fmt_percent(cagrs["real_salario"]),
                "cagr_nominal_uma": float(cagrs["nominal_uma"]),
                "cagr_nominal_uma_texto": _fmt_percent(cagrs["nominal_uma"]),
                "cagr_real_uma": float(cagrs["real_uma"]),
                "cagr_real_uma_texto": _fmt_percent(cagrs["real_uma"]),
                "lectura_esperada": "Comparar ritmos promedio anuales nominales y reales.",
            },
            {
                "section_id": "inflacion_banxico",
                "nombre": "Inflacion Anual y Politica Monetaria",
                "inflacion_maxima": float(inflation_df[INFLATION_COLUMN].max()),
                "inflacion_maxima_texto": _fmt_percent(inflation_df[INFLATION_COLUMN].max()),
                "inflacion_minima": float(inflation_df[INFLATION_COLUMN].min()),
                "inflacion_minima_texto": _fmt_percent(inflation_df[INFLATION_COLUMN].min()),
                "inflacion_final": float(inflation_df[INFLATION_COLUMN].iloc[-1]),
                "inflacion_final_texto": _fmt_percent(inflation_df[INFLATION_COLUMN].iloc[-1]),
                "tasa_banxico_final": float(last_row[BANXICO_RATE_COLUMN]),
                "tasa_banxico_final_texto": _fmt_percent(last_row[BANXICO_RATE_COLUMN]),
                "diferencial_tasa_vs_inflacion_final": float(
                    last_row[BANXICO_RATE_COLUMN] - inflation_df[INFLATION_COLUMN].iloc[-1]
                ),
                "diferencial_tasa_vs_inflacion_final_texto": _fmt_one_decimal(
                    last_row[BANXICO_RATE_COLUMN] - inflation_df[INFLATION_COLUMN].iloc[-1]
                ),
                "inflacion_final_tipo": closing_assumptions["inflacion"],
                "tasa_banxico_tipo": "ultima tasa publicada disponible",
                "lectura_esperada": "Contextualizar inflacion y tasa de referencia sin asumir causalidad directa.",
            },
            {
                "section_id": "dashboard",
                "nombre": "Dashboard / Resumen Ejecutivo",
                "salario_real_final": float(last_row[REAL_MINIMUM_WAGE_COLUMN]),
                "salario_real_final_texto": _fmt_number(last_row[REAL_MINIMUM_WAGE_COLUMN]),
                "uma_real_final": float(last_row[REAL_UMA_COLUMN]),
                "uma_real_final_texto": _fmt_number(last_row[REAL_UMA_COLUMN]),
                "inflacion_final": float(inflation_df[INFLATION_COLUMN].iloc[-1]),
                "inflacion_final_texto": _fmt_percent(inflation_df[INFLATION_COLUMN].iloc[-1]),
                "tasa_banxico_final": float(last_row[BANXICO_RATE_COLUMN]),
                "tasa_banxico_final_texto": _fmt_percent(last_row[BANXICO_RATE_COLUMN]),
                "cagr_real_salario": float(cagrs["real_salario"]),
                "cagr_real_salario_texto": _fmt_percent(cagrs["real_salario"]),
                "cagr_real_uma": float(cagrs["real_uma"]),
                "cagr_real_uma_texto": _fmt_percent(cagrs["real_uma"]),
                "diferencial_tasa_vs_inflacion_final": float(
                    last_row[BANXICO_RATE_COLUMN] - inflation_df[INFLATION_COLUMN].iloc[-1]
                ),
                "diferencial_tasa_vs_inflacion_final_texto": _fmt_one_decimal(
                    last_row[BANXICO_RATE_COLUMN] - inflation_df[INFLATION_COLUMN].iloc[-1]
                ),
                "lectura_esperada": "Sintetizar las señales principales del periodo.",
            },
        ],
    }


def request_ai_insights(payload, api_key, model):
    prompt = load_system_prompt()
    request_body = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(request_body).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Fallo la llamada a OpenAI: {exc}") from exc

    return response_payload["choices"][0]["message"]["content"]


def load_system_prompt(prompt_path=SYSTEM_PROMPT_PATH, forbidden_terms=None):
    if forbidden_terms is None:
        forbidden_terms = FORBIDDEN_EDITORIAL_TERMS
    template = Path(prompt_path).read_text(encoding="utf-8")
    return template.format(forbidden_terms=", ".join(forbidden_terms))


def parse_ai_insights(raw_response, fallback_insights=None, payload=None):
    parsed = json.loads(raw_response)
    insights = parsed.get("insights")
    if not isinstance(insights, list):
        raise ValueError("La respuesta no contiene una lista de insights.")
    if len(insights) != len(SECTION_IDS):
        raise ValueError("La respuesta no contiene exactamente 5 insights.")

    by_section = {insight.get("section_id"): insight for insight in insights}
    if set(by_section) != set(SECTION_IDS):
        raise ValueError("La respuesta no contiene los section_id esperados.")

    if fallback_insights is None:
        fallback_insights = get_fallback_insights()

    fallback_by_section = {
        insight["section_id"]: insight for insight in fallback_insights
    }
    normalized = []
    for section_id in SECTION_IDS:
        insight = by_section[section_id]
        fallback = fallback_by_section[section_id]
        normalized.append(
            {
                "section_id": section_id,
                "titulo": _text_or_fallback(insight, fallback, "titulo", section_id, payload),
                "comentario": _text_or_fallback(insight, fallback, "comentario", section_id, payload),
                "implicacion": _text_or_fallback(insight, fallback, "implicacion", section_id, payload),
            }
        )
    return normalized


def _text_or_fallback(insight, fallback, key, section_id=None, payload=None):
    value = insight.get(key)
    if not isinstance(value, str) or not value.strip():
        return fallback[key]
    value = value.strip()
    if not _is_valid_generated_text(value, key, section_id, payload):
        return fallback[key]
    return value


def _build_dynamic_fallback_insights(payload):
    sections = {section["section_id"]: section for section in payload["secciones"]}
    periodo = payload["periodo"]

    poder = sections["poder_adquisitivo"]
    base = sections["base_2016"]
    cagr = sections["cagr"]
    inflacion = sections["inflacion_banxico"]
    dashboard = sections["dashboard"]

    salary_real_label = _relative_performance_label(
        poder["crecimiento_relativo_salario_real_periodo"],
        poder["crecimiento_relativo_uma_real_periodo"],
        "salario minimo",
        "UMA",
    )
    indexed_label = _relative_performance_label(
        base["salario_real_normalizado_final"],
        base["uma_real_normalizado_final"],
        "salario minimo",
        "UMA",
    )
    cagr_label = _relative_performance_label(
        cagr["cagr_real_salario"],
        cagr["cagr_real_uma"],
        "salario minimo",
        "UMA",
    )
    financial_label = _financial_condition_label(inflacion["diferencial_tasa_vs_inflacion_final"])

    return [
        {
            "section_id": "poder_adquisitivo",
            "titulo": "Brecha real salario-UMA",
            "comentario": (
                f"Entre {periodo['inicio']} y {periodo['fin']}, el salario real paso de "
                f"{_fmt_number(poder['salario_real_inicial'])} a {_fmt_number(poder['salario_real_final'])}, "
                f"mientras la UMA real cerro en {_fmt_number(poder['uma_real_final'])}. "
                f"La brecha real final fue de {_fmt_number(poder['brecha_salario_uma_real_final'])} pesos."
            ),
            "implicacion": f"La comparacion real muestra {salary_real_label}.",
        },
        {
            "section_id": "base_2016",
            "titulo": "Divergencia indexada desde la base",
            "comentario": (
                f"Con base {periodo['base']} igual a 100, el salario real normalizado cerro en "
                f"{_fmt_number(base['salario_real_normalizado_final'])} y la UMA real normalizada en "
                f"{_fmt_number(base['uma_real_normalizado_final'])}. "
                f"La relacion final salario/UMA fue de {_fmt_number(base['relacion_salario_vs_uma_final'])} veces."
            ),
            "implicacion": f"La brecha indexada confirma {indexed_label} desde la base comun.",
        },
        {
            "section_id": "cagr",
            "titulo": "Ritmos compuestos comparables",
            "comentario": (
                f"El salario minimo crecio a una tasa compuesta anual de {_fmt_percent(cagr['cagr_nominal_salario'])} nominal y "
                f"{_fmt_percent(cagr['cagr_real_salario'])} real, frente a {_fmt_percent(cagr['cagr_nominal_uma'])} nominal y "
                f"{_fmt_percent(cagr['cagr_real_uma'])} real de la UMA. "
                f"La comparacion real indica {cagr_label}."
            ),
            "implicacion": f"El diferencial de CAGRs resume {cagr_label} en el periodo.",
        },
        {
            "section_id": "inflacion_banxico",
            "titulo": "Inflacion estimada y tasa disponible",
            "comentario": (
                f"La inflacion de cierre {periodo['fin']} es {_fmt_percent(inflacion['inflacion_final'])} "
                f"({inflacion['inflacion_final_tipo']}), mientras que la tasa de referencia corresponde "
                f"a la ultima publicada disponible, en {_fmt_percent(inflacion['tasa_banxico_final'])}. "
                f"El diferencial de {_fmt_one_decimal(inflacion['diferencial_tasa_vs_inflacion_final'])} puntos porcentuales mantiene una postura restrictiva en terminos reales."
            ),
            "implicacion": f"{financial_label}.",
        },
        {
            "section_id": "dashboard",
            "titulo": "Lectura ejecutiva integrada",
            "comentario": (
                f"El tablero integra salario real de {_fmt_number(dashboard['salario_real_final'])}, UMA real de "
                f"{_fmt_number(dashboard['uma_real_final'])}, inflacion de {_fmt_percent(dashboard['inflacion_final'])} "
                f"y tasa Banxico de {_fmt_percent(dashboard['tasa_banxico_final'])}. "
                f"La CAGR real del salario minimo fue {_fmt_percent(dashboard['cagr_real_salario'])}, frente a {_fmt_percent(dashboard['cagr_real_uma'])} de la UMA."
            ),
            "implicacion": f"La lectura conjunta combina {cagr_label} con {_financial_condition_fragment(dashboard['diferencial_tasa_vs_inflacion_final'])}.",
        },
    ]


def _closing_assumptions(end_year):
    if int(end_year) == 2026:
        return {
            "inflacion": "estimado Banxico diciembre 2026",
            "nota_interpretacion": "No tratar 2026 como cierre observado definitivo si corresponde a estimacion.",
        }
    return {
        "inflacion": f"dato de cierre {int(end_year)}",
        "nota_interpretacion": "Tratar el cierre como dato observado si la fuente de entrada ya esta consolidada.",
    }


def _is_valid_generated_text(text, key, section_id=None, payload=None):
    if _contains_forbidden_editorial_term(text):
        return False
    if _contains_unsupported_inference(text, payload):
        return False
    if key == "comentario" and _sentence_count(text) > 2:
        return False
    if key == "implicacion" and _sentence_count(text) > 1:
        return False
    if key == "comentario" and payload and _section_has_numeric_values(payload, section_id) and not _contains_digit(text):
        return False
    if key == "comentario" and section_id == "cagr" and payload and _count_percent_values(text) < 4:
        return False
    return True


def _contains_unsupported_inference(text, payload=None):
    lowered = text.lower()
    for term in UNSUPPORTED_INFERENCE_TERMS:
        if term not in lowered:
            continue
        if payload and _payload_contains_key_fragment(payload, term):
            continue
        return True
    return False


def _section_has_numeric_values(payload, section_id):
    section = _payload_section(payload, section_id)
    return any(isinstance(value, (int, float)) for value in section.values())


def _payload_section(payload, section_id):
    if not payload or not section_id:
        return {}
    for section in payload.get("secciones", []):
        if section.get("section_id") == section_id:
            return section
    return {}


def _payload_contains_key_fragment(payload, fragment):
    fragment = fragment.lower()
    for section in payload.get("secciones", []):
        if any(fragment in str(key).lower() for key in section):
            return True
    return False


def _sentence_count(text):
    parts = re.split(r"(?<!\d)[.!?]+(?:\s+|$)", text.strip())
    return len([part for part in parts if part.strip()])


def _contains_digit(text):
    return bool(re.search(r"\d", text))


def _count_percent_values(text):
    return len(re.findall(r"\d+(?:[.,]\d+)?\s*%", text))


def _relative_performance_label(left_value, right_value, left_label, right_label):
    if left_value is None or right_value is None:
        return f"una comparacion no concluyente entre {left_label} y {right_label}"
    left_value = float(left_value)
    right_value = float(right_value)
    if left_value > right_value:
        return f"mejor desempeno real del {left_label} frente a la {right_label}"
    if left_value < right_value:
        return f"menor desempeno real del {left_label} frente a la {right_label}"
    return f"desempeno real similar entre {left_label} y {right_label}"


def _financial_condition_label(differential):
    if differential is None:
        return "La comparacion entre tasa e inflacion no permite calificar las condiciones financieras"
    differential = float(differential)
    if differential > 0:
        return "El diferencial positivo mantiene presion sobre costo financiero, credito y consumo financiado"
    if differential < 0:
        return "El diferencial negativo reduce la restriccion real asociada al costo financiero"
    return "El diferencial nulo deja una lectura neutral entre tasa de referencia e inflacion"


def _financial_condition_fragment(differential):
    if differential is None:
        return "una lectura financiera no concluyente"
    differential = float(differential)
    if differential > 0:
        return "presion sobre costo financiero, credito y consumo financiado"
    if differential < 0:
        return "menor restriccion real asociada al costo financiero"
    return "una lectura neutral entre tasa de referencia e inflacion"


def _safe_ratio(numerator, denominator):
    denominator = float(denominator)
    if denominator == 0:
        return None
    return float(numerator) / denominator


def _safe_ratio_change(start_value, end_value):
    start_value = float(start_value)
    if start_value == 0:
        return None
    return (float(end_value) / start_value) - 1


def _fmt_number(value):
    if value is None:
        return "n/d"
    return f"{float(value):.2f}"


def _fmt_compact_number(value):
    if value is None:
        return "n/d"
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text


def _fmt_one_decimal(value):
    if value is None:
        return "n/d"
    return f"{float(value):.1f}"


def _fmt_percent(value):
    if value is None:
        return "n/d"
    value = float(value)
    if -0.1 < value < 0:
        text = f"{value:.2f}%"
        return "0.00%" if text == "-0.00%" else text
    if abs(value) <= 1:
        value *= 100
    text = f"{value:.2f}%"
    return "0.00%" if text == "-0.00%" else text

def _contains_forbidden_editorial_term(text):
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_EDITORIAL_TERMS)
