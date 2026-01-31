#!/usr/bin/env python3
"""
🎲 STATS ENGINE - Calculador de Probabilidades para Cash Flow
Monte Carlo Light + análisis estadístico de ventas
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import random
import math

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"


class StatsEngine:
    """Motor de probabilidades para ROI y proyecciones de ventas"""

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def get_sales_history(self, sku: str, days: int = 30) -> List[float]:
        """
        Obtiene historial de velocidad de ventas (últimos N días)

        Returns:
            Lista de velocity_daily de los últimos N días
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Intentar obtener de orders_history si existe
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='orders_history'
        """)

        if cursor.fetchone():
            # Tenemos historial real
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute("""
                SELECT sale_date, quantity
                FROM sales_history
                WHERE sku = ? AND sale_date >= ?
                ORDER BY sale_date DESC
            """, (sku, cutoff_date))

            history = [row[1] for row in cursor.fetchall()]
        else:
            # Usar velocity_daily actual + variación simulada
            cursor.execute("""
                SELECT velocity_daily
                FROM products
                WHERE sku = ?
            """, (sku,))

            result = cursor.fetchone()
            base_velocity = result[0] if result else 0

            # Simular historial con variación ±20%
            history = []
            for _ in range(days):
                variation = random.uniform(0.8, 1.2)
                history.append(base_velocity * variation)

        conn.close()
        return history if history else [0] * days

    def get_adaptive_decay_factor(self, base_decay: float = 0.3) -> float:
        """
        Calcula decay factor adaptativo basado en patrones de clics del usuario.

        Si el usuario hace muchos clics "Simular Agresivo", aumenta el decay
        para dar más peso a datos recientes (más agresivo).

        Args:
            base_decay: Factor base (default 0.3 = 30% peso adicional)

        Returns:
            Decay factor ajustado (0.3 - 0.45)
        """
        try:
            from interaction_tracker import InteractionTracker

            tracker = InteractionTracker(self.db_path)
            pattern = tracker.get_recent_pattern(days=7)

            # Boost sugerido según clics agresivos
            boost = pattern.get("suggested_decay_boost", 0.0)

            # Decay final (máximo 0.45 = 45% peso adicional)
            adaptive_decay = min(base_decay + boost, 0.45)

            return adaptive_decay

        except Exception as e:
            # Si falla, usar decay base
            return base_decay

    def calculate_statistics(self, data: List[float], decay_factor: float = 0.3) -> Dict:
        """
        Calcula media y desviación estándar con decay (más peso a datos recientes)

        Args:
            data: Lista de valores (más reciente primero)
            decay_factor: Peso adicional a últimos 7 días (0.3 = 30% más peso)

        Returns:
            {"mean": μ, "std_dev": σ, "min": min, "max": max}
        """
        if not data or all(v == 0 for v in data):
            return {"mean": 0, "std_dev": 0, "min": 0, "max": 0}

        # Aplicar decay: últimos 7 días tienen más peso
        weighted_data = []
        for i, value in enumerate(data):
            weight = 1.0 + (decay_factor if i < 7 else 0)
            weighted_data.extend([value] * int(weight * 10))  # 10x para granularidad

        # Estadísticas básicas
        mean = sum(weighted_data) / len(weighted_data)
        variance = sum((x - mean) ** 2 for x in weighted_data) / len(weighted_data)
        std_dev = math.sqrt(variance)

        return {
            "mean": round(mean, 2),
            "std_dev": round(std_dev, 2),
            "min": round(min(data), 2),
            "max": round(max(data), 2)
        }

    def monte_carlo_simulation(
        self,
        mean: float,
        std_dev: float,
        units: int,
        price: float,
        cost: float,
        iterations: int = 100
    ) -> Dict:
        """
        Simulación Monte Carlo Light para ROI

        Args:
            mean: Velocidad promedio de ventas (unidades/día)
            std_dev: Desviación estándar
            units: Unidades a reordenar
            price: Precio de venta
            cost: Costo de adquisición
            iterations: Número de simulaciones (default 100)

        Returns:
            {
                "roi_expected": ROI promedio,
                "roi_min": Peor escenario (percentil 15),
                "roi_max": Mejor escenario (percentil 85),
                "confidence_85": Rango [min, max] con 85% confianza,
                "breakeven_days": Días promedio para recuperar inversión,
                "breakeven_range": [min, max] días
            }
        """
        if mean == 0 or std_dev == 0:
            # Sin datos históricos, usar estimación conservadora
            investment = units * cost
            revenue = units * price
            roi = ((revenue - investment) / investment * 100) if investment > 0 else 0

            return {
                "roi_expected": round(roi, 1),
                "roi_min": round(roi * 0.7, 1),
                "roi_max": round(roi * 1.3, 1),
                "confidence_85": [round(roi * 0.7, 1), round(roi * 1.3, 1)],
                "breakeven_days": 30,  # Conservador
                "breakeven_range": [20, 40]
            }

        roi_results = []
        breakeven_results = []

        for _ in range(iterations):
            # Simular velocidad de ventas (distribución normal)
            simulated_velocity = random.gauss(mean, std_dev)
            simulated_velocity = max(0.1, simulated_velocity)  # Evitar negativos

            # Calcular ROI en esta iteración
            investment = units * cost
            revenue = units * price
            profit = revenue - investment
            roi = (profit / investment * 100) if investment > 0 else 0
            roi_results.append(roi)

            # Calcular breakeven (días para vender todas las unidades)
            breakeven = units / simulated_velocity if simulated_velocity > 0 else 999
            breakeven_results.append(breakeven)

        # Ordenar para sacar percentiles
        roi_results.sort()
        breakeven_results.sort()

        # Percentiles (85% confianza = sacar extremos 7.5% cada lado)
        p15_idx = int(len(roi_results) * 0.075)  # 7.5%
        p85_idx = int(len(roi_results) * 0.925)  # 92.5%

        roi_expected = sum(roi_results) / len(roi_results)
        roi_min = roi_results[p15_idx]
        roi_max = roi_results[p85_idx]

        breakeven_expected = sum(breakeven_results) / len(breakeven_results)
        breakeven_min = breakeven_results[p15_idx]
        breakeven_max = breakeven_results[p85_idx]

        return {
            "roi_expected": round(roi_expected, 1),
            "roi_min": round(roi_min, 1),
            "roi_max": round(roi_max, 1),
            "confidence_85": [round(roi_min, 1), round(roi_max, 1)],
            "breakeven_days": round(breakeven_expected, 1),
            "breakeven_range": [round(breakeven_min, 1), round(breakeven_max, 1)]
        }

    def calculate_roi_simulation(self, sku: str, units: int, use_external_signals: bool = True) -> Dict:
        """
        Calcula ROI completo con simulación para un SKU

        Args:
            sku: SKU del producto
            units: Unidades a reordenar
            use_external_signals: Si True, integra señales externas (clima + feriados)

        Returns:
            Diccionario completo con ROI, probabilidades y narrativa
        """
        # 1. Obtener datos del producto
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT price, cost_price, velocity_daily, stock, category, name
            FROM products
            WHERE sku = ?
        """, (sku,))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return {"error": f"Producto {sku} no encontrado"}

        price, cost, velocity_current, stock, category, name = result

        if not cost or cost == 0:
            return {"error": f"Producto {sku} sin costo definido"}

        # 2. Obtener historial y calcular estadísticas
        # 🧠 DECAY ADAPTATIVO: Ajusta según clics del usuario
        adaptive_decay = self.get_adaptive_decay_factor(base_decay=0.3)
        history = self.get_sales_history(sku, days=30)
        stats = self.calculate_statistics(history, decay_factor=adaptive_decay)

        # 🌡️ SEÑALES EXTERNAS: Clima + Feriados (Columbus, Ohio)
        contextual_multiplier = 1.0
        external_reason = None

        if use_external_signals:
            try:
                from external_signals_engine import ExternalSignalsEngine
                signals = ExternalSignalsEngine()
                context = signals.get_contextual_multiplier(name, use_mock_weather=True)

                if context["has_any_impact"]:
                    contextual_multiplier = context["final_multiplier"]
                    external_reason = context["combined_reason"]

                    # Ajustar mean con multiplicador contextual
                    stats["mean"] = stats["mean"] * contextual_multiplier

            except Exception as e:
                # Si falla, continuar sin señales externas
                pass

        # 3. Simulación Monte Carlo
        simulation = self.monte_carlo_simulation(
            mean=stats["mean"],
            std_dev=stats["std_dev"],
            units=units,
            price=price,
            cost=cost,
            iterations=100
        )

        # 4. Cálculos adicionales
        investment = units * cost
        revenue_expected = units * price
        profit_expected = revenue_expected - investment

        # Risk level basado en volatilidad
        cv = stats["std_dev"] / stats["mean"] if stats["mean"] > 0 else 0  # Coeficiente variación

        if cv < 0.2:
            risk_level = "bajo"
        elif cv < 0.5:
            risk_level = "medio"
        else:
            risk_level = "alto"

        # 5. Narrativa
        roi_multiplier = simulation["roi_expected"] / 100 + 1
        narrative = self._generate_roi_narrative(
            name=name,
            sku=sku,
            units=units,
            investment=investment,
            revenue=revenue_expected,
            roi=simulation["roi_expected"],
            roi_range=simulation["confidence_85"],
            breakeven=simulation["breakeven_days"],
            risk_level=risk_level,
            category=category,
            external_reason=external_reason  # 🌡️ Contexto externo
        )

        return {
            "sku": sku,
            "name": name,
            "units": units,
            "investment": round(investment, 2),
            "revenue_expected": round(revenue_expected, 2),
            "profit_expected": round(profit_expected, 2),
            "roi_expected": simulation["roi_expected"],
            "roi_range": simulation["confidence_85"],
            "roi_multiplier": round(roi_multiplier, 2),
            "breakeven_days": simulation["breakeven_days"],
            "breakeven_range": simulation["breakeven_range"],
            "risk_level": risk_level,
            "volatility": round(cv, 2),
            "current_stock": stock,
            "velocity_current": velocity_current,
            "velocity_stats": stats,
            "decay_factor_used": adaptive_decay,  # 🧠 Decay adaptativo usado
            "contextual_multiplier": contextual_multiplier,  # 🌡️ Clima + Feriados
            "external_reason": external_reason,  # Por qué del spike
            "narrative": narrative
        }

    def _generate_roi_narrative(
        self,
        name: str,
        sku: str,
        units: int,
        investment: float,
        revenue: float,
        roi: float,
        roi_range: List[float],
        breakeven: float,
        risk_level: str,
        category: str,
        external_reason: Optional[str] = None
    ) -> str:
        """Genera narrativa estilo Tiburón para la simulación"""

        # Emojis según risk level
        risk_emoji = {
            "bajo": "✅",
            "medio": "⚠️",
            "alto": "🔴"
        }

        # Comentario según categoría
        category_context = {
            "A": "producto estrella",
            "B": "producto sólido",
            "C": "producto lento",
            "Dead": "producto muerto"
        }.get(category, "producto")

        # Tono según ROI
        if roi >= 50:
            tone = "esto es dinero seguro"
        elif roi >= 30:
            tone = "movida sólida"
        elif roi >= 15:
            tone = "ganancia conservadora"
        else:
            tone = "ROI ajustado - evaluar"

        narrative = f"""🦈 **{name}** ({sku}) - {category_context.upper()}

💰 Invertís ${investment:,.0f} → Recuperás ${revenue:,.0f} en ~{breakeven:.0f} días
📊 ROI: **{roi:.1f}%** (Confianza 85%: {roi_range[0]:.1f}% - {roi_range[1]:.1f}%)
{risk_emoji[risk_level]} Riesgo: **{risk_level.upper()}**"""

        # 🌡️ CONTEXTO EXTERNO: Por qué del spike
        if external_reason:
            narrative += f"\n\n🌡️ **Contexto:** {external_reason}"

        narrative += f"\n\n**Veredicto:** Con {units} unidades, {tone}. {'Dale gas! 🔥' if roi >= 30 else 'Ajustar o liquidar primero.' if roi < 15 else 'Proceder con cautela.'}"

        return narrative


# Testing simple
if __name__ == "__main__":
    engine = StatsEngine()

    # Test con SKU real
    result = engine.calculate_roi_simulation(sku="SOMB-ARCO-09", units=25)

    print("\n" + "="*60)
    print("🦈 TIBURÓN - SIMULACIÓN ROI")
    print("="*60)
    print(result.get("narrative", "Sin narrativa"))
    print("\n📈 DATOS TÉCNICOS:")
    print(f"  - Inversión: ${result['investment']}")
    print(f"  - Profit esperado: ${result['profit_expected']}")
    print(f"  - ROI Multiplier: {result['roi_multiplier']}x")
    print(f"  - Breakeven: {result['breakeven_days']} días (rango: {result['breakeven_range']})")
    print(f"  - Volatilidad: {result['volatility']}")
    print("="*60)
