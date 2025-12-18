import requests
import pandas as pd
import logging
import os
from datetime import datetime

# ========================= CONFIGURACIÓN =========================
API_URL = "https://jsonplaceholder.typicode.com/users"  # detalle de api
OUTPUT_DIR = "output"
LOG_FILE = "api_data_fetcher.log"

# Columnas que esperamos como mínimo (ajusta según la API que uses después)
REQUIRED_COLUMNS = ["id", "name", "username", "email"] 

# Configuración de logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Crear carpeta output si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ========================= FUNCIONES =========================
def fetch_data(url: str) -> pd.DataFrame:
    """Obtiene datos de la API y los convierte en DataFrame."""
    logging.info(f"Iniciando solicitud a la API: {url}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Conectando a la API...")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Lanza excepción si hay error HTTP
        data = response.json()
        
        # Convertir a DataFrame
        df = pd.DataFrame(data)
        
        logging.info(f"Datos obtenidos exitosamente. Filas: {len(df)}")
        print(f"✅ Datos descargados: {len(df)} registros")
        return df
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Error en la solicitud HTTP: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
    except ValueError as e:
        error_msg = f"Respuesta no es JSON válido: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
    except Exception as e:
        error_msg = f"Error inesperado al obtener datos: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que el DataFrame tenga las columnas requeridas y maneja nulos."""
    logging.info("Iniciando validación de datos")
    print("Validando estructura de datos...")
    
    # Verificar columnas requeridas
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        error_msg = f"Columnas obligatorias faltantes: {missing_cols}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    # Advertencia de valores nulos en columnas críticas
    critical_nulls = df[REQUIRED_COLUMNS].isnull().any()
    if critical_nulls.any():
        null_cols = critical_nulls[critical_nulls].index.tolist()
        warning_msg = f"Advertencia: Valores nulos en columnas críticas: {null_cols}"
        logging.warning(warning_msg)
        print(f"⚠️  {warning_msg}")
    
    logging.info("Validación completada exitosamente")
    print("✅ Validación exitosa")
    return df


def save_data(df: pd.DataFrame):
    """Guarda los datos en CSV y JSON con nombres claros y timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    csv_path = os.path.join(OUTPUT_DIR, f"users_data_{timestamp}.csv")
    json_path = os.path.join(OUTPUT_DIR, f"users_data_{timestamp}.json")
    
    try:
        df.to_csv(csv_path, index=False)
        df.to_json(json_path, orient="records", indent=2, force_ascii=False)
        
        logging.info(f"Datos guardados correctamente: {csv_path} y {json_path}")
        print(f"✅ CSV guardado: {csv_path}")
        print(f"✅ JSON guardado: {json_path}")
    
    except Exception as e:
        error_msg = f"Error al guardar archivos: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise


def main():
    """Función principal del script."""
    print("🚀 Iniciando api_data_fetcher.py - Proyecto Línea Base (Mes 1)")
    logging.info("=== NUEVA EJECUCIÓN DEL SCRIPT ===")
    
    try:
        df = fetch_data(API_URL)
        df = validate_data(df)
        save_data(df)
        
        print("🎉 Script completado con éxito. Revisa la carpeta 'output/' y el log.")
        logging.info("Script finalizado exitosamente")
    
    except Exception as e:
        print("💥 El script falló. Revisa api_data_fetcher.log para detalles.")
        logging.critical(f"Script falló completamente: {e}")


if __name__ == "__main__":
    main()