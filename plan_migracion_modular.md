# Plan de migracion modular y escalamiento

## Objetivo

Evolucionar el script actual de generacion de reportes economicos hacia una aplicacion modular, escalable y preparada para consumir datos desde una API conectada a BigQuery, con una interfaz para solicitar reportes por correo y periodo.

La migracion debe hacerse por etapas para conservar el comportamiento actual, mantener pruebas automatizadas y reducir el riesgo de romper el pipeline.

## Principios de trabajo

- Migrar de forma incremental, sin reescribir todo de una sola vez.
- Mantener pruebas unitarias en cada etapa.
- Separar responsabilidades: datos, calculos, visualizaciones, PDF, correo, API y frontend.
- Preparar contratos internos antes de cambiar fuentes de datos.
- Evitar que BigQuery, SMTP o el frontend queden acoplados directamente al calculo financiero.

## Etapa 1: Modularizar sin cambiar comportamiento

### Objetivo

Separar el archivo principal actual en modulos pequenos y especializados, manteniendo el mismo resultado funcional: cargar datos, calcular metricas, generar graficas, crear PDF y enviar correo.

### Estructura sugerida

```text
indicadores/
  app/
    __init__.py
    config.py
    data_sources/
      __init__.py
      google_sheets.py
    services/
      __init__.py
      metrics.py
      visualizations.py
      pdf_report.py
      email_sender.py
      pipeline.py
    models/
      __init__.py
      report_request.py
  tests/
    test_metrics.py
    test_email_sender.py
    test_google_sheets.py
    test_pipeline.py
  main.py
  requirements.txt
  .env
```

### Entregables

- `app/services/metrics.py` con calculos financieros.
- `app/data_sources/google_sheets.py` con carga y limpieza desde Google Sheets.
- `app/services/visualizations.py` con generacion de graficas.
- `app/services/pdf_report.py` con clase y generacion de PDF.
- `app/services/email_sender.py` con envio SMTP.
- `app/services/pipeline.py` como orquestador.
- `main.py` como punto de entrada.
- Pruebas movidas a carpeta `tests/`.

### Checklist

- [x] Crear estructura de carpetas.
- [x] Mover calculos financieros.
- [x] Mover carga desde Google Sheets.
- [x] Mover envio de correo.
- [x] Mover generacion de visualizaciones.
- [x] Mover generacion de PDF.
- [x] Crear pipeline modular.
- [x] Mantener compatibilidad con ejecucion actual.
- [x] Ejecutar pruebas y confirmar que pasan.

## Etapa 1.5: Preparar extensibilidad de indicadores

### Objetivo

Antes de avanzar a contratos externos, reducir el acoplamiento interno de columnas e indicadores para que el reporte pueda crecer sin duplicar nombres tecnicos en varios modulos.

La Etapa 2 define como se solicita y devuelve un reporte, pero no resuelve por si sola como se agregan nuevos indicadores al flujo analitico. Si esa base no se atiende, cada nuevo indicador obligaria a tocar fuente de datos, calculos, graficas, PDF, payload de IA y pruebas de forma dispersa.

### Entregables

- Catalogo central de indicadores en `app/indicators.py`.
- Constantes y metadata de columnas fuente y columnas derivadas.
- Alias de columnas administrados desde el catalogo.
- Validacion unica de columnas requeridas.
- Compatibilidad de `app/schema.py` como fachada para imports existentes.
- Carga de datos que conserva indicadores numericos adicionales.
- Tests del catalogo y de preservacion de columnas extra.

### Checklist

- [x] Crear `app/indicators.py`.
- [x] Mantener compatibilidad de `app/schema.py`.
- [x] Usar el catalogo en carga de datos.
- [x] Usar el catalogo en calculos financieros.
- [x] Usar el catalogo en visualizaciones.
- [x] Usar el catalogo en payload de insights.
- [x] Agregar pruebas de catalogo.
- [x] Agregar prueba para columnas extra en fuente de datos.

