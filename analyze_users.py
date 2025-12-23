# ============================================================
# 🚀 API DATA FETCHER – PROYECTO LÍNEA BASE (MES 1–2)
# ============================================================
# Este script cumple múltiples propósitos:
#
# 1️⃣ Obtener datos desde una API pública
# 2️⃣ Guardar datos crudos en CSV y JSON
# 3️⃣ Permitir pruebas con CSV locales (sin usar API)
# 4️⃣ Limpiar datos (duplicados, columnas nuevas)
# 5️⃣ Generar alertas VISIBLES en consola
# 6️⃣ Dejar logs para auditoría futura
#
# IMPORTANTE:
# - Este archivo es intencionalmente largo (~200 líneas)
# - Está diseñado para ESTUDIAR, no para compactar
# ============================================================


# =========================
# 📦 IMPORTS
# =========================

import requests
import pandas as pd
import logging
import os
import json
import sys
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException


# =========================
# ⚙️ CONFIGURACIÓN GLOBAL
# =========================

API_URL = "https://jsonplaceholder.typicode.com/users"
OUTPUT_DIR = "output"
LOG_FILE = "api_data_fetcher.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


# =========================
# 🌐 SESIÓN HTTP ROBUSTA
# =========================

def create_session():
    """
    Crea una sesión HTTP con reintentos automáticos.
    Esto evita que el script falle por errores temporales.
    """
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# =========================
# 📥 FETCH DESDE API
# =========================

def fetch_data_api():
    """
    Obtiene datos desde la API remota.
    Retorna un DataFrame de pandas.
    """
    print("🌐 Conectando a la API...")
    session = create_session()

    try:
        response = session.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        print(f"✅ Datos obtenidos: {len(data)} registros")
        logging.info("Datos obtenidos desde API correctamente")

        return pd.DataFrame(data)

    except RequestException as e:
        logging.error(f"Error al conectar con API: {e}")
        raise RuntimeError("❌ Error al obtener datos desde la API")


# =========================
# 📂 FETCH DESDE CSV LOCAL
# =========================

def fetch_data_local(file_path):
    """
    Carga un CSV local para pruebas manuales.
    Ideal para probar duplicados y validaciones.
    """
    print(f"📂 Usando CSV local: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"❌ Archivo no encontrado: {file_path}")

    df = pd.read_csv(file_path)
    print(f"✅ Archivo cargado desde {file_path} ({len(df)} filas)")
    logging.info(f"CSV local cargado: {file_path}")

    return df


# =========================
# 🔍 VALIDACIÓN DE DATOS
# =========================

def validate_data(df):
    """
    Verifica que el DataFrame tenga estructura mínima válida.
    """
    print("🔍 Validando estructura de datos...")

    required_columns = {"id", "name", "email"}

    if not required_columns.issubset(df.columns):
        logging.error("Estructura inválida de datos")
        raise ValueError("❌ Faltan columnas obligatorias")

    print("✅ Validación exitosa")
    logging.info("Datos validados correctamente")


# =========================
# 💾 GUARDADO DE ARCHIVOS
# =========================

def save_raw_outputs(df, timestamp):
    """
    Guarda CSV y JSON originales.
    """
    csv_path = f"{OUTPUT_DIR}/users_data_{timestamp}.csv"
    json_path = f"{OUTPUT_DIR}/users_data_{timestamp}.json"

    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)

    print(f"💾 CSV guardado: {csv_path}")
    print(f"💾 JSON guardado: {json_path}")

    logging.info("Archivos crudos guardados")

    return csv_path


# =========================
# 📊 PROCESAMIENTO DE DATOS
# =========================

def process_data(df):
    """
    Limpia datos:
    - Detecta duplicados
    - Elimina duplicados
    - Agrega columnas nuevas
    """
    print("\n📊 Iniciando procesamiento de datos...")

    original_count = len(df)

    # Detectar duplicados
    duplicated_rows = df[df.duplicated()]
    duplicated_count = len(duplicated_rows)

    if duplicated_count > 0:
        print("🚨 ALERTA: SE DETECTARON DUPLICADOS")
        print(duplicated_rows)
        logging.warning(f"{duplicated_count} duplicados detectados")
    else:
        print("ℹ️ No se detectaron duplicados")

    # Eliminar duplicados
    df_clean = df.drop_duplicates()
    clean_count = len(df_clean)

    # Nueva columna ejemplo
    if "address" in df_clean.columns:
        df_clean["city"] = df_clean["address"].apply(
            lambda x: x.get("city") if isinstance(x, dict) else None
        )

    print(f"Registros originales: {original_count}")
    print(f"Registros limpios: {clean_count}")
    print(f"Duplicados eliminados: {original_count - clean_count}")

    return df_clean


# =========================
# 💾 GUARDADO LIMPIO
# =========================

def save_clean_csv(df, timestamp):
    """
    Guarda el CSV limpio final.
    """
    clean_path = f"{OUTPUT_DIR}/users_data_{timestamp}_clean.csv"
    df.to_csv(clean_path, index=False)

    print(f"✅ CSV limpio guardado: {clean_path}")
    logging.info("CSV limpio guardado")

    return clean_path


# =========================
# 🧠 FUNCIÓN PRINCIPAL
# =========================

def main():
    """
    Orquesta todo el pipeline.
    Permite:
    - python api_data_fetcher.py
    - python api_data_fetcher.py output/mi_csv_modificado.csv
    """

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- MODO CSV LOCAL ---
    if len(sys.argv) > 1:
        df = fetch_data_local(sys.argv[1])

    # --- MODO API ---
    else:
        df = fetch_data_api()

    validate_data(df)

    # Guardar crudo solo si viene de API
    if len(sys.argv) == 1:
        save_raw_outputs(df, timestamp)

    df_clean = process_data(df)
    save_clean_csv(df_clean, timestamp)

    print("\n🎉 Pipeline finalizado exitosamente")
    print("=" * 60)


# =========================
# ▶️ ENTRY POINT
# =========================

if __name__ == "__main__":
    main()
