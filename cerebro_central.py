"""
🦈🧠 CEREBRO CENTRAL - Webhooks Shopify → Alertas Instantáneas
================================================================

Procesa ventas en tiempo real y dispara alertas WhatsApp cuando:
- Venta de producto alto ROI
- Stock bajo después de venta
- Milestone alcanzado ($1000 en 1 día)
- Velocity spike detectado

Author: Claude (Cirujano Maestro)
Version: 1.0.0
"""

import os
import hmac
import hashlib
import base64
import logging
import requests
from datetime import datetime, timedelta
from flask import jsonify
from database import get_db_connection

logger = logging.getLogger(__name__)


class CerebroCentral:
    """Motor de procesamiento de webhooks Shopify con alertas instantáneas."""

    def __init__(self):
        self.shopify_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')

    def verify_shopify_hmac(self, data, hmac_header):
        """
        Verifica HMAC de Shopify para autenticidad del webhook.

        Args:
            data (bytes): Raw request body
            hmac_header (str): X-Shopify-Hmac-SHA256 header (base64)

        Returns:
            bool: True si HMAC válido
        """
        if not self.shopify_secret:
            logger.warning("⚠️ SHOPIFY_WEBHOOK_SECRET no configurado - saltando verificación")
            return True  # En desarrollo, permitir sin secret

        # Shopify envía HMAC en base64
        computed_hmac = base64.b64encode(
            hmac.new(
                self.shopify_secret.encode('utf-8'),
                data,
                hashlib.sha256
            ).digest()
        ).decode()

        # Logging detallado para debug
        logger.info(f"🔐 HMAC Debug:")
        logger.info(f"  Secret configurado: {'***' + self.shopify_secret[-4:] if len(self.shopify_secret) > 4 else 'NONE'}")
        logger.info(f"  Payload size: {len(data)} bytes")
        logger.info(f"  HMAC recibido: {hmac_header[:20]}...")
        logger.info(f"  HMAC calculado: {computed_hmac[:20]}...")
        logger.info(f"  Match: {hmac.compare_digest(computed_hmac, hmac_header)}")

        return hmac.compare_digest(computed_hmac, hmac_header)

    def process_order_webhook(self, order_data):
        """
        🧠 CEREBRO - Procesa webhook orders/create o orders/paid.

        Args:
            order_data (dict): Payload del webhook Shopify

        Returns:
            dict: {
                'success': bool,
                'alerts': list,
                'metrics_updated': dict,
                'message': str  # Para Make.com + Twilio
            }
        """
        try:
            logger.info("🧠 Cerebro Central: Procesando orden...")

            # 1. EXTRAER DATOS ORDEN
            order_id = order_data.get('id')
            order_number = order_data.get('order_number', order_id)
            customer_name = self._extract_customer_name(order_data)
            total_price = float(order_data.get('total_price', 0))
            line_items = order_data.get('line_items', [])
            created_at = order_data.get('created_at')

            logger.info(f"📦 Orden #{order_number} - {customer_name} - ${total_price:.2f}")

            # 2. ACTUALIZAR MÉTRICAS POR PRODUCTO
            metrics_updates = []
            alerts = []

            conn = get_db_connection()

            for item in line_items:
                product_update = self._process_line_item(item, conn)
                metrics_updates.append(product_update)

                # Detectar alertas post-venta
                item_alerts = self._detect_post_sale_alerts(product_update, conn)
                alerts.extend(item_alerts)

            # 3. ACTUALIZAR MÉTRICAS GLOBALES
            self._update_global_metrics(total_price, conn)

            # 4. DETECTAR MILESTONES
            milestone_alert = self._check_milestones(total_price, conn)
            if milestone_alert:
                alerts.append(milestone_alert)

            conn.commit()
            conn.close()

            # 5. GENERAR MENSAJE UNIFICADO
            message = self._generate_unified_message(
                order_number, customer_name, total_price,
                line_items, metrics_updates, alerts
            )

            logger.info(f"✅ Orden procesada: {len(alerts)} alertas generadas")

            return {
                'success': True,
                'order_id': order_id,
                'order_number': order_number,
                'total_price': total_price,
                'alerts': alerts,
                'metrics_updated': metrics_updates,
                'message': message
            }

        except Exception as e:
            logger.error(f"❌ Error procesando orden: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': f"❌ Error procesando orden:\n{str(e)}"
            }

    def _extract_customer_name(self, order_data):
        """Extrae nombre cliente del payload."""
        customer = order_data.get('customer', {})
        if customer:
            first = customer.get('first_name', '')
            last = customer.get('last_name', '')
            return f"{first} {last}".strip() or "Cliente"
        return "Cliente"

    def _extract_size_from_item(self, item):
        """
        Extrae talla del line_item de Shopify.

        Args:
            item (dict): Line item de Shopify

        Returns:
            str: Talla extraída o 'Sin talla'
        """
        # OPCIÓN 1: variant_title (más común - Shopify usa esto para variantes)
        variant_title = item.get('variant_title', '')
        if variant_title and variant_title != 'Default Title':
            return variant_title

        # OPCIÓN 2: properties custom (si el comerciante usa campos custom)
        properties = item.get('properties', [])
        if isinstance(properties, list):
            for prop in properties:
                if isinstance(prop, dict):
                    name = prop.get('name', '').lower()
                    if 'talla' in name or 'size' in name:
                        return prop.get('value', '')

        # OPCIÓN 3: title completo (a veces incluye talla al final)
        title = item.get('title', '')
        if ' - ' in title:
            parts = title.split(' - ')
            # Si la última parte parece una talla (número o "Talla X")
            last_part = parts[-1].strip()
            if last_part.replace('.', '').replace(',', '').isdigit() or 'talla' in last_part.lower():
                return last_part

        # OPCIÓN 4: variant_sku puede contener talla
        sku = item.get('sku', '')
        if sku and '-' in sku:
            # Muchos SKUs tienen formato: PRODUCTO-TALLA
            # Ej: BTA-CG-PTN-NAT-065 donde 065 podría ser la talla
            parts = sku.split('-')
            last_part = parts[-1]
            if last_part.replace('.', '').isdigit():
                return f"Talla {last_part}"

        return 'Sin talla'

    def _process_line_item(self, item, conn):
        """
        Procesa un line_item y actualiza métricas del producto.

        Returns:
            dict: {
                'sku': str,
                'product_name': str,
                'quantity': int,
                'price': float,
                'new_stock': int,
                'new_velocity': float,
                'roi': float
            }
        """
        sku = item.get('sku', item.get('variant_id', 'UNKNOWN'))
        product_name = item.get('title', 'Producto')
        quantity = item.get('quantity', 1)
        price = float(item.get('price', 0))

        # Buscar producto en DB
        product = conn.execute('''
            SELECT * FROM products WHERE sku = ?
        ''', (sku,)).fetchone()

        if not product:
            logger.warning(f"⚠️ Producto {sku} no existe - creando nuevo")
            # Crear producto nuevo con product_id
            conn.execute('''
                INSERT INTO products (product_id, sku, name, stock, price, velocity_daily, total_sales_30d)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (sku, sku, product_name, 0, price, 0, 0))
            product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()

        # Calcular nuevas métricas
        old_stock = product['stock']
        new_stock = max(0, old_stock - quantity)

        old_sales_30d = product['total_sales_30d'] or 0
        new_sales_30d = old_sales_30d + quantity

        # Velocity = ventas últimos 30 días / 30
        new_velocity = new_sales_30d / 30.0

        # ROI simplificado (si tenemos cost_price)
        cost_price = product['cost_price'] if product['cost_price'] else price * 0.5  # Fallback 50% margen
        roi = ((price - cost_price) / cost_price * 100) if cost_price > 0 else 0

        # Actualizar DB
        conn.execute('''
            UPDATE products
            SET stock = ?,
                total_sales_30d = ?,
                velocity_daily = ?,
                last_sale_date = ?
            WHERE sku = ?
        ''', (new_stock, new_sales_30d, new_velocity, datetime.now().isoformat(), sku))

        logger.info(f"  📊 {sku}: stock {old_stock}→{new_stock}, velocity {new_velocity:.1f}/día")

        return {
            'sku': sku,
            'product_name': product_name,
            'quantity': quantity,
            'price': price,
            'old_stock': old_stock,
            'new_stock': new_stock,
            'new_velocity': new_velocity,
            'roi': roi
        }

    def _detect_post_sale_alerts(self, product_update, conn):
        """
        Detecta alertas después de venta.

        Returns:
            list: Alertas generadas
        """
        alerts = []
        sku = product_update['sku']
        new_stock = product_update['new_stock']
        velocity = product_update['new_velocity']
        roi = product_update['roi']

        # ALERTA 1: Stock bajo después de venta
        if new_stock > 0 and new_stock < 10 and velocity > 0.5:
            days_to_stockout = new_stock / velocity if velocity > 0 else 999

            if days_to_stockout < 3:
                alerts.append({
                    'type': 'stock_critical_post_sale',
                    'severity': 'CRÍTICO',
                    'emoji': '🚨',
                    'sku': sku,
                    'product': product_update['product_name'],
                    'stock': new_stock,
                    'days_to_stockout': round(days_to_stockout, 1),
                    'message': f"🚨 ALERTA POST-VENTA\n\n{product_update['product_name']}\nStock: {new_stock}u → Stockout en {days_to_stockout:.1f} días"
                })

        # ALERTA 2: Venta de producto alto ROI
        if roi > 100:
            alerts.append({
                'type': 'high_roi_sale',
                'severity': 'INFO',
                'emoji': '💰',
                'sku': sku,
                'product': product_update['product_name'],
                'roi': roi,
                'quantity': product_update['quantity'],
                'message': f"💰 VENTA ALTO ROI\n\n{product_update['product_name']}\nCantidad: {product_update['quantity']}u\nROI: {roi:.0f}%"
            })

        # ALERTA 3: Velocity spike (nuevo velocity > 2x promedio histórico)
        # TODO: Implementar comparación con velocity histórico

        return alerts

    def _update_global_metrics(self, total_price, conn):
        """Actualiza métricas globales del negocio."""
        try:
            # Actualizar ventas del día
            today = datetime.now().date().isoformat()

            conn.execute('''
                INSERT INTO daily_sales (date, total_sales)
                VALUES (?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    total_sales = total_sales + excluded.total_sales
            ''', (today, total_price))

        except Exception as e:
            logger.warning(f"⚠️ Error actualizando métricas globales: {e}")
            # No crítico, continuar

    def _check_milestones(self, total_price, conn):
        """
        Detecta si se alcanzó milestone de ventas.

        Returns:
            dict or None: Alerta de milestone
        """
        try:
            today = datetime.now().date().isoformat()

            # Obtener ventas del día
            result = conn.execute('''
                SELECT total_sales FROM daily_sales WHERE date = ?
            ''', (today,)).fetchone()

            if result:
                daily_total = result['total_sales']

                # Milestone $1000 en 1 día
                if daily_total >= 1000:
                    return {
                        'type': 'milestone_1k_day',
                        'severity': 'CELEBRACIÓN',
                        'emoji': '🎉',
                        'amount': daily_total,
                        'message': f"🎉 MILESTONE ALCANZADO\n\nVentas hoy: ${daily_total:,.2f}\n¡Superamos $1,000 en 1 día!"
                    }

        except Exception as e:
            logger.warning(f"⚠️ Error verificando milestones: {e}")

        return None

    def _generate_unified_message(self, order_number, customer_name, total_price,
                                   line_items, metrics_updates, alerts):
        """
        Genera mensaje unificado para Make.com + Twilio WhatsApp.

        Returns:
            str: Mensaje formateado con emojis
        """
        # HEADER
        message = f"🛒 NUEVA VENTA - Orden #{order_number}\n\n"

        # CLIENTE
        message += f"👤 Cliente: {customer_name}\n"
        message += f"💰 Total: ${total_price:.2f}\n\n"

        # PRODUCTOS CON TALLA
        message += f"📦 Productos ({len(line_items)}):\n"

        # Combinar line_items con metrics_updates para tener talla + stock
        for i, (item, update) in enumerate(zip(line_items[:3], metrics_updates[:3])):
            # Extraer talla de múltiples fuentes posibles
            talla = self._extract_size_from_item(item)

            # Nombre producto + talla
            product_display = update['product_name'][:25]
            if talla and talla != 'Sin talla':
                product_display += f" - {talla}"

            message += f"• {product_display}\n"
            message += f"  {update['quantity']}u × ${update['price']:.2f}\n"
            message += f"  Stock: {update['old_stock']}→{update['new_stock']}\n"

        if len(line_items) > 3:
            message += f"  ... y {len(line_items) - 3} más\n"

        # ALERTAS
        if alerts:
            message += f"\n🚨 ALERTAS ({len(alerts)}):\n"
            for alert in alerts[:2]:  # Max 2 alertas
                message += f"{alert['emoji']} {alert['type'].upper()}\n"
                if alert['type'] == 'stock_critical_post_sale':
                    message += f"  {alert['product']}: {alert['stock']}u (Stockout {alert['days_to_stockout']:.1f}d)\n"
                elif alert['type'] == 'high_roi_sale':
                    message += f"  {alert['product']}: ROI {alert['roi']:.0f}%\n"
                elif alert['type'] == 'milestone_1k_day':
                    message += f"  Ventas hoy: ${alert['amount']:,.2f}\n"

        # FOOTER
        message += f"\n🦈 Tiburón procesó orden en tiempo real"

        return message


# ============================================================
# FLASK ENDPOINT WRAPPER
# ============================================================

def shopify_orders_webhook_endpoint(request):
    """
    Flask route wrapper para POST /api/webhook/shopify/orders

    Args:
        request: Flask request object

    Returns:
        tuple: (response_dict, status_code)
    """
    try:
        # 1. LOGUEAR PAYLOAD RECIBIDO (para debug)
        order_data = request.get_json()
        logger.info(f"📥 Webhook recibido: order_id={order_data.get('id', 'N/A')}, order_number={order_data.get('order_number', 'N/A')}")

        # 2. VERIFICAR SEGURIDAD
        cerebro = CerebroCentral()

        hmac_header = request.headers.get('X-Shopify-Hmac-SHA256', '')
        admin_key = request.headers.get('X-Admin-Key', '')
        expected_key = os.getenv('ADMIN_API_KEY', 'shark-predator-2026')
        shopify_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')

        # CASO 1: Webhook Shopify con HMAC
        if hmac_header:
            logger.info(f"🔐 Verificando HMAC Shopify...")
            raw_data = request.get_data()

            if not cerebro.verify_shopify_hmac(raw_data, hmac_header):
                logger.error("❌ HMAC INVÁLIDO - Webhook rechazado")
                logger.error(f"📋 Headers recibidos:")
                for key, value in request.headers.items():
                    if 'shopify' in key.lower() or 'hmac' in key.lower():
                        logger.error(f"  {key}: {value[:50]}...")
                logger.error(f"💾 Payload preview: {str(order_data)[:200]}...")
                return {
                    'success': False,
                    'error': 'Invalid HMAC signature'
                }, 403

            logger.info("✅ HMAC verificado - webhook Shopify auténtico")

        # CASO 2: Llamada manual con X-Admin-Key
        elif admin_key:
            if admin_key != expected_key:
                logger.warning("⚠️ X-Admin-Key inválido - webhook rechazado")
                return {
                    'success': False,
                    'error': 'Invalid X-Admin-Key'
                }, 403
            logger.info("✅ X-Admin-Key verificado - llamada manual")

        # CASO 3: Sin autenticación (solo permitir si NO hay secret configurado)
        elif not shopify_secret:
            logger.warning("⚠️ MODO DESARROLLO - Sin verificación de seguridad")
        else:
            # Hay secret configurado pero no enviaron HMAC ni Admin-Key
            logger.warning("⚠️ Webhook sin autenticación - rechazado")
            logger.warning(f"Headers: {dict(request.headers)}")
            return {
                'success': False,
                'error': 'Missing authentication (HMAC or X-Admin-Key required)'
            }, 403

        # 3. PROCESAR ORDEN

        if not order_data:
            return {
                'success': False,
                'error': 'No JSON payload'
            }, 400

        result = cerebro.process_order_webhook(order_data)

        logger.info(f"✅ Webhook procesado: {result['success']}")

        # 4. ENVIAR A MAKE.COM (para Twilio WhatsApp)
        make_webhook_url = os.getenv('MAKE_WEBHOOK_URL', '')

        if make_webhook_url and result['success']:
            try:
                logger.info(f"📤 Enviando a Make.com webhook...")
                make_response = requests.post(
                    make_webhook_url,
                    json=result,
                    headers={'Content-Type': 'application/json'},
                    timeout=5
                )

                if make_response.status_code == 200:
                    logger.info(f"✅ Make.com webhook enviado exitosamente")
                else:
                    logger.warning(f"⚠️ Make.com respondió con status {make_response.status_code}")

            except requests.exceptions.Timeout:
                logger.error(f"❌ Timeout enviando a Make.com (>5s)")
            except Exception as e:
                logger.error(f"❌ Error enviando a Make.com: {e}")
        elif not make_webhook_url:
            logger.warning(f"⚠️ MAKE_WEBHOOK_URL no configurado - saltando envío")

        # 5. RETORNAR RESULTADO
        status_code = 200 if result['success'] else 500

        return result, status_code

    except Exception as e:
        logger.error(f"❌ Error en webhook endpoint: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"❌ Error procesando webhook:\n{str(e)}"
        }, 500


# ============================================================
# HELPER: Crear tabla daily_sales si no existe
# ============================================================

def ensure_daily_sales_table():
    """Crea tabla daily_sales si no existe."""
    try:
        conn = get_db_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS daily_sales (
                date TEXT PRIMARY KEY,
                total_sales REAL DEFAULT 0,
                orders_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("✅ Tabla daily_sales verificada")
    except Exception as e:
        logger.error(f"❌ Error creando tabla daily_sales: {e}")
