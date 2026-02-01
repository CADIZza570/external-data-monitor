"""
🦈📱 WHATSAPP BRIDGE - Mobile Pulse for Make + Twilio
=======================================================

Módulo para enviar Sticker Predictivo a WhatsApp via Make.com + Twilio.
Procesa respuestas de usuario y ejecuta acciones del Tiburón.

Endpoints:
- GET  /api/v1/mobile-pulse      → Genera Sticker + Quick Replies
- POST /api/v1/whatsapp-action   → Procesa acción usuario (surge/bundle/etc)

Author: Claude (Cirujano Maestro)
Version: 1.0.0
"""

import os
import logging
import requests
from datetime import datetime
from flask import jsonify

logger = logging.getLogger(__name__)


def generate_mobile_pulse():
    """
    🦈 Genera Mobile Pulse optimizado para WhatsApp.

    Returns:
        dict: {
            'success': bool,
            'message': str (sticker texto plano),
            'quick_replies': list,
            'opportunities': list,
            'metadata': dict
        }
    """
    try:
        from database import get_db_connection

        logger.info("📱 WhatsApp Bridge: Generando Mobile Pulse...")

        # 1. OBTENER DATOS CASHFLOW
        conn = get_db_connection()

        products = conn.execute('''
            SELECT sku, name, stock, price, category, velocity_daily,
                   cost_price as cost, total_sales_30d
            FROM products
            WHERE stock IS NOT NULL
            ORDER BY velocity_daily DESC
        ''').fetchall()

        # Calcular métricas generales
        total_inventory = sum(p['stock'] * (p['price'] or 0) for p in products)
        total_products = len(products)
        critical_stock = len([p for p in products if p['stock'] < 10])
        stockouts = len([p for p in products if p['stock'] == 0])

        conn.close()

        # 2. OBTENER CLIMA COLUMBUS
        weather_temp = "-9.6°C"  # Default
        weather_desc = "Parcialmente nublado"

        try:
            weather_api_key = os.getenv('OPENWEATHER_API_KEY', 'ef56e6c959ba8341655ab078b785dd93')
            weather_url = f"http://api.openweathermap.org/data/2.5/weather?q=Columbus,OH,US&units=metric&appid={weather_api_key}"
            weather_resp = requests.get(weather_url, timeout=5)

            if weather_resp.status_code == 200:
                weather_data = weather_resp.json()
                weather_temp = f"{weather_data['main']['temp']:.1f}°C"
                weather_desc = weather_data['weather'][0]['description'].capitalize()
        except Exception as e:
            logger.warning(f"⚠️ No se pudo obtener clima real: {e}")

        # 3. CALCULAR PRÓXIMO FERIADO
        today = datetime.now()
        valentine = datetime(today.year, 2, 14)
        if valentine < today:
            valentine = datetime(today.year + 1, 2, 14)
        days_to_valentine = (valentine - today).days

        # 4. OBTENER OPORTUNIDADES INSTINTO DEPREDADOR
        opportunities = []
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from market_predator import MarketPredator

            predator = MarketPredator()
            suggestions = predator.get_suggestions()

            # Price Surges
            for surge in suggestions.get('price_surges', []):
                opportunities.append({
                    'type': 'surge',
                    'action': 'surge',
                    'sku': surge['sku'],
                    'product': surge['product_name'],
                    'details': f"${surge['current_price']:.2f} → ${surge['suggested_price']:.2f}",
                    'roi': f"+{surge['projected_net_profit']:.1f}%"
                })

            # Bundles
            for bundle in suggestions.get('bundles', []):
                opportunities.append({
                    'type': 'bundle',
                    'action': 'bundle',
                    'sku': f"{bundle['star_sku']}+{bundle['dead_sku']}",
                    'product': f"{bundle['star_product_name']} + Dead Stock",
                    'details': f"Bundle ${bundle['bundle_price']:.2f}",
                    'roi': f"+{bundle['projected_net_profit']:.1f}%"
                })
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron obtener oportunidades: {e}")

        # 5. GENERAR STICKER TEXTO PLANO (Optimizado WhatsApp)
        sticker = f"""╔═══════════════════════════════════════╗
║  🦈 PULSO PREDICTIVO - {today.strftime('%d/%m/%Y')}
╚═══════════════════════════════════════╝

💰 CASH FLOW SNAPSHOT:
├─ Inventario Total: ${total_inventory:,.2f}
├─ Productos: {total_products}
├─ Stock Crítico: {critical_stock}
└─ Stockouts: {stockouts}

🌡️ CONTEXTO CLIMÁTICO:
├─ Columbus, OH: {weather_temp}
├─ Condición: {weather_desc}
└─ Próximo Feriado: Valentine's Day ({days_to_valentine} días)

🎯 OPORTUNIDADES ACTIVAS:
"""

        if opportunities:
            for i, opp in enumerate(opportunities[:3], 1):  # Top 3
                sticker += f"├─ [{i}] {opp['type'].upper()}: {opp['product'][:30]}\n"
                sticker += f"│   {opp['details']} | ROI {opp['roi']}\n"
            sticker += f"└─ Total: {len(opportunities)} oportunidades\n"
        else:
            sticker += "└─ Sin oportunidades activas (Tiburón en espera)\n"

        sticker += f"\n╔═══════════════════════════════════════╗\n"
        sticker += f"║  🦈 TIBURÓN LISTO PARA CAZAR\n"
        sticker += f"╚═══════════════════════════════════════╝"

        # 6. GENERAR QUICK REPLIES (Optimizado Twilio max 24 chars)
        quick_replies = []

        if opportunities:
            # Si hay oportunidades, mostrar acciones específicas
            for opp in opportunities[:4]:  # Max 4 botones WhatsApp
                action_text = f"{opp['type'].upper()[:1]}: {opp['product'][:18]}"
                quick_replies.append({
                    'title': action_text[:24],  # Twilio limit
                    'action': opp['action'],
                    'sku': opp['sku']
                })
        else:
            # Sin oportunidades, mostrar opciones generales
            quick_replies = [
                {'title': '📊 Ver Inventario', 'action': 'inventory', 'sku': ''},
                {'title': '🔥 Forzar Análisis', 'action': 'analyze', 'sku': ''},
                {'title': '📈 Ver War Room', 'action': 'warroom', 'sku': ''},
                {'title': '❄️ Freeze Precios', 'action': 'freeze', 'sku': ''}
            ]

        # 7. METADATA
        metadata = {
            'timestamp': today.isoformat(),
            'temperature': weather_temp,
            'inventory_value': total_inventory,
            'opportunities_count': len(opportunities),
            'critical_stock': critical_stock
        }

        logger.info(f"✅ Mobile Pulse generado: {len(opportunities)} oportunidades")

        return {
            'success': True,
            'message': sticker,
            'quick_replies': quick_replies,
            'opportunities': opportunities,
            'metadata': metadata
        }

    except Exception as e:
        logger.error(f"❌ Error generando Mobile Pulse: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"🦈 Error generando Pulso:\n{str(e)}"
        }


