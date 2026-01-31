#!/usr/bin/env python3
"""
🌱 SEED REAL DATA - Columbus, Ohio Winter Catalog
Popula DB con productos reales basados en clima frío Columbus + datos realistas
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

DB_FILE = "./webhooks.db"

# Productos para Columbus, Ohio (invierno frío -20°C)
COLUMBUS_WINTER_PRODUCTS = [
    # 🔥 Categoría A: Alta rotación + clima extremo
    {
        "product_id": "WINTER-001",
        "name": "Chaqueta Térmica Winter Pro",
        "sku": "JACKET-WINTER-01",
        "stock": 12,  # Stock bajo → oportunidad
        "price": 189.99,
        "cost_price": 95.00,
        "velocity_daily": 3.2,  # ~96 unidades/mes
        "total_sales_30d": 96,
        "total_sales_60d": 180,
        "category": "A",
        "supplier": "Winter Gear Supply Co.",
        "lead_time_days": 7,
        "moq": 25,
        "notes": "Alta demanda por frío extremo Columbus"
    },
    {
        "product_id": "WINTER-002",
        "name": "Boots Waterproof Premium",
        "sku": "BOOTS-WP-01",
        "stock": 8,  # Stock crítico
        "price": 159.99,
        "cost_price": 80.00,
        "velocity_daily": 2.8,  # ~84 unidades/mes
        "total_sales_30d": 84,
        "total_sales_60d": 160,
        "category": "A",
        "supplier": "FootGear Wholesale",
        "lead_time_days": 10,
        "moq": 30,
        "notes": "Spike por nieve Columbus"
    },
    {
        "product_id": "WINTER-003",
        "name": "Guantes Térmicos Arctic",
        "sku": "GLOVES-ARC-01",
        "stock": 25,
        "price": 45.99,
        "cost_price": 18.00,
        "velocity_daily": 4.5,  # ~135 unidades/mes
        "total_sales_30d": 135,
        "total_sales_60d": 250,
        "category": "A",
        "supplier": "Winter Gear Supply Co.",
        "lead_time_days": 5,
        "moq": 50,
        "notes": "Producto estrella invierno"
    },

    # 💼 Categoría B: Rotación media
    {
        "product_id": "WINTER-004",
        "name": "Bufanda Lana Merino",
        "sku": "SCARF-WOOL-01",
        "stock": 40,
        "price": 39.99,
        "cost_price": 15.00,
        "velocity_daily": 1.8,  # ~54 unidades/mes
        "total_sales_30d": 54,
        "total_sales_60d": 100,
        "category": "B",
        "supplier": "Textile Partners Inc.",
        "lead_time_days": 14,
        "moq": 40,
        "notes": "Demanda estable invierno"
    },
    {
        "product_id": "WINTER-005",
        "name": "Gorro Térmico Fleece",
        "sku": "HAT-FLEECE-01",
        "stock": 60,
        "price": 29.99,
        "cost_price": 10.00,
        "velocity_daily": 2.1,  # ~63 unidades/mes
        "total_sales_30d": 63,
        "total_sales_60d": 120,
        "category": "B",
        "supplier": "Winter Gear Supply Co.",
        "lead_time_days": 7,
        "moq": 60,
        "notes": "Accesorio popular"
    },
    {
        "product_id": "WINTER-006",
        "name": "Abrigo Invierno Classic",
        "sku": "COAT-CLASSIC-01",
        "stock": 15,
        "price": 249.99,
        "cost_price": 130.00,
        "velocity_daily": 1.2,  # ~36 unidades/mes
        "total_sales_30d": 36,
        "total_sales_60d": 70,
        "category": "B",
        "supplier": "Premium Outerwear Ltd.",
        "lead_time_days": 14,
        "moq": 20,
        "notes": "Precio alto pero margen excelente"
    },

    # 🐌 Categoría C: Rotación baja
    {
        "product_id": "WINTER-007",
        "name": "Calentadores Manos Desechables",
        "sku": "WARMERS-HAND-01",
        "stock": 200,
        "price": 12.99,
        "cost_price": 4.00,
        "velocity_daily": 0.8,  # ~24 unidades/mes
        "total_sales_30d": 24,
        "total_sales_60d": 45,
        "category": "C",
        "supplier": "Bulk Supplies Co.",
        "lead_time_days": 3,
        "moq": 100,
        "notes": "Complemento bajo margen"
    },
    {
        "product_id": "WINTER-008",
        "name": "Termo Acero Inoxidable 500ml",
        "sku": "THERMO-500-01",
        "stock": 80,
        "price": 34.99,
        "cost_price": 15.00,
        "velocity_daily": 0.5,  # ~15 unidades/mes
        "total_sales_30d": 15,
        "total_sales_60d": 28,
        "category": "C",
        "supplier": "Kitchen & Home Depot",
        "lead_time_days": 10,
        "moq": 50,
        "notes": "Venta ocasional"
    },

    # ⚰️ Dead Stock: Sin ventas
    {
        "product_id": "SUMMER-001",
        "name": "Sandalias Verano Beach",
        "sku": "SANDALS-BEACH-01",
        "stock": 150,  # Inventario muerto invierno
        "price": 49.99,
        "cost_price": 20.00,
        "velocity_daily": 0.0,  # Cero ventas en invierno
        "total_sales_30d": 0,
        "total_sales_60d": 1,  # Solo 1 venta hace 60 días
        "category": "Dead",
        "supplier": "Summer Fashion Inc.",
        "lead_time_days": 21,
        "moq": 100,
        "notes": "Dead stock invierno - considerar liquidación"
    },
    {
        "product_id": "SUMMER-002",
        "name": "Gorra Baseball UV Protection",
        "sku": "CAP-UV-01",
        "stock": 120,
        "price": 24.99,
        "cost_price": 8.00,
        "velocity_daily": 0.02,  # ~0.6 unidades/mes
        "total_sales_30d": 1,
        "total_sales_60d": 2,
        "category": "Dead",
        "supplier": "Summer Fashion Inc.",
        "lead_time_days": 14,
        "moq": 80,
        "notes": "Temporada incorrecta - muerto"
    }
]


def create_tables_if_needed(conn):
    """Asegurar que existan todas las tablas necesarias"""
    cursor = conn.cursor()

    # Tabla products (ya debería existir, pero por si acaso)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            stock INTEGER DEFAULT 0,
            price REAL,
            cost_price REAL,
            velocity_daily REAL DEFAULT 0,
            total_sales_30d INTEGER DEFAULT 0,
            total_sales_60d INTEGER DEFAULT 0,
            category TEXT,
            shop TEXT DEFAULT 'columbus-shop',
            last_updated TEXT,
            last_sale_date TEXT
        )
    """)

    # Tabla suppliers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (
            supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            lead_time_days INTEGER DEFAULT 14,
            minimum_order_qty INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabla product_suppliers (relación producto-proveedor)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            lead_time_days INTEGER,
            moq INTEGER,
            cost_price REAL,
            notes TEXT,
            FOREIGN KEY (sku) REFERENCES products(sku)
        )
    """)

    # Tabla sales_history (schema existente - no recrear)
    # Ya existe con columnas: sku, product_name, quantity, sale_date, order_id, shop
    pass

    conn.commit()


def seed_products(conn):
    """Poblar productos Columbus winter catalog"""
    cursor = conn.cursor()

    print("\n📦 Seeding productos Columbus Winter Catalog...")

    for p in COLUMBUS_WINTER_PRODUCTS:
        # Insertar producto
        cursor.execute("""
            INSERT OR REPLACE INTO products
            (product_id, name, sku, stock, price, cost_price, velocity_daily,
             total_sales_30d, total_sales_60d, category, shop, last_updated, last_sale_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p['product_id'],
            p['name'],
            p['sku'],
            p['stock'],
            p['price'],
            p['cost_price'],
            p['velocity_daily'],
            p['total_sales_30d'],
            p.get('total_sales_60d', p['total_sales_30d'] * 2),
            p['category'],
            'columbus-shop',
            datetime.now().isoformat(),
            (datetime.now() - timedelta(days=1)).isoformat() if p['velocity_daily'] > 0 else None
        ))

        print(f"  ✅ {p['name']} ({p['sku']}) - Cat {p['category']} - Vel {p['velocity_daily']:.1f}/día")

    conn.commit()
    print(f"\n✅ {len(COLUMBUS_WINTER_PRODUCTS)} productos insertados\n")


