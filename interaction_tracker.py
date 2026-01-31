#!/usr/bin/env python3
"""
🧠 INTERACTION TRACKER - Sistema de Aprendizaje por Clics
Tracking de interacciones Discord para ajustar comportamiento del Tiburón
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"


class InteractionTracker:
    """
    Tracker de interacciones del usuario con botones Discord.

    Aprende patrones de comportamiento para ajustar agresividad del sistema.
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path

    def track_click(
        self,
        button_id: str,
        action_type: str,
        user_id: str = "fer",
        context: Optional[str] = None,
        sku: Optional[str] = None,
        units: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Registra un click en botón Discord.

        Args:
            button_id: ID del botón (ej: "approve_reorder", "simulate_aggressive")
            action_type: Tipo de acción (ej: "reorder", "liquidate", "simulate")
            user_id: Usuario que hizo click (default: "fer")
            context: Contexto adicional (ej: descripción del producto)
            sku: SKU del producto si aplica
            units: Cantidad de unidades si aplica
            metadata: Datos adicionales en JSON

        Returns:
            ID del registro insertado
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        metadata_json = json.dumps(metadata) if metadata else None

        cursor.execute("""
            INSERT INTO interaction_metrics
            (user_id, button_id, action_type, context, sku, units, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, button_id, action_type, context, sku, units, metadata_json))

        interaction_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return interaction_id

    def get_recent_pattern(self, days: int = 7, user_id: str = "fer") -> Dict:
        """
        Analiza patrón de clics recientes.

        Args:
            days: Número de días a analizar
            user_id: Usuario a analizar

        Returns:
            {
                "total_clicks": int,
                "aggressive_clicks": int,  # Clics en "Simular Agresivo"
                "approve_clicks": int,
                "reject_clicks": int,
                "aggressive_ratio": float,  # 0.0 - 1.0
                "suggested_decay_boost": float  # 0.0 - 0.15 (boost adicional)
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Contar clics por tipo
        cursor.execute("""
            SELECT button_id, COUNT(*) as count
            FROM interaction_metrics
            WHERE user_id = ?
              AND timestamp >= ?
            GROUP BY button_id
        """, (user_id, cutoff_date))

        clicks_by_button = {row[0]: row[1] for row in cursor.fetchall()}

        # Calcular totales
        total_clicks = sum(clicks_by_button.values())
        aggressive_clicks = clicks_by_button.get("simulate_aggressive", 0)
        approve_clicks = clicks_by_button.get("approve_reorder", 0)
        reject_clicks = clicks_by_button.get("reject", 0)

        # Ratio agresivo
        aggressive_ratio = (aggressive_clicks / total_clicks) if total_clicks > 0 else 0

        # Boost sugerido al decay factor
        # Si >3 clics agresivos en 7 días → boost 10-15%
        if aggressive_clicks >= 5:
            suggested_decay_boost = 0.15  # Muy agresivo
        elif aggressive_clicks >= 3:
            suggested_decay_boost = 0.10  # Moderadamente agresivo
        else:
            suggested_decay_boost = 0.0   # Normal

        conn.close()

        return {
            "total_clicks": total_clicks,
            "aggressive_clicks": aggressive_clicks,
            "approve_clicks": approve_clicks,
            "reject_clicks": reject_clicks,
            "aggressive_ratio": round(aggressive_ratio, 2),
            "suggested_decay_boost": suggested_decay_boost,
            "analysis_days": days
        }

    def get_click_history(self, limit: int = 20, user_id: str = "fer") -> List[Dict]:
        """
        Obtiene historial de clics recientes.

        Args:
            limit: Número máximo de registros
            user_id: Usuario a consultar

        Returns:
            Lista de diccionarios con datos de clics
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id, user_id, button_id, action_type, context,
                sku, units, timestamp, metadata
            FROM interaction_metrics
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))

        history = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return history

    def get_button_stats(self, days: int = 30) -> List[Dict]:
        """
        Estadísticas de uso por botón.

        Args:
            days: Días a analizar

        Returns:
            Lista de stats por botón ordenadas por popularidad
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        cursor.execute("""
            SELECT
                button_id,
                COUNT(*) as total_clicks,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(timestamp) as first_click,
                MAX(timestamp) as last_click
            FROM interaction_metrics
            WHERE timestamp >= ?
            GROUP BY button_id
            ORDER BY total_clicks DESC
        """, (cutoff_date,))

        stats = []
        for row in cursor.fetchall():
            button_id, total, users, first, last = row
            stats.append({
                "button_id": button_id,
                "total_clicks": total,
                "unique_users": users,
                "first_click": first,
                "last_click": last,
                "avg_clicks_per_user": round(total / users, 2) if users > 0 else 0
            })

        conn.close()
        return stats


# Testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧠 INTERACTION TRACKER - TEST")
    print("="*60)

    tracker = InteractionTracker()

    # Test 1: Simular algunos clics
    print("\n1️⃣ Simulando clics...")
    tracker.track_click(
        button_id="simulate_aggressive",
        action_type="simulate",
        context="ROI simulation for SOMB-ARCO-09",
        sku="SOMB-ARCO-09",
        units=25
    )
    tracker.track_click(
        button_id="simulate_aggressive",
        action_type="simulate",
        context="Testing aggressive mode",
        sku="TEST-01"
    )
    tracker.track_click(
        button_id="approve_reorder",
        action_type="reorder",
        sku="PROD-01",
        units=50
    )
    print("   ✅ 3 clics registrados")

    # Test 2: Analizar patrón
    print("\n2️⃣ Analizando patrón de clics...")
    pattern = tracker.get_recent_pattern(days=7)
    print(f"   Total clics: {pattern['total_clicks']}")
    print(f"   Clics agresivos: {pattern['aggressive_clicks']}")
    print(f"   Ratio agresivo: {pattern['aggressive_ratio']*100:.0f}%")
    print(f"   Boost sugerido: {pattern['suggested_decay_boost']*100:.0f}%")

    # Test 3: Historial
    print("\n3️⃣ Historial de clics:")
    history = tracker.get_click_history(limit=5)
    for click in history:
        print(f"   - {click['button_id']} | {click['sku']} | {click['timestamp']}")

    # Test 4: Stats por botón
    print("\n4️⃣ Stats por botón:")
    stats = tracker.get_button_stats(days=30)
    for stat in stats:
        print(f"   - {stat['button_id']}: {stat['total_clicks']} clics")

    print("="*60)
