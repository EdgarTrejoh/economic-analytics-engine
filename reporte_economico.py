import os
import logging
import datetime
import getpass
import tempfile
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from urllib.parse import urlparse, parse_qs

import pandas as pd
import matplotlib.pyplot as plt
from fpdf import FPDF
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_sheet_csv_url(sheet_url):
    """Extrae el Document ID y el GID de una URL de Google Sheets y arma la URL CSV."""
    try:
        doc_id = sheet_url.split('/d/')[1].split('/edit')[0]
        parsed_url = urlparse(sheet_url)
        fragment_dict = parse_qs(parsed_url.fragment)
        gid = fragment_dict.get('gid', ['0'])[0]
        
        if gid == '0':
            return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
        else:
            return f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid={gid}"
    except Exception as e:
        logger.error(f"Error al procesar la URL de Google Sheets: {e}")
        raise ValueError("URL de Google Sheets inválida.")

def load_and_clean_data(url_csv_export):
    """Descarga el CSV y limpia los formatos."""
    try:
        df = pd.read_csv(url_csv_export, skipinitialspace=True)
        logger.info("Datos cargados correctamente desde Google Sheets.")
    except Exception as e:
        logger.error(f"Fallo en la conexión a Google Sheets. Error: {e}")
        raise

    try:
        df['Año'] = pd.to_numeric(df['Año'], errors="coerce").astype("Int64")
        cols_to_float = [col for col in df.columns if col != 'Año']
        df[cols_to_float] = df[cols_to_float].astype(float)
        df = df.dropna(subset=['Año'])
        logger.info("Tipos de datos convertidos a flotante y entero.")
        return df
    except Exception as e:
        logger.error(f"Error al convertir tipos de datos: {e}")
        raise

def calculate_cagr(start_value, end_value, num_years):
    if num_years == 0:
        return 0.0
    return (end_value / start_value) ** (1/num_years) - 1

def calculate_financial_metrics(df):
    """Realiza todos los cálculos financieros."""
    df['inflacion'] = (df['INPC'] / df['INPC'].shift(1) - 1) * 100
    df['inflacion'] = df['inflacion'].fillna(0)
    df['Indice_de_Precios'] = (df['INPC'] / df['INPC'].iloc[0]) * 100
    df['Salario_Minimo_Real'] = (df['Salario_Minimo_Diario'] / df['Indice_de_Precios']) * 100
    df['UMA_Real'] = (df['UMA_diario'] / df['Indice_de_Precios']) * 100

    start_year = df['Año'].min()
    end_year = df['Año'].max()
    num_years = end_year - start_year

    start_row = df.loc[df['Año'] == start_year].iloc[0]
    end_row = df.loc[df['Año'] == end_year].iloc[0]

    nominal_salario_cagr = calculate_cagr(start_row['Salario_Minimo_Diario'], end_row['Salario_Minimo_Diario'], num_years)
    real_salario_cagr = calculate_cagr(start_row['Salario_Minimo_Real'], end_row['Salario_Minimo_Real'], num_years)
    nominal_uma_cagr = calculate_cagr(start_row['UMA_diario'], end_row['UMA_diario'], num_years)
    real_uma_cagr = calculate_cagr(start_row['UMA_Real'], end_row['UMA_Real'], num_years)

    base_year = start_year
    salario_real_base = df.loc[df['Año'] == base_year, 'Salario_Minimo_Real'].values[0]
    uma_real_base = df.loc[df['Año'] == base_year, 'UMA_Real'].values[0]

    df['Salario_Minimo_Real_Normalizado'] = (df['Salario_Minimo_Real'] / salario_real_base) * 100
    df['UMA_Real_Normalizado'] = (df['UMA_Real'] / uma_real_base) * 100

    cagrs = {
        'nominal_salario': nominal_salario_cagr,
        'real_salario': real_salario_cagr,
        'nominal_uma': nominal_uma_cagr,
        'real_uma': real_uma_cagr
    }

    logger.info("Cálculos financieros (Real, UMA, CAGR) ejecutados con éxito.")
    return df, cagrs, base_year, start_year, end_year

