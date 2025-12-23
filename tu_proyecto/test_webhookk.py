# ============================================================
# 🚀 TEST WEBHOOK MINI SCRIPT
# ============================================================
# Este script envía un payload de prueba al webhook de Shopify
# usando la URL pública de ngrok. Sirve para verificar flujo
# completo antes de conectar Shopify real.
# ============================================================

import requests
import json

# 🔹 Cambia esta URL por la que te da ngrok
NGROK_URL =    "https://demeritoriously-proreduction-roderick.ngrok-free.dev"

# Endpoint de Shopify simulado
WEBHOOK_ENDPOINT = f"{NGROK_URL}/webhook/shopify"

# Payload de prueba
payload = {
    "products": [
        {
            "title": "Camiseta Roja",
            "variants": [
                {
                    "id": 101,
                    "title": "S",
                    "inventory_quantity": 3,
                    "last_sold_date": "2025-12-10"
                }
            ]
        }
    ]
}

headers = {
    "Content-Type": "application/json"
}

def test_webhook():
    try:
        response = requests.post(WEBHOOK_ENDPOINT, headers=headers, data=json.dumps(payload))
        print("✅ Status Code:", response.status_code)
        print("📄 Response:", response.json())
    except Exception as e:
        print("❌ Error enviando webhook:", str(e))

if __name__ == "__main__":
    test_webhook()
