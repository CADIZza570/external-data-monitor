"""
🦈🧠 CEREBRO CENTRAL - Webhooks Shopify → Alertas Instantáneas
================================================================

VERSIÓN: 2.0.0 - GOLD STANDARD PRE-MIGRACIÓN POSTGRESQL
Optimizado para:
- Modularidad de métricas (metrics_calculator.py)
- Error handling robusto
- JSON tipado para Make.com
- Preparado para cambio de SQLite → PostgreSQL

Procesa ventas en tiempo real y dispara alertas WhatsApp cuando:
- Venta de producto alto ROI
- Stock bajo después de venta
- Milestone alcanzado ($1000 en 1 día)
- Velocity spike detectado

Author: Claude (Cirujano Maestro)
Version: 2.0.0 - Optimizado Elite
"""

import os
import hmac
import hashlib
import base64
import logging
import requests
from datetime import datetime, timedelta
from flask import jsonify
from typing import Dict, List, Optional, Any, Tuple
from database import get_db_connection
from metrics_calculator import MetricsCalculator

logger = logging.getLogger(__name__)


class CerebroCentral:
    """Motor de procesamiento de webhooks Shopify con alertas instantáneas."""

    # Constantes de configuración
    MAKE_REQUEST_TIMEOUT = 10  # segundos
    MAX_LINE_ITEMS_PROCESS = 100  # límite de productos por orden
    MAX_ALERTS_IN_MESSAGE = 3  # máximo de alertas en mensaje WhatsApp
    MAX_PRODUCTS_IN_MESSAGE = 3  # máximo de productos mostrados
    PRODUCT_NAME_MAX_LENGTH = 30  # caracteres máximos en nombre

    def __init__(self):
        """Inicializa Cerebro Central con configuración."""
        self.shopify_secret = os.getenv('SHOPIFY_WEBHOOK_SECRET', '')
        self.make_webhook_url = os.getenv('MAKE_WEBHOOK_URL', '')
        self.admin_api_key = os.getenv('ADMIN_API_KEY', 'shark-predator-2026')

    def verify_shopify_hmac(self, data: bytes, hmac_header: str) -> bool:
        """
        Verifica HMAC de Shopify para autenticidad del webhook.

        Args:
            data: Raw request body (bytes)
            hmac_header: X-Shopify-Hmac-SHA256 header (base64)

        Returns:
            bool: True si HMAC válido

        Raises:
            ValueError: Si data no es bytes o hmac_header está vacío
        """
        try:
            if not isinstance(data, bytes):
                raise ValueError(f"data debe ser bytes, recibido: {type(data)}")

            if not hmac_header:
                raise ValueError("hmac_header vacío")

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

            # Logging detallado para debug (sin exponer secret completo)
            secret_preview = f"***{self.shopify_secret[-4:]}" if len(self.shopify_secret) > 4 else "NONE"
            logger.info(f"🔐 HMAC Debug:")
            logger.info(f"  Secret: {secret_preview}")
            logger.info(f"  Payload: {len(data)} bytes")
            logger.info(f"  Recibido: {hmac_header[:20]}...")
            logger.info(f"  Calculado: {computed_hmac[:20]}...")

            is_valid = hmac.compare_digest(computed_hmac, hmac_header)
            logger.info(f"  Match: {is_valid}")

            return is_valid

        except Exception as e:
            logger.error(f"❌ Error verificando HMAC: {e}")
            return False

    def process_order_webhook(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        🧠 CEREBRO - Procesa webhook orders/create o orders/paid.

        Args:
            order_data: Payload del webhook Shopify

        Returns:
            dict: {
                'success': bool,
                'order_id': int,
                'order_number': int,
                'total_price': float,
                'alerts': List[dict],
                'metrics_updated': List[dict],
                'message': str  # Para Make.com + Twilio WhatsApp
            }
        """
        conn = None
        try:
            logger.info("🧠 Cerebro Central: Procesando orden...")

            # 1. VALIDAR Y EXTRAER DATOS
            validation_result = self._validate_order_data(order_data)
            if not validation_result['valid']:
                return self._error_response(
                    validation_result['error'],
                    order_data.get('id', 0),
                    order_data.get('order_number', 0)
                )

            order_id = validation_result['order_id']
            order_number = validation_result['order_number']
            customer_name = validation_result['customer_name']
            total_price = validation_result['total_price']
            line_items = validation_result['line_items']

            logger.info(f"📦 Orden #{order_number} - {customer_name} - ${total_price:.2f}")

            # 2. CONECTAR A BASE DE DATOS
            conn = get_db_connection()

            # 3. PROCESAR LINE ITEMS Y ACTUALIZAR MÉTRICAS
            metrics_updates = []
            alerts = []

            for item in line_items[:self.MAX_LINE_ITEMS_PROCESS]:
                try:
                    product_update = self._process_line_item(item, conn)
                    metrics_updates.append(product_update)

                    # Detectar alertas post-venta
                    item_alerts = self._detect_post_sale_alerts(product_update, conn)
                    alerts.extend(item_alerts)

                except Exception as e:
                    logger.error(f"❌ Error procesando line_item {item.get('sku', 'UNKNOWN')}: {e}")
                    # Continuar con siguiente item

            # 4. ACTUALIZAR MÉTRICAS GLOBALES
            try:
                self._update_global_metrics(total_price, conn)
            except Exception as e:
                logger.warning(f"⚠️ Error actualizando métricas globales: {e}")
                # No crítico, continuar

            # 5. DETECTAR MILESTONES
            try:
                milestone_alert = self._check_milestones(total_price, conn)
                if milestone_alert:
                    alerts.append(milestone_alert)
            except Exception as e:
                logger.warning(f"⚠️ Error verificando milestones: {e}")

            # 6. COMMIT TRANSACCIÓN
            conn.commit()

            # 7. GENERAR MENSAJE UNIFICADO (con sanitización)
            message = self._generate_unified_message(
                order_number, customer_name, total_price,
                line_items, metrics_updates, alerts
            )

            logger.info(f"✅ Orden procesada: {len(metrics_updates)} productos, {len(alerts)} alertas")

            # 8. CONSTRUIR RESPUESTA TIPADA
            result = self._build_success_response(
                order_id, order_number, total_price,
                metrics_updates, alerts, message
            )

            return result

        except Exception as e:
            logger.error(f"❌ Error crítico procesando orden: {e}", exc_info=True)
            return self._error_response(
                str(e),
                order_data.get('id', 0),
                order_data.get('order_number', 0)
            )

        finally:
            # Cerrar conexión DB
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error cerrando conexión DB: {e}")

    def _validate_order_data(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida estructura del payload de orden.

        Returns:
            dict: {
                'valid': bool,
                'error': str (si invalid),
                'order_id': int,
                'order_number': int,
                'customer_name': str,
                'total_price': float,
                'line_items': list
            }
        """
        try:
            # Validar que order_data es dict
            if not isinstance(order_data, dict):
                return {
                    'valid': False,
                    'error': f"order_data debe ser dict, recibido: {type(order_data)}"
                }

            # Extraer campos requeridos con defaults
            order_id = order_data.get('id', 0)
            order_number = order_data.get('order_number', order_id)
            line_items = order_data.get('line_items', [])

            # Validar tipos
            if not isinstance(order_id, (int, str)):
                return {'valid': False, 'error': f"order_id inválido: {order_id}"}

            if not isinstance(line_items, list):
                return {'valid': False, 'error': f"line_items debe ser lista, recibido: {type(line_items)}"}

            # Validar que hay al menos 1 producto
            if len(line_items) == 0:
                return {'valid': False, 'error': "Orden sin line_items"}

            # Extraer customer name (con fallback)
            customer_name = self._extract_customer_name(order_data)

            # Extraer y validar precio
            try:
                total_price = float(order_data.get('total_price', 0))
                if total_price < 0:
                    logger.warning(f"Precio negativo: {total_price}, usando absoluto")
                    total_price = abs(total_price)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parseando total_price: {e}, usando 0")
                total_price = 0.0

            return {
                'valid': True,
                'order_id': int(order_id) if isinstance(order_id, str) and order_id.isdigit() else order_id,
                'order_number': int(order_number) if isinstance(order_number, str) and order_number.isdigit() else order_number,
                'customer_name': customer_name,
                'total_price': total_price,
                'line_items': line_items
            }

        except Exception as e:
            logger.error(f"Error validando order_data: {e}")
            return {
                'valid': False,
                'error': f"Error validación: {str(e)}"
            }

    def _extract_customer_name(self, order_data: Dict[str, Any]) -> str:
        """
        Extrae nombre cliente del payload (con sanitización).

        Returns:
            str: Nombre limpio (max 50 caracteres)
        """
        try:
            customer = order_data.get('customer', {})
            if isinstance(customer, dict):
                first = str(customer.get('first_name', '')).strip()
                last = str(customer.get('last_name', '')).strip()
                full_name = f"{first} {last}".strip()

                if full_name:
                    # Sanitizar caracteres especiales
                    full_name = self._sanitize_text(full_name, max_length=50)
                    return full_name

            return "Cliente"

        except Exception as e:
            logger.warning(f"Error extrayendo customer_name: {e}")
            return "Cliente"

    def _extract_size_from_item(self, item: Dict[str, Any]) -> str:
        """
        Extrae talla del line_item de Shopify.

        Args:
            item: Line item de Shopify

        Returns:
            str: Talla extraída o 'Sin talla'
        """
        try:
            # OPCIÓN 1: variant_title (más común)
            variant_title = item.get('variant_title', '')
            if variant_title and variant_title != 'Default Title':
                return self._sanitize_text(variant_title, max_length=20)

            # OPCIÓN 2: properties custom
            properties = item.get('properties', [])
            if isinstance(properties, list):
                for prop in properties:
                    if isinstance(prop, dict):
                        name = prop.get('name', '').lower()
                        if 'talla' in name or 'size' in name:
                            value = prop.get('value', '')
                            if value:
                                return self._sanitize_text(str(value), max_length=20)

            # OPCIÓN 3: title completo
            title = item.get('title', '')
            if ' - ' in title:
                parts = title.split(' - ')
                last_part = parts[-1].strip()
                if last_part.replace('.', '').replace(',', '').isdigit() or 'talla' in last_part.lower():
                    return self._sanitize_text(last_part, max_length=20)

            # OPCIÓN 4: variant_sku
            sku = item.get('sku', '')
            if sku and '-' in sku:
                parts = sku.split('-')
                last_part = parts[-1]
                if last_part.replace('.', '').isdigit():
                    return f"T{last_part}"  # T065 = Talla 065

            return 'Sin talla'

        except Exception as e:
            logger.warning(f"Error extrayendo talla: {e}")
            return 'Sin talla'

    def _process_line_item(self, item: Dict[str, Any], conn) -> Dict[str, Any]:
        """
        Procesa un line_item y actualiza métricas del producto.

        Returns:
            dict: Métricas actualizadas (ver MetricsCalculator.update_product_metrics)
        """
        # Extraer datos básicos
        sku = str(item.get('sku', item.get('variant_id', 'UNKNOWN')))
        product_name = self._sanitize_text(
            str(item.get('title', 'Producto')),
            max_length=self.PRODUCT_NAME_MAX_LENGTH
        )
        quantity = int(item.get('quantity', 1))
        price = float(item.get('price', 0))

        # Buscar producto en DB
        product = conn.execute('''
            SELECT * FROM products WHERE sku = ?
        ''', (sku,)).fetchone()

        if not product:
            logger.warning(f"⚠️ Producto {sku} no existe - creando nuevo")
            # Crear producto nuevo
            conn.execute('''
                INSERT INTO products (product_id, sku, name, stock, price, velocity_daily, total_sales_30d)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (sku, sku, product_name, 0, price, 0, 0))
            product = conn.execute('SELECT * FROM products WHERE sku = ?', (sku,)).fetchone()

        # Usar MetricsCalculator para actualizar métricas
        metrics = MetricsCalculator.update_product_metrics(
            product_data=dict(product),
            quantity_sold=quantity,
            sale_price=price
        )

        # Actualizar DB
        conn.execute('''
            UPDATE products
            SET stock = ?,
                total_sales_30d = ?,
                velocity_daily = ?,
                last_sale_date = ?
            WHERE sku = ?
        ''', (
            metrics['new_stock'],
            metrics['new_sales_30d'],
            metrics['new_velocity'],
            datetime.now().isoformat(),
            sku
        ))

        logger.info(
            f"  📊 {sku}: stock {metrics['old_stock']}→{metrics['new_stock']}, "
            f"velocity {metrics['new_velocity']:.2f}/día, ROI {metrics['roi']:.0f}%"
        )

        # Retornar formato compatible con mensaje
        return {
            'sku': sku,
            'product_name': product_name,
            'quantity': quantity,
            'price': price,
            'old_stock': metrics['old_stock'],
            'new_stock': metrics['new_stock'],
            'new_velocity': metrics['new_velocity'],
            'roi': metrics['roi']
        }

    def _detect_post_sale_alerts(self, product_update: Dict[str, Any], conn) -> List[Dict[str, Any]]:
        """
        Detecta alertas después de venta usando MetricsCalculator.

        Returns:
            list: Alertas generadas
        """
        alerts = []
        sku = product_update['sku']
        new_stock = product_update['new_stock']
        velocity = product_update['new_velocity']
        roi = product_update['roi']

        # ALERTA 1: Stock crítico (usando MetricsCalculator)
        if MetricsCalculator.is_critical_stock(new_stock, velocity):
            days_to_stockout = MetricsCalculator.calculate_days_to_stockout(new_stock, velocity)

            if days_to_stockout is not None and days_to_stockout < 3:
                alerts.append({
                    'type': 'stock_critical_post_sale',
                    'severity': 'CRÍTICO',
                    'emoji': '🚨',
                    'sku': sku,
                    'product': product_update['product_name'],
                    'stock': new_stock,
                    'days_to_stockout': round(days_to_stockout, 1),
                    'message': self._sanitize_text(
                        f"🚨 Stock crítico: {product_update['product_name']} "
                        f"({new_stock}u → {days_to_stockout:.1f}d)"
                    )
                })

        # ALERTA 2: Venta alto ROI (usando MetricsCalculator)
        if MetricsCalculator.is_high_roi_sale(roi):
            alerts.append({
                'type': 'high_roi_sale',
                'severity': 'INFO',
                'emoji': '💰',
                'sku': sku,
                'product': product_update['product_name'],
                'roi': round(roi, 1),
                'quantity': product_update['quantity'],
                'message': self._sanitize_text(
                    f"💰 Venta alto ROI: {product_update['product_name']} "
                    f"({product_update['quantity']}u, {roi:.0f}% ROI)"
                )
            })

        return alerts

    def _update_global_metrics(self, total_price: float, conn):
        """Actualiza métricas globales del negocio."""
        today = datetime.now().date().isoformat()

        conn.execute('''
            INSERT INTO daily_sales (date, total_sales)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET
                total_sales = total_sales + excluded.total_sales
        ''', (today, total_price))

    def _check_milestones(self, total_price: float, conn) -> Optional[Dict[str, Any]]:
        """
        Detecta si se alcanzó milestone de ventas.

        Returns:
            dict or None: Alerta de milestone
        """
        today = datetime.now().date().isoformat()

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
                    'amount': round(daily_total, 2),
                    'message': f"🎉 ¡Milestone! ${daily_total:,.2f} hoy"
                }

        return None

    def _generate_unified_message(
        self,
        order_number: int,
        customer_name: str,
        total_price: float,
        line_items: List[Dict],
        metrics_updates: List[Dict],
        alerts: List[Dict]
    ) -> str:
        """
        Genera mensaje unificado para Make.com + Twilio WhatsApp.
        Con sanitización completa de caracteres especiales.

        Returns:
            str: Mensaje formateado con emojis (max 1600 caracteres para WhatsApp)
        """
        try:
            # HEADER
            message = f"🛒 NUEVA VENTA - Orden #{order_number}\n\n"

            # CLIENTE
            message += f"👤 {customer_name}\n"
            message += f"💰 Total: ${total_price:.2f}\n\n"

            # PRODUCTOS CON TALLA
            products_count = len(line_items)
            message += f"📦 Productos ({products_count}):\n"

            # Mostrar max 3 productos
            for i, (item, update) in enumerate(zip(line_items[:self.MAX_PRODUCTS_IN_MESSAGE], metrics_updates[:self.MAX_PRODUCTS_IN_MESSAGE])):
                talla = self._extract_size_from_item(item)

                product_display = update['product_name']
                if talla and talla != 'Sin talla':
                    product_display += f" - {talla}"

                message += f"• {product_display}\n"
                message += f"  {update['quantity']}u × ${update['price']:.2f}\n"
                message += f"  Stock: {update['old_stock']}→{update['new_stock']}\n"

            if products_count > self.MAX_PRODUCTS_IN_MESSAGE:
                message += f"  ... y {products_count - self.MAX_PRODUCTS_IN_MESSAGE} más\n"

            # ALERTAS
            if alerts:
                alerts_count = len(alerts)
                message += f"\n🚨 ALERTAS ({alerts_count}):\n"

                for alert in alerts[:self.MAX_ALERTS_IN_MESSAGE]:
                    message += f"{alert['emoji']} {alert['type'].upper()}\n"

                    if alert['type'] == 'stock_critical_post_sale':
                        message += f"  {alert['product']}: {alert['stock']}u (Stockout {alert['days_to_stockout']}d)\n"
                    elif alert['type'] == 'high_roi_sale':
                        message += f"  {alert['product']}: ROI {alert['roi']:.0f}%\n"
                    elif alert['type'] == 'milestone_1k_day':
                        message += f"  Ventas hoy: ${alert['amount']:,.2f}\n"

            # FOOTER
            message += f"\n🦈 Tiburón procesó orden en tiempo real"

            # Sanitizar mensaje completo
            message = self._sanitize_text(message, max_length=1600)

            return message

        except Exception as e:
            logger.error(f"Error generando mensaje: {e}")
            # Mensaje fallback
            return f"🛒 Nueva venta #{order_number} - ${total_price:.2f}"

    def _sanitize_text(self, text: str, max_length: int = 500) -> str:
        """
        Sanitiza texto para WhatsApp/JSON.

        - Remueve caracteres de control
        - Escapa comillas dobles
        - Limita longitud
        - Preserva emojis y acentos

        Args:
            text: Texto a sanitizar
            max_length: Longitud máxima

        Returns:
            str: Texto limpio
        """
        if not isinstance(text, str):
            text = str(text)

        # Remover caracteres de control (excepto \n, \t)
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')

        # Limitar longitud
        if len(text) > max_length:
            text = text[:max_length-3] + "..."

        return text

    def _build_success_response(
        self,
        order_id: int,
        order_number: int,
        total_price: float,
        metrics_updates: List[Dict],
        alerts: List[Dict],
        message: str
    ) -> Dict[str, Any]:
        """
        Construye respuesta exitosa con tipos bien definidos para Make.com.

        Returns:
            dict: Respuesta tipada
        """
        return {
            'success': True,
            'order_id': int(order_id),
            'order_number': int(order_number),
            'total_price': round(float(total_price), 2),
            'alerts': alerts,  # Lista de dicts
            'metrics_updated': metrics_updates,  # Lista de dicts
            'message': str(message),  # String UTF-8 limpio
            'timestamp': datetime.now().isoformat(),
            'processed_items': len(metrics_updates)
        }

    def _error_response(
        self,
        error: str,
        order_id: int = 0,
        order_number: int = 0
    ) -> Dict[str, Any]:
        """
        Construye respuesta de error con estructura consistente.

        Returns:
            dict: Respuesta de error
        """
        error_message = self._sanitize_text(str(error), max_length=200)

        return {
            'success': False,
            'order_id': int(order_id),
            'order_number': int(order_number),
            'total_price': 0.0,
            'alerts': [],
            'metrics_updated': [],
            'message': f"❌ Error: {error_message}",
            'error': error_message,
            'timestamp': datetime.now().isoformat()
        }


# ============================================================
# FLASK ENDPOINT WRAPPER
# ============================================================

def shopify_orders_webhook_endpoint(request):
    """
    Flask route wrapper para POST /api/webhook/shopify/orders

    OPTIMIZADO v2.0:
    - Error handling robusto en cada paso
    - Validación de autenticación mejorada
    - Integración Make.com con retry
    - Logs detallados para debugging

    Args:
        request: Flask request object

    Returns:
        tuple: (response_dict, status_code)
    """
    try:
        # 1. VALIDAR PAYLOAD
        try:
            order_data = request.get_json()
            if not order_data:
                logger.warning("⚠️ Payload JSON vacío")
                return {'success': False, 'error': 'Empty JSON payload'}, 400
        except Exception as e:
            logger.error(f"❌ Error parseando JSON: {e}")
            return {'success': False, 'error': 'Invalid JSON'}, 400

        order_id = order_data.get('id', 'N/A')
        order_number = order_data.get('order_number', 'N/A')
        logger.info(f"📥 Webhook recibido: order_id={order_id}, order_number={order_number}")

        # 2. VERIFICAR SEGURIDAD
        cerebro = CerebroCentral()
        auth_result = _verify_authentication(request, cerebro)

        if not auth_result['valid']:
            return {
                'success': False,
                'error': auth_result['error']
            }, auth_result['status_code']

        logger.info(f"✅ Autenticación: {auth_result['method']}")

        # 3. PROCESAR ORDEN
        result = cerebro.process_order_webhook(order_data)

        if not result['success']:
            logger.error(f"❌ Error procesando: {result.get('error', 'Unknown')}")
            return result, 500

        logger.info(f"✅ Orden procesada: {result['processed_items']} items, {len(result['alerts'])} alertas")

        # 4. ENVIAR A MAKE.COM (si configurado)
        if cerebro.make_webhook_url and result['success']:
            _send_to_make(cerebro.make_webhook_url, result)

        return result, 200

    except Exception as e:
        logger.error(f"❌ Error crítico en endpoint: {e}", exc_info=True)
        return {
            'success': False,
            'error': 'Internal server error',
            'message': f"❌ Error crítico: {str(e)[:100]}"
        }, 500


def _verify_authentication(request, cerebro: CerebroCentral) -> Dict[str, Any]:
    """
    Verifica autenticación del webhook.

    Returns:
        dict: {
            'valid': bool,
            'method': str ('HMAC', 'Admin-Key', 'Dev-Mode'),
            'error': str (si invalid),
            'status_code': int (si invalid)
        }
    """
    hmac_header = request.headers.get('X-Shopify-Hmac-SHA256', '')
    admin_key = request.headers.get('X-Admin-Key', '')
    shopify_secret = cerebro.shopify_secret

    # CASO 1: Webhook Shopify con HMAC
    if hmac_header:
        logger.info("🔐 Verificando HMAC Shopify...")
        raw_data = request.get_data()

        try:
            if not cerebro.verify_shopify_hmac(raw_data, hmac_header):
                logger.error("❌ HMAC INVÁLIDO")
                return {
                    'valid': False,
                    'error': 'Invalid HMAC signature',
                    'status_code': 403
                }
            return {'valid': True, 'method': 'HMAC'}

        except Exception as e:
            logger.error(f"❌ Error verificando HMAC: {e}")
            return {
                'valid': False,
                'error': 'HMAC verification failed',
                'status_code': 403
            }

    # CASO 2: Llamada manual con X-Admin-Key
    if admin_key:
        if admin_key != cerebro.admin_api_key:
            logger.warning("⚠️ X-Admin-Key inválido")
            return {
                'valid': False,
                'error': 'Invalid X-Admin-Key',
                'status_code': 403
            }
        return {'valid': True, 'method': 'Admin-Key'}

    # CASO 3: Sin autenticación (solo permitir si NO hay secret)
    if not shopify_secret:
        logger.warning("⚠️ MODO DESARROLLO - Sin verificación")
        return {'valid': True, 'method': 'Dev-Mode'}

    # Hay secret pero no enviaron autenticación
    logger.warning("⚠️ Webhook sin autenticación rechazado")
    return {
        'valid': False,
        'error': 'Missing authentication (HMAC or X-Admin-Key required)',
        'status_code': 403
    }


def _send_to_make(make_url: str, result: Dict[str, Any]):
    """
    Envía resultado a Make.com con retry logic.

    Args:
        make_url: URL del webhook Make.com
        result: Resultado del procesamiento
    """
    max_retries = 2
    timeout = CerebroCentral.MAKE_REQUEST_TIMEOUT

    for attempt in range(max_retries):
        try:
            logger.info(f"📤 Enviando a Make.com (intento {attempt + 1}/{max_retries})...")

            response = requests.post(
                make_url,
                json=result,
                headers={'Content-Type': 'application/json'},
                timeout=timeout
            )

            if response.status_code == 200:
                logger.info("✅ Make.com webhook enviado exitosamente")
                return

            logger.warning(f"⚠️ Make.com respondió con status {response.status_code}")

            # No reintentar si es error 4xx (client error)
            if 400 <= response.status_code < 500:
                break

        except requests.exceptions.Timeout:
            logger.error(f"❌ Timeout enviando a Make.com (>{timeout}s)")
        except Exception as e:
            logger.error(f"❌ Error enviando a Make.com: {e}")

        # Esperar antes de reintentar (excepto último intento)
        if attempt < max_retries - 1:
            import time
            time.sleep(1)

    logger.warning("⚠️ No se pudo enviar a Make.com después de reintentos")


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