def generate_visualizations(df, cagrs, base_year, start_year, end_year, temp_dir):
    """Genera los gráficos y los guarda en el directorio temporal."""
    image_paths = []
    
    # 1. Comparativo Salario vs UMA
    path1 = os.path.join(temp_dir, "plot1.png")
    plt.figure(figsize=(12, 7))
    plt.plot(df['Año'], df['Salario_Minimo_Real'], marker='o', label='Salario mínimo (valor real)', color='skyblue', linewidth=3, linestyle='-')
    plt.plot(df['Año'], df['UMA_Real'], marker='o', label='UMA valor real', color='green', linewidth=3, linestyle='-')
    plt.plot(df['Año'], df['Salario_Minimo_Diario'], marker='o', label='Salario mínimo nominal', color='orange', linewidth=3, linestyle='--')
    plt.plot(df['Año'], df['UMA_diario'], marker='o', label='UMA valor nominal', color='red', linewidth=3, linestyle='--')
    plt.title('Comparativo de la evolución: Salario Mínimo vs. UMA', fontsize=16, fontweight='bold')
    plt.xlabel('Año', fontsize=12)
    plt.ylabel('Valor Diario (MXN ajustado por inflación)', fontsize=12)
    plt.legend(loc='upper left', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xticks(df['Año'])
    # Hacer anotación dinámica para 3 años después del inicio si es posible
    ano_anotacion = start_year + 3 if (start_year + 3) <= end_year else start_year
    try:
        val_anotacion = df['Salario_Minimo_Real'].loc[df['Año'] == ano_anotacion].values[0]
        plt.annotate('Incremento acelerado', xy=(ano_anotacion, val_anotacion),
                     xytext=(ano_anotacion, val_anotacion + 20), arrowprops=dict(facecolor='black', shrink=0.05), fontsize=10, ha='center')
    except IndexError:
        pass
    plt.savefig(path1, format='png', bbox_inches='tight')
    plt.close()
    image_paths.append(path1)

    # 2. Base 100
    path2 = os.path.join(temp_dir, "plot2.png")
    plt.figure(figsize=(12, 6))
    plt.plot(df['Año'], df['Salario_Minimo_Real_Normalizado'], marker='o', label=f'Salario Real (Base {base_year} = 100)', color='skyblue', linewidth=3)
    plt.plot(df['Año'], df['UMA_Real_Normalizado'], marker='o', label=f'UMA Real (Base {base_year} = 100)', color='green', linewidth=3)
    plt.title(f'Salario Mínimo vs. UMA (Base Año {base_year})', fontsize=16)
    plt.xlabel('Año', fontsize=12)
    plt.ylabel(f'Índice ({base_year} = 100)', fontsize=12)
    plt.legend()
    plt.grid(True)
    plt.xticks(df['Año'])
    plt.savefig(path2, format='png', bbox_inches='tight')
    plt.close()
    image_paths.append(path2)

    # 3. CAGR
    path3 = os.path.join(temp_dir, "plot3.png")
    cagr_values = [cagrs['nominal_salario'], cagrs['real_salario'], cagrs['nominal_uma'], cagrs['real_uma']]
    labels = ['Salario Nominal', 'Salario Real', 'UMA Nominal', 'UMA Real']
    colors = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd']
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, [c*100 for c in cagr_values], color=colors)
    plt.title(f'Crecimiento Anual Compuesto (CAGR) {start_year}-{end_year}', fontsize=16, fontweight='bold')
    plt.ylabel('CAGR (%)', fontsize=12)
    plt.ylim(0, max([c*100 for c in cagr_values]) + 5)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f'{yval:.2f}%', ha='center', va='bottom', fontsize=10)
    plt.savefig(path3, format='png', bbox_inches='tight')
    plt.close()
    image_paths.append(path3)

    # 4. Inflación vs Banxico
    path4 = os.path.join(temp_dir, "plot4.png")
    fig, ax1 = plt.subplots(figsize=(12, 7))
    ax1.plot(df['Año'], df['inflacion'], marker='o', color='green', linewidth=3, label='Inflación Anual (%)')
    ax1.set_xlabel('Año', fontsize=12)
    ax1.set_ylabel('Inflación Anual (%)', color='green', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='green')
    ax1.set_title('Inflación Anual vs. Tasa de Referencia de Banxico', fontsize=16, fontweight='bold')
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc='upper left')
    ax2 = ax1.twinx()
    ax2.plot(df['Año'], df['Tasa_Referencia_Banxico'], marker='s', color='red', linestyle='--', linewidth=3, label='Tasa de Referencia Banxico (%)')
    ax2.set_ylabel('Tasa de Referencia Banxico (%)', color='red', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='red')
    ax2.legend(loc='upper right')
    plt.savefig(path4, format='png', bbox_inches='tight')
    plt.close()
    image_paths.append(path4)

    # 5. Dashboard
    path5 = os.path.join(temp_dir, "plot5.png")
    fig, (ax1_dash, ax2_dash, ax3_dash) = plt.subplots(3, 1, figsize=(12, 15))
    fig.suptitle(f'Análisis Económico Integral ({start_year}-{end_year})', fontsize=20, fontweight='bold')
    
    ax1_dash.plot(df['Año'], df['Salario_Minimo_Real'], marker='o', label='Poder Adquisitivo (Salario)', color='skyblue', linewidth=3)
    ax1_dash.plot(df['Año'], df['UMA_Real'], marker='o', label='Poder Adquisitivo (UMA)', color='green', linewidth=3, linestyle='--')
    ax1_dash.set_title('Evolución del Poder Adquisitivo: Salario Mínimo vs. UMA', fontsize=14)
    ax1_dash.set_ylabel(f'Valor Diario (MXN a precios de {base_year})', fontsize=12)
    ax1_dash.legend(loc='upper left', fontsize=10)
    ax1_dash.grid(True, linestyle='--', alpha=0.6)
    ax1_dash.set_xticks(df['Año'])
    
    bars = ax2_dash.bar(labels, [c*100 for c in cagr_values], color=colors)
    ax2_dash.set_title('Crecimiento Anual Compuesto (CAGR)', fontsize=14)
    ax2_dash.set_ylabel('CAGR (%)', fontsize=12)
    ax2_dash.grid(axis='y', linestyle='--', alpha=0.7)
    ax2_dash.set_ylim(0, max([c*100 for c in cagr_values]) + 5)
    for bar in bars:
        yval = bar.get_height()
        ax2_dash.text(bar.get_x() + bar.get_width()/2.0, yval + 0.5, f'{yval:.2f}%', ha='center', va='bottom', fontsize=10)
        
    ax3_dash.plot(df['Año'], df['inflacion'], marker='o', color='green', linewidth=3, label='Inflación Anual (%)')
    ax3_dash.set_ylabel('Inflación Anual (%)', color='green', fontsize=12)
    ax3_dash.tick_params(axis='y', labelcolor='green')
    ax3_dash.set_title('Inflación Anual vs. Tasa de Referencia de Banxico', fontsize=14)
    ax3_dash.grid(True, linestyle='--', alpha=0.6)
    ax3_dash.legend(loc='upper left')
    ax3_dash.set_xticks(df['Año'])
    ax3_twin = ax3_dash.twinx()
    ax3_twin.plot(df['Año'], df['Tasa_Referencia_Banxico'], marker='s', color='red', linestyle='--', linewidth=3, label='Tasa de Referencia Banxico (%)')
    ax3_twin.set_ylabel('Tasa de Referencia Banxico (%)', color='red', fontsize=12)
    ax3_twin.tick_params(axis='y', labelcolor='red')
    ax3_twin.legend(loc='upper right')
    ax3_dash.set_xlabel('Año', fontsize=12)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(path5, format='png', bbox_inches='tight')
    plt.close()
    image_paths.append(path5)

    logger.info("Gráficos generados y guardados en directorio temporal.")
    return image_paths