def seed_suppliers(conn):
    """Poblar proveedores únicos"""
    cursor = conn.cursor()

    print("🏭 Seeding proveedores...")

    # Extraer proveedores únicos
    unique_suppliers = {}
    for p in COLUMBUS_WINTER_PRODUCTS:
        supplier = p['supplier']
        if supplier not in unique_suppliers:
            unique_suppliers[supplier] = {
                'lead_time': p['lead_time_days'],
                'moq': p['moq']
            }

    for supplier_name, info in unique_suppliers.items():
        cursor.execute("""
            INSERT OR REPLACE INTO suppliers (name, lead_time_days, minimum_order_qty, notes)
            VALUES (?, ?, ?, ?)
        """, (
            supplier_name,
            info['lead_time'],
            info['moq'],
            f"Proveedor catálogo Columbus Winter"
        ))

        print(f"  ✅ {supplier_name} - Lead time: {info['lead_time']}d, MOQ: {info['moq']}")

    conn.commit()
    print(f"\n✅ {len(unique_suppliers)} proveedores insertados\n")


def seed_product_suppliers(conn):
    """Relacionar productos con proveedores"""
    cursor = conn.cursor()

    print("🔗 Relacionando productos → proveedores...")

    for p in COLUMBUS_WINTER_PRODUCTS:
        cursor.execute("""
            INSERT OR REPLACE INTO product_suppliers
            (sku, supplier_name, lead_time_days, moq, cost_price, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            p['sku'],
            p['supplier'],
            p['lead_time_days'],
            p['moq'],
            p['cost_price'],
            p.get('notes', '')
        ))

    conn.commit()
    print(f"✅ {len(COLUMBUS_WINTER_PRODUCTS)} relaciones producto-proveedor creadas\n")


def seed_sales_history(conn):
    """Generar historial de ventas realista (últimos 60 días)"""
    cursor = conn.cursor()

    print("📊 Generando historial ventas (60 días)...")

    today = datetime.now()

    for p in COLUMBUS_WINTER_PRODUCTS:
        sku = p['sku']
        product_name = p['name']
        velocity = p['velocity_daily']
        price = p['price']

        if velocity == 0:
            print(f"  ⚰️ {sku}: Sin ventas (dead stock)")
            continue

        sales_count = 0

        # Generar ventas día a día (últimos 60 días)
        for days_ago in range(60, 0, -1):
            sale_date = today - timedelta(days=days_ago)

            # Variabilidad realista: ±30% de la velocity
            daily_sales = max(0, int(velocity + random.uniform(-velocity * 0.3, velocity * 0.3)))

            # Spike en días fríos extremos (simular -20°C hace 10-15 días)
            if 10 <= days_ago <= 15 and ('chaqueta' in p['name'].lower() or 'boots' in p['name'].lower()):
                daily_sales = int(daily_sales * 1.5)  # +50% spike frío

            if daily_sales > 0:
                # Generar múltiples registros si hay varias unidades vendidas ese día
                for sale_num in range(daily_sales):
                    order_id = f"ORD-{sale_date.strftime('%Y%m%d')}-{sku}-{sale_num:03d}"

                    cursor.execute("""
                        INSERT INTO sales_history (sku, product_name, quantity, sale_date, order_id, shop)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (sku, product_name, 1, sale_date.isoformat(), order_id, 'columbus-shop'))

                sales_count += daily_sales

        print(f"  ✅ {sku}: {sales_count} ventas en 60 días (vel {velocity:.1f}/día)")

    conn.commit()
    print(f"\n✅ Historial de ventas generado\n")