### Limite consciente

Esta etapa no convierte todavia el PDF en un constructor dinamico de secciones. Las cinco secciones actuales se conservan para no cambiar el comportamiento del reporte. La siguiente mejora natural seria definir `ReportSection` o una especificacion de secciones para que nuevas graficas e insights se agreguen por configuracion y no por codigo duplicado.

## Etapa 2: Definir contratos internos

### Objetivo

Definir modelos y contratos simples para que el pipeline no dependa directamente de detalles como Google Sheets, BigQuery o variables sueltas.

### Modelos implementados

```python
class ReportRequest:
    recipient_email: str | None
    start_year: int | None
    end_year: int | None
    report_file_name: str
    nota_metodologica: str | None
```

```python
class ReportResult:
    report_file_path: str
    email_sent: bool
    generated_at: datetime
    status: str
```

### Interfaz conceptual de fuente de datos

```python
class DataSource:
    def load_indicators(self, start_year: int | None, end_year: int | None):
        ...
```

### Entregables

- Modelo `ReportRequest`.
- Modelo `ReportResult`.
- Fuente `GoogleSheetsDataSource` compatible con el pipeline.
- Pipeline que recibe una solicitud estructurada en vez de argumentos sueltos.

### Checklist

- [x] Crear `ReportRequest`.
- [x] Crear `ReportResult`.
- [x] Adaptar pipeline para recibir `ReportRequest`.
- [x] Encapsular fuente actual como `GoogleSheetsDataSource`.
- [x] Agregar pruebas del pipeline usando mocks.

## Etapa 3: Crear API backend

### Objetivo

Exponer la generacion del reporte mediante HTTP para que pueda ser consumida por un frontend u otros sistemas.

### Tecnologia sugerida

FastAPI.

### Endpoint inicial

```text
POST /reports
```

### Request esperado

```json
{
  "recipient_email": "cliente@correo.com",
  "start_year": 2016,
  "end_year": 2025
}
```

### Response esperado

```json
{
  "status": "completed",
  "report_file": "Reporte_Economico_Ejecutivo.pdf",
  "email_sent": true
}
```

### Entregables

- `app/api/main.py` o `app/api/routes.py`.
- Endpoint `POST /reports`.
- Validacion de correo y periodo.
- Pruebas del endpoint.

### Checklist

- [ ] Agregar FastAPI al proyecto.
- [ ] Crear endpoint `POST /reports`.
- [ ] Conectar endpoint con pipeline.
- [ ] Validar correo receptor.
- [ ] Validar periodo inicial y final.
- [ ] Agregar pruebas con `TestClient`.

## Etapa 4: Migrar fuente de datos a BigQuery

### Objetivo

Reemplazar gradualmente Google Sheets por BigQuery como fuente principal, sin modificar los calculos ni la generacion del reporte.

### Modulo sugerido

```text
app/data_sources/bigquery.py
```

### Query conceptual

```sql
SELECT
  anio AS Año,
  inpc AS INPC,
  salario_minimo_diario AS Salario_Minimo_Diario,
  uma_diario AS UMA_diario,
  tasa_referencia_banxico AS Tasa_Referencia_Banxico
FROM dataset.indicadores
WHERE anio BETWEEN @start_year AND @end_year
ORDER BY anio
```

### Entregables

- `BigQueryDataSource`.
- Query parametrizada por periodo.
- Pruebas unitarias con mock del cliente de BigQuery.
- Opcion de configurar la fuente activa desde `.env`.

### Checklist

- [ ] Agregar dependencia de BigQuery.
- [ ] Crear `BigQueryDataSource`.
- [ ] Definir variables `.env` para proyecto, dataset y tabla.
- [ ] Implementar query parametrizada.
- [ ] Probar transformacion a DataFrame compatible.
- [ ] Permitir elegir fuente `google_sheets` o `bigquery`.

