"""
🔐 AUTHENTICATION MIDDLEWARE - API Key Validation
Sistema de autenticación para endpoints críticos de La Chaparrita.

Uso:
    from auth_middleware import require_api_key

    @app.route('/api/protected')
    @require_api_key
    def protected_endpoint():
        return {"data": "sensitive"}

Variables de Entorno Requeridas:
    SHOPIFY_API_KEY - Admin full access
    READONLY_API_KEY - Read-only access (opcional)
"""

from functools import wraps
from flask import request, jsonify
import os
import logging

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN DE API KEYS
# ============================================================

# API Keys desde variables de entorno
API_KEYS = {}

# Key principal (admin full access)
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')
if SHOPIFY_API_KEY:
    API_KEYS[SHOPIFY_API_KEY] = {
        'shop': 'la-chaparrita',
        'role': 'admin',
        'permissions': ['read', 'write', 'delete']
    }
    logger.info("✅ SHOPIFY_API_KEY configurada")
else:
    logger.warning("⚠️ SHOPIFY_API_KEY no configurada - auth deshabilitado")

# Key read-only (opcional)
READONLY_API_KEY = os.getenv('READONLY_API_KEY')
if READONLY_API_KEY:
    API_KEYS[READONLY_API_KEY] = {
        'shop': '*',  # Todas las tiendas
        'role': 'readonly',
        'permissions': ['read']
    }
    logger.info("✅ READONLY_API_KEY configurada")

# Modo desarrollo (sin auth si no hay keys)
AUTH_ENABLED = len(API_KEYS) > 0

# ============================================================
# DECORADOR DE AUTENTICACIÓN
# ============================================================

def require_api_key(f):
    """
    Decorator que requiere API Key válida en header X-API-Key.

    Si AUTH_ENABLED = False (no hay keys configuradas):
        → Permite acceso (modo desarrollo)
        → Loguea warning

    Si AUTH_ENABLED = True:
        → Valida X-API-Key header
        → 401 Unauthorized si falta o es inválida

    Ejemplo:
        @cashflow_bp.route('/api/cashflow/summary')
        @require_api_key
        def get_cashflow_summary():
            # Solo accesible con API key válida
            return jsonify({"data": "..."})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Modo desarrollo: permitir sin auth
        if not AUTH_ENABLED:
            logger.debug(f"⚠️ Auth bypass (no keys configuradas) - {request.path}")
            return f(*args, **kwargs)

        # Obtener API key del header
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            logger.warning(f"🚫 Auth failed: Missing X-API-Key header - {request.path} from {request.remote_addr}")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Missing X-API-Key header'
            }), 401

        # Validar API key
        if api_key not in API_KEYS:
            logger.warning(f"🚫 Auth failed: Invalid API key - {request.path} from {request.remote_addr}")
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Invalid API key'
            }), 401

        # Auth exitoso
        key_info = API_KEYS[api_key]
        logger.debug(f"✅ Auth OK: {key_info['role']} - {request.path}")

        # Agregar info de auth al request (disponible en endpoint)
        request.api_key_info = key_info

        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# HELPER: VERIFICAR PERMISOS
# ============================================================

def has_permission(permission: str) -> bool:
    """
    Verifica si la API key actual tiene un permiso específico.

    Args:
        permission: 'read', 'write', 'delete'

    Returns:
        bool: True si tiene permiso

    Ejemplo:
        @require_api_key
        def delete_product():
            if not has_permission('delete'):
                return jsonify({'error': 'Forbidden'}), 403
            # ... proceder con delete
    """
    if not hasattr(request, 'api_key_info'):
        return False

    return permission in request.api_key_info.get('permissions', [])


# ============================================================
# TESTING / DEBUG
# ============================================================

if __name__ == "__main__":
    # Configurar logging para testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n=== AUTH MIDDLEWARE TEST ===\n")
    print(f"AUTH_ENABLED: {AUTH_ENABLED}")
    print(f"Configured API Keys: {len(API_KEYS)}")

    for key, info in API_KEYS.items():
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        print(f"  - {masked_key}: {info['role']} ({info['shop']})")

    if not AUTH_ENABLED:
        print("\n⚠️ WARNING: No API keys configured - auth disabled!")
        print("Set SHOPIFY_API_KEY environment variable to enable auth.")
