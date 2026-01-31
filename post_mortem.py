#!/usr/bin/env python3
"""
📊 POST-MORTEM - Análisis de Opportunity Cost de Silencios
Calcula impacto de congelamientos (freeze) y sugiere ajustes
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"


class PostMortemAnalyzer:
    """
    Analizador de oportunidades perdidas durante freeze sessions.

    Calcula:
    - Ventas perdidas (basado en velocity promedio)
    - Oportunidades de reorden bloqueadas
    - Sugerencias de ajuste al Escudo
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def record_freeze_session(
        self,
        freeze_timestamp: datetime,
        frozen_by: str,
        reason: str
    ) -> int:
        """
        Registra inicio de freeze session.

        Args:
            freeze_timestamp: Timestamp del freeze
            frozen_by: Quién activó el freeze
            reason: Razón del freeze

        Returns:
            ID de la sesión creada
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO freeze_sessions
            (freeze_timestamp, frozen_by, reason)
            VALUES (?, ?, ?)
        """, (freeze_timestamp.isoformat(), frozen_by, reason))

        session_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return session_id

    def close_freeze_session(
        self,
        thaw_timestamp: datetime,
        thawed_by: str
    ) -> Optional[int]:
        """
        Cierra la sesión de freeze más reciente aún abierta.

        Args:
            thaw_timestamp: Timestamp del thaw
            thawed_by: Quién desactivó el freeze

        Returns:
            ID de la sesión cerrada, o None si no había sesión abierta
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buscar sesión abierta más reciente
        cursor.execute("""
            SELECT id, freeze_timestamp
            FROM freeze_sessions
            WHERE thaw_timestamp IS NULL
            ORDER BY freeze_timestamp DESC
            LIMIT 1
        """)

        result = cursor.fetchone()

        if not result:
            conn.close()
            return None

        session_id, freeze_ts = result

        # Calcular duración
        freeze_dt = datetime.fromisoformat(freeze_ts)
        duration_hours = (thaw_timestamp - freeze_dt).total_seconds() / 3600

        # Actualizar sesión
        cursor.execute("""
            UPDATE freeze_sessions
            SET thaw_timestamp = ?,
                thawed_by = ?,
                duration_hours = ?
            WHERE id = ?
        """, (thaw_timestamp.isoformat(), thawed_by, duration_hours, session_id))

        conn.commit()
        conn.close()

        return session_id

    def calculate_opportunity_cost(self, session_id: int) -> Dict:
        """
        Calcula opportunity cost de una freeze session.

        Args:
            session_id: ID de la sesión a analizar

        Returns:
            {
                "session_id": int,
                "duration_hours": float,
                "estimated_sales_lost": float,
                "reorder_opportunities_blocked": int,
                "capital_locked": float,
                "recommendation": str
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Obtener datos de la sesión
        cursor.execute("""
            SELECT freeze_timestamp, thaw_timestamp, duration_hours
            FROM freeze_sessions
            WHERE id = ?
        """, (session_id,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return {"error": f"Session {session_id} not found"}

        freeze_ts, thaw_ts, duration_hours = result

        if not thaw_ts:
            conn.close()
            return {"error": "Session not closed yet"}

        # Calcular ventas perdidas basado en velocity promedio
        cursor.execute("""
            SELECT
                SUM(velocity_daily * price * ?) as estimated_revenue_lost,
                COUNT(*) as products_with_velocity
            FROM products
            WHERE velocity_daily > 0
              AND price > 0
        """, (duration_hours / 24,))  # Convertir horas a días

        revenue_result = cursor.fetchone()
        estimated_sales_lost = revenue_result[0] or 0
        active_products = revenue_result[1] or 0

        # Identificar reordenes bloqueados (productos que estaban bajo stock)
        cursor.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE stock < (velocity_daily * 7)
              AND velocity_daily > 0
              AND category IN ('A', 'B')
        """)

        reorder_opportunities = cursor.fetchone()[0] or 0

        # Capital locked (inventario que no pudo moverse)
        cursor.execute("""
            SELECT SUM(stock * cost_price)
            FROM products
            WHERE cost_price > 0
        """)

        capital_locked = cursor.fetchone()[0] or 0

        # Guardar opportunity cost en la sesión
        cursor.execute("""
            UPDATE freeze_sessions
            SET opportunity_cost = ?
            WHERE id = ?
        """, (estimated_sales_lost, session_id))

        conn.commit()
        conn.close()

        # Generar recomendación
        days_frozen = duration_hours / 24

        if estimated_sales_lost > 1000:
            recommendation = f"🔴 ALTO COSTO: Congelaste {days_frozen:.1f} días – perdimos ${estimated_sales_lost:,.0f} en ventas proyectadas. Considerá subir el umbral del Escudo 15% para evitar freezes innecesarios."
        elif estimated_sales_lost > 500:
            recommendation = f"⚠️ COSTO MODERADO: {days_frozen:.1f} días frozen = ${estimated_sales_lost:,.0f} en oportunidad. Blindamos ${capital_locked:,.0f} - balance aceptable. Umbral OK."
        else:
            recommendation = f"✅ FREEZE JUSTIFICADO: {days_frozen:.1f} días, solo ${estimated_sales_lost:,.0f} perdidos. Protegimos ${capital_locked:,.0f}. Decisión correcta."

        return {
            "session_id": session_id,
            "duration_hours": round(duration_hours, 2),
            "duration_days": round(days_frozen, 2),
            "estimated_sales_lost": round(estimated_sales_lost, 2),
            "reorder_opportunities_blocked": reorder_opportunities,
            "capital_locked": round(capital_locked, 2),
            "active_products": active_products,
            "recommendation": recommendation
        }

    def generate_post_mortem(self, session_id: int) -> Dict:
        """
        Genera análisis post-mortem completo.

        Args:
            session_id: ID de la sesión

        Returns:
            Dict con análisis completo + narrativa para Discord
        """
        analysis = self.calculate_opportunity_cost(session_id)

        if "error" in analysis:
            return analysis

        # Generar narrativa para Discord
        narrative = f"""📊 **POST-MORTEM - ANÁLISIS DE SILENCIO**

🧊 **Sesión de Freeze #{session_id}**
⏱️ Duración: **{analysis['duration_days']:.1f} días** ({analysis['duration_hours']:.1f} horas)

💸 **Opportunity Cost:**
- Ventas perdidas (proyectadas): **${analysis['estimated_sales_lost']:,.0f}**
- Reordenes bloqueados: **{analysis['reorder_opportunities_blocked']} productos**
- Capital bloqueado: **${analysis['capital_locked']:,.0f}**
- Productos activos afectados: **{analysis['active_products']}**

🎯 **Recomendación:**
{analysis['recommendation']}

📈 **Próximos pasos:**
{'Ajustá el umbral del Escudo en liquidity_guard.py' if analysis['estimated_sales_lost'] > 1000 else 'Sistema balanceado - continuar monitoring'}"""

        analysis['narrative'] = narrative

        return analysis

    def mark_post_mortem_sent(self, session_id: int):
        """Marca que el post-mortem ya fue enviado."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE freeze_sessions
            SET post_mortem_sent = 1,
                post_mortem_timestamp = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), session_id))

        conn.commit()
        conn.close()

    def get_pending_post_mortems(self, hours_after_thaw: int = 24) -> List[int]:
        """
        Obtiene IDs de sesiones que necesitan post-mortem.

        Args:
            hours_after_thaw: Horas después de thaw para enviar post-mortem

        Returns:
            Lista de session IDs pendientes
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_time = (datetime.now() - timedelta(hours=hours_after_thaw)).isoformat()

        cursor.execute("""
            SELECT id
            FROM freeze_sessions
            WHERE thaw_timestamp IS NOT NULL
              AND thaw_timestamp <= ?
              AND post_mortem_sent = 0
            ORDER BY thaw_timestamp ASC
        """, (cutoff_time,))

        pending = [row[0] for row in cursor.fetchall()]

        conn.close()

        return pending


# Testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("📊 POST-MORTEM ANALYZER - TEST")
    print("="*60)

    analyzer = PostMortemAnalyzer()

    # Test: Simular freeze session
    print("\n1️⃣ Simulando freeze session...")
    freeze_time = datetime.now() - timedelta(days=2, hours=3)
    session_id = analyzer.record_freeze_session(
        freeze_timestamp=freeze_time,
        frozen_by="test_user",
        reason="Testing post-mortem"
    )
    print(f"   ✅ Session {session_id} creada")

    # Cerrar sesión
    thaw_time = datetime.now() - timedelta(hours=1)
    analyzer.close_freeze_session(
        thaw_timestamp=thaw_time,
        thawed_by="test_admin"
    )
    print(f"   ✅ Session cerrada")

    # Calcular opportunity cost
    print("\n2️⃣ Calculando opportunity cost...")
    analysis = analyzer.calculate_opportunity_cost(session_id)
    print(f"   Duración: {analysis['duration_days']:.1f} días")
    print(f"   Ventas perdidas: ${analysis['estimated_sales_lost']:,.2f}")
    print(f"   Reordenes bloqueados: {analysis['reorder_opportunities_blocked']}")

    # Generar post-mortem
    print("\n3️⃣ Generando post-mortem...")
    post_mortem = analyzer.generate_post_mortem(session_id)
    print(post_mortem['narrative'])

    print("="*60)