## Etapa 5: Crear frontend minimo

### Objetivo

Permitir que un usuario solicite un reporte sin tocar el codigo.

### Campos del formulario

- Correo receptor.
- Año inicial.
- Año final.
- Boton para generar reporte.
- Estado del proceso.
- Opcion de descarga del PDF si aplica.

### Opciones de tecnologia

- FastAPI + HTML/Jinja + HTMX para una interfaz ligera.
- Streamlit para prototipo rapido.
- React + FastAPI si el frontend crecera como producto independiente.

### Recomendacion inicial

Comenzar con FastAPI + HTML simple o Streamlit. Migrar a React solo si la interfaz necesita crecer.

### Checklist

- [ ] Crear pantalla/formulario de solicitud.
- [ ] Validar correo.
- [ ] Validar periodo.
- [ ] Mostrar estado de generacion.
- [ ] Mostrar resultado de envio.
- [ ] Agregar enlace de descarga si el PDF queda disponible.

## Etapa 6: Reportes asincronos

### Objetivo

Evitar que la API se quede bloqueada mientras se genera el reporte, especialmente cuando BigQuery, PDF o correo tarden.

### Endpoints futuros

```text
POST /reports
GET /reports/{report_id}
GET /reports/{report_id}/download
```

### Estados sugeridos

```text
queued
running
completed
failed
email_sent
```

### Checklist

- [ ] Crear identificador `report_id`.
- [ ] Registrar estado inicial.
- [ ] Ejecutar generacion en background.
- [ ] Consultar estado por API.
- [ ] Exponer descarga del PDF.

## Etapa 7: Almacenamiento y auditoria

### Objetivo

Tener trazabilidad de cada solicitud de reporte.

### Datos a guardar

- ID del reporte.
- Correo receptor.
- Periodo solicitado.
- Fecha y hora de solicitud.
- Estado.
- Ruta del PDF.
- Error, si existe.

### Opciones

- SQLite para desarrollo local.
- PostgreSQL o Cloud SQL para operacion.
- BigQuery para auditoria analitica.
- Cloud Storage para PDFs.

### Checklist

- [ ] Definir tabla de solicitudes.
- [ ] Guardar cada solicitud.
- [ ] Guardar estado final.
- [ ] Guardar errores.
- [ ] Guardar ruta del PDF.

## Etapa 8: Despliegue

### Objetivo

Convertir la aplicacion en un servicio desplegable.

### Ruta recomendada si se usa BigQuery

- Backend en Cloud Run.
- Datos en BigQuery.
- PDFs en Cloud Storage.
- Secretos en Secret Manager.
- Servicio de correo transaccional o SMTP corporativo.

### Checklist

- [ ] Crear Dockerfile.
- [ ] Configurar variables de entorno.
- [ ] Configurar secretos.
- [ ] Configurar permisos de BigQuery.
- [ ] Configurar almacenamiento de PDFs.
- [ ] Desplegar en Cloud Run.
- [ ] Probar flujo completo en ambiente desplegado.

## Riesgos y decisiones pendientes

- Definir si el envio de correo seguira con Gmail SMTP o pasara a un proveedor transaccional.
- Definir si los PDFs se guardaran localmente, en Cloud Storage o ambos.
- Definir si el frontend sera simple o una aplicacion React separada.
- Definir esquema final de BigQuery.
- Definir si el pipeline debe fallar duro ante errores o devolver estados controlados.

## Primer siguiente paso recomendado

Iniciar con la Etapa 3: crear API backend sobre los contratos internos ya definidos.

El primer movimiento concreto seria crear:

1. `app/api/main.py`.
2. Endpoint `POST /reports`.
3. Validacion de correo y periodo.
4. Pruebas con `TestClient`.

Con eso la base queda lista para exponer la generacion de reportes sin acoplar la API al calculo financiero ni a Google Sheets.
