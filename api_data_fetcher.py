import requests
import pandas as pd
import logging
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException

# ========================= CONFIGURACIÓN =========================
API_URL = API_URL = "https://jsonplaceholder.typicode.com/users"  # detalle de api
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
    """Obtiene datos de la API con reintentos automáticos.
    
    Estrategia de resiliencia:
    - 3 reintentos máximo
    - Espera progresiva: 1s, 2s, 4s (backoff exponencial)
    - Solo reintenta en errores de servidor (500, 502, 503, 504)
    
    Args:
        url: URL de la API a consumir
        
    Returns:
        DataFrame con los datos obtenidos
        
    Raises:
        RequestException: Si todos los reintentos fallan
    """
    logging.info(f"Iniciando solicitud a la API: {url}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Conectando a la API...")
    
    # Configurar sesión con reintentos automáticos
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        df = pd.DataFrame(data)
        
        logging.info(f"Datos obtenidos exitosamente. Filas: {len(df)}")
        print(f"✅ Datos descargados: {len(df)} registros")
        return df
        
    except requests.exceptions.Timeout:
        error_msg = f"Timeout al conectar con {url} (>10s)"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Error de conexión: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"Error HTTP {response.status_code}: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise
        
    except RequestException as e:
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
    finally:
        session.close()

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
        print(f"⚠️ {warning_msg}")
    
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
        
        return csv_path  # <--- ESTO ES LO QUE FALTABA
    
    except Exception as e:
        error_msg = f"Error al guardar archivos: {e}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise

def validate_required_fields(df: pd.DataFrame) -> bool:
    """Verifica que el DataFrame tenga todas las columnas críticas.
    
    Esta función es la primera línea de defensa antes de procesar datos.
    Si faltan columnas esenciales, es mejor fallar rápido que continuar
    con datos incompletos.
    
    Args:
        df: DataFrame a validar
        
    Returns:
        True si todas las columnas requeridas están presentes
        
    Raises:
        ValueError: Si faltan columnas críticas
        
    Example:
        >>> df = pd.DataFrame({"id": [1], "name": ["Ana"]})
        >>> validate_required_fields(df)
        ValueError: Columnas obligatorias faltantes: ['email']
    """
    logging.info("Validando campos requeridos en DataFrame")
    
    # Columnas mínimas necesarias (ajusta según tu caso)
    required_fields = ["id", "name", "email"]
    
    # Identificar columnas faltantes
    missing_fields = [field for field in required_fields if field not in df.columns]
    
    if missing_fields:
        error_msg = f"Columnas obligatorias faltantes: {missing_fields}"
        logging.error(error_msg)
        print(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    logging.info(f"✅ Todas las columnas requeridas presentes: {required_fields}")
    print(f"✅ Validación de campos: OK")
    
    # Validación adicional: detectar columnas completamente vacías
    empty_cols = df.columns[df.isnull().all()].tolist()
    if empty_cols:
        warning_msg = f"Advertencia: Columnas completamente vacías: {empty_cols}"
        logging.warning(warning_msg)
        print(f"⚠️ {warning_msg}")
    
    return True

def main():
    """Función principal del script."""
    print("🚀 Iniciando api_data_fetcher.py - Proyecto Línea Base (Mes 1-2)")
    logging.info("=== NUEVA EJECUCIÓN DEL SCRIPT ===")
    
    try:
        df = fetch_data(API_URL)
        df = validate_data(df)
        csv_path = save_data(df)  # save_data ahora devuelve la ruta del CSV
        
        # MES 2: Procesar datos con Pandas
        clean_path = process_data(csv_path)
        
        print("🎉 Script completado con éxito. Revisa la carpeta 'output/' y el log.")
        print(f"   - Original: {csv_path}")
        print(f"   - Limpio: {clean_path}")
        logging.info("Script finalizado exitosamente")
    
    except Exception as e:
        print("💥 El script falló. Revisa api_data_fetcher.log para detalles.")
        logging.critical(f"Script falló completamente: {e}")

import pandas as pd

def process_data(csv_path: str):
    """Procesa y limpia el CSV generado (Mes 2 - Pandas mínimo viable)."""
    print("Iniciando procesamiento de datos con Pandas...")
    logging.info("Iniciando procesamiento de datos con Pandas")

    # Leer el CSV
    df = pd.read_csv(csv_path)
    before_rows = len(df)
    print(f"Registros originales: {before_rows}")

    # Limpieza mínima viable (Mes 2)
    # 1. Seleccionar columnas útiles (incluyendo address para extraer city)
    useful_columns = ["id", "name", "username", "email", "phone", "website", "address"]
    df_clean = df[useful_columns].copy()

    # 2. Extraer "city" del address anidado (es un string dict, lo parseamos)
    def extract_city(address_str):
        try:
            # Convertir el string dict a dict real
            address = eval(address_str)  # Seguro porque es datos confiables de JSONPlaceholder
            return address['city']
        except:
            return "Unknown"  # Fallback si falla

    df_clean['city'] = df_clean['address'].apply(extract_city)

    # 3. Eliminar la columna address original (ya extrajimos city)
    df_clean = df_clean.drop(columns=['address'])

    # 4. Eliminar duplicados por email
    df_clean = df_clean.drop_duplicates(subset=["email"])

    # 5. Estandarizar emails a minúsculas
    df_clean.loc[:, "email"] = df_clean["email"].str.lower()

    # 6. Filtrar emails válidos (contienen @)
    df_clean = df_clean[df_clean["email"].str.contains("@")]

    after_rows = len(df_clean)
    print(f"Registros después de limpieza: {after_rows}")
    print(f"Registros eliminados/duplicados: {before_rows - after_rows}")

    # Reporte simple
    report = f"""
REPORTE DE LIMPIEZA (Mes 2)
- Registros originales: {before_rows}
- Registros limpios: {after_rows}
- Duplicados/eliminados: {before_rows - after_rows}
- Columnas seleccionadas: {', '.join(df_clean.columns)}
- Nueva columna extraída: city
"""
    print(report)
    logging.info(report.strip())

    # Guardar versión limpia
    clean_path = csv_path.replace(".csv", "_clean.csv")
    df_clean.to_csv(clean_path, index=False)
    print(f"✅ CSV limpio guardado: {clean_path}")

    return clean_path

import schedule
import time

def run_full_pipeline():
    """Ejecuta el flujo completo del script."""
    print("\n" + "="*50)
    print("EJECUCIÓN AUTOMÁTICA PROGRAMADA")
    print("="*50)
    logging.info("=== EJECUCIÓN AUTOMÁTICA PROGRAMADA ===")
    
    main()  # Tu función main() ya tiene todo el flujo

if __name__ == "__main__":
    print("🚀 Iniciando daemon con schedule - Proyecto Línea Base (Mes 3)")
    logging.info("Daemon iniciado con schedule")
    
    # PROGRAMACIÓN (ajusta según quieras probar)
    # Cada 10 minutos (para pruebas rápidas)
    schedule.every(10).minutes.do(run_full_pipeline)
    
    # O cada hora
    # schedule.every().hour.do(run_full_pipeline)
    
    # O todos los días a las 9:00 AM
    # schedule.every().day.at("09:00").do(run_full_pipeline)
    
    # Ejecución inicial inmediata
    run_full_pipeline()
    
    # Loop infinito que revisa si hay jobs pendientes
    while True:
        schedule.run_pending()
        time.sleep(60)  # Revisa cada minuto (bajo consumo)