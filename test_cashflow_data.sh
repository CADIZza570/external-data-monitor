#!/bin/bash
# ============================================================
# Script de Prueba - Popular DB con Datos Cash Flow
# ============================================================
# Envía webhooks de prueba con datos completos de Cash Flow
# para verificar que los endpoints funcionan correctamente.
# ============================================================

API_URL="https://tranquil-freedom-production.up.railway.app"

echo "🚀 Enviando productos de prueba con datos Cash Flow..."
echo "============================================================"

# Producto 1: Categoría A (Alta rotación)
echo "📦 Producto 1: Botas Vaqueras Premium (Categoría A)"
curl -X POST "$API_URL/webhook/shopify" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -H "X-Shopify-Shop-Domain: chaparrita-boots.myshopify.com" \
  -d '{
    "id": 100001,
    "title": "Botas Vaqueras Premium - Talla 7",
    "variants": [{
      "id": 1,
      "sku": "BVP-007",
      "inventory_quantity": 8,
      "price": "399.99",
      "cost": "180.00"
    }]
  }' -s | jq -r '.status'

sleep 2

# Producto 2: Categoría B (Rotación media)
echo "📦 Producto 2: Texanas Clásicas (Categoría B)"
curl -X POST "$API_URL/webhook/shopify" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -H "X-Shopify-Shop-Domain: chaparrita-boots.myshopify.com" \
  -d '{
    "id": 100002,
    "title": "Texanas Clásicas - Talla 6",
    "variants": [{
      "id": 2,
      "sku": "TXC-006",
      "inventory_quantity": 12,
      "price": "279.99",
      "cost": "120.00"
    }]
  }' -s | jq -r '.status'

sleep 2

# Producto 3: Stock crítico
echo "📦 Producto 3: Botines Casuales (CRÍTICO)"
curl -X POST "$API_URL/webhook/shopify" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -H "X-Shopify-Shop-Domain: chaparrita-boots.myshopify.com" \
  -d '{
    "id": 100003,
    "title": "Botines Casuales - Talla 5",
    "variants": [{
      "id": 3,
      "sku": "BTC-005",
      "inventory_quantity": 2,
      "price": "199.99",
      "cost": "85.00"
    }]
  }' -s | jq -r '.status'

sleep 2

# Producto 4: Agotado
echo "📦 Producto 4: Sandalias Verano (AGOTADO)"
curl -X POST "$API_URL/webhook/shopify" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -H "X-Shopify-Shop-Domain: chaparrita-boots.myshopify.com" \
  -d '{
    "id": 100004,
    "title": "Sandalias Verano - Talla 7",
    "variants": [{
      "id": 4,
      "sku": "SAN-007",
      "inventory_quantity": 0,
      "price": "149.99",
      "cost": "60.00"
    }]
  }' -s | jq -r '.status'

sleep 2

# Producto 5: Dev store
echo "📦 Producto 5: Producto de Prueba DEV"
curl -X POST "$API_URL/webhook/shopify" \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -H "X-Shopify-Shop-Domain: connie-dev-studio.myshopify.com" \
  -d '{
    "id": 999001,
    "title": "Test Product - Dev Store",
    "variants": [{
      "id": 99,
      "sku": "TEST-DEV-001",
      "inventory_quantity": 15,
      "price": "99.99",
      "cost": "40.00"
    }]
  }' -s | jq -r '.status'

echo ""
echo "============================================================"
echo "✅ Productos enviados correctamente"
echo "============================================================"
echo ""
echo "🔍 Verificando resultados..."
echo ""

# Verificar que se guardaron
echo "📊 Total de productos:"
curl -s "$API_URL/api/products" | jq '.count'

echo ""
echo "🚨 Productos críticos:"
curl -s "$API_URL/api/products/critical" | jq '.count'

echo ""
echo "✅ Script completado"
