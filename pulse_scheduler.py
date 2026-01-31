#!/usr/bin/env python3
"""
🕐 PULSE SCHEDULER - Despertador del Tiburón Predictivo

Envia Sticker diario a las 8:00 AM con:
- Resumen Cash Flow
- ROI Top 3 productos (con contexto clima Columbus + feriados)
- Alertas de liquidez
- Recomendaciones predictivas

Modos:
- Normal: Cron diario a las 8:00 AM
- Manual: --now (enviar ahora)
- Testing: --dry-run (no enviar, solo imprimir)

Autor: Claude Code
Fecha: 2026-01-31
"""

import os
import sys
import time
import argparse
import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Configuración logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5001")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
PULSE_SCHEDULE_HOUR = int(os.getenv("PULSE_SCHEDULE_HOUR", "8"))  # 8:00 AM default


class PulseScheduler:
    """Scheduler para envío automático del Sticker Tiburón"""

    def __init__(
        self,
        api_base_url: str = API_BASE_URL,
        discord_webhook: str = DISCORD_WEBHOOK_URL,
        weather_api_key: str = OPENWEATHER_API_KEY
    ):
        self.api_base_url = api_base_url.rstrip('/')
        self.discord_webhook = discord_webhook
        self.weather_api_key = weather_api_key

    def fetch_cashflow_summary(self) -> Dict:
        """Obtiene resumen de cash flow desde API"""
        try:
            url = f"{self.api_base_url}/api/cashflow/summary"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error fetching summary: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Exception fetching summary: {e}")
            return {}

    def fetch_liquidity_shield(self) -> Dict:
        """Obtiene estado del Escudo de Liquidez"""
        try:
            url = f"{self.api_base_url}/api/cashflow/liquidity-shield"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error fetching shield: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Exception fetching shield: {e}")
            return {}

    def fetch_predator_suggestions(self) -> Dict:
        """
        Obtiene sugerencias comerciales depredadoras (Price Surge + Bundles).

        Returns:
            Dict con price_surges y bundles
        """
        try:
            url = f"{self.api_base_url}/api/predator-suggestions"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error fetching predator suggestions: {response.status_code}")
                return {'price_surges': [], 'bundles': [], 'has_opportunities': False}

        except Exception as e:
            logger.error(f"Exception fetching predator suggestions: {e}")
            return {'price_surges': [], 'bundles': [], 'has_opportunities': False}

    def fetch_top_roi_products(self, limit: int = 3) -> List[Dict]:
        """
        Obtiene top productos con mejor ROI usando external signals.

        Args:
            limit: Número de productos a retornar

        Returns:
            Lista de productos con ROI simulado
        """
        try:
            # 1. Obtener clasificación ABC
            url = f"{self.api_base_url}/api/cashflow/abc-classification"
            response = requests.get(url, timeout=10)

            if response.status_code != 200:
                logger.warning(f"Error fetching ABC: {response.status_code}")
                return []

            data = response.json()
            products = data.get('products', [])

            if not products:
                logger.info("No products available for ROI simulation")
                return []

            # 2. Simular ROI para productos categoría A y B (top performers)
            top_products = []

            for product in products:
                if product.get('category') in ['A', 'B']:
                    sku = product.get('sku')
                    velocity = product.get('velocity_daily', 0)
                    stock = product.get('stock', 0)

                    # Calcular unidades a reordenar (conservador: 7 días de stock)
                    units_to_order = max(int(velocity * 7), 10)

                    # Simular ROI con external signals
                    roi_data = self.simulate_roi_with_signals(sku, units_to_order)

                    if roi_data and 'error' not in roi_data:
                        roi_data['product'] = product
                        top_products.append(roi_data)

                    # Limitar requests para no sobrecargar
                    if len(top_products) >= limit:
                        break

            # Ordenar por ROI esperado (descendente)
            top_products.sort(key=lambda x: x.get('roi_expected', 0), reverse=True)

            return top_products[:limit]

        except Exception as e:
            logger.error(f"Exception fetching top ROI: {e}")
            return []

    def simulate_roi_with_signals(self, sku: str, units: int) -> Optional[Dict]:
        """
        Simula ROI para un producto usando external signals.

        Args:
            sku: SKU del producto
            units: Unidades a simular

        Returns:
            Datos de ROI con contexto predictivo
        """
        try:
            url = f"{self.api_base_url}/api/cashflow/roi-simulator"
            payload = {
                "sku": sku,
                "units": units,
                "use_external_signals": True
            }

            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error simulating ROI for {sku}: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Exception simulating ROI for {sku}: {e}")
            return None

    def fetch_external_signals(self, product_name: str = "Generic Product") -> Dict:
        """Obtiene señales externas (clima + feriados) para contexto"""
        try:
            url = f"{self.api_base_url}/api/debug/external-signals"
            params = {"product_name": product_name}

            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error fetching signals: {response.status_code}")
                return {}

        except Exception as e:
            logger.error(f"Exception fetching signals: {e}")
            return {}

    def generate_sticker(
        self,
        summary: Dict,
        shield: Dict,
        top_roi: List[Dict],
        signals: Dict,
        predator: Optional[Dict] = None
    ) -> Dict:
        """
        Genera Sticker Tiburón con contexto predictivo.

        Args:
            summary: Resumen cash flow
            shield: Estado del Escudo
            top_roi: Top productos ROI
            signals: Señales externas (clima + feriados)
            predator: Sugerencias comerciales depredadoras (price surge + bundles)

        Returns:
            Dict con mensaje Discord + embed
        """
        if predator is None:
            predator = {'price_surges': [], 'bundles': [], 'has_opportunities': False}

        # Header con timestamp
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M")

        # 🌡️ CONTEXTO EXTERNO
        weather_context = ""
        if signals.get('weather_data'):
            weather = signals['weather_data']
            temp = weather.get('temp_celsius', 0)
            condition = weather.get('condition', 'Unknown')
            weather_context = f"🌡️ **Columbus, Ohio:** {temp:.1f}°C, {condition}"

        # 🎉 FERIADOS PRÓXIMOS
        holidays_context = ""
        if signals.get('upcoming_holidays'):
            holidays = signals['upcoming_holidays']
            if holidays:
                next_holiday = holidays[0]
                days = next_holiday.get('days_until', 0)
                name = next_holiday.get('name', '')
                holidays_context = f"\n🎉 **Próximo feriado:** {name} (en {days} días)"

        # 💰 CASH FLOW SUMMARY
        total_value = summary.get('total_inventory_value', 0)
        stockout_cost = summary.get('stockout_opportunity_cost', 0)
        dead_value = summary.get('dead_stock_value', 0)

        # 🛡️ ESCUDO DE LIQUIDEZ
        shield_status = "✅ ACTIVO" if shield.get('shield_active', False) else "🔴 INACTIVO"
        ccc_days = shield.get('cash_conversion_cycle_days', 0)
        freeze_active = shield.get('freeze_active', False)

        freeze_emoji = "🧊 FREEZE ACTIVO" if freeze_active else "🔥 OPERATIVO"

        # 📊 TOP ROI PRODUCTS (con contexto predictivo)
        roi_section = ""
        if top_roi:
            roi_section = "\n\n📊 **TOP OPORTUNIDADES (ROI Predictivo):**\n"
            for i, item in enumerate(top_roi, 1):
                name = item.get('name', 'Unknown')
                roi = item.get('roi_expected', 0)
                units = item.get('units', 0)
                external_reason = item.get('external_reason', '')

                roi_line = f"{i}. **{name}**: ROI {roi:.1f}% ({units} unidades)"

                # Agregar contexto predictivo si existe
                if external_reason:
                    roi_line += f"\n   🌡️ *{external_reason}*"

                roi_section += f"{roi_line}\n"
        else:
            roi_section = "\n\n📊 **TOP OPORTUNIDADES:** Sin datos disponibles"

        # 🚨 ALERTAS
        alerts = []
        if freeze_active:
            alerts.append("🧊 Sistema en FREEZE - acciones bloqueadas")
        if stockout_cost > 1000:
            alerts.append(f"⚠️ Stockouts costando ${stockout_cost:,.0f}/mes")
        if dead_value > 5000:
            alerts.append(f"💀 ${dead_value:,.0f} en inventario muerto")

        alerts_section = ""
        if alerts:
            alerts_section = "\n\n🚨 **ALERTAS:**\n" + "\n".join(f"- {alert}" for alert in alerts)

        # 💹 SUGERENCIAS COMERCIALES DEPREDADORAS
        predator_section = ""
        if predator.get('has_opportunities'):
            predator_section = "\n\n💹 **INSTINTO DEPREDADOR:**\n"

            # Price Surges
            price_surges = predator.get('price_surges', [])
            if price_surges:
                surge = price_surges[0]  # Top surge
                sku = surge.get('sku', '')
                surge_pct = surge.get('surge_percentage', 0)
                projected_increase = surge.get('projected_net_increase', 0)
                projected_increase_pct = surge.get('projected_net_increase_pct', 0)

                predator_section += f"- 💹 **Price Surge:** +{surge_pct:.0f}% en {sku} (48h)\n"
                predator_section += f"  📈 Proyección: +${projected_increase:.0f} neto (+{projected_increase_pct:.0f}%)\n"

            # Bundles
            bundles = predator.get('bundles', [])
            if bundles:
                bundle = bundles[0]  # Top bundle
                star_name = bundle.get('star_name', '')
                dead_value = bundle.get('dead_stock_value', 0)
                margin = bundle.get('projected_margin', 0)

                predator_section += f"- 📦 **Bundle Parásito:** {star_name} absorbe dead stock\n"
                predator_section += f"  💰 Libera ${dead_value:.0f} + margen ${margin:.0f}\n"

        # MENSAJE COMPLETO
        message = f"""🦈 **TIBURÓN PREDICTIVO - PULSO DIARIO**
⏰ {timestamp}

{weather_context}{holidays_context}

💰 **Cash Flow:**
- Inventario: ${total_value:,.0f}
- Stockout Cost: ${stockout_cost:,.0f}/mes
- Dead Stock: ${dead_value:,.0f}

🛡️ **Escudo de Liquidez:** {shield_status}
- CCC: {ccc_days:.1f} días
- Estado: {freeze_emoji}
{roi_section}{predator_section}{alerts_section}

**Veredicto:** {'🔥 Dale gas con las oportunidades!' if top_roi and not freeze_active else '🛡️ Modo cautela - monitorear liquidez'}
"""

        # Botones interactivos
        components = []
        buttons = []

        if not freeze_active:
            # Botón reorder si hay ROI top
            if top_roi:
                top_product = top_roi[0]
                sku = top_product.get('sku')
                units = top_product.get('units')

                buttons.append({
                    "type": 2,
                    "style": 3,  # Green
                    "label": f"🔥 Reordenar {units}x",
                    "custom_id": f"approve_reorder_{sku}_{units}"
                })

            # Botón Price Surge si existe oportunidad
            if predator.get('price_surges'):
                surge = predator['price_surges'][0]
                sku = surge.get('sku', '')
                surge_pct = surge.get('surge_percentage', 0)

                buttons.append({
                    "type": 2,
                    "style": 1,  # Blue
                    "label": f"💹 Surge +{surge_pct:.0f}%",
                    "custom_id": f"price_surge_{sku}"
                })

            # Botón Bundle si existe oportunidad
            if predator.get('bundles'):
                bundle = predator['bundles'][0]
                star_sku = bundle.get('star_sku', '')
                dead_sku = bundle.get('dead_sku', '')

                buttons.append({
                    "type": 2,
                    "style": 3,  # Green
                    "label": f"📦 Bundle",
                    "custom_id": f"bundle_{star_sku}_{dead_sku}"
                })

            # Botón Ver Detalles
            if buttons:
                buttons.append({
                    "type": 2,
                    "style": 2,  # Gray
                    "label": "📊 Detalles",
                    "custom_id": "details_pulse"
                })

        if buttons:
            components = [
                {
                    "type": 1,
                    "components": buttons[:5]  # Max 5 botones
                }
            ]

        return {
            "content": message,
            "components": components
        }

    def send_to_discord(self, sticker: Dict, dry_run: bool = False) -> bool:
        """
        Envía Sticker a Discord.

        Args:
            sticker: Dict con mensaje y componentes
            dry_run: Si True, solo imprime sin enviar

        Returns:
            True si se envió exitosamente
        """
        if dry_run:
            logger.info("🧪 DRY RUN - No se envió a Discord")
            logger.info(f"Mensaje:\n{sticker.get('content', '')}")
            return True

        if not self.discord_webhook:
            logger.error("DISCORD_WEBHOOK_URL no configurado")
            return False

        try:
            response = requests.post(
                self.discord_webhook,
                json=sticker,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code in [200, 204]:
                logger.info("✅ Sticker enviado a Discord exitosamente")
                return True
            else:
                logger.error(f"Error enviando a Discord: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Exception enviando a Discord: {e}")
            return False

    def run_pulse(self, dry_run: bool = False) -> bool:
        """
        Ejecuta el pulso completo.

        Args:
            dry_run: Si True, no envía a Discord

        Returns:
            True si se ejecutó exitosamente
        """
        logger.info("🦈 Iniciando Pulso Tiburón Predictivo...")

        # 1. Fetch data
        logger.info("Obteniendo datos...")
        summary = self.fetch_cashflow_summary()
        shield = self.fetch_liquidity_shield()
        top_roi = self.fetch_top_roi_products(limit=3)
        signals = self.fetch_external_signals(
            product_name=top_roi[0].get('name', 'Generic Product') if top_roi else 'Generic Product'
        )
        predator = self.fetch_predator_suggestions()

        # 2. Generate Sticker
        logger.info("Generando Sticker...")
        sticker = self.generate_sticker(summary, shield, top_roi, signals, predator)

        # 3. Send
        logger.info("Enviando a Discord...")
        success = self.send_to_discord(sticker, dry_run=dry_run)

        if success:
            logger.info("✅ Pulso completado exitosamente")
        else:
            logger.error("❌ Pulso falló")

        return success

    def schedule_loop(self):
        """Loop principal - envía pulso diario a hora configurada"""
        logger.info(f"🕐 Scheduler iniciado - Pulso diario a las {PULSE_SCHEDULE_HOUR}:00")

        while True:
            now = datetime.now()

            # Verificar si es la hora del pulso
            if now.hour == PULSE_SCHEDULE_HOUR and now.minute < 5:
                logger.info(f"⏰ Hora del pulso: {now.strftime('%H:%M')}")
                self.run_pulse(dry_run=False)

                # Esperar hasta la próxima hora para evitar duplicados
                time.sleep(60 * 60)  # 1 hora
            else:
                # Calcular tiempo hasta próximo pulso
                next_pulse = now.replace(hour=PULSE_SCHEDULE_HOUR, minute=0, second=0, microsecond=0)
                if now.hour >= PULSE_SCHEDULE_HOUR:
                    # Pulso es mañana
                    next_pulse += timedelta(days=1)

                wait_seconds = (next_pulse - now).total_seconds()
                logger.info(f"⏳ Próximo pulso en {wait_seconds/3600:.1f} horas ({next_pulse.strftime('%Y-%m-%d %H:%M')})")

                # Esperar, pero revisar cada 10 minutos por si acaso
                time.sleep(min(wait_seconds, 600))


def main():
    parser = argparse.ArgumentParser(description='Pulse Scheduler - Tiburón Predictivo')
    parser.add_argument('--now', action='store_true', help='Enviar pulso ahora (ignorar schedule)')
    parser.add_argument('--dry-run', action='store_true', help='Testing mode - no enviar a Discord')

    args = parser.parse_args()

    scheduler = PulseScheduler()

    if args.now:
        # Modo manual - enviar ahora
        logger.info("🚀 Modo manual - enviando pulso inmediatamente...")
        success = scheduler.run_pulse(dry_run=args.dry_run)
        sys.exit(0 if success else 1)
    else:
        # Modo scheduler - loop infinito
        logger.info("🕐 Modo scheduler - iniciando loop...")
        scheduler.schedule_loop()


if __name__ == "__main__":
    main()
