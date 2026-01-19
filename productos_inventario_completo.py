#!/usr/bin/env python3
"""
Script para poblar inventario con productos variados
Ejecutar: python productos_inventario_completo.py
"""

import requests
import json
from datetime import datetime

# URL del webhook en Railway (producción)
WEBHOOK_URL = "https://tranquil-freedom-production.up.railway.app/webhook/shopify"

# Productos con TODA la variedad: stock crítico, medio, alto, agotados, diferentes velocidades
PRODUCTOS = [
    # ========== CATEGORÍA A: ALTA ROTACIÓN (>= 2 ud/día) - CRÍTICOS ==========
    {
        "product_id": "BV-001",
        "title": "Botas Vaqueras Negras - Talla 6",
        "sku": "BV-001",
        "quantity": 2,  # CRÍTICO - Solo 2 unidades
        "price": 89.99,
        "cost": 45.00,
        "category": "Botas Vaqueras",
        "velocity": 2.5,  # Alta rotación
        "last_sale_date": "2026-01-18"
    },
    {
        "product_id": "BV-002",
        "title": "Botas Vaqueras Café - Talla 7",
        "sku": "BV-002",
        "quantity": 0,  # AGOTADO
        "price": 89.99,
        "cost": 45.00,
        "category": "Botas Vaqueras",
        "velocity": 3.0,  # Muy alta rotación
        "last_sale_date": "2026-01-19"
    },
    {
        "product_id": "BV-003",
        "title": "Botas Vaqueras Decoradas - Talla 8",
        "sku": "BV-003",
        "quantity": 5,
        "price": 109.99,
        "cost": 55.00,
        "category": "Botas Vaqueras",
        "velocity": 2.2,
        "last_sale_date": "2026-01-17"
    },
    {
        "product_id": "BV-004",
        "title": "Botas Vaqueras Piel - Talla 9",
        "sku": "BV-004",
        "quantity": 1,  # URGENTE - Solo 1
        "price": 129.99,
        "cost": 65.00,
        "category": "Botas Vaqueras",
        "velocity": 2.8,
        "last_sale_date": "2026-01-19"
    },

    # ========== TEXANAS - VARIEDAD ==========
    {
        "product_id": "TX-001",
        "title": "Texanas Clásicas - Talla 5",
        "sku": "TX-001",
        "quantity": 0,  # AGOTADO
        "price": 79.99,
        "cost": 40.00,
        "category": "Texanas",
        "velocity": 2.5,
        "last_sale_date": "2026-01-18"
    },
    {
        "product_id": "TX-002",
        "title": "Texanas Decoradas - Talla 6",
        "sku": "TX-002",
        "quantity": 8,
        "price": 89.99,
        "cost": 45.00,
        "category": "Texanas",
        "velocity": 1.8,
        "last_sale_date": "2026-01-16"
    },
    {
        "product_id": "TX-003",
        "title": "Texanas Premium - Talla 7",
        "sku": "TX-003",
        "quantity": 3,
        "price": 99.99,
        "cost": 50.00,
        "category": "Texanas",
        "velocity": 2.1,
        "last_sale_date": "2026-01-18"
    },

    # ========== CATEGORÍA B: ROTACIÓN MEDIA (0.5-2 ud/día) ==========
    {
        "product_id": "BT-001",
        "title": "Botines Cuero Negro - Talla 6",
        "sku": "BT-001",
        "quantity": 12,
        "price": 69.99,
        "cost": 35.00,
        "category": "Botines",
        "velocity": 1.2,
        "last_sale_date": "2026-01-17"
    },
    {
        "product_id": "BT-002",
        "title": "Botines Tacón - Talla 7",
        "sku": "BT-002",
        "quantity": 6,
        "price": 74.99,
        "cost": 37.50,
        "category": "Botines",
        "velocity": 0.9,
        "last_sale_date": "2026-01-15"
    },
    {
        "product_id": "BT-003",
        "title": "Botines Casual - Talla 8",
        "sku": "BT-003",
        "quantity": 4,
        "price": 64.99,
        "cost": 32.50,
        "category": "Botines",
        "velocity": 1.5,
        "last_sale_date": "2026-01-18"
    },
    {
        "product_id": "BT-004",
        "title": "Botines Piel - Talla 5",
        "sku": "BT-004",
        "quantity": 0,  # AGOTADO
        "price": 79.99,
        "cost": 40.00,
        "category": "Botines",
        "velocity": 1.1,
        "last_sale_date": "2026-01-12"
    },

    # ========== SANDALIAS - TEMPORADA ==========
    {
        "product_id": "SD-001",
        "title": "Sandalias Huarache - Talla 5",
        "sku": "SD-001",
        "quantity": 25,
        "price": 39.99,
        "cost": 20.00,
        "category": "Sandalias",
        "velocity": 0.8,
        "last_sale_date": "2026-01-10"
    },
    {
        "product_id": "SD-002",
        "title": "Sandalias Plataforma - Talla 6",
        "sku": "SD-002",
        "quantity": 18,
        "price": 49.99,
        "cost": 25.00,
        "category": "Sandalias",
        "velocity": 1.0,
        "last_sale_date": "2026-01-14"
    },
    {
        "product_id": "SD-003",
        "title": "Sandalias Decoradas - Talla 7",
        "sku": "SD-003",
        "quantity": 15,
        "price": 44.99,
        "cost": 22.50,
        "category": "Sandalias",
        "velocity": 0.7,
        "last_sale_date": "2026-01-11"
    },

    # ========== CATEGORÍA C: BAJA ROTACIÓN (<0.5 ud/día) ==========
    {
        "product_id": "CN-001",
        "title": "Cinturón Cuero Trenzado - M",
        "sku": "CN-001",
        "quantity": 30,
        "price": 29.99,
        "cost": 15.00,
        "category": "Cinturones",
        "velocity": 0.3,
        "last_sale_date": "2026-01-05"
    },
    {
        "product_id": "CN-002",
        "title": "Cinturón Hebilla Plateada - L",
        "sku": "CN-002",
        "quantity": 22,
        "price": 34.99,
        "cost": 17.50,
        "category": "Cinturones",
        "velocity": 0.4,
        "last_sale_date": "2026-01-08"
    },
    {
        "product_id": "CN-003",
        "title": "Cinturón Piteado - M",
        "sku": "CN-003",
        "quantity": 8,
        "price": 44.99,
        "cost": 22.50,
        "category": "Cinturones",
        "velocity": 0.2,
        "last_sale_date": "2025-12-28"
    },

    # ========== BOLSAS - VARIEDAD DE STOCK ==========
    {
        "product_id": "BL-001",
        "title": "Bolsa Artesanal Grande",
        "sku": "BL-001",
        "quantity": 7,
        "price": 59.99,
        "cost": 30.00,
        "category": "Bolsas",
        "velocity": 1.3,
        "last_sale_date": "2026-01-16"
    },
    {
        "product_id": "BL-002",
        "title": "Bolsa Bordada Mediana",
        "sku": "BL-002",
        "quantity": 3,
        "price": 49.99,
        "cost": 25.00,
        "category": "Bolsas",
        "velocity": 1.7,
        "last_sale_date": "2026-01-17"
    },
    {
        "product_id": "BL-003",
        "title": "Bolsa Crossbody Cuero",
        "sku": "BL-003",
        "quantity": 0,  # AGOTADO
        "price": 64.99,
        "cost": 32.50,
        "category": "Bolsas",
        "velocity": 2.0,
        "last_sale_date": "2026-01-19"
    },
    {
        "product_id": "BL-004",
        "title": "Mochila Textil Mexicana",
        "sku": "BL-004",
        "quantity": 14,
        "price": 54.99,
        "cost": 27.50,
        "category": "Bolsas",
        "velocity": 0.9,
        "last_sale_date": "2026-01-13"
    },

    # ========== SOMBREROS ==========
    {
        "product_id": "SM-001",
        "title": "Sombrero Vaquero Negro",
        "sku": "SM-001",
        "quantity": 10,
        "price": 45.99,
        "cost": 23.00,
        "category": "Sombreros",
        "velocity": 0.6,
        "last_sale_date": "2026-01-12"
    },
    {
        "product_id": "SM-002",
        "title": "Sombrero Charro Premium",
        "sku": "SM-002",
        "quantity": 2,
        "price": 79.99,
        "cost": 40.00,
        "category": "Sombreros",
        "velocity": 1.8,
        "last_sale_date": "2026-01-18"
    },
    {
        "product_id": "SM-003",
        "title": "Gorra Bordada",
        "sku": "SM-003",
        "quantity": 35,
        "price": 24.99,
        "cost": 12.50,
        "category": "Sombreros",
        "velocity": 0.5,
        "last_sale_date": "2026-01-09"
    },

    # ========== ACCESORIOS ==========
    {
        "product_id": "AC-001",
        "title": "Paliacate Tradicional",
        "sku": "AC-001",
        "quantity": 50,
        "price": 14.99,
        "cost": 7.50,
        "category": "Accesorios",
        "velocity": 0.3,
        "last_sale_date": "2026-01-06"
    },
    {
        "product_id": "AC-002",
        "title": "Aretes Plata",
        "sku": "AC-002",
        "quantity": 20,
        "price": 19.99,
        "cost": 10.00,
        "category": "Accesorios",
        "velocity": 0.8,
        "last_sale_date": "2026-01-15"
    },
    {
        "product_id": "AC-003",
        "title": "Pulsera Artesanal",
        "sku": "AC-003",
        "quantity": 28,
        "price": 16.99,
        "cost": 8.50,
        "category": "Accesorios",
        "velocity": 0.4,
        "last_sale_date": "2026-01-10"
    },

    # ========== PRODUCTOS PREMIUM - ALTO VALOR ==========
    {
        "product_id": "PR-001",
        "title": "Botas Premium Piel Exótica - Talla 7",
        "sku": "PR-001",
        "quantity": 1,  # CRÍTICO - Producto caro
        "price": 299.99,
        "cost": 150.00,
        "category": "Premium",
        "velocity": 0.5,
        "last_sale_date": "2026-01-10"
    },
    {
        "product_id": "PR-002",
        "title": "Bolsa Cuero Diseñador",
        "sku": "PR-002",
        "quantity": 2,
        "price": 199.99,
        "cost": 100.00,
        "category": "Premium",
        "velocity": 0.3,
        "last_sale_date": "2025-12-30"
    },
]


