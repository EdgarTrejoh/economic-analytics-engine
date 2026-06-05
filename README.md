# Indicadores Economicos

Proyecto en Python para generar un reporte economico ejecutivo a partir de indicadores como INPC, salario minimo, UMA y tasa de referencia de Banxico.

Actualmente funciona como un pipeline local modular: carga datos desde Google Sheets, limpia la informacion, calcula metricas financieras, genera graficas, construye un PDF con lecturas ejecutivas por seccion, agrega una nota metodologica externa y opcionalmente envia el reporte por correo usando SMTP de Gmail.

## Foto actual del proyecto

```text
indicadores/
  app/
    __init__.py
    config.py
    data_sources/
      __init__.py
      google_sheets.py
    models/
      __init__.py
    services/
      __init__.py
      ai_insights.py
      email_sender.py
      metrics.py
      pdf_report.py
      pipeline.py
      visualizations.py
  input/
    nota_metodologica.txt
  tests/
    __init__.py
    conftest.py
    test_ai_insights.py
    test_email_sender.py
    test_google_sheets.py
    test_metrics.py
    test_pdf_report.py
    test_pipeline.py
    test_reporte_economico.py
    test_visualizations.py
  .env
  .env.example
  .gitignore
  main.py
  README.md
  plan_migracion_modular.md
  reporte_economico.py
  Reporte_Economico_Ejecutivo.pdf
  requirements.txt
```

Tambien pueden existir carpetas generadas localmente como:

```text
.venv/
.pytest_cache/
__pycache__/
```

## Flujo actual

1. Lee configuracion desde `.env`.
2. Convierte una URL de Google Sheets a una URL de exportacion CSV.
3. Carga y limpia los datos con `pandas`.
4. Calcula metricas financieras:
   - Inflacion anual.
   - Indice de precios.
   - Salario minimo real.
   - UMA real.
   - CAGR nominal y real.
5. Genera visualizaciones con `matplotlib`.
6. Genera comentarios ejecutivos para las 5 secciones del PDF.
7. Crea el PDF ejecutivo con `fpdf`.
8. Agrega una hoja final con la nota metodologica desde `input/nota_metodologica.txt`.
9. Si existe `APP_PASSWORD`, envia el PDF por correo usando Gmail SMTP.

## Insights ejecutivos

El modulo `app/services/ai_insights.py` genera los textos ejecutivos que aparecen debajo de cada grafica del PDF.

Las secciones cubiertas son:

1. Evolucion del Poder Adquisitivo: Salario vs. UMA.
2. Salario Minimo vs. UMA con base 2016.
3. Crecimiento Anual Compuesto.
4. Inflacion Anual y Politica Monetaria.
5. Dashboard / Resumen Ejecutivo.

La IA no analiza imagenes. Recibe datos estructurados calculados por el pipeline, como periodo, valores iniciales/finales, maximos, minimos, variaciones y CAGR.

Si `AI_INSIGHTS_ENABLED` esta activo y existe `OPENAI_API_KEY`, el pipeline solicita una sola respuesta JSON para las 5 secciones. Si IA esta desactivada, no hay API key o la respuesta falla, usa fallback local.

Los textos generados se filtran para evitar lenguaje debil o ambiguo como:

- `puede impulsar`
- `puede favorecer`
- `puede influir`
- `puede afectar`
- `posible presion`
- `sugiere`
- `inflacion controlada`

Si un campo generado por IA contiene alguna frase bloqueada, se reemplaza por fallback ejecutivo.

## Nota metodologica

El PDF lee una nota externa desde:

```text
input/nota_metodologica.txt
```

Esa nota se agrega como hoja final con el titulo:

```text
Notas metodologicas y supuestos de cierre 2026
```

Si el archivo no existe, el PDF se sigue generando y el pipeline registra un warning.

## Requisitos

- Python 3.10 o superior recomendado.
- Cuenta de Gmail con App Password si se desea enviar correo.
- Acceso al Google Sheet configurado en `.env`.
- API key de OpenAI solo si se desea activar insights con IA.

Dependencias actuales:

```text
pandas
matplotlib
fpdf
python-dotenv
pytest
```

La integracion con OpenAI usa HTTP estandar de Python, por lo que no requiere dependencia adicional.

## Instalacion

Crear y activar entorno virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Configuracion

Crear un archivo `.env` tomando como base `.env.example`:

```env
APP_PASSWORD=tu_contrasena_de_aplicacion_aqui
SHEET_URL=https://docs.google.com/spreadsheets/d/ID_DEL_DOCUMENTO/edit?usp=sharing
SENDER_EMAIL=tu_correo@gmail.com
RECIPIENT_EMAIL=destinatario@correo.com
```

Configuracion opcional para insights con IA:

```env
AI_INSIGHTS_ENABLED=true
OPENAI_API_KEY=tu_api_key_de_openai
OPENAI_MODEL=gpt-4o-mini
```

Notas:

- `APP_PASSWORD` debe ser una App Password de Google, no la contrasena normal de Gmail.
- `SENDER_EMAIL` debe coincidir con la cuenta donde se genero la App Password.
- Si `APP_PASSWORD` no existe, el reporte se genera localmente pero no se envia por correo.
- Si `AI_INSIGHTS_ENABLED` no esta activo o falta `OPENAI_API_KEY`, se usan comentarios fallback.
- Por seguridad, `.env.example` deja `AI_INSIGHTS_ENABLED=false`.
- No subir `.env` con credenciales reales.

