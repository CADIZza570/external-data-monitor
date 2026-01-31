#!/usr/bin/env python3
"""
🌡️ EXTERNAL SIGNALS ENGINE - Predicción por Contexto Externo
Integra clima (OpenWeather) y feriados para predecir spikes de demanda
"""

import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# APIs configurables
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")  # Gratis: openweathermap.org
CITY = "Columbus,OH,US"  # Columbus, Ohio - Market focus


class ExternalSignalsEngine:
    """
    Motor de señales externas para predicción contextual.

    Analiza:
    - Clima actual y forecast (temperatura, lluvia, nieve)
    - Feriados y eventos especiales
    - Correlaciones: frío extremo → spike en chaquetas, boots
    """

    # Correlaciones clima → categorías de productos
    WEATHER_CORRELATIONS = {
        "extreme_cold": {  # < -15°C
            "categories": ["chaqueta", "jacket", "boot", "waterproof", "térmi", "abrigo", "winter", "invierno"],
            "velocity_multiplier": 1.50,  # +50%
            "confidence": 0.85,
            "reason": "Frío extremo en Columbus"
        },
        "cold": {  # -15°C a 5°C
            "categories": ["chaqueta", "jacket", "sweater", "bufanda"],
            "velocity_multiplier": 1.30,  # +30%
            "confidence": 0.75,
            "reason": "Clima frío en Columbus"
        },
        "rain": {  # Lluvia
            "categories": ["waterproof", "boots", "paraguas", "impermeables"],
            "velocity_multiplier": 1.25,  # +25%
            "confidence": 0.70,
            "reason": "Lluvia en Columbus"
        },
        "hot": {  # > 25°C
            "categories": ["sombreros", "sandalias", "sunglasses", "verano"],
            "velocity_multiplier": 1.20,  # +20%
            "confidence": 0.65,
            "reason": "Clima cálido en Columbus"
        }
    }

    # Feriados USA (placeholders - en producción usar API)
    HOLIDAYS_2026 = {
        "2026-01-01": "New Year's Day",
        "2026-02-14": "Valentine's Day",
        "2026-03-17": "St. Patrick's Day",
        "2026-07-04": "Independence Day",
        "2026-10-31": "Halloween",
        "2026-11-26": "Thanksgiving",
        "2026-12-25": "Christmas"
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or OPENWEATHER_API_KEY
        self.city = CITY

    def get_weather_data(self, use_mock: bool = False) -> Dict:
        """
        Obtiene datos de clima actual de OpenWeather API.

        Args:
            use_mock: Si True, retorna datos mock (para testing sin API key)

        Returns:
            {
                "temp_celsius": float,
                "condition": str (Clear, Rain, Snow, etc.),
                "humidity": int,
                "description": str
            }
        """
        if use_mock or not self.api_key:
            # Mock data: Frío extremo en Columbus (invierno)
            return {
                "temp_celsius": -22.0,
                "condition": "Snow",
                "humidity": 85,
                "description": "Nieve ligera",
                "wind_speed": 15,
                "feels_like": -28.0
            }

        try:
            url = f"https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": self.city,
                "appid": self.api_key,
                "units": "metric"  # Celsius
            }

            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                data = response.json()

                return {
                    "temp_celsius": data["main"]["temp"],
                    "condition": data["weather"][0]["main"],
                    "humidity": data["main"]["humidity"],
                    "description": data["weather"][0]["description"],
                    "wind_speed": data.get("wind", {}).get("speed", 0),
                    "feels_like": data["main"].get("feels_like", data["main"]["temp"])
                }
            else:
                logger.warning(f"Weather API error: {response.status_code}")
                return self.get_weather_data(use_mock=True)

        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return self.get_weather_data(use_mock=True)

    def get_upcoming_holidays(self, days_ahead: int = 7) -> List[Dict]:
        """
        Obtiene feriados próximos.

        Args:
            days_ahead: Días hacia adelante a revisar

        Returns:
            Lista de feriados: [{"date": "2026-01-01", "name": "New Year's Day", "days_until": 5}]
        """
        today = datetime.now().date()
        upcoming = []

        for date_str, name in self.HOLIDAYS_2026.items():
            holiday_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            days_until = (holiday_date - today).days

            if 0 <= days_until <= days_ahead:
                upcoming.append({
                    "date": date_str,
                    "name": name,
                    "days_until": days_until
                })

        return sorted(upcoming, key=lambda x: x["days_until"])

    def analyze_weather_impact(
        self,
        product_name: str,
        weather_data: Optional[Dict] = None
    ) -> Dict:
        """
        Analiza impacto del clima en un producto específico.

        Args:
            product_name: Nombre del producto (ej: "Chaqueta Térmica Winter Pro")
            weather_data: Datos de clima (opcional, obtiene automático si no se pasa)

        Returns:
            {
                "has_impact": bool,
                "weather_condition": str,
                "velocity_multiplier": float (1.0 = sin cambio, 1.5 = +50%),
                "confidence": float (0.0 - 1.0),
                "reason": str
            }
        """
        if weather_data is None:
            weather_data = self.get_weather_data()

        temp = weather_data["temp_celsius"]
        condition = weather_data["condition"]

        # Determinar categoría de clima
        weather_category = None

        if temp < -15:
            weather_category = "extreme_cold"
        elif temp < 5:
            weather_category = "cold"
        elif temp > 25:
            weather_category = "hot"
        elif condition in ["Rain", "Drizzle", "Thunderstorm"]:
            weather_category = "rain"

        if not weather_category:
            return {
                "has_impact": False,
                "weather_condition": f"{temp:.1f}°C, {condition}",
                "velocity_multiplier": 1.0,
                "confidence": 0.0,
                "reason": "Clima neutral"
            }

        # Verificar si el producto está en categorías correlacionadas
        correlation = self.WEATHER_CORRELATIONS[weather_category]
        product_lower = product_name.lower()

        matches_category = any(cat in product_lower for cat in correlation["categories"])

        if matches_category:
            return {
                "has_impact": True,
                "weather_condition": f"{temp:.1f}°C, {condition}",
                "velocity_multiplier": correlation["velocity_multiplier"],
                "confidence": correlation["confidence"],
                "reason": f"{correlation['reason']} → spike en {product_name}"
            }
        else:
            return {
                "has_impact": False,
                "weather_condition": f"{temp:.1f}°C, {condition}",
                "velocity_multiplier": 1.0,
                "confidence": 0.0,
                "reason": "Producto no correlacionado con clima actual"
            }

    def analyze_holiday_impact(
        self,
        product_name: str,
        days_ahead: int = 7
    ) -> Dict:
        """
        Analiza impacto de feriados próximos en un producto.

        Args:
            product_name: Nombre del producto
            days_ahead: Días adelante a revisar

        Returns:
            {
                "has_impact": bool,
                "holiday_name": str,
                "days_until": int,
                "velocity_multiplier": float,
                "reason": str
            }
        """
        holidays = self.get_upcoming_holidays(days_ahead=days_ahead)

        if not holidays:
            return {
                "has_impact": False,
                "holiday_name": None,
                "days_until": None,
                "velocity_multiplier": 1.0,
                "reason": "Sin feriados próximos"
            }

        # Analizar correlación producto-feriado
        product_lower = product_name.lower()

        for holiday in holidays:
            name = holiday["name"]
            days_until = holiday["days_until"]

            # Correlaciones simples (expandir según negocio)
            if "Valentine" in name and any(kw in product_lower for kw in ["rose", "chocolate", "gift", "amor"]):
                return {
                    "has_impact": True,
                    "holiday_name": name,
                    "days_until": days_until,
                    "velocity_multiplier": 1.40,  # +40%
                    "reason": f"{name} en {days_until} días → spike en regalos"
                }
            elif "Christmas" in name and any(kw in product_lower for kw in ["gift", "decoration", "tree"]):
                return {
                    "has_impact": True,
                    "holiday_name": name,
                    "days_until": days_until,
                    "velocity_multiplier": 1.60,  # +60%
                    "reason": f"{name} en {days_until} días → spike navideño"
                }
            elif "Halloween" in name and any(kw in product_lower for kw in ["costume", "candy", "pumpkin"]):
                return {
                    "has_impact": True,
                    "holiday_name": name,
                    "days_until": days_until,
                    "velocity_multiplier": 1.35,  # +35%
                    "reason": f"{name} en {days_until} días → spike disfraces"
                }

        return {
            "has_impact": False,
            "holiday_name": holidays[0]["name"],
            "days_until": holidays[0]["days_until"],
            "velocity_multiplier": 1.0,
            "reason": f"{holidays[0]['name']} próximo pero sin correlación directa"
        }

    def get_contextual_multiplier(
        self,
        product_name: str,
        use_mock_weather: bool = False
    ) -> Dict:
        """
        Calcula multiplicador contextual total (clima + feriados).

        Args:
            product_name: Nombre del producto
            use_mock_weather: Usar datos mock de clima

        Returns:
            {
                "final_multiplier": float,
                "weather_impact": Dict,
                "holiday_impact": Dict,
                "combined_reason": str
            }
        """
        weather_data = self.get_weather_data(use_mock=use_mock_weather)
        weather_impact = self.analyze_weather_impact(product_name, weather_data)
        holiday_impact = self.analyze_holiday_impact(product_name)

        # Multiplicador final = producto de ambos factores
        # (ej: clima +30% × feriado +20% = 1.3 × 1.2 = 1.56 = +56%)
        final_multiplier = weather_impact["velocity_multiplier"] * holiday_impact["velocity_multiplier"]

        # Razón combinada
        reasons = []
        if weather_impact["has_impact"]:
            reasons.append(weather_impact["reason"])
        if holiday_impact["has_impact"]:
            reasons.append(holiday_impact["reason"])

        combined_reason = " + ".join(reasons) if reasons else "Sin señales externas significativas"

        return {
            "final_multiplier": round(final_multiplier, 2),
            "weather_impact": weather_impact,
            "holiday_impact": holiday_impact,
            "combined_reason": combined_reason,
            "has_any_impact": weather_impact["has_impact"] or holiday_impact["has_impact"]
        }


