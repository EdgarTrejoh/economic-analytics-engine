# Indicadores Economicos

Proyecto en Python para generar un reporte economico ejecutivo a partir de indicadores como INPC, salario minimo, UMA y tasa de referencia de Banxico.

Actualmente funciona como un pipeline local modular: carga datos desde Google Sheets, normaliza columnas, calcula metricas financieras, genera graficas, construye un PDF con lecturas ejecutivas por seccion, agrega una nota metodologica y opcionalmente envia el reporte por correo usando SMTP de Gmail.

## Foto actual del proyecto

```text
indicadores/
  app/
    __init__.py
    config.py
    schema.py
    data_sources/
      __init__.py
      google_sheets.py
    models/
      __init__.py
    prompts/
      ai_insights_system_v1.md
    services/
      __init__.py
      ai_insights.py
      email_sender.py
      metrics.py
      pdf_report.py
      pipeline.py
      visualizations.py
  data/
    nota_metodologica.txt
  output/
    Reporte_Economico_Ejecutivo.pdf
  tests/
    __init__.py
    conftest.py
    test_ai_insights.py
    test_email_sender.py
    test_google_sheets.py
    test_metrics.py
    test_pdf_report.py
    test_pipeline.py
    test_visualizations.py
  .env
  .env.example
  .gitignore
  app_ui.py
  main.py
  README.md
  plan_migracion_modular.md
  requirements.txt
```

Tambien pueden existir carpetas generadas localmente como:

```text
.venv/
.pytest_cache/
__pycache__/
data/
output/
```

## Flujo actual

1. Lee configuracion desde `.env`.
2. Convierte una URL de Google Sheets a una URL de exportacion CSV.
3. Carga, normaliza encabezados y limpia los datos con `pandas`.
4. Calcula metricas financieras:
   - Inflacion anual.
   - Indice de precios.
   - Salario minimo real.
   - UMA real.
   - CAGR nominal y real.
5. Genera visualizaciones con `matplotlib`.
6. Genera comentarios ejecutivos para las 5 secciones del PDF.
7. Crea el PDF ejecutivo con `fpdf`.
8. Agrega una hoja final con la nota metodologica enviada por configuracion o, si no existe, desde `data/nota_metodologica.txt`.
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

Si un campo generado por IA contiene alguna frase bloqueada o incumple validaciones editoriales basicas, se reemplaza por fallback ejecutivo.

## Nota metodologica

El PDF puede recibir la nota metodologica en memoria mediante `Settings.nota_metodologica`. Si ese campo no viene definido, lee una nota local desde:

```text
data/nota_metodologica.txt
```

Esa nota se agrega como hoja final con el titulo:

```text
Notas metodologicas y supuestos de cierre 2026
```

Si el archivo no existe, el PDF se sigue generando y el pipeline registra un warning. La interfaz Streamlit pasa la nota metodologica directamente en memoria sin escribirla en disco.

## Requisitos

- Python 3.10 o superior recomendado.
- Cuenta de Gmail con App Password si se desea enviar correo.
- Acceso al Google Sheet configurado en `.env`.
- API key de OpenAI solo si se desea activar insights con IA.

Dependencias actuales:

