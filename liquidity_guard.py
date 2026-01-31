#!/usr/bin/env python3
"""
🛡️ LIQUIDITY GUARD - Escudo de Liquidez y Cash Conversion Cycle
Protege la caja y monitorea flujo de dinero
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"


class LiquidityGuard:
    """Guardián de liquidez - monitorea CCC y protege reservas"""

    # Configuración de Escudo
    ESCUDO_THRESHOLD_ROI = 2.0  # ROI risk-adjusted mínimo para no reservar
    ESCUDO_RESERVE_PCT = 0.20   # 20% del budget se reserva si hay riesgo
    CRITICAL_DAYS = 7           # Días de cobertura críticos
    WARNING_DAYS = 15           # Días de cobertura en warning
    HEALTHY_DAYS = 30           # Días de cobertura saludables

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def calculate_ccc(self) -> Dict:
        """
        Calcula Cash Conversion Cycle (CCC)

        CCC = DIO + DSO - DPO
        Donde:
        - DIO (Days Inventory Outstanding): Días que inventario está en stock
        - DSO (Days Sales Outstanding): Días para cobrar (asumimos 0 - e-commerce)
        - DPO (Days Payable Outstanding): Días que tardamos en pagar proveedores

        En e-commerce simplificado:
        CCC ≈ DIO - DPO
        CCC negativo = BIEN (cobramos antes de pagar)
        CCC positivo = dinero atascado

        Returns:
            {
                "ccc_days": días totales,
                "dio": días inventario en stock,
                "dso": días cobranza (0 para e-commerce),
                "dpo": días pago a proveedores,
                "trend": "acelerando" | "estable" | "ralentizando",
                "health": "crítico" | "warning" | "saludable"
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Calcular DIO (Days Inventory Outstanding)
        # DIO = (Inventario Promedio / Costo de Ventas) * 365

        cursor.execute("""
            SELECT
                AVG(stock * cost_price) as avg_inventory,
                SUM(velocity_daily * cost_price * 30) as cogs_30d
            FROM products
            WHERE cost_price > 0 AND velocity_daily > 0
        """)

        result = cursor.fetchone()
        avg_inventory = result[0] if result[0] else 0
        cogs_30d = result[1] if result[1] else 1  # Evitar división por cero

        dio = (avg_inventory / (cogs_30d / 30)) if cogs_30d > 0 else 0

        # 2. DSO = 0 (e-commerce cobra inmediato)
        dso = 0

        # 3. DPO (Days Payable Outstanding) - estimado
        # Asumimos pago a proveedores a 30 días (configurable)
        dpo = 30  # TODO: hacer configurable por proveedor

        # 4. CCC
        ccc = dio + dso - dpo

        # 5. Trend (comparar con período anterior)
        # TODO: implementar cálculo de trend real con histórico
        if ccc < 0:
            trend = "acelerando"  # Dinero fluye rápido
        elif ccc < 10:
            trend = "estable"
        else:
            trend = "ralentizando"  # Dinero atascado

        # 6. Health
        if ccc > 20:
            health = "crítico"
        elif ccc > 10:
            health = "warning"
        else:
            health = "saludable"

        conn.close()

        return {
            "ccc_days": round(ccc, 1),
            "dio": round(dio, 1),
            "dso": dso,
            "dpo": dpo,
            "trend": trend,
            "health": health,
            "interpretation": self._interpret_ccc(ccc, trend)
        }

    def _interpret_ccc(self, ccc: float, trend: str) -> str:
        """Genera interpretación humana del CCC"""

        if ccc < 0:
            return f"🚀 CCC negativo ({ccc:.1f} días) - Cobrás ANTES de pagar. Flujo acelerado!"
        elif ccc < 5:
            return f"✅ CCC bajo ({ccc:.1f} días) - Flujo saludable. Dinero casi no se atasca."
        elif ccc < 15:
            return f"⚠️ CCC medio ({ccc:.1f} días) - Dinero tarda en circular. Optimizar inventario."
        else:
            return f"🔴 CCC alto ({ccc:.1f} días) - Dinero muy atascado. Liquidar dead stock YA."

    def calculate_liquidity_shield(self, proposed_investment: float = 0) -> Dict:
        """
        Calcula estado del Escudo de Liquidez

        Args:
            proposed_investment: Inversión propuesta (para simular impacto)

        Returns:
            {
                "current_inventory_value": valor total inventario,
                "available_cash": efectivo disponible (simulado),
                "daily_burn_rate": gasto diario operacional,
                "days_of_coverage": días sin ventas que resistimos,
                "escudo_active": bool - si escudo está activado,
                "escudo_reserve": monto reservado por el escudo,
                "post_investment_coverage": días después de invertir,
                "risk_level": "crítico" | "warning" | "saludable",
                "recommendation": texto narrativo
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Valor total de inventario
        cursor.execute("""
            SELECT SUM(stock * cost_price) as total_inventory
            FROM products
            WHERE cost_price > 0
        """)

        inventory_value = cursor.fetchone()[0] or 0

        # 2. Daily burn rate (estimado)
        # Burn = costo operacional fijo + costo variable promedio
        # Simplificado: 2.5% del inventario por día (ajustable)
        daily_burn = inventory_value * 0.025

        # 3. Available cash (simulado - en producción vendría de accounting)
        # Por ahora: asumimos cash = inventario (caso conservador)
        available_cash = inventory_value

        # 4. Days of coverage
        days_coverage = (available_cash / daily_burn) if daily_burn > 0 else 999

        # 5. Risk level
        if days_coverage < self.CRITICAL_DAYS:
            risk_level = "crítico"
        elif days_coverage < self.WARNING_DAYS:
            risk_level = "warning"
        else:
            risk_level = "saludable"

        # 6. Escudo activation
        ccc = self.calculate_ccc()
        escudo_active = False
        escudo_reserve = 0

        # Activar escudo si:
        # - CCC está subiendo (health != saludable)
        # - O la inversión propuesta reduce coverage bajo threshold
        post_investment_cash = available_cash - proposed_investment
        post_investment_coverage = (post_investment_cash / daily_burn) if daily_burn > 0 else 999

        if ccc["health"] != "saludable" or post_investment_coverage < self.WARNING_DAYS:
            escudo_active = True
            escudo_reserve = proposed_investment * self.ESCUDO_RESERVE_PCT

        # 7. Recommendation
        recommendation = self._generate_escudo_recommendation(
            days_coverage=days_coverage,
            post_investment_coverage=post_investment_coverage,
            escudo_active=escudo_active,
            escudo_reserve=escudo_reserve,
            risk_level=risk_level,
            ccc_health=ccc["health"]
        )

        conn.close()

        return {
            "current_inventory_value": round(inventory_value, 2),
            "available_cash": round(available_cash, 2),
            "daily_burn_rate": round(daily_burn, 2),
            "days_of_coverage": round(days_coverage, 1),
            "escudo_active": escudo_active,
            "escudo_reserve": round(escudo_reserve, 2),
            "post_investment_coverage": round(post_investment_coverage, 1),
            "risk_level": risk_level,
            "ccc_status": ccc,
            "recommendation": recommendation,
            "breakpoints": {
                "critical": self.CRITICAL_DAYS,
                "warning": self.WARNING_DAYS,
                "healthy": self.HEALTHY_DAYS
            }
        }

    def _generate_escudo_recommendation(
        self,
        days_coverage: float,
        post_investment_coverage: float,
        escudo_active: bool,
        escudo_reserve: float,
        risk_level: str,
        ccc_health: str
    ) -> str:
        """Genera recomendación narrativa del Escudo"""

        if escudo_active:
            return f"""🛡️ **ESCUDO ACTIVO** - Reserva ${escudo_reserve:,.0f} por volatilidad

📊 Cobertura actual: **{days_coverage:.0f} días**
📉 Post-inversión: **{post_investment_coverage:.0f} días**
⚠️ CCC Status: **{ccc_health.upper()}**

**Fer, jugada defensiva:** El Escudo reserva {int(self.ESCUDO_RESERVE_PCT * 100)}% del budget porque {'el CCC está subiendo' if ccc_health != 'saludable' else 'la inversión te deja con poca cobertura'}.

**Recomendación:** Liquidá dead stock primero para liberar ${escudo_reserve:,.0f}, o ajustá el reorden."""

        else:
            if days_coverage >= self.HEALTHY_DAYS:
                return f"""✅ **ESCUDO DESACTIVADO** - Liquidez saludable

📊 Cobertura: **{days_coverage:.0f} días** (objetivo: {self.HEALTHY_DAYS}+)
🚀 CCC: **{ccc_health.upper()}**

**Fer, estás blindado.** Tenés {days_coverage:.0f} días de cobertura - podés invertir sin drama. Dale gas! 🔥"""

            else:
                return f"""⚠️ **ESCUDO DESACTIVADO** - Pero cobertura en warning

📊 Cobertura: **{days_coverage:.0f} días** (objetivo: {self.HEALTHY_DAYS}+)
📉 Post-inversión: **{post_investment_coverage:.0f} días**

**Fer, movida ajustada.** No activé el Escudo porque CCC está OK, pero ojo con la cobertura. Considerá liquidar algo antes."""

    def get_dead_stock_candidates(self, min_days_stagnant: int = 60) -> List[Dict]:
        """
        Identifica productos candidatos a liquidación (dead stock)

        Args:
            min_days_stagnant: Días mínimos sin ventas para considerar dead

        Returns:
            Lista de productos con potencial de liquidación
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Dead stock = velocity muy baja + stock alto
        cursor.execute("""
            SELECT
                sku,
                name,
                stock,
                cost_price,
                price,
                velocity_daily,
                category,
                (stock * cost_price) as capital_trapped
            FROM products
            WHERE velocity_daily < 0.1
              AND stock > 0
              AND cost_price > 0
              AND category IN ('C', 'Dead')
            ORDER BY capital_trapped DESC
            LIMIT 20
        """)

        candidates = []
        for row in cursor.fetchall():
            sku, name, stock, cost, price, velocity, category, capital = row

            # Días para agotar stock a velocidad actual
            days_to_deplete = (stock / velocity) if velocity > 0 else 999

            candidates.append({
                "sku": sku,
                "name": name,
                "stock": stock,
                "cost_price": cost,
                "price": price,
                "velocity_daily": velocity,
                "category": category,
                "capital_trapped": round(capital, 2),
                "days_to_deplete": round(days_to_deplete, 1),
                "liquidation_priority": "alta" if capital > 500 else "media" if capital > 200 else "baja"
            })

        conn.close()
        return candidates

    def simulate_liquidation_impact(self, skus: List[str], discount_pct: float = 0.30) -> Dict:
        """
        Simula impacto de liquidar productos con descuento

        Args:
            skus: Lista de SKUs a liquidar
            discount_pct: Descuento a aplicar (default 30%)

        Returns:
            {
                "capital_freed": dinero liberado,
                "revenue_at_discount": ingreso con descuento,
                "loss_vs_original": pérdida vs precio original,
                "coverage_gain_days": días de cobertura ganados,
                "recommendation": narrativa
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(skus))
        cursor.execute(f"""
            SELECT
                SUM(stock * cost_price) as capital_trapped,
                SUM(stock * price) as revenue_original,
                SUM(stock * price * ?) as revenue_discounted
            FROM products
            WHERE sku IN ({placeholders})
        """, [1 - discount_pct] + skus)

        result = cursor.fetchone()
        capital_trapped = result[0] or 0
        revenue_original = result[1] or 0
        revenue_discounted = result[2] or 0

        loss_vs_original = revenue_original - revenue_discounted

        # Calcular ganancia en días de cobertura
        shield_data = self.calculate_liquidity_shield(proposed_investment=0)
        burn_rate = shield_data["daily_burn_rate"]
        coverage_gain = (revenue_discounted / burn_rate) if burn_rate > 0 else 0

        recommendation = f"""💰 **LIQUIDACIÓN SIMULADA** ({int(discount_pct * 100)}% descuento)

📦 Capital atrapado: ${capital_trapped:,.0f}
💵 Ingreso con descuento: ${revenue_discounted:,.0f}
📉 Pérdida vs precio original: ${loss_vs_original:,.0f}
⏱️ Días de cobertura ganados: **+{coverage_gain:.0f} días**

**Fer, los números muerden:** Sacrificás ${loss_vs_original:,.0f} pero liberás liquidez para {coverage_gain:.0f} días más de runway. {'Vale la pena - dale!' if coverage_gain >= 7 else 'Ganancia marginal - evaluar.'}"""

        conn.close()

        return {
            "capital_freed": round(capital_trapped, 2),
            "revenue_at_discount": round(revenue_discounted, 2),
            "revenue_original": round(revenue_original, 2),
            "loss_vs_original": round(loss_vs_original, 2),
            "coverage_gain_days": round(coverage_gain, 1),
            "discount_applied": discount_pct,
            "recommendation": recommendation
        }


# Testing simple
if __name__ == "__main__":
    guard = LiquidityGuard()

    print("\n" + "="*60)
    print("🛡️ ESCUDO DE LIQUIDEZ - TEST")
    print("="*60)

    # Test CCC
    ccc = guard.calculate_ccc()
    print("\n📊 CASH CONVERSION CYCLE:")
    print(f"  CCC: {ccc['ccc_days']} días")
    print(f"  Health: {ccc['health']}")
    print(f"  {ccc['interpretation']}")

    # Test Shield
    shield = guard.calculate_liquidity_shield(proposed_investment=1500)
    print("\n🛡️ ESCUDO:")
    print(shield["recommendation"])

    # Test Dead Stock
    dead = guard.get_dead_stock_candidates()
    print(f"\n💀 DEAD STOCK CANDIDATES: {len(dead)} productos")
    if dead:
        top = dead[0]
        print(f"  Top: {top['name']} - ${top['capital_trapped']} atrapados")

    print("="*60)