# Testing
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🌡️ EXTERNAL SIGNALS ENGINE - TEST")
    print("="*70)

    engine = ExternalSignalsEngine()

    # Test 1: Weather data
    print("\n1️⃣ Obteniendo clima de Columbus, Ohio...")
    weather = engine.get_weather_data(use_mock=True)
    print(f"   Temperatura: {weather['temp_celsius']:.1f}°C")
    print(f"   Condición: {weather['condition']} ({weather['description']})")
    print(f"   Sensación térmica: {weather['feels_like']:.1f}°C")

    # Test 2: Holiday data
    print("\n2️⃣ Feriados próximos (7 días)...")
    holidays = engine.get_upcoming_holidays(days_ahead=365)
    if holidays:
        for h in holidays[:3]:
            print(f"   - {h['name']}: en {h['days_until']} días")
    else:
        print("   Sin feriados próximos")

    # Test 3: Weather impact en chaqueta
    print("\n3️⃣ Impacto clima en 'Chaqueta Térmica Winter Pro'...")
    impact = engine.analyze_weather_impact("Chaqueta Térmica Winter Pro", weather)
    print(f"   Tiene impacto: {impact['has_impact']}")
    print(f"   Multiplicador: {impact['velocity_multiplier']}x ({(impact['velocity_multiplier']-1)*100:.0f}%)")
    print(f"   Razón: {impact['reason']}")
    print(f"   Confianza: {impact['confidence']*100:.0f}%")

    # Test 4: Contextual multiplier total
    print("\n4️⃣ Multiplicador contextual total (clima + feriados)...")
    context = engine.get_contextual_multiplier("Chaqueta Térmica Winter Pro", use_mock_weather=True)
    print(f"   Multiplicador final: {context['final_multiplier']}x")
    print(f"   Razón: {context['combined_reason']}")

    print("="*70)
