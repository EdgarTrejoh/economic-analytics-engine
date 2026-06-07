from pathlib import Path

import streamlit as st
from app.config import load_settings
from app.services.pdf_report import METHODOLOGICAL_NOTE_PATH
from app.services.pipeline import run_pipeline

st.set_page_config(page_title="Generador de Reporte Económico", page_icon="📈")

st.title("Generador de Reporte Económico Ejecutivo")
st.markdown("Ingresa los datos requeridos para generar y enviar el reporte económico.")

# Actividad 1.3: Campo para capturar el correo electrónico
recipient_email = st.text_input(
    "Correo Electrónico del Destinatario",
    placeholder="ejemplo@correo.com"
)

# Actividad 1.4: Campo para la nota metodológica
default_nota = ""
if METHODOLOGICAL_NOTE_PATH.exists():
    default_nota = METHODOLOGICAL_NOTE_PATH.read_text(encoding="utf-8")

nota_metodologica = st.text_area(
    "Consideraciones de la Nota Metodológica",
    value=default_nota,
    height=200,
    placeholder="Escribe aquí las notas metodológicas..."
)

# Actividad 1.5: Botón para ejecutar
if st.button("Generar y Enviar Reporte", type="primary"):
    if not recipient_email.strip():
        st.warning("Por favor, ingresa el correo electrónico del destinatario.")
    elif not nota_metodologica.strip():
        st.warning("Por favor, ingresa la nota metodológica.")
    else:
        with st.spinner("Generando reporte... esto puede tomar unos momentos."):
            try:
                # Cargar configuración sin pedir datos por consola
                settings = load_settings(prompt_for_password=False)
                
                # Sobrescribir temporalmente el correo destino con el de la UI
                settings.recipient_email = recipient_email.strip()
                settings.nota_metodologica = nota_metodologica.strip()

                # Ejecutar el pipeline
                run_pipeline(settings)

                # Verificar si se creó el PDF para habilitar la descarga
                report_path = Path(settings.report_file_name)
                if report_path.exists():
                    st.success("¡Reporte generado con éxito!")
                    
                    pdf_bytes = report_path.read_bytes()
                        
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=pdf_bytes,
                        file_name=report_path.name,
                        mime="application/pdf"
                    )

                    if settings.app_password:
                        st.info(f"Se ha intentado enviar el reporte por correo a: {settings.recipient_email}")
                    else:
                        st.warning("No se detectó contraseña de correo (APP_PASSWORD) en la configuración, por lo que el PDF no fue enviado. Sin embargo, puedes descargarlo usando el botón de arriba.")
                else:
                    st.error("Error: El pipeline finalizó pero no se encontró el archivo PDF generado.")

            except Exception as e:
                st.error(f"Ocurrió un error inesperado durante la ejecución: {str(e)}")
