#!/usr/bin/env python3
"""
🔧 SCRIPT DE MIGRACIÓN FORZADA
Ejecuta ALTER TABLE para agregar columnas faltantes a products.

Uso:
    python3 run_migration.py

Este script se ejecuta automáticamente al arrancar Railway si se agrega
al Procfile o se llama desde webhook_server.py
"""

import sqlite3
import os

# Ruta de la DB
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = os.path.join(DATA_DIR, "webhooks.db")

def run_migration():
    """Ejecuta migración forzada de columnas analytics."""
    print("=" * 60)
    print("🔧 INICIANDO MIGRACIÓN FORZADA DE COLUMNAS")
    print("=" * 60)

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Lista de columnas a agregar
        migrations = [
            ("velocity_daily", "REAL DEFAULT 0"),
            ("category", "TEXT DEFAULT 'C'"),
            ("cost_price", "REAL"),
            ("last_sale_date", "TIMESTAMP"),
            ("total_sales_30d", "INTEGER DEFAULT 0")
        ]

        added_count = 0
        exists_count = 0
        error_count = 0

        for col_name, col_type in migrations:
            try:
                cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
                conn.commit()
                print(f"✅ Columna '{col_name}' agregada exitosamente")
                added_count += 1
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"✓ Columna '{col_name}' ya existe")
                    exists_count += 1
                elif "no such table" in str(e).lower():
                    print(f"⚠️ Tabla 'products' no existe aún - migración pendiente para próximo arranque")
                    error_count += 1
                    break  # No continuar si la tabla no existe
                else:
                    print(f"❌ Error en columna '{col_name}': {e}")
                    error_count += 1

        # Verificar columnas finales
        try:
            cursor.execute("PRAGMA table_info(products)")
            columns = [row[1] for row in cursor.fetchall()]
            print("\n📊 Columnas actuales en tabla products:")
            for col in columns:
                marker = "🆕" if col in ['velocity_daily', 'category', 'cost_price', 'last_sale_date', 'total_sales_30d'] else "  "
                print(f"  {marker} {col}")
        except sqlite3.OperationalError:
            print("⚠️ No se pudo obtener lista de columnas (tabla puede no existir)")

        conn.close()

        print("\n" + "=" * 60)
        print(f"✅ MIGRACIÓN COMPLETADA")
        print(f"   Agregadas: {added_count}")
        print(f"   Ya existían: {exists_count}")
        print(f"   Errores: {error_count}")
        print("=" * 60)

        return added_count > 0 or exists_count > 0

    except Exception as e:
        print(f"\n❌ ERROR FATAL EN MIGRACIÓN: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
