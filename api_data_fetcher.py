import requests
import pandas as pd
import logging
import os
import json
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException

# ========================= CONFIGURACIÓN =========================
API_URL = "https://jsonplaceholder.typicode.com/users"
OUTPUT_DIR = "output"
LOG_FILE = "api_data_fetcher.log"
REQUIRED_COLUMNS = ["id", "name", "username", "email"]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========================= API =========================

def fetch_data(url: str) -> pd.DataFrame:
    """Obtiene datos desde la API con reintentos automáticos (Mes 1 + 4)."""
    logging.info(f"Solicitando datos a {url}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 Conectando a la API...")
    
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.mount("http://", HTTPAdapter(max_retries=retries))
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        
        logging.info(f"✅ Datos obtenidos exitosamente. Filas: {len(df)}")
        print(f"✅ Datos descargados: {len(df)} registros")
        return df
        
    except requests.exceptions.Timeout:
        error_msg = f"⏱️ Timeout al conectar (>10s)"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP {response.status_code}: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    except RequestException as e:
        error_msg = f"Error de conexión: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    finally:
        session.close()

# ========================= VALIDACIÓN =========================

def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida columnas mínimas requeridas (Mes 1)."""
    logging.info("Iniciando validación de datos")
    print("🔍 Validando estructura de datos...")
    
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        error_msg = f"Faltan columnas requeridas: {missing}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Advertencia de nulos
    critical_nulls = df[REQUIRED_COLUMNS].isnull().any()
    if critical_nulls.any():
        null_cols = critical_nulls[critical_nulls].index.tolist()
        warning_msg = f"⚠️ Valores nulos en: {null_cols}"
        logging.warning(warning_msg)
        print(warning_msg)
    
    logging.info("✅ Validación exitosa")
    print("✅ Validación exitosa")
    return df

# ========================= PERSISTENCIA =========================

def save_data(df: pd.DataFrame) -> str:
    """Guarda CSV y JSON con timestamp (Mes 1)."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"users_data_{ts}.csv")
    json_path = os.path.join(OUTPUT_DIR, f"users_data_{ts}.json")
    
    try:
        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        
        logging.info(f"Datos guardados: {csv_path}")
        print(f"💾 CSV guardado: {csv_path}")
        print(f"💾 JSON guardado: {json_path}")
        return csv_path
        
    except Exception as e:
        error_msg = f"Error al guardar archivos: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise

# ========================= PROCESAMIENTO =========================

def process_data(csv_path: str) -> str:
    """Limpieza y normalización de datos con Pandas (Mes 2)."""
    print("\n📊 Iniciando procesamiento de datos...")
    logging.info("Iniciando procesamiento con Pandas")
    
    df = pd.read_csv(csv_path)
    before_rows = len(df)
    print(f"Registros originales: {before_rows}")
    
    # Seleccionar columnas útiles
    useful_cols = ["id", "name", "username", "email", "phone", "website", "address"]
    df_clean = df[useful_cols].copy()
    
    # Extraer ciudad (CORREGIDO para CSV - no dict directo)
    def extract_city(address_str):
        """Extrae city de string que representa dict."""
        try:
            # Convertir string a dict de forma segura
            address_dict = json.loads(address_str.replace("'", '"'))
            return address_dict.get('city', 'Unknown')
        except (json.JSONDecodeError, AttributeError, TypeError):
            return "Unknown"
    
    df_clean["city"] = df_clean["address"].apply(extract_city)
    df_clean = df_clean.drop(columns=["address"])
    
    # Limpieza estándar
    df_clean = df_clean.drop_duplicates(subset=["email"])
    df_clean["email"] = df_clean["email"].str.lower()
    df_clean = df_clean[df_clean["email"].str.contains("@", na=False)]
    
    after_rows = len(df_clean)
    eliminated = before_rows - after_rows
    
    # Reporte
    print(f"Registros limpios: {after_rows}")
    print(f"Duplicados eliminados: {eliminated}")
    print(f"Nueva columna: city")
    
    report = f"""Limpieza completada:
- Originales: {before_rows}
- Limpios: {after_rows}
- Eliminados: {eliminated}
- Columnas finales: {', '.join(df_clean.columns)}"""
    
    logging.info(report)
    
    # Guardar versión limpia
    clean_path = csv_path.replace(".csv", "_clean.csv")
    df_clean.to_csv(clean_path, index=False)
    print(f"✅ CSV limpio guardado: {clean_path}")
    
    return clean_path

# ========================= ORQUESTACIÓN =========================

def main():
    """Ejecuta el flujo completo de datos (lógica pura, sin automatización)."""
    print("="*60)
    print("🚀 API Data Fetcher - Proyecto Línea Base (Mes 1-2)")
    print("="*60)
    logging.info("=== NUEVA EJECUCIÓN DEL SCRIPT ===")
    
    try:
        # Pipeline completo
        df = fetch_data(API_URL)
        df = validate_data(df)
        csv_path = save_data(df)
        clean_path = process_data(csv_path)
        
        # Resumen final
        print("\n" + "="*60)
        print("🎉 Pipeline finalizado exitosamente")
        print("="*60)
        print(f"📂 Original: {csv_path}")
        print(f"📂 Limpio:   {clean_path}")
        print(f"📋 Log:      {LOG_FILE}")
        print("="*60)
        
        logging.info("✅ Script finalizado exitosamente")
        
    except Exception as e:
        print("\n" + "="*60)
        print("💥 El script falló")
        print("="*60)
        print(f"Error: {e}")
        print(f"📋 Revisa {LOG_FILE} para más detalles")
        print("="*60)
        
        logging.critical(f"❌ Script falló: {e}")
        raise


if __name__ == "__main__":
    main()