#!/usr/bin/env python3
"""
📥 SINCRONIZACIÓN HISTÓRICA DE SHOPIFY - Cash Flow v1.0

Jala órdenes de los últimos 60 días de Shopify para:
- Calcular Venta Diaria Promedio (VDP)
- Determinar last_sale_date
- Poblar orders_history

Rate Limiting:
- Shopify API: 40 requests/segundo max (2 requests/segundo seguro)
- 600 órdenes = ~300 segundos (~5 minutos)

Ejecutar una sola vez: python sync_shopify_history.py
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Shopify API
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")  # tu-tienda.myshopify.com
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")

# Base de datos
DB_FILE = os.getenv("DATA_DIR", ".") + "/webhooks.db"

# Rate limiting
REQUESTS_PER_SECOND = 2  # Seguro para Shopify (max 40/s)
DELAY_BETWEEN_REQUESTS = 1.0 / REQUESTS_PER_SECOND

# Periodo histórico
DAYS_TO_SYNC = 60

# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_db_connection():
    """Retorna conexión a SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def shopify_request(endpoint, params=None):
    """
    Realiza request GET a Shopify API con rate limiting.

    Args:
        endpoint: URL del endpoint (ej: /admin/api/2024-01/orders.json)
        params: Query parameters (opcional)

    Returns:
        dict: Response JSON o None si falla
    """
    if not SHOPIFY_STORE or not SHOPIFY_ACCESS_TOKEN:
        print("❌ Error: SHOPIFY_STORE o SHOPIFY_ACCESS_TOKEN no configurados")
        return None

    url = f"https://{SHOPIFY_STORE}{endpoint}"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    try:
        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

        response = requests.get(url, headers=headers, params=params, timeout=30)

        # Revisar rate limit
        if "X-Shopify-Shop-Api-Call-Limit" in response.headers:
            limit_info = response.headers["X-Shopify-Shop-Api-Call-Limit"]
            print(f"📊 Rate limit: {limit_info}")

        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"❌ Error en request a Shopify: {e}")
        return None

def save_order_to_db(order, shop):
    """
    Guarda una orden en la tabla orders_history.

    Args:
        order: Objeto order de Shopify
        shop: Dominio de la tienda

    Returns:
        int: Número de líneas guardadas
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    order_id = str(order.get("id"))
    order_date = order.get("created_at")

    saved_count = 0

    # Iterar sobre cada line_item (producto en la orden)
    for item in order.get("line_items", []):
        product_id = str(item.get("product_id", ""))
        variant_id = str(item.get("variant_id", ""))
        sku = item.get("sku", "")
        quantity = item.get("quantity", 0)
        price = float(item.get("price", 0))
        total_price = price * quantity

        try:
            cursor.execute('''
                INSERT INTO orders_history
                (order_id, product_id, sku, quantity, price, total_price, order_date, shop)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id, product_id, shop) DO NOTHING
            ''', (order_id, variant_id or product_id, sku, quantity, price, total_price, order_date, shop))

            if cursor.rowcount > 0:
                saved_count += 1

        except Exception as e:
            print(f"⚠️  Error guardando item: {e}")
            continue

    conn.commit()
    conn.close()

    return saved_count

def sync_orders_history():
    """
    Sincroniza órdenes de los últimos X días desde Shopify.

    Returns:
        dict: Estadísticas de la sincronización
    """
    print("=" * 60)
    print("📥 SINCRONIZACIÓN HISTÓRICA DE SHOPIFY")
    print("=" * 60)
    print(f"🏪 Tienda: {SHOPIFY_STORE}")
    print(f"📅 Periodo: Últimos {DAYS_TO_SYNC} días")
    print(f"📁 Database: {DB_FILE}")
    print("=" * 60)

    # Calcular fecha de inicio
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_TO_SYNC)

    print(f"📆 Desde: {start_date.strftime('%Y-%m-%d')}")
    print(f"📆 Hasta: {end_date.strftime('%Y-%m-%d')}")
    print()

    # Preparar parámetros
    params = {
        "status": "any",  # Incluir todas las órdenes (paid, pending, cancelled, etc)
        "created_at_min": start_date.isoformat(),
        "limit": 250  # Max permitido por Shopify
    }

    total_orders = 0
    total_items = 0
    page = 1

    # Paginación
    while True:
        print(f"📄 Página {page}... ", end="", flush=True)

        data = shopify_request("/admin/api/2024-01/orders.json", params)

        if not data or "orders" not in data:
            print("❌ No se pudo obtener órdenes")
            break

        orders = data["orders"]

        if not orders:
            print("✅ No hay más órdenes")
            break

        print(f"({len(orders)} órdenes)")

        # Guardar cada orden
        for order in orders:
            items_saved = save_order_to_db(order, SHOPIFY_STORE)
            total_items += items_saved

        total_orders += len(orders)

        # Obtener siguiente página (si existe)
        # Shopify usa "Link" header para paginación
        # Simplificación: usar since_id del último order
        if len(orders) < 250:
            # Última página
            break

        # Actualizar params para siguiente página
        last_order_id = orders[-1]["id"]
        params["since_id"] = last_order_id
        page += 1

    print()
    print("=" * 60)
    print("✅ SINCRONIZACIÓN COMPLETADA")
    print("=" * 60)
    print(f"📦 Órdenes procesadas: {total_orders}")
    print(f"📊 Items guardados: {total_items}")
    print("=" * 60)

    return {
        "total_orders": total_orders,
        "total_items": total_items,
        "period_days": DAYS_TO_SYNC
    }

def calculate_vpd_for_all_products():
    """
    Calcula VDP (Venta Diaria Promedio) para todos los productos.
    Actualiza products.velocity_daily y products.total_sales_30d
    """
    print("\n🧮 CALCULANDO VDP (Venta Diaria Promedio)...")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Calcular ventas por SKU en últimos 30 días
    cursor.execute('''
        SELECT
            sku,
            SUM(quantity) as total_quantity,
            MAX(order_date) as last_sale
        FROM orders_history
        WHERE order_date >= datetime('now', '-30 days')
        AND sku IS NOT NULL AND sku != ''
        GROUP BY sku
    ''')

    results = cursor.fetchall()
    updated_count = 0

    for row in results:
        sku = row["sku"]
        total_quantity = row["total_quantity"]
        last_sale = row["last_sale"]

        # VDP = Total vendido / 30 días
        vpd = total_quantity / 30.0

        # Actualizar en tabla products
        cursor.execute('''
            UPDATE products
            SET
                velocity_daily = ?,
                total_sales_30d = ?,
                last_sale_date = ?
            WHERE sku = ?
        ''', (vpd, total_quantity, last_sale, sku))

        if cursor.rowcount > 0:
            updated_count += 1

    conn.commit()
    conn.close()

    print(f"✅ VDP calculado para {updated_count} productos")

    return updated_count

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    # Validar configuración
    if not SHOPIFY_STORE or not SHOPIFY_ACCESS_TOKEN:
        print("❌ ERROR: Variables de entorno faltantes")
        print("Necesitas configurar:")
        print("  - SHOPIFY_STORE (ej: tu-tienda.myshopify.com)")
        print("  - SHOPIFY_ACCESS_TOKEN")
        sys.exit(1)

    # Ejecutar sincronización
    start_time = time.time()

    stats = sync_orders_history()

    # Calcular VDP
    calculate_vpd_for_all_products()

    elapsed = time.time() - start_time

    print(f"\n⏱️  Tiempo total: {elapsed:.1f} segundos")
    print("\n🎉 ¡Sincronización histórica completada!")
    print("Ya puedes usar las métricas de Cash Flow basadas en datos reales.")
