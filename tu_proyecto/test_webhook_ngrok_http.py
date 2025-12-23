# test_webhook_ngrok_http.py
# Mini script para probar webhook Shopify vía ngrok usando HTTP

from dotenv import load_dotenv
import os
import requests
import json

# Cargar variables de entorno
load_dotenv()

# 🔹 Aquí pones tu URL pública de ngrok (usa HTTP, no HTTPS para evitar bloqueos)
NGROK_URL = os.getenv ("http://demeritoriously-proreduction-roderick.ngrok-free.dev/webhook/shopify")

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

try:
    resp = requests.post(
    "https://demeritoriously-proreduction-roderick.ngrok-free.dev/webhook/shopify",
    json=payload,
    verify=False
)
    print("Status code:", resp.status_code)

    # Intentar parsear JSON, si no es JSON mostrar contenido crudo
    try:
        data = resp.json()
        print("Respuesta JSON:", json.dumps(data, indent=2))
    except ValueError:
        print("Respuesta no es JSON, raw content:\n", resp.text)

except requests.exceptions.RequestException as e:
    print("Error enviando webhook:", e)
