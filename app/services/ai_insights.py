import json
import logging
import urllib.error
import urllib.request


logger = logging.getLogger(__name__)

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
        return parse_ai_insights(raw_response, get_fallback_insights(payload))
    except Exception as exc:
        logger.warning("No se pudieron generar insights con IA; se usara fallback. Error: %s", exc)
        return get_fallback_insights(payload)


def build_insight_payload(df, cagrs, base_year, start_year, end_year):
    inflation_df = df.loc[df["Año"] > start_year].copy()
    last_row = df.loc[df["Año"] == end_year].iloc[0]
    first_row = df.loc[df["Año"] == start_year].iloc[0]

    return {
        "periodo": {"inicio": int(start_year), "fin": int(end_year), "base": int(base_year)},
        "supuestos_2026": {
            "inflacion_2026": "estimado de Banxico al mes de diciembre",
            "tasa_banxico": "ultima tasa de referencia publicada disponible",
            "nota_interpretacion": "No tratar 2026 como cierre observado definitivo si corresponde a estimacion.",
        },
        "secciones": [
            {
                "section_id": "poder_adquisitivo",
                "nombre": "Evolucion del Poder Adquisitivo: Salario vs. UMA",
                "salario_real_inicial": float(first_row["Salario_Minimo_Real"]),
                "salario_real_final": float(last_row["Salario_Minimo_Real"]),
                "uma_real_inicial": float(first_row["UMA_Real"]),
                "uma_real_final": float(last_row["UMA_Real"]),
                "brecha_salario_uma_real_final": float(last_row["Salario_Minimo_Real"] - last_row["UMA_Real"]),
                "crecimiento_salario_real_periodo": float(last_row["Salario_Minimo_Real"] - first_row["Salario_Minimo_Real"]),
                "crecimiento_uma_real_periodo": float(last_row["UMA_Real"] - first_row["UMA_Real"]),
                "crecimiento_relativo_salario_real_periodo": _safe_ratio_change(
                    first_row["Salario_Minimo_Real"],
                    last_row["Salario_Minimo_Real"],
                ),
                "crecimiento_relativo_uma_real_periodo": _safe_ratio_change(
                    first_row["UMA_Real"],
                    last_row["UMA_Real"],
                ),
                "lectura_esperada": "Comparar salario minimo real contra UMA real sin atribuir causalidades no soportadas.",
            },
            {
                "section_id": "base_2016",
                "nombre": f"Salario Minimo vs. UMA (Base {base_year} = 100)",
                "salario_real_normalizado_final": float(last_row["Salario_Minimo_Real_Normalizado"]),
                "uma_real_normalizado_final": float(last_row["UMA_Real_Normalizado"]),
                "brecha_normalizada_final": float(
                    last_row["Salario_Minimo_Real_Normalizado"] - last_row["UMA_Real_Normalizado"]
                ),
                "relacion_salario_vs_uma_final": _safe_ratio(
                    last_row["Salario_Minimo_Real_Normalizado"],
                    last_row["UMA_Real_Normalizado"],
                ),
                "lectura_esperada": "Explicar la brecha indexada acumulada desde el año base.",
            },
            {
                "section_id": "cagr",
                "nombre": f"Crecimiento Anual Compuesto (CAGR {start_year}-{end_year})",
                "cagr_nominal_salario": float(cagrs["nominal_salario"]),
                "cagr_real_salario": float(cagrs["real_salario"]),
                "cagr_nominal_uma": float(cagrs["nominal_uma"]),
                "cagr_real_uma": float(cagrs["real_uma"]),
                "lectura_esperada": "Comparar ritmos promedio anuales nominales y reales.",
            },
            {
                "section_id": "inflacion_banxico",
                "nombre": "Inflacion Anual y Politica Monetaria",
                "inflacion_maxima": float(inflation_df["inflacion"].max()),
                "inflacion_minima": float(inflation_df["inflacion"].min()),
                "inflacion_final": float(inflation_df["inflacion"].iloc[-1]),
                "tasa_banxico_final": float(last_row["Tasa_Referencia_Banxico"]),
                "diferencial_tasa_vs_inflacion_final": float(
                    last_row["Tasa_Referencia_Banxico"] - inflation_df["inflacion"].iloc[-1]
                ),
                "inflacion_final_tipo": "estimado Banxico diciembre 2026",
                "tasa_banxico_tipo": "ultima tasa publicada disponible",
                "lectura_esperada": "Contextualizar inflacion y tasa de referencia sin asumir causalidad directa.",
            },
            {
                "section_id": "dashboard",
                "nombre": "Dashboard / Resumen Ejecutivo",
                "salario_real_final": float(last_row["Salario_Minimo_Real"]),
                "uma_real_final": float(last_row["UMA_Real"]),
                "inflacion_final": float(inflation_df["inflacion"].iloc[-1]),
                "tasa_banxico_final": float(last_row["Tasa_Referencia_Banxico"]),
                "cagr_real_salario": float(cagrs["real_salario"]),
                "cagr_real_uma": float(cagrs["real_uma"]),
                "diferencial_tasa_vs_inflacion_final": float(
                    last_row["Tasa_Referencia_Banxico"] - inflation_df["inflacion"].iloc[-1]
                ),
                "lectura_esperada": "Sintetizar las señales principales del periodo.",
            },
        ],
    }


