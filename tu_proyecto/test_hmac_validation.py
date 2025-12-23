#!/usr/bin/env python3
"""
Script para probar validación HMAC del webhook server.
Genera firma HMAC correcta usando el secret del .env
"""
import hmac
import hashlib
import base64
import json
import requests
from datetime import datetime
from config_shared import SHOPIFY_WEBHOOK_SECRET

# Payload de prueba
payload = {
    "products": [
        {
            "title": "HMAC Test Product",
            "variants": [
                {
                    "id": 99999,
                    "title": "Medium",
                    "inventory_quantity": 2
                }
            ]
        }
    ]
}

# Convertir a JSON string
payload_json = json.dumps(payload)
payload_bytes = payload_json.encode('utf-8')

# Generar firma HMAC (igual que Shopify)
calculated_hmac = base64.b64encode(
    hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).digest()
).decode('utf-8')

print("=" * 60)
print("🔐 TEST DE VALIDACIÓN HMAC")
print("=" * 60)
print(f"Secret usado: {SHOPIFY_WEBHOOK_SECRET[:10]}...")
print(f"Firma HMAC: {calculated_hmac[:20]}...")
print("=" * 60)

# Enviar webhook con HMAC válido
print("\n📤 Enviando webhook con HMAC VÁLIDO...")
response = requests.post(
    'http://localhost:5001/webhook/shopify',
    json=payload,
    headers={
        'Content-Type': 'application/json',
        'X-Shopify-Hmac-Sha256': calculated_hmac,
        'X-Shopify-Topic': 'products/update',
        'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

if response.status_code == 200:
    print("\n✅ HMAC VÁLIDO ACEPTADO - Test PASÓ")
else:
    print("\n❌ HMAC VÁLIDO RECHAZADO - Test FALLÓ")

print("\n" + "=" * 60)

# Enviar webhook con HMAC INVÁLIDO
print("📤 Enviando webhook con HMAC INVÁLIDO...")
response_bad = requests.post(
    'http://localhost:5001/webhook/shopify',
    json=payload,
    headers={
        'Content-Type': 'application/json',
        'X-Shopify-Hmac-Sha256': 'FIRMA_FALSA_12345',
        'X-Shopify-Topic': 'products/update',
        'X-Shopify-Shop-Domain': 'test-store.myshopify.com'
    }
)

print(f"Status Code: {response_bad.status_code}")
print(f"Response: {json.dumps(response_bad.json(), indent=2)}")

if response_bad.status_code == 401:
    print("\n✅ HMAC INVÁLIDO RECHAZADO - Test PASÓ")
else:
    print("\n❌ HMAC INVÁLIDO ACEPTADO - Test FALLÓ (PROBLEMA DE SEGURIDAD)")

print("\n" + "=" * 60)
print("🎯 RESUMEN:")
print("  - HMAC válido debe retornar 200")
print("  - HMAC inválido debe retornar 401")
print("=" * 60)