class PDFReport(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_y(10)
            self.set_font('Arial', 'B', 12)
            self.cell(0, 5, 'Reporte Ejecutivo', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def add_cover(self, titulo, subtitulo, autor, fecha):
        self.add_page()
        self.set_font('Arial', 'B', 24)
        self.ln(50)
        self.multi_cell(0, 10, titulo, align='C')
        self.set_font('Arial', 'I', 16)
        self.ln(10)
        self.multi_cell(0, 10, subtitulo, align='C')
        self.ln(40)
        self.set_font('Arial', '', 14)
        self.cell(0, 10, f'Autor: {autor}', align='C')
        self.ln(10)
        self.cell(0, 10, f'Fecha: {fecha.strftime("%Y-%m-%d")}', align='C')
        self.ln(10)

    def add_section(self, title):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)

    def add_paragraph(self, text):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 5, text)
        self.ln(5)

def create_pdf_report(df, cagrs, base_year, start_year, end_year, image_paths, report_file_name):
    """Genera el PDF combinando análisis de texto e imágenes."""
    pdf = PDFReport()
    pdf.add_cover(
        titulo="Reporte Ejecutivo: El Poder Adquisitivo",
        subtitulo=f"Análisis de Salario Mínimo, UMA e Inflación en México ({start_year}-{end_year})",
        autor="Pipeline Analítico Automatizado",
        fecha=datetime.date.today()
    )

    pdf.add_page()
    pdf.add_section('1. Evolución del Poder Adquisitivo: Salario vs. UMA')
    pdf.image(image_paths[0], x=20, w=170)
    pdf.add_paragraph(
        "El comparativo muestra la evolución de los valores nominales (líneas punteadas) frente a los valores reales (líneas continuas), ajustados por la inflación. "
        "Se observa el comportamiento del Salario Mínimo Real frente a la UMA, reflejando el impacto de la política económica en el poder de compra real."
    )

    pdf.add_page()
    pdf.add_section(f'2. Salario Mínimo vs. UMA (Base {base_year} = 100)')
    pdf.image(image_paths[1], x=20, w=170)
    pdf.add_paragraph(
        f"Al establecer el {base_year} como año base (100), la divergencia en el poder adquisitivo se vuelve más evidente. "
        "Este índice ilustra el desafío de mantener los indicadores alineados frente a la inflación a lo largo del periodo de estudio."
    )

    pdf.add_page()
    pdf.add_section(f'3. Crecimiento Anual Compuesto (CAGR {start_year}-{end_year})')
    pdf.image(image_paths[2], x=20, w=170)
    pdf.add_paragraph(
        f"El CAGR (Tasa de Crecimiento Anual Compuesto) es la métrica clave. En el periodo analizado ({start_year} a {end_year}):\n"
        f" * CAGR Salario Nominal: {cagrs['nominal_salario']:.2%} \n"
        f" * CAGR Salario Real (Poder Adquisitivo): {cagrs['real_salario']:.2%} \n"
        f"Esta comparativa con el crecimiento de la UMA valida el éxito relativo de la recuperación salarial en términos reales."
    )

    pdf.add_page()
    pdf.add_section('4. Inflación Anual y Política Monetaria (Banco de México)')
    pdf.image(image_paths[3], x=20, w=170)
    pdf.add_paragraph(
        "El gráfico de dos ejes muestra la danza entre la Inflación Anual y la Tasa de Referencia de Banxico. "
        "Se observa cómo los incrementos en la tasa de referencia son la respuesta a los ciclos inflacionarios, lo cual es "
        "fundamental para entender la gestión de riesgos y la estrategia monetaria del país."
    )

    pdf.add_page()
    pdf.add_section('5. Dashboard (Resumen Ejecutivo)')
    pdf.image(image_paths[4], x=20, w=170)
    pdf.add_paragraph(
        "El dashboard consolida la narrativa. La política de recuperación del poder adquisitivo y la gestión de la inflación por parte de Banxico "
        "sirven como telón de fondo para demostrar la dinámica económica del periodo."
    )

    pdf.output(report_file_name)
    logger.info(f"Reporte '{report_file_name}' generado exitosamente.")

