import os
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage

import pandas as pd

# =========================
# CONFIGURACIÓN
# =========================

OUTPUT_DIR = "output"

EMAIL_SENDER = "tu_email@gmail.com"
EMAIL_PASSWORD = "TU_PASSWORD"
EMAIL_RECIPIENTS = ["destinatario@gmail.com"]
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 465

def alert_missing_data(df: pd.DataFrame):
    """
    Revisa filas con NaNs en columnas críticas y genera alerta.
    También guarda CSV opcional para revisión.
    """
    if "stock" in df.columns:
        critical_cols = ["product_id", "name", "stock"]
    else:
        critical_cols = ["id", "name", "email"]

    missing_rows = df[df[critical_cols].isnull().any(axis=1)]

    if not missing_rows.empty:
        alert_msg = f"🚨 ALERTA: {len(missing_rows)} filas con datos críticos faltantes"
        print(alert_msg)
        print(missing_rows[critical_cols])
        logging.warning(alert_msg)

        # Guardar CSV opcional para control
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/missing_data_{ts}.csv"
        missing_rows.to_csv(path, index=False)
        print(f"💾 CSV de registros incompletos guardado: {path}")
    else:
        print("ℹ️ No se detectaron filas con datos críticos faltantes")



def alert_no_sales(df: pd.DataFrame, days_threshold: int = 60):
    """
    Revisa productos que no han tenido ventas en los últimos `days_threshold` días.
    Requiere columnas: 'product_id', 'name', 'last_sold_date' (YYYY-MM-DD).
    Guarda CSV automáticamente para control.
    """
    if not {"product_id", "name", "last_sold_date"}.issubset(df.columns):
        print("ℹ️ Columnas necesarias para alerta de ventas no detectadas, alerta ignorada")
        return

    df['last_sold_date'] = pd.to_datetime(df['last_sold_date'], errors='coerce')
    threshold_date = pd.Timestamp.now() - pd.Timedelta(days=days_threshold)
    no_sales = df[df['last_sold_date'] < threshold_date]

    if not no_sales.empty:
        alert_msg = f"🚨 ALERTA: {len(no_sales)} productos sin ventas en los últimos {days_threshold} días"
        print(alert_msg)
        print(no_sales[['product_id', 'name', 'last_sold_date']])
        logging.warning(alert_msg)

        # Guardar CSV automáticamente
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/no_sales_{ts}.csv"
        no_sales.to_csv(path, index=False)
        print(f"💾 CSV de productos sin ventas guardado: {path}")
    else:
        print(f"ℹ️ Todos los productos tienen ventas recientes (< {days_threshold} días)")



def alert_low_stock(df: pd.DataFrame, threshold: int = 5):
    """
    Revisa productos con stock menor o igual al umbral y genera alerta.
    Guarda CSV automáticamente para control.
    """
    if "stock" not in df.columns or "product_id" not in df.columns:
        print("ℹ️ No se detectó columna 'stock' o 'product_id', alerta de stock ignorada")
        return

    low_stock = df[df["stock"] <= threshold]

    if not low_stock.empty:
        alert_msg = f"🚨 ALERTA: {len(low_stock)} productos con stock <= {threshold}"
        print(alert_msg)
        print(low_stock[["product_id", "name", "stock"]])
        logging.warning(alert_msg)

        # Guardar CSV automáticamente
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/low_stock_{ts}.csv"
        low_stock.to_csv(path, index=False)
        print(f"💾 CSV de stock crítico guardado: {path}")
    else:
        print("ℹ️ No hay productos con stock crítico")




def send_email(subject: str, body: str, attachments: list = None):
    """
    Envía un email con asunto, cuerpo y archivos adjuntos opcionales.
    """
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(EMAIL_RECIPIENTS)
    msg["Subject"] = subject
    msg.set_content(body)

    attachments = attachments or []
    for filepath in attachments:
        try:
            with open(filepath, "rb") as f:
                data = f.read()
                name = os.path.basename(filepath)
            msg.add_attachment(data, maintype="application", subtype="octet-stream", filename=name)
        except Exception as e:
            print(f"⚠️ No se pudo adjuntar {filepath}: {e}")

    try:
        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVER, EMAIL_SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print(f"📧 Email enviado: {subject}")
    except Exception as e:
        print(f"❌ Error enviando email: {e}")