def request_ai_insights(payload, api_key, model):
    prompt = (
        "Genera comentarios ejecutivos breves en JSON estricto. "
        "Usa exclusivamente los datos estructurados enviados por el usuario; no analices imagenes. "
        "No inventes causalidades. "
        "No uses lenguaje alarmista. "
        "No menciones IA dentro del texto generado. "
        "No uses frases debiles o ambiguas como puede impulsar, puede favorecer, puede influir, posible presion, sugiere o inflacion controlada. "
        "Cada comentario debe tener maximo 2 oraciones y cada implicacion maximo 1 oracion. "
        "Cuando la seccion incluya datos numericos, el comentario debe mencionar al menos un dato concreto. "
        "Evita frases genericas o tibias como: esto sugiere, puede influir, estos datos sintetizan, "
        "la grafica muestra, se observa, principales señales economicas, decisiones economicas o equivalentes. "
        "Las implicaciones deben aterrizar una consecuencia economica concreta: poder adquisitivo, brecha relativa, "
        "presion sobre credito, consumo financiado, inversion, costo financiero o lectura ejecutiva del periodo. "
        "Para salario y UMA, enfatiza brecha, divergencia real, poder adquisitivo y diferencia entre avance nominal y avance real. "
        "Para CAGR, compara explicitamente salario nominal, salario real, UMA nominal y UMA real usando porcentajes. "
        "Para inflacion y Banxico, contrasta inflacion final contra tasa final sin afirmar causalidad directa. "
        "Para el cierre de 2026, considera que la inflacion corresponde al estimado de Banxico al mes de diciembre. "
        "La tasa de referencia de Banco de Mexico debe interpretarse como la ultima tasa publicada disponible. "
        "No presentes el cierre de 2026 como dato definitivo observado cuando corresponda a estimacion. "
        "Si salario real crece mas que UMA real, no uses deterioro, impacto negativo ni desigualdad. "
        "Para poder_adquisitivo y base_2016, interpreta la brecha como recuperacion o fortalecimiento relativo del salario minimo frente a la UMA. "
        "Para CAGR, si cagr_real_salario es mayor que cagr_real_uma, la implicacion debe indicar mejor desempeno real del salario minimo frente a la UMA. "
        "No uses desigualdad salvo que el payload incluya una metrica de distribucion social; este reporte no la incluye. "
        "No uses podria influir. "
        "No uses sugiere cuando la relacion este directamente soportada por los datos. "
        "No uses decisiones de politica monetaria como implicacion si no se modela la reaccion de Banxico. "
        "Para Banxico, usa ultima tasa publicada disponible. "
        "Para inflacion 2026, usa estimado Banxico a diciembre. "
        "Las implicaciones deben ser concretas y no deben contradecir el signo de los datos. "
        "El texto debe sonar como comentario ejecutivo de analisis economico, no como descripcion generica de grafica. "
        "Devuelve exactamente este objeto: "
        '{"insights":[{"section_id":"poder_adquisitivo","titulo":"","comentario":"","implicacion":""},'
        '{"section_id":"base_2016","titulo":"","comentario":"","implicacion":""},'
        '{"section_id":"cagr","titulo":"","comentario":"","implicacion":""},'
        '{"section_id":"inflacion_banxico","titulo":"","comentario":"","implicacion":""},'
        '{"section_id":"dashboard","titulo":"","comentario":"","implicacion":""}]}'
    )
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


