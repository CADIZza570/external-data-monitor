import requests
import json

# Tu URL HTTP de ngrok
NGROK_URL = "http://demeritoriously-proreduction-roderick.ngrok-free.dev/webhook/shopify"

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
    resp = requests.post(NGROK_URL, json=payload)
    print("Status code:", resp.status_code)
    
    # Manejar caso de respuesta vacía
    try:
        data = resp.json()
        print("Response JSON:", json.dumps(data, indent=2))
    except ValueError:
        print("Respuesta no es JSON, raw content:", resp.text)

except Exception as e:
    print("Error enviando webhook:", e)
