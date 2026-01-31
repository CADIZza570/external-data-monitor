#!/usr/bin/env python3
"""
🧪 Test de API Key de OpenWeather

Uso:
  export OPENWEATHER_API_KEY="tu_key_aqui"
  python3 test_api_key.py
"""

import os
import requests
import sys

def test_openweather_key():
    api_key = os.getenv("OPENWEATHER_API_KEY", "")

    if not api_key:
        print("❌ ERROR: OPENWEATHER_API_KEY no configurada")
        print("\nPasos para obtener una key:")
        print("1. Ir a: https://openweathermap.org/api")
        print("2. Sign Up / Log In")
        print("3. Ir a 'API keys' en tu cuenta")
        print("4. Copiar tu key (32 caracteres)")
        print("\nLuego:")
        print("  export OPENWEATHER_API_KEY='tu_key_aqui'")
        print("  python3 test_api_key.py")
        sys.exit(1)

    print(f"\n🔑 Testing API key: {api_key[:8]}...{api_key[-4:]}")
    print("🌍 Ciudad: Columbus, OH, US\n")

    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "Columbus,OH,US",
            "appid": api_key,
            "units": "metric"
        }

        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()

            print("✅ API KEY VÁLIDA!\n")
            print(f"🌡️ Temperatura: {data['main']['temp']:.1f}°C")
            print(f"🌤️ Condición: {data['weather'][0]['main']}")
            print(f"📝 Descripción: {data['weather'][0]['description']}")
            print(f"💧 Humedad: {data['main']['humidity']}%")
            print(f"🌬️ Viento: {data.get('wind', {}).get('speed', 0)} m/s")
            print(f"🥶 Sensación térmica: {data['main'].get('feels_like', 0):.1f}°C")

            print("\n" + "="*60)
            print("PRÓXIMO PASO:")
            print("="*60)
            print("1. Ir a Railway → pulse-scheduler → Variables")
            print(f"2. Actualizar: OPENWEATHER_API_KEY={api_key}")
            print("3. Redeploy automático en Railway")
            print("4. Testear: python3 pulse_scheduler.py --now --dry-run")

        elif response.status_code == 401:
            print("❌ API KEY INVÁLIDA")
            print(f"\nRespuesta: {response.json()}")
            print("\nPasos:")
            print("1. Verificá que copiaste la key completa (32 caracteres)")
            print("2. La key puede tardar unos minutos en activarse después de crearla")
            print("3. Revisá en https://home.openweathermap.org/api_keys")

        else:
            print(f"❌ Error HTTP {response.status_code}")
            print(f"Respuesta: {response.text}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_openweather_key()
