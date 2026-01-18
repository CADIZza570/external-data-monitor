#!/usr/bin/env python3
"""
🔧 MIGRACIÓN DE BASE DE DATOS - CASH FLOW v1.0

Agrega columnas necesarias para el sistema de Cash Flow:
- cost_price: Costo de adquisición del producto
- last_sale_date: Última fecha de venta
- total_sales_30d: Total de ventas en últimos 30 días
- category: Clasificación ABC del producto

Ejecutar una sola vez: python migrate_db_cashflow.py
"""

import sqlite3
import os
from datetime import datetime

# Usar el mismo archivo DB que database.py
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"

# Crear directorio si no existe
os.makedirs(DATA_DIR, exist_ok=True)

def migrate_database():
    """
    Migra la base de datos agregando columnas para Cash Flow.
    Usa ALTER TABLE ADD COLUMN IF NOT EXISTS (seguro ejecutar múltiples veces).
    """
    print("🔧 Iniciando migración de base de datos...")
    print(f"📁 DB File: {DB_FILE}")

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Lista de columnas a agregar
        migrations = [
            ("cost_price", "REAL DEFAULT 0", "Costo de adquisición"),
            ("last_sale_date", "TIMESTAMP", "Última fecha de venta"),
            ("total_sales_30d", "INTEGER DEFAULT 0", "Ventas últimos 30 días"),
            ("category", "TEXT DEFAULT 'C'", "Clasificación ABC (A/B/C)"),
            ("velocity_daily", "REAL DEFAULT 0", "Velocidad de ventas diaria (VDP)")
        ]

        # Verificar qué columnas ya existen
        cursor.execute("PRAGMA table_info(products)")
        existing_columns = [row[1] for row in cursor.fetchall()]

        print(f"✅ Columnas existentes: {existing_columns}")

        # Agregar cada columna si no existe
        for column_name, column_type, description in migrations:
            if column_name not in existing_columns:
                try:
                    sql = f"ALTER TABLE products ADD COLUMN {column_name} {column_type}"
                    cursor.execute(sql)
                    print(f"✅ Columna agregada: {column_name} ({description})")
                except sqlite3.OperationalError as e:
                    # Si la columna ya existe, continuar
                    if "duplicate column name" in str(e).lower():
                        print(f"⚠️  Columna ya existe: {column_name}")
                    else:
                        raise
            else:
                print(f"⏭️  Columna ya existe: {column_name}")

        conn.commit()

        # Verificar estado final
        cursor.execute("PRAGMA table_info(products)")
        final_columns = [row[1] for row in cursor.fetchall()]

        print("\n📊 ESTADO FINAL DE LA TABLA 'products':")
        print(f"Total de columnas: {len(final_columns)}")
        print(f"Columnas: {final_columns}")

        # Crear tabla de costos si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL UNIQUE,
                cost_price REAL NOT NULL,
                supplier TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        ''')
        print("\n✅ Tabla 'product_costs' verificada/creada")

        # Crear tabla de órdenes históricas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                product_id TEXT NOT NULL,
                sku TEXT,
                quantity INTEGER NOT NULL,
                price REAL,
                total_price REAL,
                order_date TIMESTAMP NOT NULL,
                shop TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(order_id, product_id, shop)
            )
        ''')
        print("✅ Tabla 'orders_history' verificada/creada")

        conn.commit()
        conn.close()

        print("\n🎉 MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR EN MIGRACIÓN: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
