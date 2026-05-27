# Indicadores Economicos

Proyecto en Python para generar un reporte economico ejecutivo a partir de indicadores como INPC, salario minimo, UMA y tasa de referencia de Banxico.

Actualmente el proyecto funciona como un pipeline local: carga datos desde Google Sheets, limpia la informacion, calcula metricas financieras, genera graficas, construye un PDF y opcionalmente lo envia por correo usando SMTP de Gmail.

## Foto actual del proyecto

```text
indicadores/
  .env                         # Variables locales, no versionar secretos
  .env.example                 # Plantilla de configuracion
  .gitignore
  README.md
  plan_migracion_modular.md    # Mapa de avance para escalar la app
  reporte_economico.py         # Script principal actual
  Reporte_Economico_Ejecutivo.pdf
  requirements.txt
  test_reporte_economico.py    # Pruebas unitarias
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
6. Crea un PDF ejecutivo con `fpdf`.
7. Si existe `APP_PASSWORD`, envia el PDF por correo usando Gmail SMTP.

## Requisitos

- Python 3.10 o superior recomendado.
- Cuenta de Gmail con App Password si se desea enviar correo.
- Acceso al Google Sheet configurado en `.env`.

Dependencias actuales:

```text
pandas
matplotlib
fpdf
python-dotenv
pytest
```

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

Notas:

- `APP_PASSWORD` debe ser una App Password de Google, no la contrasena normal de Gmail.
- `SENDER_EMAIL` debe coincidir con la cuenta donde se genero la App Password.
- Si `APP_PASSWORD` no existe, el reporte se genera localmente pero no se envia por correo.

## Ejecucion

Ejecutar el pipeline completo:

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

Estado actual verificado:

```text
13 passed
```

## Archivos principales

### `reporte_economico.py`

Contiene el pipeline completo actual:

- `get_sheet_csv_url`
- `load_and_clean_data`
- `calculate_cagr`
- `calculate_financial_metrics`
- `generate_visualizations`
- `PDFReport`
- `create_pdf_report`
- `send_report_email`
- `execute_economic_pipeline`

### `test_reporte_economico.py`

Contiene pruebas unitarias del comportamiento actual. Las pruebas de correo usan mocks, por lo que no se conectan realmente a Gmail.

### `plan_migracion_modular.md`

Mapa de trabajo para evolucionar el proyecto hacia una aplicacion modular con API, BigQuery y frontend.

## Estado de arquitectura

El proyecto se encuentra en una etapa inicial funcional. El codigo principal todavia esta concentrado en un solo archivo, lo cual es adecuado para prototipo, pero el siguiente paso recomendado es modularizar.

Proxima estructura objetivo:

```text
app/
  config.py
  data_sources/
    google_sheets.py
    bigquery.py
  services/
    metrics.py
    visualizations.py
    pdf_report.py
    email_sender.py
    pipeline.py
  models/
    report_request.py
main.py
tests/
```

## Evolucion prevista

La evolucion planeada esta documentada en `plan_migracion_modular.md`.

Resumen de etapas:

1. Modularizar sin cambiar comportamiento.
2. Definir modelos internos como `ReportRequest` y `ReportResult`.
3. Crear API backend con FastAPI.
4. Migrar fuente de datos a BigQuery.
5. Crear frontend para capturar correo receptor y periodo.
6. Ejecutar reportes de forma asincrona.
7. Guardar auditoria y archivos generados.
8. Desplegar en Cloud Run u otra plataforma.

## Consideraciones de seguridad

- No subir `.env` con credenciales reales.
- No incluir App Passwords en commits.
- Evaluar un proveedor transaccional de correo para produccion.
- Usar Secret Manager o equivalente si se despliega en la nube.

## Siguiente paso recomendado

Iniciar la Etapa 1 del plan: separar el script actual en modulos sin cambiar comportamiento, empezando por:

1. `metrics.py`
2. `email_sender.py`
3. `google_sheets.py`
4. `pipeline.py`