```text
pandas>=2.0,<3
matplotlib>=3.7,<4
fpdf>=1.7.2,<2
python-dotenv>=1.0,<2
pytest>=7.0
streamlit>=1.30
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
- `SHEET_URL` debe apuntar a una hoja accesible. Si falla la conexion a Google Sheets, el pipeline propaga un error claro para que la UI lo muestre.
- Por seguridad, `.env.example` deja `AI_INSIGHTS_ENABLED=false`.
- No subir `.env` con credenciales reales.

## Ejecucion

Ejecutar el pipeline completo desde el punto de entrada principal:

```powershell
python main.py
```

Salida esperada:

```text
output/Reporte_Economico_Ejecutivo.pdf
```

Tambien existe una interfaz temporal con Streamlit:

```powershell
streamlit run app_ui.py
```

La UI carga la nota local como valor inicial cuando existe, pero al generar el reporte la envia en memoria mediante `settings.nota_metodologica`.

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
- Normalizacion de aliases de columna de año: `Ano`, `Anio`, `Year`, `Ejercicio`.
- Error de lectura de datos.
- Error claro de conexion a Google Sheets.
- Columnas requeridas faltantes.
- Orquestacion del pipeline.
- Propagacion de errores del pipeline hacia CLI/UI.
- Generacion de PDF con bloques `Lectura ejecutiva` e `Implicacion`.
- Nota metodologica en PDF desde `data/nota_metodologica.txt`.
- Nota metodologica en PDF desde memoria.
- Generacion del PDF aunque falte la nota metodologica.
- Prompt de insights cargado desde archivo Markdown.
- Fallback de insights cuando no hay API key.
- Parseo de JSON esperado de IA.
- Fallback cuando la IA responde mal.
- Validacion de exactamente 5 insights.
- Filtros editoriales contra lenguaje debil o ambiguo en insights.
- Validaciones post-IA de cifras, longitud e inferencias no soportadas.
- Manejo de conexion SMTP fallida antes de inicializar servidor.
- Visualizacion de inflacion sin mostrar el ano base 2016.
- Layout compacto de lecturas ejecutivas para evitar cortes de texto.

Estado actual verificado:

```text
45 passed
```

## Archivos principales

### `main.py`

Punto de entrada principal del pipeline modular. Usa `app.services.pipeline.run_pipeline`.

### `app_ui.py`

Interfaz temporal en Streamlit para capturar correo destinatario, editar la nota metodologica y ejecutar el pipeline. La nota se pasa en memoria al reporte.

### `app/config.py`

Carga configuracion desde `.env`, incluyendo correo, Google Sheets, ruta de salida del reporte, nota metodologica opcional e insights opcionales con IA.

### `app/schema.py`

Centraliza los nombres internos de columnas y alias aceptados del Google Sheet. El pipeline normaliza encabezados como `Ano`, `Anio`, `Year` o `Ejercicio` hacia `Año`.

### `app/data_sources/google_sheets.py`

Contiene la construccion de URL CSV, la normalizacion de encabezados y la carga/limpieza de datos desde Google Sheets. Expone `GoogleSheetsConnectionError` para errores legibles de conexion.

### `app/services/metrics.py`

Contiene los calculos financieros principales. Mantiene `fillna(0)` en inflacion por compatibilidad interna.

### `app/services/visualizations.py`

Contiene la generacion de graficas. La visualizacion de inflacion usa una copia filtrada para iniciar despues del ano base y no mostrar el 0% artificial de 2016.

### `app/services/ai_insights.py`

Prepara datos estructurados, carga el prompt desde `app/prompts/`, solicita una sola respuesta JSON para las 5 secciones cuando IA esta habilitada, aplica validaciones post-IA, filtra lenguaje editorial debil y devuelve fallback si algo falla.

### `app/prompts/ai_insights_system_v1.md`

Contiene el prompt de sistema versionado para los insights ejecutivos.

### `app/services/pdf_report.py`

Contiene la clase `PDFReport`, la generacion del PDF con bloques de `Lectura ejecutiva` e `Implicacion`, crea la carpeta de salida cuando hace falta y agrega la hoja final de nota metodologica desde memoria o archivo.

### `app/services/email_sender.py`

Contiene el envio SMTP y cierre seguro de la conexion cuando el servidor se inicializa.

### `app/services/pipeline.py`

Orquesta el flujo completo: datos, metricas, insights, visualizaciones, PDF, nota metodologica y correo. Registra errores con traceback y los vuelve a propagar para CLI/UI.

### `data/nota_metodologica.txt`

Contiene las notas metodologicas y supuestos de cierre 2026 que se agregan al final del PDF. La carpeta `data/` esta ignorada por Git para mantener datos locales fuera del repositorio.

### `output/`

Carpeta local donde se depositan los reportes generados. Esta ignorada por Git.

### `tests/`

Contiene pruebas unitarias por modulo.

### `plan_migracion_modular.md`

Mapa de trabajo para evolucionar el proyecto hacia una aplicacion modular con API, BigQuery y frontend.

## Estado de arquitectura

El proyecto ya completo la Etapa 1 del plan: modularizacion sin cambio de comportamiento general. El codigo principal esta separado por responsabilidades y `main.py` queda como punto de entrada principal.

Estructura base actual:

```text
app/
  config.py
  schema.py
  data_sources/
    google_sheets.py
  services/
    ai_insights.py
    metrics.py
    visualizations.py
    pdf_report.py
    email_sender.py
    pipeline.py
  prompts/
    ai_insights_system_v1.md
  models/
data/
  nota_metodologica.txt
output/
  Reporte_Economico_Ejecutivo.pdf
main.py
app_ui.py
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
