# ============================================================
# 🚀 API DATA FETCHER – ORQUESTADOR
# ============================================================

import sys
from datetime import datetime

# Importamos nuestros módulos reorganizados
from tu_proyecto.config import *
from tu_proyecto.fetchers.fetchers import fetch_data_api, fetch_data_local, fetch_data_shopify, process_data, save_raw, save_clean
from tu_proyecto.alerts.alerts import alert_missing_data, alert_low_stock
from tu_proyecto.diagnostics.diagnostics import backup_script, validate_data


# =========================
# 🧠 MAIN
# =========================

def main():
    # 💾 Backup automático al inicio
    backup_script(__file__)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # =========================
    # 🔁 SELECCIÓN DE FUENTE
    # =========================

    if len(sys.argv) > 1:
        source = sys.argv[1]

        if source == "shopify":
            df = fetch_data_shopify()
            save_raw(df, ts)
        else:
            df = fetch_data_local(source)
            save_raw(df, ts)
    else:
        df = fetch_data_api()
        save_raw(df, ts)

    # =========================
    # 🔍 VALIDACIÓN
    # =========================
    validate_data(df)

    # -------------------------
    # 🚨 ALERTAS
    # -------------------------
    alert_missing_data(df)
    alert_low_stock(df, LOW_STOCK_THRESHOLD)

    # =========================
    # 📊 PROCESAMIENTO Y GUARDADO LIMPIO
    # =========================
    df_clean = process_data(df)
    save_clean(df_clean, ts)

    print("\n🎉 Pipeline finalizado correctamente")
    print("=" * 60)

# =========================
# ▶️ ENTRY POINT
# =========================

if __name__ == "__main__":
    main()