def print_summary(conn):
    """Mostrar resumen de datos seeded"""
    cursor = conn.cursor()

    print("\n" + "="*70)
    print("📊 RESUMEN SEED REAL DATA - Columbus Winter Catalog")
    print("="*70 + "\n")

    # Resumen por categoría
    cursor.execute("""
        SELECT category, COUNT(*), SUM(stock),
               ROUND(AVG(velocity_daily), 2),
               ROUND(SUM(stock * cost_price), 2)
        FROM products
        GROUP BY category
        ORDER BY
            CASE category
                WHEN 'A' THEN 1
                WHEN 'B' THEN 2
                WHEN 'C' THEN 3
                WHEN 'Dead' THEN 4
                ELSE 5
            END
    """)

    print("📦 PRODUCTOS POR CATEGORÍA:")
    print(f"{'Categoría':<10} {'Productos':<10} {'Stock Total':<12} {'Vel Promedio':<15} {'Valor Inv':<12}")
    print("-" * 70)

    for row in cursor.fetchall():
        cat, count, stock, avg_vel, inv_value = row
        print(f"{cat:<10} {count:<10} {stock:<12} {avg_vel:<15} ${inv_value:<11.2f}")

    # Top oportunidades ROI
    print("\n🎯 TOP OPORTUNIDADES ROI (Stock bajo + Alta velocity):")
    cursor.execute("""
        SELECT name, sku, stock, velocity_daily,
               ROUND((stock / NULLIF(velocity_daily, 0)), 1) as days_of_stock,
               category
        FROM products
        WHERE velocity_daily > 0
        ORDER BY days_of_stock ASC
        LIMIT 5
    """)

    print(f"{'Producto':<35} {'SKU':<18} {'Stock':<8} {'Vel/día':<10} {'Días Stock':<12}")
    print("-" * 70)

    for row in cursor.fetchall():
        name, sku, stock, vel, days, cat = row
        emoji = "🔥" if days < 5 else "⚠️" if days < 10 else "✅"
        print(f"{emoji} {name:<33} {sku:<18} {stock:<8} {vel:<10.1f} {days:<12.1f}")

    # Dead stock
    print("\n⚰️ DEAD STOCK (velocity = 0):")
    cursor.execute("""
        SELECT name, sku, stock, ROUND(stock * cost_price, 2) as dead_value
        FROM products
        WHERE velocity_daily = 0 OR category = 'Dead'
    """)

    for row in cursor.fetchall():
        name, sku, stock, value = row
        print(f"  💀 {name} ({sku}): {stock} unidades = ${value:.2f} muerto")

    # Total inventario
    cursor.execute("""
        SELECT
            ROUND(SUM(stock * cost_price), 2) as total_inventory_value,
            ROUND(SUM(CASE WHEN category = 'Dead' THEN stock * cost_price ELSE 0 END), 2) as dead_value
        FROM products
    """)

    total_inv, dead_inv = cursor.fetchone()

    print(f"\n💰 INVENTARIO TOTAL: ${total_inv:,.2f}")
    print(f"⚰️ Dead Stock: ${dead_inv:,.2f} ({(dead_inv/total_inv*100):.1f}%)")

    print("\n" + "="*70 + "\n")


