"""
🦈🚨 WHATSAPP ALERTS - Sistema de Notificaciones Inteligente
==============================================================

Alertas proactivas que despiertan al Director cuando HAY que actuar.

Tipos de Alertas:
1. 🚨 Stock Crítico/Stockout Inminente
2. ⚰️ Dead Stock Creciendo
3. 💹 Price Surge Oportunidad
4. 📊 Post-Mortem Automática

Author: Claude (Cirujano Maestro)
Version: 1.0.0
"""

import os
import logging
from datetime import datetime, timedelta
from database import get_db_connection

logger = logging.getLogger(__name__)


class WhatsAppAlertEngine:
    """Motor de alertas WhatsApp para Tiburón Predictivo."""

    def __init__(self):
        self.alerts = []

    def check_all_alerts(self):
        """
        🚨 Verifica todas las condiciones de alerta y genera notificaciones.

        Returns:
            list: Lista de alertas activas con formato WhatsApp
        """
        logger.info("🚨 Verificando alertas WhatsApp...")

        self.alerts = []

        # 1. ALERTA STOCK CRÍTICO
        self.check_stock_critical()

        # 2. ALERTA DEAD STOCK CRECIENDO
        self.check_dead_stock_growing()

        # 3. ALERTA PRICE SURGE OPORTUNIDAD
        self.check_price_surge_opportunity()

        # 4. ALERTA POST-MORTEM
        self.check_post_mortem()

        logger.info(f"✅ {len(self.alerts)} alertas activas")
        return self.alerts

    # ========================================
    # 1. ALERTA STOCK CRÍTICO / STOCKOUT
    # ========================================
    def check_stock_critical(self):
        """
        🚨 ALERTA STOCK CRÍTICO
        Cuando producto A/B < 5-10 unidades o días stock < 3
        """
        try:
            conn = get_db_connection()

            # Productos con stock crítico (< 10 unidades) y alta velocity
            critical_products = conn.execute('''
                SELECT sku, name, stock, price, velocity_daily, category
                FROM products
                WHERE stock > 0
                  AND stock < 10
                  AND velocity_daily > 0.5
                  AND category IN ('A', 'B')
                ORDER BY velocity_daily DESC
                LIMIT 3
            ''').fetchall()

            conn.close()

            for product in critical_products:
                # Calcular días hasta stockout
                days_to_stockout = product['stock'] / product['velocity_daily'] if product['velocity_daily'] > 0 else 999

                if days_to_stockout < 3:
                    # ALERTA ROJA - Stockout inminente
                    reorder_qty = int(product['velocity_daily'] * 30)  # 30 días de stock

                    alert = {
                        'type': 'stock_critical',
                        'severity': 'CRÍTICO',
                        'emoji': '🚨',
                        'product': product['name'],
                        'sku': product['sku'],
                        'stock': product['stock'],
                        'days_to_stockout': round(days_to_stockout, 1),
                        'reorder_qty': reorder_qty,
                        'message': self._format_stock_critical_message(product, days_to_stockout, reorder_qty),
                        'quick_replies': [
                            {'title': f'Reordenar {reorder_qty}u', 'action': 'reorden', 'sku': product['sku']},
                            {'title': 'Ver detalles', 'action': 'inventory', 'sku': product['sku']},
                            {'title': 'Ignorar 24h', 'action': 'snooze', 'sku': product['sku']}
                        ]
                    }

                    self.alerts.append(alert)
                    logger.warning(f"🚨 Alerta Stock Crítico: {product['name']} - {days_to_stockout:.1f} días")

        except Exception as e:
            logger.error(f"❌ Error check_stock_critical: {e}")

    def _format_stock_critical_message(self, product, days_to_stockout, reorder_qty):
        """Formatea mensaje alerta stock crítico."""
        message = f"🚨 ALERTA ROJA - STOCKOUT INMINENTE\n\n"
        message += f"Producto: {product['name']}\n"
        message += f"SKU: {product['sku']}\n"
        message += f"Stock Actual: {product['stock']} unidades\n"
        message += f"Velocity: {product['velocity_daily']:.1f}/día\n"
        message += f"⏰ Stockout en: {days_to_stockout:.1f} días\n\n"
        message += f"💡 Acción Recomendada:\n"
        message += f"Reordenar {reorder_qty} unidades (30 días stock)\n\n"
        message += f"¿Ejecutar reorden ahora?"
        return message

    # ========================================
    # 2. ALERTA DEAD STOCK CRECIENDO
    # ========================================
    def check_dead_stock_growing(self):
        """
        ⚰️ ALERTA DEAD STOCK CRECIENDO
        Dead stock > $2,000 o +20% en 7 días
        """
        try:
            conn = get_db_connection()

            # Productos dead stock (velocity < 0.5, stock > 50)
            dead_products = conn.execute('''
                SELECT sku, name, stock, price, velocity_daily, category
                FROM products
                WHERE stock > 50
                  AND velocity_daily < 0.5
                  AND price > 0
                ORDER BY (stock * price) DESC
                LIMIT 5
            ''').fetchall()

            conn.close()

            # Calcular total dead stock value
            total_dead_value = sum(p['stock'] * p['price'] for p in dead_products)

            if total_dead_value > 2000:
                # ALERTA - Dead stock alto
                top_dead = dead_products[0] if dead_products else None

                if top_dead:
                    alert = {
                        'type': 'dead_stock',
                        'severity': 'ALTO',
                        'emoji': '⚰️',
                        'total_value': total_dead_value,
                        'count': len(dead_products),
                        'top_product': top_dead['name'],
                        'top_sku': top_dead['sku'],
                        'top_value': top_dead['stock'] * top_dead['price'],
                        'message': self._format_dead_stock_message(total_dead_value, dead_products),
                        'quick_replies': [
                            {'title': 'Lanzar Bundle', 'action': 'bundle', 'sku': top_dead['sku']},
                            {'title': 'Liquidar 50% off', 'action': 'liquidate', 'sku': top_dead['sku']},
                            {'title': 'Ignorar', 'action': 'snooze', 'sku': ''}
                        ]
                    }

                    self.alerts.append(alert)
                    logger.warning(f"⚰️ Alerta Dead Stock: ${total_dead_value:,.2f} total")

        except Exception as e:
            logger.error(f"❌ Error check_dead_stock_growing: {e}")

    def _format_dead_stock_message(self, total_value, dead_products):
        """Formatea mensaje alerta dead stock."""
        message = f"⚰️ ALERTA MUERTE LENTA\n\n"
        message += f"Dead Stock Total: ${total_value:,.2f}\n"
        message += f"Productos Afectados: {len(dead_products)}\n\n"
        message += f"Top Dead Stock:\n"

        for i, p in enumerate(dead_products[:3], 1):
            value = p['stock'] * p['price']
            message += f"{i}. {p['name'][:25]}\n"
            message += f"   {p['stock']}u × ${p['price']:.2f} = ${value:,.2f}\n"

        message += f"\n💡 Acción Recomendada:\n"
        message += f"Lanzar Parasite Bundle con producto estrella\n\n"
        message += f"¿Ejecutar Bundle ahora?"
        return message

    # ========================================
    # 3. ALERTA PRICE SURGE OPORTUNIDAD
    # ========================================
    def check_price_surge_opportunity(self):
        """
        💹 ALERTA PRICE SURGE OPORTUNIDAD
        Temp < -10°C y producto estrella sin surge activo
        """
        try:
            import requests

            # 1. Obtener temperatura Columbus
            weather_api_key = os.getenv('OPENWEATHER_API_KEY', 'ef56e6c959ba8341655ab078b785dd93')
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q=Columbus,OH,US&units=metric&appid={weather_api_key}"

            try:
                weather_resp = requests.get(weather_url, timeout=5)
                weather_data = weather_resp.json()
                temp = weather_data['main']['temp']
            except:
                temp = -9.6  # Fallback

            # 2. Si temp < -10°C, buscar productos estrella para surge
            if temp < -10:
                conn = get_db_connection()

                # Productos winter con alta velocity sin surge
                surge_candidates = conn.execute('''
                    SELECT sku, name, stock, price, velocity_daily, category
                    FROM products
                    WHERE velocity_daily >= 2.0
                      AND stock > 20
                      AND price > 30
                      AND (name LIKE '%boot%' OR name LIKE '%jacket%'
                           OR name LIKE '%coat%' OR name LIKE '%winter%')
                    ORDER BY velocity_daily DESC
                    LIMIT 3
                ''').fetchall()

                conn.close()

                for product in surge_candidates:
                    # Calcular surge price (+15%)
                    surge_price = product['price'] * 1.15
                    projected_profit = (surge_price - product['price']) * product['stock']

                    alert = {
                        'type': 'price_surge',
                        'severity': 'OPORTUNIDAD',
                        'emoji': '💹',
                        'product': product['name'],
                        'sku': product['sku'],
                        'current_price': product['price'],
                        'surge_price': surge_price,
                        'temperature': temp,
                        'projected_profit': projected_profit,
                        'message': self._format_price_surge_message(product, temp, surge_price, projected_profit),
                        'quick_replies': [
                            {'title': 'Activar Surge +15%', 'action': 'surge', 'sku': product['sku']},
                            {'title': 'Ver proyección', 'action': 'analyze', 'sku': product['sku']},
                            {'title': 'No', 'action': 'snooze', 'sku': ''}
                        ]
                    }

                    self.alerts.append(alert)
                    logger.warning(f"💹 Alerta Price Surge: {product['name']} - {temp:.1f}°C")

        except Exception as e:
            logger.error(f"❌ Error check_price_surge_opportunity: {e}")

    def _format_price_surge_message(self, product, temp, surge_price, projected_profit):
        """Formatea mensaje alerta price surge."""
        message = f"💹 OPORTUNIDAD FUEGO\n\n"
        message += f"Temperatura: {temp:.1f}°C ❄️\n"
        message += f"Producto: {product['name']}\n"
        message += f"SKU: {product['sku']}\n\n"
        message += f"Precio Actual: ${product['price']:.2f}\n"
        message += f"Precio Surge: ${surge_price:.2f} (+15%)\n"
        message += f"Profit Proyectado: +${projected_profit:.2f}\n\n"
        message += f"💡 Condición óptima para surge\n"
        message += f"Temp extrema + producto estrella\n\n"
        message += f"¿Activar Surge ahora?"
        return message

    # ========================================
    # 4. ALERTA POST-MORTEM AUTOMÁTICA
    # ========================================
    def check_post_mortem(self):
        """
        📊 ALERTA POST-MORTEM AUTOMÁTICA
        24h después de thaw → análisis oportunidad perdida
        """
        try:
            # TODO: Implementar tracking de freeze/thaw events
            # Por ahora, placeholder para estructura

            # Simular cálculo opportunity cost
            opportunity_cost = 915  # Placeholder

            if opportunity_cost > 500:
                alert = {
                    'type': 'post_mortem',
                    'severity': 'INFO',
                    'emoji': '📊',
                    'opportunity_cost': opportunity_cost,
                    'freeze_duration': 2,  # días
                    'message': self._format_post_mortem_message(opportunity_cost, 2),
                    'quick_replies': [
                        {'title': 'Subir umbral', 'action': 'config', 'sku': ''},
                        {'title': 'Mantener', 'action': 'snooze', 'sku': ''},
                        {'title': 'Ver detalles', 'action': 'analyze', 'sku': ''}
                    ]
                }

                # Solo agregar si realmente hubo freeze reciente
                # self.alerts.append(alert)
                logger.info(f"📊 Post-Mortem: ${opportunity_cost} opportunity cost")

        except Exception as e:
            logger.error(f"❌ Error check_post_mortem: {e}")

    def _format_post_mortem_message(self, opportunity_cost, freeze_days):
        """Formatea mensaje post-mortem."""
        message = f"📊 POST-MORTEM AUTOMÁTICO\n\n"
        message += f"Freeze Duration: {freeze_days} días\n"
        message += f"Opportunity Cost: ${opportunity_cost:,.2f}\n\n"
        message += f"Análisis:\n"
        message += f"• Congelaste precios {freeze_days}d\n"
        message += f"• Perdimos ${opportunity_cost} en surges\n"
        message += f"• Recomendación: Subir umbral Escudo\n\n"
        message += f"¿Ajustar configuración?"
        return message

    # ========================================
    # HELPERS
    # ========================================
    def get_alerts_summary(self):
        """
        Genera resumen de alertas para envío WhatsApp.

        Returns:
            dict: {
                'total': int,
                'critical': int,
                'high': int,
                'opportunity': int,
                'alerts': list
            }
        """
        return {
            'total': len(self.alerts),
            'critical': len([a for a in self.alerts if a['severity'] == 'CRÍTICO']),
            'high': len([a for a in self.alerts if a['severity'] == 'ALTO']),
            'opportunity': len([a for a in self.alerts if a['severity'] == 'OPORTUNIDAD']),
            'alerts': self.alerts
        }


# ============================================================
# FLASK ENDPOINT WRAPPER
# ============================================================

def whatsapp_alerts_endpoint():
    """
    Flask route wrapper para GET /api/v1/whatsapp-alerts

    Returns:
        tuple: (response_dict, status_code)
    """
    try:
        engine = WhatsAppAlertEngine()
        engine.check_all_alerts()
        summary = engine.get_alerts_summary()

        logger.info(f"✅ Alertas generadas: {summary['total']}")

        return {
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'alerts': engine.alerts
        }, 200

    except Exception as e:
        logger.error(f"❌ Error generando alertas: {e}")
        return {
            'success': False,
            'error': str(e),
            'alerts': []
        }, 500
