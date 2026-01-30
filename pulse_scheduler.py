"""
🗓️ PULSE SCHEDULER - El Corazón del Centinela
Envía resumen narrativo diario a Discord con el "Pulso de La Chaparrita"

Track 3.0: "El Primer Pulso"
Automatiza el envío de mensajes diarios con personalidad chilena/callejera,
transformando métricas frías en consejos accionables.

Funcionalidades:
- Fetch de datos desde API local (cashflow summary + reorder calculator)
- Generación de mensaje narrativo con narrative_engine.py
- Envío a Discord con retry logic
- Scheduler diario a las 8:00 AM
- Logging de éxito/fallo

Uso:
    python pulse_scheduler.py           # Inicia scheduler (loop infinito)
    python pulse_scheduler.py --now     # Envía pulso inmediato (testing)
"""

import schedule
import time
import logging
import sys
import argparse
from datetime import datetime
from typing import Optional, Dict, List

# Imports locales
from narrative_engine import generar_pulso_diario
from retry_utils import get_retry_session
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURACIÓN
# ============================================================

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/pulse_scheduler.log', mode='a')
    ]
)

# URLs de endpoints locales (Railway o localhost)
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5001')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL_CHAPARRITA') or os.getenv('DISCORD_WEBHOOK_URL')
SHOPIFY_API_KEY = os.getenv('SHOPIFY_API_KEY')  # Para auth

# Hora de envío diario (formato 24h)
PULSE_SEND_TIME = os.getenv('PULSE_SEND_TIME', '08:00')

# Validación inicial
if not DISCORD_WEBHOOK_URL:
    logger.warning("⚠️ DISCORD_WEBHOOK_URL no configurado - pulsos NO se enviarán a Discord")

# ============================================================
# HELPERS - FETCH DE DATOS
# ============================================================

def fetch_cashflow_summary(shop: str = 'la-chaparrita') -> Optional[Dict]:
    """
    Obtiene summary de cashflow desde endpoint local.

    Returns:
        Dict con total_products, inventory_value, stockouts_count, etc.
        None si falla
    """
    url = f"{API_BASE_URL}/api/cashflow/summary"
    params = {'shop': shop}
    headers = {}

    if SHOPIFY_API_KEY:
        headers['X-API-Key'] = SHOPIFY_API_KEY

    try:
        session = get_retry_session(retries=3, backoff_factor=1.0)
        response = session.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Cashflow summary obtenido: {data.get('total_products', 0)} productos")
            return data
        else:
            logger.error(f"❌ Error obteniendo cashflow summary: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ Excepción al obtener cashflow summary: {e}")
        return None