def enviar_producto(producto):
    """Envía un producto al webhook"""
    payload = {
        "topic": "inventory/update",
        "shop_domain": "chaparrita-boots.myshopify.com",
        "created_at": datetime.now().isoformat(),
        "inventory_item": producto
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ {producto['sku']}: {producto['title'][:40]} | Stock: {producto['quantity']} | Velocity: {producto['velocity']}")
        else:
            print(f"❌ Error {producto['sku']}: {response.status_code}")
    except Exception as e:
        print(f"❌ Error enviando {producto['sku']}: {e}")


def main():
    print("=" * 80)
    print("🚀 POBLANDO INVENTARIO - CHAPARRITA BOOTS")
    print("=" * 80)
    print(f"\nTotal productos a cargar: {len(PRODUCTOS)}")
    print("\nResumen:")

    # Análisis rápido
    agotados = [p for p in PRODUCTOS if p['quantity'] == 0]
    criticos = [p for p in PRODUCTOS if p['quantity'] > 0 and p['quantity'] <= 3]
    alta_rotacion = [p for p in PRODUCTOS if p['velocity'] >= 2.0]

    print(f"  • Productos agotados: {len(agotados)}")
    print(f"  • Stock crítico (1-3 unidades): {len(criticos)}")
    print(f"  • Alta rotación (≥2 ud/día): {len(alta_rotacion)}")
    print(f"\n{'='*80}\n")

    # Enviar productos
    for i, producto in enumerate(PRODUCTOS, 1):
        print(f"[{i}/{len(PRODUCTOS)}] ", end="")
        enviar_producto(producto)

    print(f"\n{'='*80}")
    print("✅ INVENTARIO POBLADO EXITOSAMENTE")
    print("=" * 80)
    print("\n💡 Ahora puedes:")
    print("  1. Revisar el dashboard: https://tranquil-freedom-production.up.railway.app/dashboard")
    print("  2. Ver productos críticos, agotados y métricas")
    print("  3. Exportar reportes en PDF")
    print("  4. Filtrar por categorías ABC\n")


if __name__ == "__main__":
    main()
