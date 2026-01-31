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

        # ============= PASO 0: Crear tabla products si no existe =============
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                sku TEXT,
                stock INTEGER DEFAULT 0,
                price REAL,
                shop TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(product_id, shop)
            )
        ''')
        conn.commit()
        print("✅ Tabla 'products' verificada/creada")
        # ====================================================================

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

        # Crear tabla de historial de ventas (para trending)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                product_name TEXT,
                quantity INTEGER NOT NULL,
                sale_date TIMESTAMP NOT NULL,
                order_id TEXT,
                shop TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Tabla 'sales_history' verificada/creada")

        # Crear tabla de insights (para cacheo de análisis)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                UNIQUE(type)
            )
        ''')
        print("✅ Tabla 'insights' verificada/creada")

        # Crear índice para búsquedas eficientes de insights
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_insights_type_expires
            ON insights(type, expires_at)
        ''')
        print("✅ Índice 'idx_insights_type_expires' verificado/creado")

        # ============================================================================
        # 🧠 TIBURÓN EVOLUTIVO - Tabla de Métricas de Interacción
        # ============================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interaction_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT DEFAULT 'fer',
                button_id TEXT NOT NULL,
                action_type TEXT,
                context TEXT,
                sku TEXT,
                units INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        print("✅ Tabla 'interaction_metrics' verificada/creada")

        # Crear índices para consultas rápidas
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_interaction_user_timestamp
            ON interaction_metrics(user_id, timestamp DESC)
        ''')
        print("✅ Índice 'idx_interaction_user_timestamp' verificado/creado")

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_interaction_button
            ON interaction_metrics(button_id, timestamp DESC)
        ''')
        print("✅ Índice 'idx_interaction_button' verificado/creado")

        # ============================================================================
        # 📊 POST-MORTEM - Tabla de Análisis de Silencios
        # ============================================================================
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS freeze_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                freeze_timestamp TIMESTAMP NOT NULL,
                thaw_timestamp TIMESTAMP,
                frozen_by TEXT,
                thawed_by TEXT,
                reason TEXT,
                duration_hours REAL,
                opportunity_cost REAL,
                post_mortem_sent BOOLEAN DEFAULT 0,
                post_mortem_timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        print("✅ Tabla 'freeze_sessions' verificada/creada")

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
