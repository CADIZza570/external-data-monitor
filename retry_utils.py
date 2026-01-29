"""
🔄 RETRY UTILITIES - Exponential Backoff para Integraciones
Sistema de retry automático para Discord, Google Sheets, SendGrid.

Evita pérdida de alertas críticas por fallos temporales de red.

Uso:
    from retry_utils import get_retry_session

    session = get_retry_session(retries=3)
    response = session.post(discord_webhook_url, json=payload, timeout=10)
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)

# ============================================================
# RETRY SESSION FACTORY
# ============================================================

def get_retry_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: list = None,
    timeout: int = 10
) -> requests.Session:
    """
    Crea una session de requests con retry automático y exponential backoff.

    Args:
        retries: Número máximo de reintentos (default: 3)
        backoff_factor: Factor de backoff exponencial (default: 0.5)
            → Espera: {backoff_factor} * (2 ^ {retry_number})
            → Retry 1: 0.5s, Retry 2: 1s, Retry 3: 2s
        status_forcelist: HTTP status codes que disparan retry
            Default: [429, 500, 502, 503, 504]
        timeout: Timeout default para requests (default: 10s)

    Returns:
        requests.Session configurada con retry

    Ejemplo:
        session = get_retry_session(retries=3, backoff_factor=0.5)
        response = session.post(
            "https://discord.com/api/webhooks/...",
            json={"content": "Alert!"},
            timeout=10
        )

    Comportamiento:
        ✅ Retry automático en errores de red (ConnectionError, Timeout)
        ✅ Retry en HTTP 429 (rate limit), 500-504 (server errors)
        ✅ Exponential backoff (evita hammer el servidor)
        ⏭️ No retry en 4xx client errors (400, 401, 404, etc)
    """
    if status_forcelist is None:
        status_forcelist = [429, 500, 502, 503, 504]

    session = requests.Session()

    # Configurar estrategia de retry
    retry_strategy = Retry(
        total=retries,                    # Máximo de reintentos
        backoff_factor=backoff_factor,    # Exponential backoff
        status_forcelist=status_forcelist, # HTTP codes que disparan retry
        allowed_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],  # Todos los métodos
        raise_on_status=False              # No lanzar excepción en retry
    )

    # Aplicar retry a HTTP y HTTPS
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    logger.debug(f"✅ Retry session creada: {retries} retries, {backoff_factor}s backoff")

    return session


# ============================================================
# HELPERS: WRAPPERS CON RETRY
# ============================================================

def post_with_retry(url: str, json_data: dict = None, retries: int = 3, timeout: int = 10) -> requests.Response:
    """
    POST con retry automático (wrapper simple).

    Args:
        url: URL destino
        json_data: Payload JSON
        retries: Número de reintentos
        timeout: Timeout en segundos

    Returns:
        requests.Response

    Raises:
        requests.RequestException si falla después de todos los retries

    Ejemplo:
        response = post_with_retry(
            "https://discord.com/api/webhooks/...",
            json_data={"content": "Stock bajo!"},
            retries=3
        )
        if response.status_code == 204:
            print("✅ Alert enviada")
    """
    session = get_retry_session(retries=retries)

    try:
        logger.debug(f"📤 POST {url} (retry: {retries}x)")
        response = session.post(url, json=json_data, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"❌ POST failed después de {retries} retries: {url} - {e}")
        raise


def get_with_retry(url: str, params: dict = None, retries: int = 3, timeout: int = 10) -> requests.Response:
    """
    GET con retry automático (wrapper simple).

    Args:
        url: URL destino
        params: Query parameters
        retries: Número de reintentos
        timeout: Timeout en segundos

    Returns:
        requests.Response

    Raises:
        requests.RequestException si falla después de todos los retries
    """
    session = get_retry_session(retries=retries)

    try:
        logger.debug(f"📥 GET {url} (retry: {retries}x)")
        response = session.get(url, params=params, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"❌ GET failed después de {retries} retries: {url} - {e}")
        raise


# ============================================================
# TESTING / DEBUG
# ============================================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("\n=== RETRY UTILITIES TEST ===\n")

    # Test 1: URL que falla (simulación)
    print("Test 1: Retry en error 500")
    try:
        session = get_retry_session(retries=3, backoff_factor=0.3)
        # httpstat.us retorna el status code que le pidas
        response = session.get("https://httpstat.us/500", timeout=5)
        print(f"  Status: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Failed después de retries: {e}")

    # Test 2: URL que funciona
    print("\nTest 2: Request exitoso")
    try:
        response = get_with_retry("https://httpstat.us/200", retries=3, timeout=5)
        print(f"  ✅ Status: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Error: {e}")

    # Test 3: Mostrar backoff times
    print("\nTest 3: Exponential backoff times:")
    print("  Backoff factor: 0.5")
    print("  Retry 1: 0.5s")
    print("  Retry 2: 1.0s")
    print("  Retry 3: 2.0s")
    print("  Total max wait: ~3.5s + request times")
