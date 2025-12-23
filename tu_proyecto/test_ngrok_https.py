import requests

NGROK_URL = "http://demeritoriously-proreduction-roderick.ngrok-free.dev/webhook/shopify"

try:
    resp = requests.get(NGROK_URL, verify=False)  # 🔹 Ignoramos SSL solo para prueba
    print("Status code:", resp.status_code)
    print("Contenido:")
    print(resp.text[:500])  # solo los primeros 500 caracteres
except requests.exceptions.RequestException as e:
    print("Error de conexión:", e)