def send_report_email(sender_email, app_password, recipient_email, report_file_name):
    """Envía el PDF generado por correo electrónico."""
    smtp_server = "smtp.gmail.com"
    smtp_port = 587 

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Reporte Económico Ejecutivo - Análisis de Poder Adquisitivo ({os.path.basename(report_file_name)})"

    body = "Adjunto el Reporte Económico Ejecutivo completo, generado automáticamente por el pipeline de Python."
    msg.attach(MIMEText(body, 'plain'))

    try:
        with open(report_file_name, "rb") as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename= {report_file_name}")
            msg.attach(part)
    except FileNotFoundError:
        logger.error(f"No se pudo encontrar el archivo adjunto: {report_file_name}")
        return

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, recipient_email, msg.as_string())
        logger.info(f"Correo electrónico enviado exitosamente a {recipient_email}.")
    except smtplib.SMTPAuthenticationError:
        logger.error("ERROR DE AUTENTICACIÓN SMTP: La contraseña o el correo no son correctos.")
    except Exception as e:
        logger.error(f"Fallo al enviar el correo: {e}")
    finally:
        if 'server' in locals() and server:
            server.quit()

def execute_economic_pipeline():
    """Ejecución central (Pipeline)"""
    # 1. Cargar Configuración
    load_dotenv()
    sheet_url = os.getenv("SHEET_URL", "https://docs.google.com/spreadsheets/d/1JiB0WJPRTcq5yE1Zy3jW7n7K2hgfdRNcwXhiS8P1XTI/edit?usp=sharing")
    sender_email = os.getenv("SENDER_EMAIL")
    recipient_email = os.getenv("RECIPIENT_EMAIL")
    
    app_password = os.getenv('APP_PASSWORD')
    if not app_password or app_password == "TU_CONTRASEÑA_DE_APLICACION_AQUI":
        logger.warning("Contraseña de aplicación no encontrada o es inválida en el .env.")
        try:
            app_password = getpass.getpass("Ingresa la Contraseña de Aplicación de Google (16 dígitos) o presiona Enter para omitir el correo: ")
        except EOFError:
            app_password = ""

    report_file_name = "Reporte_Economico_Ejecutivo.pdf"

    # 2. Ejecutar procesamiento
    try:
        url_csv_export = get_sheet_csv_url(sheet_url)
        df_raw = load_and_clean_data(url_csv_export)
        df_calc, cagrs, base_year, start_year, end_year = calculate_financial_metrics(df_raw)
        
        # Uso de entorno temporal para no ensuciar el disco
        with tempfile.TemporaryDirectory() as temp_dir:
            image_paths = generate_visualizations(df_calc, cagrs, base_year, start_year, end_year, temp_dir)
            create_pdf_report(df_calc, cagrs, base_year, start_year, end_year, image_paths, report_file_name)
            
            # 3. Enviar correo si hay contraseña válida
            if app_password:
                send_report_email(sender_email, app_password, recipient_email, report_file_name)
            else:
                logger.info("No se proporcionó contraseña. El correo no fue enviado, pero el reporte se conservó localmente.")
                
    except Exception as e:
        logger.error(f"El pipeline falló en la ejecución: {e}")

if __name__ == "__main__":
    execute_economic_pipeline()
