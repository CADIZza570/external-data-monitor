#!/usr/bin/env python3
"""
🔧 SCRIPT DE POBLACIÓN - DATOS DE PRUEBA CASH FLOW

Actualiza los productos existentes con datos de Cash Flow realistas
para testing del dashboard y endpoints de analytics.

Ejecutar: python populate_cashflow_test_data.py
"""

import requests
import json
import time

API_URL = "https://tranquil-freedom-production.up.railway.app"

# Datos de prueba para cada producto
test_data = [
    {
        "sku": "BVP-007",
        "cost_price": 180.00,
        "total_sales_30d": 75,  # ~2.5 ud/día = Categoría A
        "name": "Botas Vaqueras Premium - Talla 7"
    },
    {
        "sku": "TXC-006",
        "cost_price": 120.00,
        "total_sales_30d": 25,  # ~0.83 ud/día = Categoría B
        "name": "Texanas Clásicas - Talla 6"
    },
    {
        "sku": "BTC-005",
        "cost_price": 85.00,
        "total_sales_30d": 8,   # ~0.27 ud/día = Categoría C (CRÍTICO)
        "name": "Botines Casuales - Talla 5"
    },
    {
        "sku": "SAN-007",
        "cost_price": 60.00,
        "total_sales_30d": 0,   # 0 ud/día = Categoría C (AGOTADO)
        "name": "Sandalias Verano - Talla 7"
    },
    {
        "sku": "TEST-DEV-001",
        "cost_price": 40.00,
        "total_sales_30d": 120, # ~4 ud/día = Categoría A (DEV)
        "name": "Test Product - Dev Store"
    }
]

def update_cashflow(product_data):
    """Actualiza Cash Flow de un producto vía API"""
    endpoint = f"{API_URL}/api/products/update-cashflow"

    payload = {
        "sku": product_data["sku"],
        "cost_price": product_data["cost_price"],
        "total_sales_30d": product_data["total_sales_30d"]
    }

    try:
        response = requests.post(endpoint, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            return True, result
        else:
            return False, response.text

    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("🚀 POBLANDO BASE DE DATOS CON DATOS CASH FLOW")
    print("=" * 70)
    print()

    success_count = 0
    error_count = 0

    for product in test_data:
        print(f"📦 Actualizando: {product['name']}")
        print(f"   SKU: {product['sku']}")
        print(f"   Costo: ${product['cost_price']:.2f}")
        print(f"   Ventas 30d: {product['total_sales_30d']} unidades")

        success, result = update_cashflow(product)

        if success:
            product_info = result.get('product', {})
            velocity = product_info.get('velocity_daily', 0)
            category = product_info.get('category', 'N/A')
            margin = product_info.get('margin_percent', 0)

            print(f"   ✅ Actualizado - Velocity: {velocity} ud/día, Categoría: {category}, Margen: {margin}%")
            success_count += 1
        else:
            print(f"   ❌ Error: {result}")
            error_count += 1

        print()
        time.sleep(1)  # Rate limiting

    print("=" * 70)
    print(f"✅ Completado: {success_count} productos actualizados")
    if error_count > 0:
        print(f"⚠️  Errores: {error_count} productos fallidos")
    print("=" * 70)
    print()

    # Verificar resultados
    print("🔍 Verificando endpoints...")
    print()

    try:
        # Total productos
        r = requests.get(f"{API_URL}/api/products", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"📊 Total productos: {data.get('count', 0)}")

        # Productos críticos
        r = requests.get(f"{API_URL}/api/products/critical", timeout=10)
        if r.status_code == 200:
            data = r.json()
            print(f"🚨 Productos críticos: {data.get('count', 0)}")

        # Analytics Cash Flow
        r = requests.get(f"{API_URL}/api/analytics/cashflow", timeout=10)
        if r.status_code == 200:
            data = r.json()
            overall = data.get('overall', {})
            print(f"💰 Valor total inventario: ${overall.get('total_inventory_value', 0):.2f}")
            print(f"📈 Margen promedio: {overall.get('avg_margin_percent', 0):.2f}%")
            print(f"⚡ Velocity promedio: {overall.get('avg_velocity_daily', 0):.2f} ud/día")

        # Clasificación ABC
        r = requests.get(f"{API_URL}/api/products/abc", timeout=10)
        if r.status_code == 200:
            data = r.json()
            stats = data.get('stats', {})
            print(f"🎯 Categoría A: {stats.get('category_A', 0)} productos")
            print(f"🎯 Categoría B: {stats.get('category_B', 0)} productos")
            print(f"🎯 Categoría C: {stats.get('category_C', 0)} productos")

    except Exception as e:
        print(f"⚠️  Error verificando endpoints: {e}")

    print()
    print("✅ Script completado exitosamente")


if __name__ == "__main__":
    main()
