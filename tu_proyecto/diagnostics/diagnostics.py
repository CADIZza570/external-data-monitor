# ============================================================
# 🧠 DIAGNOSTICS MODULE
# ============================================================
# Responsabilidades:
# - Guardar datos raw
# - Guardar datos limpios
# - Procesamiento base de DataFrame
# ============================================================

import os
import pandas as pd
from datetime import datetime
import logging

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def save_raw(df: pd.DataFrame, prefix: str = "raw_data"):
    """
    Guarda datos originales (raw) en CSV
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{OUTPUT_DIR}/{prefix}_{ts}.csv"
    df.to_csv(path, index=False)
    logging.info(f"Raw data guardado en {path}")
    print(f"💾 Raw guardado: {path}")
    return path


def save_clean(df: pd.DataFrame, prefix: str = "clean_data"):
    """
    Guarda datos procesados/limpios en CSV
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{OUTPUT_DIR}/{prefix}_{ts}.csv"
    df.to_csv(path, index=False)
    logging.info(f"Clean data guardado en {path}")
    print(f"✅ Clean guardado: {path}")
    return path


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Procesamiento mínimo:
    - Elimina duplicados
    - Resetea índice
    """
    original = len(df)
    df_clean = df.drop_duplicates().reset_index(drop=True)
    print(f"📊 Procesamiento: {original} → {len(df_clean)} filas")
    return df_clean


