#!/usr/bin/env python3
"""
❄️ LOCKDOWN MANAGER - Protocolo Cero Absoluto
Sistema de congelamiento global para emergencias
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"


class LockdownManager:
    """
    Gestor de estado de congelamiento del sistema.

    Protocolo Cero Absoluto:
    - SYSTEM_FROZEN = True → Bloquea TODOS los endpoints de ejecución
    - Persiste en DB para sobrevivir reinicios
    - Registra eventos de seguridad
    """

    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._ensure_lockdown_table()

    def _ensure_lockdown_table(self):
        """Crear tabla de lockdown si no existe"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_lockdown (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                frozen BOOLEAN DEFAULT 0,
                frozen_at TIMESTAMP,
                frozen_by TEXT,
                reason TEXT,
                thawed_at TIMESTAMP,
                thawed_by TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insertar registro inicial si no existe
        cursor.execute("""
            INSERT OR IGNORE INTO system_lockdown (id, frozen)
            VALUES (1, 0)
        """)

        conn.commit()
        conn.close()

    def is_frozen(self) -> bool:
        """
        Verifica si el sistema está congelado.

        Returns:
            bool - True si está congelado, False si operacional
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT frozen FROM system_lockdown WHERE id = 1")
        result = cursor.fetchone()

        conn.close()

        if result:
            return bool(result[0])
        return False

    def freeze(self, frozen_by: str = "manual", reason: str = "Emergency lockdown") -> Dict:
        """
        Congela el sistema - activa Protocolo Cero Absoluto.

        Args:
            frozen_by: Quién activó el freeze (user ID, IP, etc.)
            reason: Razón del congelamiento

        Returns:
            Dict con status del freeze
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            UPDATE system_lockdown
            SET frozen = 1,
                frozen_at = ?,
                frozen_by = ?,
                reason = ?,
                last_updated = ?
            WHERE id = 1
        """, (now, frozen_by, reason, now))

        conn.commit()

        # Registrar evento de seguridad
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT DEFAULT 'high',
                description TEXT,
                triggered_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO security_events (event_type, severity, description, triggered_by)
            VALUES ('SYSTEM_FREEZE', 'critical', ?, ?)
        """, (reason, frozen_by))

        conn.commit()
        conn.close()

        logger.critical(f"❄️ PROTOCOLO CERO ABSOLUTO ACTIVADO - Frozen by: {frozen_by}, Reason: {reason}")

        return {
            "frozen": True,
            "frozen_at": now,
            "frozen_by": frozen_by,
            "reason": reason,
            "message": "🧊 Sistema criogenizado. Muro de fuego activado - nada sale, nada entra."
        }

    def thaw(self, thawed_by: str = "manual") -> Dict:
        """
        Descongela el sistema - desactiva Protocolo Cero Absoluto.

        Args:
            thawed_by: Quién desactivó el freeze

        Returns:
            Dict con status del thaw
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Verificar si estaba congelado
        cursor.execute("SELECT frozen, frozen_at FROM system_lockdown WHERE id = 1")
        result = cursor.fetchone()

        if not result or not result[0]:
            conn.close()
            return {
                "frozen": False,
                "message": "⚠️ Sistema ya estaba descongelado"
            }

        frozen_at = result[1]

        cursor.execute("""
            UPDATE system_lockdown
            SET frozen = 0,
                thawed_at = ?,
                thawed_by = ?,
                last_updated = ?
            WHERE id = 1
        """, (now, thawed_by, now))

        conn.commit()

        # Registrar evento de seguridad
        cursor.execute("""
            INSERT INTO security_events (event_type, severity, description, triggered_by)
            VALUES ('SYSTEM_THAW', 'high', ?, ?)
        """, (f"System thawed after freeze at {frozen_at}", thawed_by))

        conn.commit()
        conn.close()

        logger.warning(f"🔥 PROTOCOLO CERO ABSOLUTO DESACTIVADO - Thawed by: {thawed_by}")

        return {
            "frozen": False,
            "thawed_at": now,
            "thawed_by": thawed_by,
            "message": "🔥 Sistema reactivado. Muro de fuego desactivado - operaciones restauradas."
        }

    def get_status(self) -> Dict:
        """
        Obtiene estado completo del lockdown.

        Returns:
            Dict con estado actual y detalles
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT frozen, frozen_at, frozen_by, reason, thawed_at, thawed_by, last_updated
            FROM system_lockdown
            WHERE id = 1
        """)

        result = cursor.fetchone()
        conn.close()

        if not result:
            return {
                "frozen": False,
                "message": "Sistema operacional"
            }

        status = dict(result)
        status['message'] = (
            "🧊 SISTEMA CONGELADO - Protocolo Cero Absoluto activo"
            if status['frozen']
            else "✅ Sistema operacional"
        )

        return status

    def get_security_events(self, limit: int = 10) -> list:
        """
        Obtiene últimos eventos de seguridad relacionados con lockdown.

        Args:
            limit: Número máximo de eventos a retornar

        Returns:
            Lista de eventos de seguridad
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT event_type, severity, description, triggered_by, created_at
            FROM security_events
            WHERE event_type IN ('SYSTEM_FREEZE', 'SYSTEM_THAW')
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))

        events = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return events


# Singleton global
_lockdown_manager = None

def get_lockdown_manager() -> LockdownManager:
    """Retorna instancia singleton del LockdownManager"""
    global _lockdown_manager
    if _lockdown_manager is None:
        _lockdown_manager = LockdownManager()
    return _lockdown_manager


# Testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("❄️ PROTOCOLO CERO ABSOLUTO - TEST")
    print("="*60)

    manager = LockdownManager()

    # Test 1: Status inicial
    print("\n1️⃣ Status inicial:")
    status = manager.get_status()
    print(f"   Frozen: {status['frozen']}")
    print(f"   Message: {status['message']}")

    # Test 2: Freeze
    print("\n2️⃣ Activando freeze...")
    result = manager.freeze(frozen_by="test_user", reason="Testing Protocolo Cero Absoluto")
    print(f"   {result['message']}")
    print(f"   Frozen at: {result['frozen_at']}")

    # Test 3: Verificar frozen
    print("\n3️⃣ Verificando estado congelado:")
    print(f"   is_frozen(): {manager.is_frozen()}")

    # Test 4: Thaw
    print("\n4️⃣ Descongelando...")
    result = manager.thaw(thawed_by="test_admin")
    print(f"   {result['message']}")

    # Test 5: Eventos de seguridad
    print("\n5️⃣ Eventos de seguridad:")
    events = manager.get_security_events(limit=5)
    for event in events:
        print(f"   - [{event['event_type']}] {event['description']} (by: {event['triggered_by']})")

    print("="*60)