def main():
    """Ejecutar seed completo"""
    print("\n" + "🌱" * 35)
    print("🦈 TIBURÓN PREDICTIVO - SEED REAL DATA")
    print("🌡️ Columbus, Ohio Winter Catalog (Clima: -20°C)")
    print("🌱" * 35 + "\n")

    if not os.path.exists(DB_FILE):
        print(f"⚠️ DB no encontrada: {DB_FILE}")
        print(f"Creando nueva DB...")

    conn = sqlite3.connect(DB_FILE)

    try:
        # 1. Crear tablas si no existen
        create_tables_if_needed(conn)

        # 2. Seed productos
        seed_products(conn)

        # 3. Seed proveedores
        seed_suppliers(conn)

        # 4. Relacionar productos-proveedores
        seed_product_suppliers(conn)

        # 5. Generar historial ventas
        seed_sales_history(conn)

        # 6. Mostrar resumen
        print_summary(conn)

        print("✅ SEED COMPLETADO - DB lista para Tiburón Predictivo!")
        print("\n🎯 Próximos pasos:")
        print("  1. python3 pulse_scheduler.py --now --dry-run")
        print("  2. Ver Sticker con ROI real productos Columbus")
        print("  3. Verificar multiplicador clima frío (-20°C)")
        print("\n🦈 ¡El Tiburón está listo para cazar con datos reales!\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