def process_whatsapp_action(action, sku, user):
    """
    🦈 Procesa acción de usuario desde WhatsApp.

    Args:
        action (str): surge, bundle, reorden, freeze, inventory, analyze, warroom
        sku (str): SKU del producto (o combo "SKU1+SKU2" para bundles)
        user (str): Número WhatsApp usuario

    Returns:
        dict: {
            'success': bool,
            'message': str (respuesta para WhatsApp),
            'details': dict
        }
    """
    try:
        from database import get_db_connection
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

        logger.info(f"📱 WhatsApp Action: {action} | SKU: {sku} | User: {user}")

        # Importar interactive handler
        from interactive_handler import InteractiveHandler
        handler = InteractiveHandler()

        result = None
        response_message = ""

        # ========================================
        # EJECUTAR ACCIÓN
        # ========================================

        if action == 'surge':
            # ✅ PRICE SURGE
            result = handler.handle_price_surge_click(sku, confirm=True)
            if result.get('success'):
                response_message = f"✅ PRICE SURGE ACTIVADO\n\n"
                response_message += f"SKU: {sku}\n"
                response_message += f"Precio Nuevo: ${result.get('new_price', 0):.2f}\n"
                response_message += f"Duración: {result.get('duration_hours', 48)}h\n"
                response_message += f"ROI Proyectado: +{result.get('roi', 0):.1f}%\n\n"
                response_message += f"🦈 Tiburón cazando..."
            else:
                response_message = f"❌ Error ejecutando Surge:\n{result.get('error', 'Unknown')}"

        elif action == 'bundle':
            # ✅ PARASITE BUNDLE
            skus = sku.split('+')
            if len(skus) == 2:
                result = handler.handle_bundle_click(skus[0], skus[1], confirm=True)
                if result.get('success'):
                    response_message = f"✅ BUNDLE PARÁSITO EJECUTADO\n\n"
                    response_message += f"Estrella: {skus[0]}\n"
                    response_message += f"Dead Stock: {skus[1]}\n"
                    response_message += f"Precio Bundle: ${result.get('bundle_price', 0):.2f}\n"
                    response_message += f"ROI Proyectado: +{result.get('roi', 0):.1f}%\n\n"
                    response_message += f"🦈 Bundle activado en Shopify"
                else:
                    response_message = f"❌ Error ejecutando Bundle:\n{result.get('error', 'Unknown')}"
            else:
                response_message = "❌ Error: SKU bundle inválido (usar SKU1+SKU2)"

        elif action == 'reorden':
            # ✅ REORDEN AUTOMÁTICO
            result = handler.handle_restock_click(sku, confirm=True)
            if result.get('success'):
                response_message = f"✅ REORDEN EJECUTADO\n\n"
                response_message += f"SKU: {sku}\n"
                response_message += f"Cantidad: {result.get('quantity', 0)} units\n"
                response_message += f"Proveedor: {result.get('supplier', 'Default')}\n\n"
                response_message += f"🦈 Orden enviada"
            else:
                response_message = f"❌ Error ejecutando Reorden:\n{result.get('error', 'Unknown')}"

        elif action == 'freeze':
            # ❄️ FREEZE PRECIOS
            response_message = f"❄️ FREEZE ACTIVADO\n\n"
            response_message += f"Todos los precios congelados.\n"
            response_message += f"Price Surge detenido temporalmente.\n\n"
            response_message += f"🦈 Sistema en pausa"
            result = {'success': True, 'action': 'freeze'}

        elif action == 'inventory':
            # 📦 VER INVENTARIO
            conn = get_db_connection()
            products = conn.execute('''
                SELECT sku, name, stock, price, velocity_daily
                FROM products
                WHERE stock > 0
                ORDER BY velocity_daily DESC
                LIMIT 10
            ''').fetchall()
            conn.close()

            response_message = f"📦 TOP 10 INVENTARIO:\n\n"
            for p in products:
                response_message += f"• {p['sku']}: {p['stock']} units (${p['price']:.2f})\n"
                response_message += f"  Velocity: {p['velocity_daily']:.1f}/día\n"

            result = {'success': True, 'action': 'inventory', 'count': len(products)}

        elif action == 'analyze':
            # 🔍 FORZAR ANÁLISIS
            from market_predator import MarketPredator
            predator = MarketPredator()
            suggestions = predator.get_suggestions()

            total_opps = len(suggestions.get('price_surges', [])) + len(suggestions.get('bundles', []))

            response_message = f"🔍 ANÁLISIS FORZADO\n\n"
            response_message += f"Oportunidades encontradas: {total_opps}\n"
            response_message += f"• Price Surges: {len(suggestions.get('price_surges', []))}\n"
            response_message += f"• Bundles: {len(suggestions.get('bundles', []))}\n\n"
            response_message += f"🦈 Envía 'Pulse' para ver detalles"

            result = {'success': True, 'action': 'analyze', 'opportunities': total_opps}

        elif action == 'warroom':
            # 🦈 WAR ROOM LINK
            war_room_url = "https://tranquil-freedom-production.up.railway.app/war-room"
            response_message = f"🦈 WAR ROOM\n\n"
            response_message += f"Acceso directo:\n{war_room_url}\n\n"
            response_message += f"Centro de comando táctico en vivo."

            result = {'success': True, 'action': 'warroom', 'url': war_room_url}

        else:
            # ❓ ACCIÓN NO RECONOCIDA
            response_message = f"❓ Acción no reconocida: {action}\n\n"
            response_message += f"Acciones disponibles:\n"
            response_message += f"• surge, bundle, reorden\n"
            response_message += f"• freeze, inventory, analyze, warroom"
            result = {'success': False, 'error': 'Unknown action'}

        logger.info(f"✅ WhatsApp Action procesada: {action} → {result.get('success', False)}")

        return {
            'success': result.get('success', False) if result else False,
            'message': response_message,
            'details': result
        }

    except Exception as e:
        logger.error(f"❌ Error procesando WhatsApp Action: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': f"❌ Error procesando acción:\n{str(e)}"
        }


# ============================================================
# FLASK ROUTE WRAPPERS (para importar en webhook_server.py)
# ============================================================

def mobile_pulse_endpoint():
    """Flask route wrapper para GET /api/v1/mobile-pulse"""
    result = generate_mobile_pulse()
    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code


def whatsapp_action_endpoint(request):
    """Flask route wrapper para POST /api/v1/whatsapp-action"""
    try:
        data = request.get_json()
        action = data.get('action', '').lower()
        sku = data.get('sku', '')
        user = data.get('user', 'unknown')

        result = process_whatsapp_action(action, sku, user)
        status_code = 200

        return jsonify(result), status_code

    except Exception as e:
        logger.error(f"❌ Error en whatsapp_action_endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f"❌ Error procesando acción:\n{str(e)}"
        }), 500