def fetch_reorder_calculator(shop: str = 'la-chaparrita', top_n: int = 5) -> Optional[List[Dict]]:
    """
    Obtiene lista de productos para reordenar desde endpoint local.

    Returns:
        Lista de dicts con sku, name, units_needed, urgency, priority
        None si falla
    """
    url = f"{API_BASE_URL}/api/reorder-calculator"
    params = {
        'shop': shop,
        'top_n': top_n,
        'min_priority': 'B'  # Solo B y A (urgentes)
    }
    headers = {}

    if SHOPIFY_API_KEY:
        headers['X-API-Key'] = SHOPIFY_API_KEY

    try:
        session = get_retry_session(retries=3, backoff_factor=1.0)
        response = session.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            reorder_list = data.get('reorder_list', [])
            logger.info(f"✅ Reorder calculator obtenido: {len(reorder_list)} productos")
            return reorder_list
        else:
            logger.error(f"❌ Error obteniendo reorder calculator: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        logger.error(f"❌ Excepción al obtener reorder calculator: {e}")
        return None


def send_to_discord(mensaje: str, webhook_url: str = None) -> bool:
    """
    Envía mensaje narrativo a Discord usando webhook.

    Args:
        mensaje: Texto completo del pulso narrativo
        webhook_url: URL del webhook (opcional, usa DISCORD_WEBHOOK_URL por defecto)

    Returns:
        True si envío exitoso, False si falla
    """
    url = webhook_url or DISCORD_WEBHOOK_URL

    if not url:
        logger.warning("⚠️ Discord webhook no configurado - mensaje NO enviado")
        return False

    payload = {
        "content": mensaje,
        "username": "Centinela - La Chaparrita",
        "avatar_url": "https://i.imgur.com/4M34hi2.png"  # Opcional: Ícono personalizado
    }

    try:
        session = get_retry_session(retries=3, backoff_factor=1.0)
        response = session.post(url, json=payload, timeout=10)

        if response.status_code == 204:
            logger.info("✅ Pulso enviado a Discord exitosamente!")
            return True
        else:
            logger.error(f"❌ Error enviando a Discord: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"❌ Excepción al enviar a Discord: {e}")
        return False


# ============================================================
# PULSO PRINCIPAL
# ============================================================

def enviar_pulso_diario():
    """
    Función principal del scheduler: obtiene datos, genera mensaje, envía a Discord.

    Flow:
        1. Fetch cashflow summary
        2. Fetch reorder calculator
        3. Generar mensaje narrativo
        4. Enviar a Discord con retry
        5. Log resultado
    """
    logger.info("=" * 60)
    logger.info("🤖 INICIANDO PULSO DIARIO DE LA CHAPARRITA")
    logger.info("=" * 60)

    start_time = time.time()

    # 1. Fetch datos
    logger.info("📡 Obteniendo datos de cashflow...")
    summary = fetch_cashflow_summary()

    if not summary:
        logger.error("❌ FALLO: No se pudo obtener cashflow summary - ABORTANDO pulso")
        return

    logger.info("📡 Obteniendo productos para reordenar...")
    reorder_list = fetch_reorder_calculator(top_n=3)

    if reorder_list is None:
        logger.warning("⚠️ No se pudo obtener reorder list - pulso enviará solo summary")
        reorder_list = []

    # 2. Generar mensaje narrativo
    logger.info("🗣️ Generando mensaje narrativo con personalidad...")
    try:
        mensaje_pulso = generar_pulso_diario(
            summary=summary,
            top_reorder=reorder_list
        )

        logger.info(f"✅ Mensaje narrativo generado ({len(mensaje_pulso)} caracteres)")

        # Log preview (primeras 200 caracteres)
        preview = mensaje_pulso[:200].replace('\n', ' ')
        logger.info(f"📄 Preview: {preview}...")

    except Exception as e:
        logger.error(f"❌ FALLO: Error generando mensaje narrativo: {e}")
        return

    # 3. Enviar a Discord
    logger.info("📤 Enviando pulso a Discord...")
    success = send_to_discord(mensaje_pulso)

    # 4. Log resultado final
    elapsed = time.time() - start_time

    if success:
        logger.info("=" * 60)
        logger.info(f"✅ PULSO ENVIADO EXITOSAMENTE en {elapsed:.2f}s")
        logger.info("=" * 60)
    else:
        logger.error("=" * 60)
        logger.error(f"❌ PULSO FALLÓ después de {elapsed:.2f}s")
        logger.error("=" * 60)


# ============================================================
# SCHEDULER
# ============================================================

def run_scheduler():
    """
    Inicia scheduler que ejecuta enviar_pulso_diario() todos los días a PULSE_SEND_TIME.
    Loop infinito - debe correr como proceso persistente.
    """
    logger.info("🕒 PULSE SCHEDULER INICIADO")
    logger.info(f"⏰ Pulso programado para: {PULSE_SEND_TIME} (hora local)")
    logger.info(f"🌐 API Base URL: {API_BASE_URL}")
    logger.info(f"💬 Discord webhook: {'✅ Configurado' if DISCORD_WEBHOOK_URL else '❌ NO configurado'}")
    logger.info("=" * 60)

    # Programar tarea diaria
    schedule.every().day.at(PULSE_SEND_TIME).do(enviar_pulso_diario)

    logger.info(f"✅ Próximo pulso: {schedule.next_run()}")

    # Loop infinito
    while True:
        schedule.run_pending()
        time.sleep(60)  # Chequea cada 60 segundos


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pulse Scheduler - El Corazón del Centinela")
    parser.add_argument(
        '--now',
        action='store_true',
        help='Envía pulso inmediatamente (testing) en vez de iniciar scheduler'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Genera mensaje pero NO lo envía a Discord (testing)'
    )

    args = parser.parse_args()

    if args.now:
        logger.info("🚀 Modo --now: Enviando pulso inmediatamente...")

        if args.dry_run:
            logger.info("🧪 Modo --dry-run: Mensaje NO será enviado a Discord")

            # Fetch y generar, pero no enviar
            summary = fetch_cashflow_summary()
            if summary:
                reorder_list = fetch_reorder_calculator(top_n=3) or []
                mensaje = generar_pulso_diario(summary, reorder_list)

                print("\n" + "=" * 60)
                print("📄 PREVIEW DEL MENSAJE:")
                print("=" * 60)
                print(mensaje)
                print("=" * 60)
                logger.info("✅ Dry-run completado")
            else:
                logger.error("❌ No se pudo obtener datos")
        else:
            enviar_pulso_diario()
    else:
        # Modo normal: scheduler
        run_scheduler()