## Ejecucion

Ejecutar el pipeline completo desde el punto de entrada principal:

```powershell
python main.py
```

Tambien se conserva compatibilidad con la ejecucion anterior:

```powershell
python reporte_economico.py
```

Salida esperada:

```text
Reporte_Economico_Ejecutivo.pdf
```

## Pruebas

Ejecutar la suite:

```powershell
python -m pytest -q
```

Cobertura actual de pruebas:

- Calculo de CAGR.
- Calculos financieros principales.
- Flujo SMTP sin conexion real a Gmail.
- Manejo de PDF adjunto inexistente.
- Manejo de error de autenticacion SMTP.
- Construccion de URL CSV desde Google Sheets.
- Carga y limpieza de datos.
- Error de lectura de datos.
- Columnas requeridas faltantes.
- Fachada legacy `reporte_economico.py`.
- Orquestacion del pipeline.
- Generacion de PDF con bloques `Lectura ejecutiva` e `Implicacion`.
- Nota metodologica en PDF desde `input/nota_metodologica.txt`.
- Generacion del PDF aunque falte la nota metodologica.
- Fallback de insights cuando no hay API key.
- Parseo de JSON esperado de IA.
- Fallback cuando la IA responde mal.
- Validacion de exactamente 5 insights.
- Filtros editoriales contra lenguaje debil o ambiguo en insights.
- Visualizacion de inflacion sin mostrar el ano base 2016.
- Layout compacto de lecturas ejecutivas para evitar cortes de texto.

Estado actual verificado:

```text
34 passed
```

## Archivos principales

### `main.py`

Punto de entrada principal del pipeline modular. Usa `app.services.pipeline.run_pipeline`.

### `reporte_economico.py`

Fachada de compatibilidad. Reexporta funciones publicas para no romper imports o ejecuciones anteriores.

### `app/config.py`

Carga configuracion desde `.env`, incluyendo correo, Google Sheets e insights opcionales con IA.

### `app/data_sources/google_sheets.py`

Contiene la construccion de URL CSV y la carga/limpieza de datos desde Google Sheets.

### `app/services/metrics.py`

Contiene los calculos financieros principales. Mantiene `fillna(0)` en inflacion por compatibilidad interna.

### `app/services/visualizations.py`

Contiene la generacion de graficas. La visualizacion de inflacion usa una copia filtrada para iniciar despues del ano base y no mostrar el 0% artificial de 2016.

### `app/services/ai_insights.py`

Prepara datos estructurados, solicita una sola respuesta JSON para las 5 secciones cuando IA esta habilitada, filtra lenguaje editorial debil y devuelve fallback si algo falla.

### `app/services/pdf_report.py`

Contiene la clase `PDFReport`, la generacion del PDF con bloques de `Lectura ejecutiva` e `Implicacion`, y la hoja final de nota metodologica.

### `app/services/email_sender.py`

Contiene el envio SMTP.

### `app/services/pipeline.py`

Orquesta el flujo completo: datos, metricas, insights, visualizaciones, PDF, nota metodologica y correo.

### `input/nota_metodologica.txt`

Contiene las notas metodologicas y supuestos de cierre 2026 que se agregan al final del PDF.

### `tests/`

Contiene pruebas unitarias por modulo y una prueba minima de compatibilidad legacy.

### `plan_migracion_modular.md`

Mapa de trabajo para evolucionar el proyecto hacia una aplicacion modular con API, BigQuery y frontend.

## Estado de arquitectura

El proyecto ya completo la Etapa 1 del plan: modularizacion sin cambio de comportamiento general. El codigo principal esta separado por responsabilidades y `reporte_economico.py` se conserva como fachada compatible.

Estructura base actual:

```text
app/
  config.py
  data_sources/
    google_sheets.py
  services/
    ai_insights.py
    metrics.py
    visualizations.py
    pdf_report.py
    email_sender.py
    pipeline.py
  models/
input/
  nota_metodologica.txt
main.py
tests/
```

## Evolucion prevista

La evolucion planeada esta documentada en `plan_migracion_modular.md`.

Resumen de etapas:

1. Modularizar sin cambiar comportamiento. Completada.
2. Definir modelos internos como `ReportRequest` y `ReportResult`.
3. Crear API backend con FastAPI.
4. Migrar fuente de datos a BigQuery.
5. Crear frontend para capturar correo receptor y periodo.
6. Ejecutar reportes de forma asincrona.
7. Guardar auditoria y archivos generados.
8. Desplegar en Cloud Run u otra plataforma.

## Consideraciones de seguridad

- No subir `.env` con credenciales reales.
- No incluir App Passwords ni API keys en commits.
- Evaluar un proveedor transaccional de correo para produccion.
- Usar Secret Manager o equivalente si se despliega en la nube.
- Mantener `AI_INSIGHTS_ENABLED=false` o sin definir si no se desea llamar a OpenAI.

## Siguiente paso recomendado

Iniciar la Etapa 2 del plan: definir contratos internos como `ReportRequest`, `ReportResult` y una interfaz de fuente de datos que permita integrar BigQuery sin acoplarlo al pipeline.
