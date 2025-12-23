import os

# =========================
# CONFIGURACIÓN
# =========================
BASE_DIR = os.getcwd()  # ~/Documents/python-automation/tu_proyecto

folders = {
    "fetchers": {
        "__init__.py": "",
        "fetchers.py": """import pandas as pd
# Código base de fetchers
def fetch_data_local(path):
    print(f"📂 Cargando CSV: {path}")
    return pd.read_csv(path)

def fetch_data_shopify():
    print("🛒 Fetch Shopify simulado")
    return pd.DataFrame()

def process_data(df):
    print("📊 Procesando datos en fetchers")
    return df
"""
    },
    "alerts": {
        "__init__.py": "",
        "alerts.py": """# Código base de alertas
def alert_missing_data(df):
    print("🚨 Revisando filas incompletas")

def alert_low_stock(df):
    print("🚨 Revisando stock bajo")

def alert_no_sales(df):
    print("🚨 Revisando productos sin ventas")
"""
    },
    "diagnostics": {
        "__init__.py": "",
        "diagnostics.py": """import pandas as pd
from datetime import datetime
import os

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    print("📊 Procesando datos...")
    return df

def save_clean(df: pd.DataFrame, ts: str = None):
    ts = ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{OUTPUT_DIR}/data_clean_{ts}.csv"
    df.to_csv(path, index=False)
    print(f"✅ CSV limpio guardado: {path}")

def save_raw(df: pd.DataFrame, ts: str = None):
    ts = ts or datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = f"{OUTPUT_DIR}/data_raw_{ts}.csv"
    df.to_csv(csv_path, index=False)
    print(f"💾 CSV guardado: {csv_path}")
"""
    }
}

# =========================
# CREAR CARPETAS Y ARCHIVOS
# =========================
for folder, files in folders.items():
    folder_path = os.path.join(BASE_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    for filename, content in files.items():
        file_path = os.path.join(folder_path, filename)
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(content)
            print(f"✅ Archivo creado: {file_path}")
        else:
            print(f"ℹ️ Archivo ya existe, se omite: {file_path}")

print("\n🎉 Estructura y módulos base listos")