def parse_ai_insights(raw_response, fallback_insights=None):
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
                "titulo": _text_or_fallback(insight, fallback, "titulo"),
                "comentario": _text_or_fallback(insight, fallback, "comentario"),
                "implicacion": _text_or_fallback(insight, fallback, "implicacion"),
            }
        )
    return normalized


def _text_or_fallback(insight, fallback, key):
    value = insight.get(key)
    if not isinstance(value, str) or not value.strip():
        return fallback[key]
    if _contains_forbidden_editorial_term(value):
        return fallback[key]
    return value.strip()


def _build_dynamic_fallback_insights(payload):
    sections = {section["section_id"]: section for section in payload["secciones"]}
    periodo = payload["periodo"]

    poder = sections["poder_adquisitivo"]
    base = sections["base_2016"]
    cagr = sections["cagr"]
    inflacion = sections["inflacion_banxico"]
    dashboard = sections["dashboard"]

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
            "implicacion": "La mejora relativa del salario minimo fortalece la capacidad de compra medida contra la UMA.",
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
            "implicacion": "La brecha indexada confirma un fortalecimiento relativo del salario minimo frente a la UMA.",
        },
        {
            "section_id": "cagr",
            "titulo": "Ritmos compuestos comparables",
            "comentario": (
                f"El salario minimo crecio a una tasa compuesta anual de {_fmt_percent(cagr['cagr_nominal_salario'])} nominal y "
                f"{_fmt_percent(cagr['cagr_real_salario'])} real, frente a {_fmt_percent(cagr['cagr_nominal_uma'])} nominal y "
                f"{_fmt_percent(cagr['cagr_real_uma'])} real de la UMA. "
                "La comparacion confirma un desempeno superior del salario minimo tanto en terminos nominales como reales."
            ),
            "implicacion": "El diferencial de CAGRs refuerza la recuperacion salarial real frente a una UMA practicamente estancada.",
        },
        {
            "section_id": "inflacion_banxico",
            "titulo": "Inflacion estimada y tasa disponible",
            "comentario": (
                f"La inflacion de cierre {periodo['fin']} se estima en {_fmt_number(inflacion['inflacion_final'])}% "
                "con base en Banxico al mes de diciembre, mientras que la tasa de referencia corresponde "
                f"a la ultima publicada disponible, en {_fmt_compact_number(inflacion['tasa_banxico_final'])}%. "
                f"El diferencial de {_fmt_one_decimal(inflacion['diferencial_tasa_vs_inflacion_final'])} puntos porcentuales mantiene una postura restrictiva en terminos reales."
            ),
            "implicacion": "El entorno conserva presion sobre costo financiero, credito y consumo financiado.",
        },
        {
            "section_id": "dashboard",
            "titulo": "Lectura ejecutiva integrada",
            "comentario": (
                f"El tablero resume una mejora del salario real frente a la UMA, inflacion estimada de {_fmt_number(dashboard['inflacion_final'])}% "
                f"y tasa Banxico de {_fmt_compact_number(dashboard['tasa_banxico_final'])}% como ultimo dato publicado disponible. "
                f"La CAGR real del salario minimo de {_fmt_percent(dashboard['cagr_real_salario'])} contrasta con una UMA real practicamente sin crecimiento."
            ),
            "implicacion": "La lectura conjunta apunta a recuperacion salarial real con condiciones financieras todavia restrictivas.",
        },
    ]


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
        return f"{value:.2f}%"
    if abs(value) <= 1:
        value *= 100
    return f"{value:.2f}%"

def _contains_forbidden_editorial_term(text):
    lowered = text.lower()
    return any(term in lowered for term in FORBIDDEN_EDITORIAL_TERMS)
