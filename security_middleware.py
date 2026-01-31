#!/usr/bin/env python3
"""
🔒 SECURITY MIDDLEWARE - Decoradores de intercepción
Capa de abstracción de seguridad para endpoints
"""

from functools import wraps
from flask import jsonify, request
from lockdown_manager import get_lockdown_manager
import logging
import os

logger = logging.getLogger(__name__)

# Admin API Key (para endpoints protegidos)
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "your-super-secret-admin-key")


def check_system_status(f):
    """
    Decorador que verifica si el sistema está congelado.

    Bloquea ejecución de endpoints si SYSTEM_FROZEN = True.
    Retorna 423 Locked con mensaje explicativo.

    Usage:
        @app.route('/api/execute-reorder', methods=['POST'])
        @check_system_status
        def execute_reorder():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        manager = get_lockdown_manager()

        if manager.is_frozen():
            status = manager.get_status()

            logger.warning(
                f"🧊 BLOCKED by Protocolo Cero Absoluto: {request.path} "
                f"from {request.remote_addr}"
            )

            return jsonify({
                "error": "System frozen",
                "code": "PROTOCOLO_CERO_ABSOLUTO",
                "message": "🧊 Fer, sistema criogenizado. He puesto un muro de fuego en el Cashflow. Nada sale, nada entra hasta tu comando de reactivación.",
                "frozen_since": status.get('frozen_at'),
                "frozen_by": status.get('frozen_by'),
                "reason": status.get('reason'),
                "contact": "Usa /api/admin/thaw con ADMIN_API_KEY para reactivar"
            }), 423  # 423 Locked

        # Sistema operacional - continuar
        return f(*args, **kwargs)

    return decorated_function


def require_admin_key(f):
    """
    Decorador que requiere ADMIN_API_KEY en header.

    Protege endpoints administrativos sensibles.

    Usage:
        @app.route('/api/admin/thaw', methods=['POST'])
        @require_admin_key
        def admin_thaw():
            ...

    Header requerido:
        X-Admin-Key: your-super-secret-admin-key
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Admin-Key')

        if not api_key:
            logger.warning(
                f"🔒 BLOCKED - Missing admin key: {request.path} from {request.remote_addr}"
            )
            return jsonify({
                "error": "Missing admin key",
                "message": "Header X-Admin-Key requerido"
            }), 401

        if api_key != ADMIN_API_KEY:
            logger.warning(
                f"🔒 BLOCKED - Invalid admin key: {request.path} from {request.remote_addr}"
            )
            return jsonify({
                "error": "Invalid admin key",
                "message": "X-Admin-Key inválido"
            }), 403

        # Key válido - continuar
        logger.info(f"🔓 Admin access granted: {request.path}")
        return f(*args, **kwargs)

    return decorated_function


def log_execution_attempt(f):
    """
    Decorador que registra intentos de ejecución (audit log).

    Útil para endpoints críticos como execute-reorder, execute-liquidate.

    Usage:
        @app.route('/api/execute-reorder', methods=['POST'])
        @log_execution_attempt
        @check_system_status
        def execute_reorder():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Log antes de ejecutar
        logger.info(
            f"📝 EXECUTION ATTEMPT: {request.path} "
            f"from {request.remote_addr} "
            f"method={request.method}"
        )

        # Ejecutar función
        result = f(*args, **kwargs)

        # Log después de ejecutar
        logger.info(f"✅ EXECUTION COMPLETED: {request.path}")

        return result

    return decorated_function
