#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mini script para probar tu webhook de Shopify vía ngrok.
✅ Envía un POST con datos de prueba
✅ Detecta si la respuesta es JSON o HTML bloqueado
"""

import requests
import json

# -------------------------
# URL pública de ngrok
# -------------------------
NGROK_URL = "http://demeritoriously-proreduction-roderick.ngrok-free.dev/webhook/shopify"

# -------------------------
# Payload de prueba
# -------------------------
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

# -------------------------
# Enviar POST
# -------------------------
try:
    resp = requests.post(NGROK_URL, json=payload, verify=False)
    print(f"Status code: {resp.status_code}")

    # Intentar parsear como JSON
    try:
        data = resp.json()
        print("Respuesta JSON recibida:")
        print(json.dumps(data, indent=4))
    except json.JSONDecodeError:
        print("Respuesta no es JSON, raw content:")
        print(resp.text[:500] + " ...")  # imprime solo los primeros 500 caracteres

except requests.exceptions.RequestException as e:
    print("Error enviando webhook:", e)
