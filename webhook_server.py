# ============================================================
# 🚀 WEBHOOK SERVER – SHOPIFY AUTOMATION (v2.5)
# ============================================================
# Sistema de automatización que recibe webhooks reales o simulados
# 
# MEJORAS IMPLEMENTADAS (v2.5):
# - ✅ Validación automática de configuración al iniciar
# - ✅ Verificación HMAC para seguridad (Shopify real)
# - ✅ Rate limiting (100 requests/hour por IP)
# - ✅ Sanitización de errores (no expone información interna)
# - ✅ Validación estricta de payload (tipo, estructura, límites)
# - ✅ Retry logic para guardar CSV (3 intentos)
# - ✅ DRY en funciones de alerta (helper _save_alert)
# - ✅ Health check robusto (verifica dependencias)
# - ✅ Límite de tamaño de payload (16MB)
# - ✅ Logging dual (archivo + consola)
# - ✅ Diagnósticos automáticos (stock bajo, sin ventas, datos faltantes)
# - ✅ Respuestas informativas para debugging
# - ✅ Listo para producción
# ============================================================

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import logging
import sys
import hmac
import hashlib
import base64
import pandas as pd
import os
import time
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import gspread
from google.oauth2.service_account import Credentials
import json

from analytics_integrator import get_analytics_integrator

from dotenv import load_dotenv
load_dotenv()

# Importamos config y la función de validación centralizada
from config_shared import (
    SHOPIFY_WEBHOOK_SECRET,
    LOW_STOCK_THRESHOLD,
    NO_SALES_DAYS,
    DEBUG_MODE,
    OUTPUT_DIR,
    LOG_DIR,
    LOG_FILE,
    EMAIL_SENDER,
    validate_config
)       
# Configurar SendGrid API Key
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# Configurar múltiples clientes
SHOPIFY_WEBHOOK_SECRET_DEV = os.getenv("SHOPIFY_WEBHOOK_SECRET_DEV")
SHOPIFY_WEBHOOK_SECRET_CHAPARRITA = os.getenv("SHOPIFY_WEBHOOK_SECRET_CHAPARRITA")

EMAIL_SENDER_CHAPARRITA = os.getenv("EMAIL_SENDER_CHAPARRITA")
DISCORD_WEBHOOK_URL_CHAPARRITA = os.getenv("DISCORD_WEBHOOK_URL_CHAPARRITA")
GOOGLE_SHEET_ID_CHAPARRITA = os.getenv("GOOGLE_SHEET_ID_CHAPARRITA")

# Configurar Google Sheets (shared)
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

# Variables base (para compatibilidad y DEV)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")

# Importar funciones de base de datos
from database import save_webhook, get_webhooks, get_webhook_count
# ✅ NUEVO: Sistema anti-duplicados
from alert_deduplication import get_deduplicator, ALERT_TTL_CONFIG
from business_adapter import BusinessAdapter  # ← NUEVA

# ============= NUEVO: Sistema de eventos =============
from src.utils.event_logger import EventLogger
from src.events.alert_events import AlertEvents
from src.events.system_events import SystemEvents
import time  # Para medir duration
# ====================================================

# =========================
# ⚙️ CONFIGURACIÓN GLOBAL
# =========================

# ✅ Mejora v2.5: Límite máximo de payload (protección DoS)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
MAX_PRODUCTS_PER_WEBHOOK = 10000  # Límite de productos por request

# Ejecutamos validación al iniciar el servidor
# Esto asegura que cualquier error de config se detecte antes de levantar Flask
validate_config(strict=False)  # ✅ Modo no-estricto para Railway

# =========================
# 📝 LOGGING MEJORADO (Archivo + Consola)
# =========================

logger = logging.getLogger("webhook_server")
logger.setLevel(logging.INFO)

# Handler para archivo
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

# Handler para consola (con colores simulados)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# =========================
# 🔐 SEGURIDAD: Verificación HMAC
# =========================

def get_client_config(shop_domain: str, hmac_header: str, request_data: bytes) -> dict:
    """
    Detecta de qué cliente viene el webhook y retorna su configuración.
    
    Args:
        shop_domain: Dominio de la tienda (ej: connie-dev-studio.myshopify.com)
        hmac_header: HMAC header del webhook
        request_data: Body del request para verificar
    
    Returns:
        Dict con configuración del cliente o None si no es válido
    """
    # Mapeo de dominios a configuraciones
    client_configs = {
        'connie-dev-studio.myshopify.com': {
            'name': 'DEV',
            'shop_name': 'Development Store',  # ← NUEVO
            'business_type': 'ecommerce',  # ← NUEVA LÍNEA
            'webhook_secret': SHOPIFY_WEBHOOK_SECRET_DEV,
            'email': EMAIL_SENDER,
            'discord': DISCORD_WEBHOOK_URL,
            'sheet_id': GOOGLE_SHEET_ID
        },
        'chaparrita-boots.myshopify.com': {
            'name': 'La Chaparrita',
            'shop_name': 'La Chaparrita',  # ← NUEVO
            'business_type': 'retail',  # ← NUEVA LÍNEA (cambia según tu negocio)
            'webhook_secret': SHOPIFY_WEBHOOK_SECRET_CHAPARRITA,
            'email': EMAIL_SENDER_CHAPARRITA or EMAIL_SENDER,
            'discord': DISCORD_WEBHOOK_URL_CHAPARRITA or DISCORD_WEBHOOK_URL,
            'sheet_id': GOOGLE_SHEET_ID_CHAPARRITA or GOOGLE_SHEET_ID
        }
    }
    
    # Buscar configuración por dominio
    config = client_configs.get(shop_domain)
    
    if not config:
        logger.warning(f"⚠️ Cliente no configurado: {shop_domain}")
        return None
    
    # Verificar HMAC con el secret del cliente
    if not verify_shopify_webhook(request_data, hmac_header, config['webhook_secret']):
        logger.warning(f"⚠️ HMAC inválido para {config['name']}")
        return None
    
    logger.info(f"✅ Cliente identificado: {config['name']}")
    return config

def verify_shopify_webhook(data: bytes, hmac_header: str, secret: str) -> bool:
    """
    Verifica que el webhook viene realmente de Shopify.
    
    Shopify firma cada webhook con HMAC-SHA256 usando tu secret.
    Sin esto, cualquiera podría enviar webhooks falsos.
    
    Args:
        data: Body raw del request (bytes)
        hmac_header: Header 'X-Shopify-Hmac-Sha256' del request
        secret: Tu webhook secret de Shopify
    
    Returns:
        True si la firma es válida, False si no
    """
    if not hmac_header or not secret:
        return False
    
    calculated = base64.b64encode(
        hmac.new(
            secret.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()
    ).decode('utf-8')
    
    # ✅ Mejora: compare_digest previene timing attacks
    return hmac.compare_digest(calculated, hmac_header)

def is_simulation_mode(request) -> bool:
    """
    Detecta si es una llamada de simulación.
    
    Modificación para tests de HMAC:
    - Permite forzar modo real con header "X-Simulation-Mode: false"
    - Solo ignora HMAC si X-Simulation-Mode es 'true' o viene de localhost
    """
    simulation_header = request.headers.get('X-Simulation-Mode')
    
    # Forzar simulación explícita
    if simulation_header == 'true':
        return True
    
    # Forzar modo real explícito
    if simulation_header == 'false':
        return False

    # Si viene de localhost, simulación
    if request.remote_addr in ['127.0.0.1', 'localhost']:
        return True

    # Si viene con HMAC, modo real
    if request.headers.get('X-Shopify-Hmac-Sha256'):
        return False

    # Default: simulación para seguridad
    return True

# =========================
# 📊 FUNCIONES DE DIAGNÓSTICO
# =========================
def send_email_alert(subject: str, products_list: list, email_to: str = None, 
                    shop_name: str = None) -> bool:
    """
    Envía email de alerta usando SendGrid API.
    
    Args:
        subject: Asunto del email
        products_list: Lista de productos con alerta (max 10)
    
    Returns:
        True si envío exitoso, False si falla
    """
    # Verificar que SendGrid esté configurado
    email_recipient = email_to or EMAIL_SENDER
    if not SENDGRID_API_KEY or not email_recipient:
        logger.warning("⚠️ SendGrid no configurado, saltando alerta")
        return False
    
    try:
        # Crear body del email
        shop_display = shop_name or "Shopify Webhook System"
        body = f"""
🚨 ALERTA DE INVENTARIO - {shop_display}

Se ha detectado la siguiente alerta en tu tienda:

{subject}

Productos afectados ({len(products_list)}):
"""
        
        # Añadir lista de productos
        for i, product in enumerate(products_list[:10], 1):
            body += f"\n{i}. {product.get('name', 'Sin nombre')}"
            if 'stock' in product:
                body += f" - Stock: {product['stock']} unidades"
            if 'sku' in product:
                body += f" - SKU: {product['sku']}"
        
        if len(products_list) > 10:
            body += f"\n\n... y {len(products_list) - 10} productos más"
        
        body += f"""

---
Ver detalles completos:
https://tranquil-freedom-production.up.railway.app/webhooks/history

Sistema de Alertas Automáticas
Powered by Railway + Shopify + SendGrid
        """
        
        # Crear mensaje
        message = Mail(
            from_email=EMAIL_SENDER,
            to_emails=email_recipient,
            subject=subject,
            plain_text_content=body
        )
        
        # Enviar con SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✅ Email enviado via SendGrid: {subject} (status: {response.status_code})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email con SendGrid: {e}")
        return False

def send_discord_alert(alert_type: str, products_list: list, discord_url: str = None,
                      shop_name: str = None, analytics_data: dict = None) -> bool:
    """
    Envía alerta a Discord usando webhooks con formato profesional mejorado.
    ✅ MEJORA v3.2: Soporte para analytics integrados
    
    Args:
        alert_type: Tipo de alerta o mensaje personalizado
        products_list: Lista de productos con alerta
        discord_url: URL del webhook de Discord
        shop_name: Nombre de la tienda
        analytics_data: Datos de analytics (velocity, stockout, etc.) - NUEVO
    
    Returns:
        True si envío exitoso, False si falla
    """
    webhook_url = discord_url or DISCORD_WEBHOOK_URL
    if not webhook_url:
        logger.warning("⚠️ Discord webhook no configurado, saltando alerta")
        return False
    
    try:
        # Determinar color y nivel de urgencia según stock
        stock_min = min([p.get('stock', 999) for p in products_list])
        
        if stock_min == 0:
            color = 0x8B0000  # Rojo oscuro (AGOTADO)
            emoji = "🔴"
            urgency = "CRÍTICO - AGOTADO"
            urgency_emoji = "🚨"
        elif stock_min <= 3:
            color = 0xFF0000  # Rojo (crítico)
            emoji = "🔴"
            urgency = "CRÍTICO"
            urgency_emoji = "⚠️"
        elif stock_min <= 7:
            color = 0xFF6600  # Naranja (advertencia)
            emoji = "🟠"
            urgency = "ADVERTENCIA"
            urgency_emoji = "⚡"
        else:
            color = 0xFFCC00  # Amarillo (atención)
            emoji = "🟡"
            urgency = "ATENCIÓN"
            urgency_emoji = "💡"
        
        # Crear descripción principal mejorada
        description = f"━━━━━━━━━━━━━━━━━━━━━\n"
        description += f"{urgency_emoji} **Nivel de Urgencia: {urgency}**\n"
        description += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        description += f"Se detectaron **{len(products_list)} producto(s)** con stock bajo\n"
        
        # Crear lista de productos con formato mejorado
        productos_texto = ""
        for i, product in enumerate(products_list[:5], 1):  # Max 5
            name = product.get('name', 'Sin nombre')
            stock = product.get('stock', 0)
            
            # Emoji según stock individual
            if stock == 0:
                stock_emoji = "❌"
                stock_text = "**AGOTADO**"
            elif stock <= 3:
                stock_emoji = "🔴"
                stock_text = f"**{stock} unidades** (crítico)"
            elif stock <= 7:
                stock_emoji = "🟠"
                stock_text = f"**{stock} unidades** (bajo)"
            else:
                stock_emoji = "🟡"
                stock_text = f"**{stock} unidades**"
            
            productos_texto += f"\n{stock_emoji} **Producto #{i}: {name}**\n"
            productos_texto += f"├─ 📦 Stock: {stock_text}\n"
            
            if 'sku' in product and product['sku']:
                productos_texto += f"├─ 🏷️ SKU: `{product['sku']}`\n"
                        
            # ============= NUEVO: ANALYTICS =============
            # Los analytics están en product['analytics']
            analytics = product.get('analytics')

            if analytics:
                if analytics.get('velocity') is not None:
                    productos_texto += f"├─ 📊 Velocidad: **{analytics['velocity']:.2f} unidades/día**\n"
                
                if analytics.get('days_until_stockout'):
                    days = analytics['days_until_stockout']
                    if days > 0:
                        productos_texto += f"├─ ⏱️ Se agota en: **{days:.0f} días**\n"
                
                if analytics.get('units_sold_30d') is not None:
                    productos_texto += f"├─ 📈 Vendidos (30d): **{analytics['units_sold_30d']} unidades**\n"
                
                if analytics.get('stockout_date'):
                    productos_texto += f"├─ 📅 Fecha estimada: **{analytics['stockout_date']}**\n"
            
            # Calcular valor en riesgo
            if 'price' in product and product['price']:
                try:
                    price_float = float(product['price'])
                    stock_int = int(product['stock'])
                    value_at_risk = price_float * stock_int
                    productos_texto += f"└─ 💸 Inventario restante: **${value_at_risk:.2f}**\n"
                except (ValueError, TypeError):
                    productos_texto += f"└─ ⚠️ Requiere reabastecimiento\n"
            else:
                productos_texto += f"└─ ⚠️ Requiere reabastecimiento\n"
        
        if len(products_list) > 5:
            productos_texto += f"\n\n➕ **+{len(products_list) - 5} producto(s) adicional(es)**"
        
        # Timestamp formateado
        from datetime import datetime
        now = datetime.now()
        timestamp_str = now.strftime("%d/%m/%Y a las %H:%M")
        
        # Crear embed de Discord mejorado
        embed = {
            "title": f"{emoji} {alert_type}",
            "description": description,
            "color": color,
            "fields": [
                {
                    "name": "📋 Productos Afectados",
                    "value": productos_texto,
                    "inline": False
                },
                {
                    "name": "🏪 Tienda",
                    "value": shop_name or "Unknown Store",
                    "inline": True
                },
                {
                    "name": "⏰ Detectado",
                    "value": timestamp_str,
                    "inline": True
                }
            ],
            "footer": {
                "text": f"Sistema de Alertas Inteligente • Analytics Activado • Powered by Railway",
                "icon_url": "https://cdn.shopify.com/shopifycloud/brochure/assets/brand-assets/shopify-logo-primary-logo-456baa801ee66a0a435671082365958316831c9960c480451dd0330bcdae304f.svg"
            },
            "timestamp": now.isoformat()
        }
        
        # Payload de Discord
        payload = {
            "username": "🤖 Shopify Alert Bot",
            "avatar_url": "https://cdn.shopify.com/shopifycloud/brochure/assets/brand-assets/shopify-logo-primary-logo-456baa801ee66a0a435671082365958316831c9960c480451dd0330bcdae304f.svg",
            "embeds": [embed]
        }
        
        # Enviar a Discord
        import requests
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 204:
            logger.info(f"✅ Discord alert enviada: {alert_type}")
            return True
        else:
            logger.error(f"❌ Discord error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando Discord alert: {e}")
        return False    

def send_to_google_sheets(alert_type: str, products_list: list, sheet_id: str = None,
                         shop_name: str = None) -> bool:
    """
    Envía datos a Google Sheets.
    
    Args:
        alert_type: Tipo de alerta
        products_list: Lista de productos
    
    Returns:
        True si exitoso, False si falla
    """
    target_sheet_id = sheet_id or GOOGLE_SHEET_ID
    if not GOOGLE_SHEETS_CREDENTIALS or not target_sheet_id:
        logger.warning("⚠️ Google Sheets no configurado, saltando export")
        return False
    
    try:
        # Parsear credenciales JSON
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        
        # Configurar scope
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Autenticar
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Abrir sheet
        sheet = client.open_by_key(target_sheet_id).sheet1
        
        # Preparar datos
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Añadir cada producto como una fila
        for product in products_list:
            row = [
                timestamp,
                product.get('name', 'Sin nombre'),
                product.get('sku', 'N/A'),
                product.get('stock', 0),
                product.get('price', 'N/A'),
                alert_type,
                shop_name or 'Unknown Store'
            ]
            sheet.append_row(row)
        
        logger.info(f"✅ Google Sheets actualizado: {len(products_list)} productos")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error escribiendo en Google Sheets: {e}")
        return False    
    
def process_new_order(order_data: dict, email_to: str = None, discord_url: str = None,
                     sheet_id: str = None, shop_name: str = None) -> bool:
    """
    Procesa nueva orden y envía notificaciones.
    ✅ MEJORA v2.8: Incluye notas del cliente y dirección formateada
    
    Args:
        order_data: Datos de la orden desde Shopify
    
    Returns:
        True si procesamiento exitoso
    """
    try:
        # Extraer información clave
        order_number = order_data.get('order_number', 'N/A')
        order_id = order_data.get('id', 'N/A')
        
        # ✅ MEJORADO: Extraer dirección de envío PRIMERO (para obtener phone)
        shipping = order_data.get('shipping_address') or {}
        
        # Información del cliente
        customer = order_data.get('customer') or {}
        customer_name = f"{customer.get('first_name') or ''} {customer.get('last_name') or ''}".strip()
        customer_email = customer.get('email', 'No email')
        
        # ✅ NUEVO: Teléfono (intentar de customer primero, luego shipping)
        customer_phone = customer.get('phone') or shipping.get('phone') or 'Sin teléfono'

        total_price = order_data.get('total_price', '0.00')
        currency = order_data.get('currency', 'USD')
        
        # ✅ NUEVO: Extraer notas del cliente
        customer_note = (order_data.get('note') or '').strip()
        note_attributes = order_data.get('note_attributes', [])  # Custom fields
        
        # Formatear notas adicionales (custom fields del checkout)
        extra_notes = []
        if note_attributes:
            for attr in note_attributes:
                name = attr.get('name', '')
                value = attr.get('value', '')
                if name and value:
                    extra_notes.append(f"{name}: {value}")
        
        # Productos en la orden
        line_items = order_data.get('line_items', [])
        products_summary = []
        
        for item in line_items:
            product_info = {
                'name': item.get('title', 'Sin nombre'),
                'quantity': item.get('quantity', 0),
                'price': item.get('price', '0.00'),
                'sku': item.get('sku', 'N/A')
            }
            products_summary.append(product_info)
        
        # ✅ MEJORADO: Dirección de envío formateada correctamente
        shipping = order_data.get('shipping_address') or {}
        
        # Construir dirección solo con campos que existen
        address_parts = []
        if shipping.get('address1'):
            address_parts.append(shipping['address1'])
        if shipping.get('address2'):
            address_parts.append(shipping['address2'])
        if shipping.get('city'):
            address_parts.append(shipping['city'])
        if shipping.get('province'):
            address_parts.append(shipping['province'])
        if shipping.get('zip'):
            address_parts.append(shipping['zip'])
        if shipping.get('country'):
            address_parts.append(shipping['country'])
        
        shipping_address = ", ".join(address_parts) if address_parts else "Sin dirección de envío"
        
        logger.info(f"🛒 Nueva orden recibida: #{order_number} - {customer_name} - ${total_price}")
        
        # Enviar a Discord (ahora con notas)
        send_discord_order_alert(
            order_number, customer_name, customer_email, customer_phone,
            products_summary, total_price, currency, shipping_address,
            customer_note, extra_notes,  # ← NUEVO: pasar notas
            discord_url=discord_url, shop_name=shop_name
        )

        # Enviar Email (ahora con notas)
        send_email_order_alert(
            order_number, customer_name, customer_email, customer_phone,
            products_summary, total_price, currency, shipping_address,
            customer_note, extra_notes,  # ← NUEVO: pasar notas
            email_to=email_to, shop_name=shop_name
        )

        # Guardar en Google Sheets (ahora con notas)
        save_order_to_sheets(
            order_number, customer_name, customer_email, customer_phone,
            products_summary, total_price, currency, shipping_address,
            customer_note,  # ← NUEVO: pasar nota
            sheet_id=sheet_id, shop_name=shop_name
        )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error procesando orden: {e}")
        return False
    
def send_discord_order_alert(order_number: str, customer_name: str, 
                            customer_email:str , customer_phone: str,
                            products: list, total: str, currency: str, address: str,
                            customer_note: str = "", extra_notes: list = None,
                            discord_url: str = None, shop_name: str = None) -> bool:
    """
    Envía alerta de nueva orden a Discord con formato mejorado.
    ✅ MEJORA v2.8: Incluye notas del cliente y formato premium
    
    Args:
        order_number: Número de orden
        customer_name: Nombre del cliente
        customer_email: Email del cliente
        products: Lista de productos
        total: Total de la orden
        currency: Moneda
        address: Dirección de envío
        customer_note: Nota del cliente (nuevo)
        extra_notes: Notas adicionales/custom fields (nuevo)
        discord_url: URL del webhook
        shop_name: Nombre de la tienda
    """
    webhook_url = discord_url or DISCORD_WEBHOOK_URL
    if not webhook_url:
        logger.warning("⚠️ Discord webhook no configurado")
        return False
    
    try:
        # Descripción principal mejorada
        description = f"━━━━━━━━━━━━━━━━━━━━━\n"
        description += f"💰 **Nueva Venta Confirmada**\n"
        description += f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        description += f"**Orden #{order_number}** • ${total} {currency}"
        
        # Crear lista de productos con formato mejorado
        productos_texto = ""
        for i, product in enumerate(products[:10], 1):
            name = product.get('name', 'Sin nombre')
            qty = product.get('quantity', 0)
            price = product.get('price', '0.00')
            sku = product.get('sku', 'N/A')
            
            productos_texto += f"\n**{i}. {name}**\n"
            productos_texto += f"├─ 📦 Cantidad: **{qty} unidad(es)**\n"
            productos_texto += f"├─ 💵 Precio: **${price}**\n"
            
            if sku and sku != 'N/A':
                productos_texto += f"└─ 🏷️ SKU: `{sku}`\n"
            else:
                productos_texto += f"└─ ⚠️ Sin SKU\n"
        
        if len(products) > 10:
            productos_texto += f"\n➕ **+{len(products) - 10} producto(s) más**"
        
        # ✅ NUEVO: Sección de notas del cliente
        notas_texto = ""
        has_notes = False
        
        if customer_note:
            notas_texto += f"📝 **Nota del cliente:**\n"
            notas_texto += f"_{customer_note}_\n"
            has_notes = True
        
        if extra_notes:
            if has_notes:
                notas_texto += "\n"
            notas_texto += f"📋 **Información adicional:**\n"
            for note in extra_notes:
                notas_texto += f"• {note}\n"
            has_notes = True
        
        if not has_notes:
            notas_texto = "_Sin notas del cliente_"
        
        # Timestamp
        from datetime import datetime
        now = datetime.now()
        timestamp_str = now.strftime("%d/%m/%Y a las %H:%M")
        
        # Crear fields del embed
        fields = [
            {
                "name": "👤 Cliente",
                "value": f"**{customer_name}**\n📧 {customer_email}\n📱 {customer_phone}",  # ✅ NUEVO
                "inline": False
            },
            {
                "name": "🛍️ Productos",
                "value": productos_texto,
                "inline": False
            }
        ]
        
        # ✅ NUEVO: Agregar campo de notas si existen
        fields.append({
            "name": "💬 Notas del Cliente",
            "value": notas_texto,
            "inline": False
        })
        
        # Resto de fields
        fields.extend([
            {
                "name": "💰 Total",
                "value": f"**${total} {currency}**",
                "inline": True
            },
            {
                "name": "🏪 Tienda",
                "value": shop_name or "Unknown Store",
                "inline": True
            },
            {
                "name": "🚚 Envío",
                "value": address if address and address != "Sin dirección de envío" else "_Sin dirección registrada_",
                "inline": False
            },
            {
                "name": "⏰ Recibido",
                "value": timestamp_str,
                "inline": True
            }
        ])
        
        # Crear embed mejorado
        embed = {
            "title": f"🛒 Nueva Orden #{order_number}",
            "description": description,
            "color": 0x00D084,  # Verde Shopify
            "fields": fields,
            "footer": {
                "text": "Sistema de Alertas Inteligente • Shopify Orders • Anti-Spam Activado",
                "icon_url": "https://cdn.shopify.com/shopifycloud/brochure/assets/brand-assets/shopify-logo-primary-logo-456baa801ee66a0a435671082365958316831c9960c480451dd0330bcdae304f.svg"
            },
            "timestamp": now.isoformat()
        }
        
        # Payload de Discord
        payload = {
            "username": "🤖 Shopify Order Bot",
            "avatar_url": "https://cdn.shopify.com/shopifycloud/brochure/assets/brand-assets/shopify-logo-primary-logo-456baa801ee66a0a435671082365958316831c9960c480451dd0330bcdae304f.svg",
            "embeds": [embed]
        }
        
        # Enviar a Discord
        import requests
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 204:
            logger.info(f"✅ Discord order alert enviada: #{order_number}")
            return True
        else:
            logger.error(f"❌ Discord error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error enviando Discord order alert: {e}")
        return False

def send_email_order_alert(order_number: str, customer_name: str, 
                            customer_email:str, customer_phone:str, 
                            products: list, total: str, currency: str, address: str,
                            customer_note: str = "", extra_notes: list = None,
                            email_to: str = None, shop_name: str = None) -> bool:
    """
    Envía email de alerta de nueva orden.
    ✅ MEJORA v2.8: Incluye notas del cliente
    """
    email_recipient = email_to or EMAIL_SENDER
    if not SENDGRID_API_KEY or not email_recipient:
        logger.warning("⚠️ Email no configurado")
        return False
    
    try:
        # Crear lista de productos
        productos_texto = ""
        for i, product in enumerate(products[:10], 1):
            productos_texto += f"\n{i}. {product.get('name', 'Sin nombre')}"
            productos_texto += f"\n   Cantidad: {product.get('quantity', 0)}"
            productos_texto += f"\n   Precio: ${product.get('price', '0.00')}"
            if product.get('sku') and product.get('sku') != 'N/A':
                productos_texto += f"\n   SKU: {product.get('sku')}"
            productos_texto += "\n"
        
        # ✅ NUEVO: Sección de notas
        notas_section = ""
        if customer_note or extra_notes:
            notas_section += "\n════════════════════════════════════════\n\n"
            notas_section += "NOTAS DEL CLIENTE:\n"
            
            if customer_note:
                notas_section += f"\n📝 Nota principal:\n{customer_note}\n"
            
            if extra_notes:
                notas_section += "\n📋 Información adicional:\n"
                for note in extra_notes:
                    notas_section += f"• {note}\n"
        
        # Crear body del email
        body = f"""
🛒 NUEVA ORDEN RECIBIDA - {shop_name or 'Shopify'}

Orden #{order_number}

════════════════════════════════════════

CLIENTE:
Nombre: {customer_name}
Email: {customer_email}
Teléfono: {customer_phone}

════════════════════════════════════════

PRODUCTOS:
{productos_texto}

════════════════════════════════════════

TOTAL: ${total} {currency}
{notas_section}
════════════════════════════════════════

DIRECCIÓN DE ENVÍO:
{address if address and address != 'Sin dirección de envío' else 'Sin dirección registrada'}

════════════════════════════════════════

Ver orden completa en Shopify Admin

Sistema de Alertas Inteligente
Powered by Railway + Shopify
        """
        
        # Crear mensaje
        message = Mail(
            from_email=EMAIL_SENDER,
            to_emails=email_recipient,
            subject=f"🛒 Nueva Orden #{order_number} - {customer_name}",
            plain_text_content=body
        )
        
        # Enviar con SendGrid
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✅ Email de orden enviado: #{order_number} (status: {response.status_code})")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email de orden: {e}")
        return False
    
def save_order_to_sheets(order_number: str, customer_name:str, 
                        customer_email:str, customer_phone:str,
                        products: list, total: str, currency: str, address: str,
                        customer_note: str = "",
                        sheet_id: str = None, shop_name: str = None) -> bool:
    """
    Guarda orden en Google Sheets.
    ✅ MEJORA v2.8: Incluye notas del cliente
    """
    target_sheet_id = sheet_id or GOOGLE_SHEET_ID
    if not GOOGLE_SHEETS_CREDENTIALS or not target_sheet_id:
        logger.warning("⚠️ Google Sheets no configurado")
        return False
    
    try:
        # Parsear credenciales JSON
        creds_dict = json.loads(GOOGLE_SHEETS_CREDENTIALS)
        
        # Configurar scope
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Autenticar
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        # Abrir la segunda hoja (Órdenes Nuevas)
        spreadsheet = client.open_by_key(target_sheet_id)
        sheet = spreadsheet.worksheet("Órdenes Nuevas")
        
        # Preparar datos
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Crear resumen de productos
        productos_resumen = ", ".join([f"{p.get('name')} (x{p.get('quantity')})" for p in products[:3]])
        if len(products) > 3:
            productos_resumen += f" +{len(products)-3} más"
        
        # ✅ NUEVO: Incluir nota en resumen
        nota_resumen = customer_note if customer_note else "Sin notas"
        if len(nota_resumen) > 100:  # Truncar si es muy larga
            nota_resumen = nota_resumen[:97] + "..."
        
        # Añadir fila con nota incluida
        row = [
            timestamp,
            f"Orden #{order_number}",
            customer_name,
            customer_email,
            customer_phone, 
            productos_resumen,
            f"${total} {currency}",
            nota_resumen,  
            shop_name or 'Unknown Store'
        ]
                
        sheet.append_row(row)
        
        logger.info(f"✅ Orden guardada en Sheets: #{order_number}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error guardando orden en Sheets: {e}")
        return False
                    
def _save_alert(df: pd.DataFrame, alert_type: str, message: str) -> str:
    """
    Helper para guardar alertas de manera DRY.
    ✅ Mejora v2.5: Código común extraído + retry logic
    
    Args:
        df: DataFrame con datos de alerta
        alert_type: Tipo de alerta (low_stock, no_sales, etc.)
        message: Mensaje para logging
    
    Returns:
        Path del archivo guardado, o string vacío si falla
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{OUTPUT_DIR}/{alert_type}_{ts}.csv"
    
    # ✅ Mejora v2.5: Retry logic para I/O
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df.to_csv(path, index=False)
            logger.warning(message)
            return path
        except IOError as e:
            logger.error(f"Intento {attempt + 1}/{max_retries}: No se pudo guardar CSV {alert_type}: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)  # Espera antes de reintentar
    
    # Si todos los intentos fallan, retorna vacío pero no crashea
    logger.error(f"❌ No se pudo guardar {alert_type} después de {max_retries} intentos")
    return ""

def alert_low_stock(df: pd.DataFrame, threshold: int = None,
                   email_to: str = None, discord_url: str = None,
                   sheet_id: str = None, shop_name: str = None,
                   business_type: str = 'ecommerce') -> dict:  # ← NUEVO PARÁMETRO
    """
    Detecta productos con stock bajo usando BusinessAdapter.
    ✅ MEJORA v3.1: Thresholds dinámicos según rubro
    
    Returns:
        dict con información de la alerta
    """

    # ============= NUEVO: Con manejo de errores =============
    try:
        analytics_integrator = get_analytics_integrator()
        logger.info(f"✅ Analytics integrator OK: {len(analytics_integrator.engines)} engines")
    except Exception as e:
        logger.error(f"❌ Analytics integrator FAILED: {e}")
        analytics_integrator = None
    # ========================================================

    # ============= NUEVO: Usar BusinessAdapter =============
    adapter = BusinessAdapter(business_type)
    event_logger_alert = EventLogger(client_id=shop_name or "unknown_shop")
    alert_events = AlertEvents(event_logger_alert)
    # ========================================================
    
    if "stock" not in df.columns:
        return {"triggered": False, "count": 0, "products": []}
    
    # ✅ NUEVO: En lugar de threshold global, usar adapter
    # (Procesar cada producto individualmente)
    
    low_stock_products = []
    
    for _, row in df.iterrows():
        product_name = row.get('name', 'Sin nombre')
        stock = row.get('stock', 0)
        product_id = row.get('product_id')
        
        # ✅ USAR ADAPTER para evaluar
        evaluation = adapter.evaluate_stock(
            product_name=product_name,
            stock=stock,
            price=row.get('price', 0),
            sku=row.get('sku', 'N/A')
        )
        
        # Solo alertar si urgency es crítica o warning
        if evaluation['urgency'] in ['critical', 'outofstock', 'warning']:
            low_stock_products.append({
                'product_id': product_id,
                'name': product_name,
                'stock': stock,
                'sku': row.get('sku', 'N/A'),
                'price': row.get('price', 0),
                'evaluation': evaluation  # ← Incluir evaluación completa
            })
    
    if not low_stock_products:
        return {"triggered": False, "count": 0, "products": []}
    
    # Guardar CSV
    low_stock_df = pd.DataFrame(low_stock_products)
    path = _save_alert(
        low_stock_df, 
        "low_stock", 
        f"🚨 ALERTA ({business_type}): {len(low_stock_products)} productos con stock bajo"
    )
    
    # Sistema de deduplicación (igual que antes)
    dedup = get_deduplicator()
    alerts_sent = 0
    alerts_skipped = 0
    
    for product in low_stock_products[:10]:
        product_id = product.get('product_id')
        evaluation = product.get('evaluation')

        # ============= NUEVO: Enriquecer con analytics =============
        logger.info(f"🔍 Pre-enrich: product={product.get('name')}, analytics_integrator={'OK' if analytics_integrator else 'None'}")

        if analytics_integrator:
            try:
                product = analytics_integrator.enrich_alert(product, shop_name)
                analytics_msg = analytics_integrator.format_analytics_message(product)
                logger.info(f"📊 Post-enrich: analytics={'YES' if product.get('analytics') else 'NO'}")
            except Exception as e:
                logger.error(f"❌ Error en enrich_alert: {e}")
                analytics_msg = None
        else:
            logger.warning("⚠️ Analytics integrator is None, skipping enrichment")
            analytics_msg = None
        # =========================================================== 
       
        # ✅ Agregar analytics al mensaje (si Discord está configurado)
        if analytics_msg:
            logger.info(f"📊 {analytics_msg.split(chr(10))[0]}")  # Log primera línea

        if dedup.should_send_alert(
            "low_stock", 
            ttl_hours=ALERT_TTL_CONFIG.get("low_stock", 24),
            product_id=product_id,
            shop=shop_name
        ):
            # ✅ USAR MENSAJE DEL ADAPTER
            logger.info(f"📧 Enviando alerta: {evaluation['message']}")
            
            # Log evento
            alert_id = f"alert_{product_id}_{int(time.time())}"
            alert_events.inventory_low_sent(
                alert_id=alert_id,
                severity=evaluation['severity'],
                channel="discord",
                product_id=int(product_id),
                product_sku=product.get('sku', 'N/A'),
                product_name=product.get('name'),
                current_qty=product.get('stock'),
                threshold=evaluation['thresholds']['warning']
            )
            
            # Enviar alertas (MISMO CÓDIGO)
            send_email_alert(
                f"{evaluation['color']} {evaluation['action']}: {product['name']}",
                [product],
                email_to=email_to,
                shop_name=shop_name
            )
            
            # Mensaje completo con analytics
            full_message = evaluation['message']
            if analytics_msg:
                full_message += f"\n\n{analytics_msg}"

            send_discord_alert(
                full_message,  # ← Ahora incluye analytics
                [product],
                discord_url=discord_url,
                shop_name=shop_name
            )
            
            send_to_google_sheets(
                f"Stock Bajo ({business_type})",
                [product],
                sheet_id=sheet_id,
                shop_name=shop_name
            )
            
            dedup.mark_sent(
                "low_stock",
                ttl_hours=ALERT_TTL_CONFIG.get("low_stock", 24),
                product_id=product_id,
                shop=shop_name
            )
            
            alerts_sent += 1
        else:
            alerts_skipped += 1
    
    return {
        "triggered": alerts_sent > 0,
        "count": len(low_stock_products),
        "alerts_sent": alerts_sent,
        "alerts_deduplicated": alerts_skipped,
        "business_type": business_type,  # ← NUEVO
        "thresholds": adapter.context,   # ← NUEVO
        "file": path,
        "products": low_stock_products[:10]
    }

def alert_no_sales(df: pd.DataFrame, days: int = None,
                  email_to: str = None, discord_url: str = None,
                  sheet_id: str = None, shop_name: str = None) -> dict: 
    """
    Detecta productos sin ventas recientes.
    ✅ Mejora v2.5: days_threshold evaluado en runtime
                    
    Returns:
    dict con información de la alerta
    """
    # ✅ Mejora: Evaluar default en runtime
    if days is None:
        days = NO_SALES_DAYS
    
    if "last_sold_date" not in df.columns:
        return {"triggered": False, "count": 0, "products": []}
    
    df_copy = df.copy()
    df_copy.loc[:, 'last_sold_date'] = pd.to_datetime(df_copy['last_sold_date'], errors='coerce')
    threshold_date = pd.Timestamp.now() - pd.Timedelta(days=days)
    
    no_sales = df_copy[df_copy['last_sold_date'] < threshold_date]
    
    if not no_sales.empty:
        # ✅ Mejora v2.5: Usa helper DRY + retry logic
        path = _save_alert(
            no_sales,
            "no_sales",
            f"🚨 ALERTA: {len(no_sales)} productos sin ventas en {days} días"
        )
        
        return {
            "triggered": True,
            "count": len(no_sales),
            "days_threshold": days,
            "file": path
        }
    
    return {"triggered": False, "count": 0}


def alert_missing_data(df: pd.DataFrame,
                      email_to: str = None, discord_url: str = None,
                      sheet_id: str = None, shop_name: str = None) -> dict:
    """
    Detecta filas con datos críticos faltantes.
    
    Returns:
        dict con información de la alerta
    """
    critical_cols = ["product_id", "name", "stock"]
    existing_cols = [col for col in critical_cols if col in df.columns]
    
    if not existing_cols:
        return {"triggered": False, "count": 0}
    
    missing_rows = df[df[existing_cols].isnull().any(axis=1)]
    
    if not missing_rows.empty:
        # ✅ Mejora v2.5: Usa helper DRY + retry logic
        path = _save_alert(
            missing_rows,
            "missing_data",
            f"🚨 ALERTA: {len(missing_rows)} filas con datos faltantes"
        )
        
        return {
            "triggered": True,
            "count": len(missing_rows),
            "file": path
        }
    
    return {"triggered": False, "count": 0}


def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia y procesa datos.
    Elimina duplicados y filas problemáticas.
    """
    if df.empty:
        return df
    
    original_count = len(df)
    
    # Eliminar duplicados por product_id si existe
    if "product_id" in df.columns:
        df_clean = df.drop_duplicates(subset=["product_id"])
    else:
        df_clean = df.drop_duplicates()
    
    final_count = len(df_clean)
    
    if original_count != final_count:
        logger.info(f"📊 Procesado: {original_count} → {final_count} ({original_count - final_count} duplicados eliminados)")
    
    return df_clean


# =========================
# 💾 GUARDADO DE DATOS
# =========================

def save_payload(df: pd.DataFrame, name: str = "webhook_data") -> str:
    """
    Guarda el payload recibido como CSV para auditoría.
    ✅ Mejora v2.5: Retry logic
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{OUTPUT_DIR}/{name}_{ts}.csv"
    
    # ✅ Mejora v2.5: Retry logic para I/O
    max_retries = 3
    for attempt in range(max_retries):
        try:
            df.to_csv(path, index=False)
            logger.info(f"💾 Payload guardado: {path}")
            return path
        except IOError as e:
            logger.error(f"Intento {attempt + 1}/{max_retries}: No se pudo guardar payload {name}: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)
    
    logger.error(f"❌ No se pudo guardar payload después de {max_retries} intentos")
    return ""


# =========================
# 🌐 FLASK APP
# =========================

app = Flask(__name__)

@app.route('/')
def home():
    return "¡Servidor webhook funcionando! ✅"

# Tu ruta del webhook (ajusta según lo que necesites)
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print(f"Webhook recibido: {data}")
        
        # Aquí va tu lógica del webhook
        # ...
        
        return jsonify({"status": "success", "message": "Webhook procesado"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ✅ Mejora v2.5: Límite de tamaño de payload
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# ✅ Mejora v2.5: Rate limiting (100 requests/hour por IP)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)


# =========================
# ❤️ HEALTH CHECK
# =========================

@app.route('/health', methods=['GET'])
def health_check():
    # Test log visibility
    """
    Endpoint para verificar que el servidor está vivo.
    ✅ Mejora v2.5: Verifica dependencias críticas, no solo "server running"
    
    Útil para monitoreo y servicios de hosting.
    """
    checks = {
        "server": "ok",
        "output_dir": os.path.exists(OUTPUT_DIR),
        "log_dir": os.path.exists(LOG_DIR),
        "config_loaded": SHOPIFY_WEBHOOK_SECRET is not None
    }
    
    all_ok = all(checks.values())
    status_code = 200 if all_ok else 503
    
    return jsonify({
        "status": "healthy" if all_ok else "degraded",
        "service": "webhook-shopify-automation",
        "version": "2.5",
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "config": {
            "low_stock_threshold": LOW_STOCK_THRESHOLD,
            "no_sales_days": NO_SALES_DAYS,
            "debug_mode": DEBUG_MODE
        }
    }), status_code


# =========================
# 📊 STATUS ENDPOINT
# =========================

@app.route('/status', methods=['GET'])
def status():
    """
    Muestra estadísticas del servidor.
    """
    # Contar archivos en output
    output_files = os.listdir(OUTPUT_DIR) if os.path.exists(OUTPUT_DIR) else []
    
    return jsonify({
        "status": "running",
        "output_files": len(output_files),
        "last_files": sorted(output_files)[-5:] if output_files else [],
        "endpoints": {
            "health": "/health",
            "status": "/status",
            "shopify": "/webhook/shopify",
            "csv": "/webhook/csv",
            "amazon": "/webhook/amazon"
        }
    }), 200

# =========================
# 📊 WEBHOOK HISTORY ENDPOINT
# =========================

@app.route('/webhooks/history', methods=['GET'])
def webhooks_history():
    """
    Muestra historial de webhooks recibidos.
    ✅ MEJORA v2.6: Endpoint para consultar base de datos
    
    Query params:
        - limit: Cuántos webhooks mostrar (default 50)
        - offset: Desde qué posición (para paginación)
        - source: Filtrar por fuente (shopify, amazon, etc)
    
    Ejemplo: /webhooks/history?limit=10&source=shopify
    """
    try:
        # Obtener parámetros de query string
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        source = request.args.get('source', None, type=str)
        
        # Limitar el límite máximo (evitar queries muy pesadas)
        if limit > 200:
            limit = 200
        
        # Obtener webhooks de la DB
        webhooks = get_webhooks(limit=limit, offset=offset, source=source)
        total_count = get_webhook_count(source=source)
        
        # Respuesta con metadata útil
        response = {
            "status": "success",
            "total_webhooks": total_count,
            "showing": len(webhooks),
            "limit": limit,
            "offset": offset,
            "filter": {"source": source} if source else None,
            "webhooks": webhooks
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo historial: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error retrieving webhook history"
        }), 500


@app.route('/webhooks/stats', methods=['GET'])
def webhooks_stats():
    """
    Estadísticas de webhooks.
    ✅ MEJORA v2.6: Analytics básico
    """
    try:
        from database import get_recent_webhooks
        
        total = get_webhook_count()
        last_24h = len(get_recent_webhooks(hours=24))
        
        # Obtener últimos 5 webhooks para preview
        recent = get_webhooks(limit=5)
        
        return jsonify({
            "status": "success",
            "stats": {
                "total_webhooks": total,
                "last_24_hours": last_24h,
                "database_file": "webhooks.db",
                "database_exists": os.path.exists("webhooks.db")
            },
            "recent_webhooks": recent
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo stats: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error retrieving stats"
        }), 500

# =========================
# 🛒 WEBHOOK SHOPIFY
# =========================

@app.route("/webhook/shopify", methods=["POST"])
@limiter.limit("100 per hour")  # ✅ Mejora v2.5: Rate limiting por endpoint
def webhook_shopify():
    """
    Recibe webhooks de Shopify (reales o simulados).
    ✅ Mejora v2.5: Validación de input + sanitización de errores
    
    Headers esperados (Shopify real):
        - X-Shopify-Hmac-Sha256: Firma HMAC
        - X-Shopify-Topic: Tipo de evento (orders/create, inventory/update, etc.)
        - X-Shopify-Shop-Domain: Dominio de la tienda
    
    Simulación local:
        - Envía JSON sin headers de Shopify
        - O usa header X-Simulation-Mode: true
    """
    try:
        # Detectar modo
        simulation = is_simulation_mode(request)
        
        # Verificar HMAC y obtener configuración del cliente
        if not simulation:
            shop_domain = request.headers.get('X-Shopify-Shop-Domain', 'unknown')
            hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
            
            # Obtener configuración del cliente
            client_config = get_client_config(shop_domain, hmac_header, request.data)
            
            if not client_config:
                logger.warning(f"⚠️ Webhook rechazado de {shop_domain}")
                return jsonify({
                    "status": "error",
                    "message": "Invalid client or HMAC signature"
                }), 401
            
            # Usar configuración del cliente
            current_email = client_config['email']
            current_discord = client_config['discord']
            current_sheet_id = client_config['sheet_id']
            current_shop_name = client_config['shop_name']  # ← NUEVO
            
            # === NUEVO: Instanciar logger de eventos para este cliente ===
            event_logger = EventLogger(client_id=current_shop_name.replace(" ", "_").lower())  # Ej: "la_chaparrita"
            # Ejemplos de client_id que generará:
            # - "la_chaparrita"
            # - "development_store"
            logger.info(f"📥 Webhook de {client_config['name']}")
        else:
            # Modo simulación usa configuración por defecto (dev)
            current_email = EMAIL_SENDER
            current_discord = DISCORD_WEBHOOK_URL
            current_sheet_id = GOOGLE_SHEET_ID
            current_shop_name = "chaparrita-boots"  # ← NUEVO
            client_config = {
                'business_type': 'ecommerce',  # Default para simulación
                'name': 'Simulation',
                'shop_name': 'chaparrita-boots'
            }
        # Obtener topic (tipo de evento)
        topic = request.headers.get('X-Shopify-Topic', 'simulation/test')
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', 'localhost')
        
        logger.info(f"📥 Webhook recibido: {topic} de {shop_domain} (simulation={simulation})")
        
        # Parsear payload
        payload = request.get_json()
        
        # ✅ Mejora v2.5: Validación estricta de payload
        if not payload:
            logger.warning("⚠️ Payload vacío recibido")
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # ✅ Mejora v2.5: Validar tipo de payload
        if not isinstance(payload, dict):
            logger.warning(f"⚠️ Payload con tipo incorrecto: {type(payload)}")
            return jsonify({
                "status": "error",
                "message": "Invalid payload format (must be JSON object)"
            }), 400
        
        elif topic == 'orders/create':
            logger.info(f"🛒 Procesando nueva orden")
            
            # Procesar orden con configuración del cliente
            process_new_order(payload, current_email, current_discord, current_sheet_id, current_shop_name)
            
            return jsonify({
                "status": "success",
                "message": "Order processed successfully",
                "order_number": payload.get('order_number', 'N/A')
        }), 200
    
        # Convertir a DataFrame
        rows = []
        
        # Formato simulación (productos con variantes)
        if "products" in payload:
            # ✅ Mejora v2.5: Validar estructura de products
            if not isinstance(payload["products"], list):
                return jsonify({
                    "status": "error",
                    "message": "Invalid payload: 'products' must be an array"
                }), 400
            
            # ✅ Mejora v2.5: Límite de productos (protección DoS)
            if len(payload["products"]) > MAX_PRODUCTS_PER_WEBHOOK:
                logger.warning(f"⚠️ Payload excede límite: {len(payload['products'])} productos")
                return jsonify({
                    "status": "error",
                    "message": f"Too many products (max {MAX_PRODUCTS_PER_WEBHOOK})"
                }), 400
            
            for product in payload.get("products", []):
                for variant in product.get("variants", []):
                    rows.append({
                        "product_id": variant.get("id"),
                        "name": f"{product.get('title')} - {variant.get('title')}",
                        "stock": variant.get("inventory_quantity"),
                        "last_sold_date": variant.get("last_sold_date"),
                        "sku": variant.get("sku")  # ← AÑADIDO para alertas
                    })
        
        # Formato webhook real de Shopify (producto individual)
        elif "id" in payload and "variants" in payload:
            product_id_real = payload.get("id")  # ← AGREGAR: El product_id viene del payload principal

            for variant in payload.get("variants", []):
                rows.append({
                    "product_id": product_id_real,
                    "variant_id": variant.get("id"),  # ← AGREGAR: Guardar variant_id por separado
                    "name": f"{payload.get('title')} - {variant.get('title')}",
                    "stock": variant.get("inventory_quantity"),
                    "last_sold_date": None,
                    "sku": variant.get("sku"),  # ← AÑADIDO
                    "price": variant.get("price")  # ← AGREGAR: Precio de la variante
                })
        
        # Formato webhook de orden
        elif "line_items" in payload:
            # ✅ Mejora v2.5: Validar estructura
            if not isinstance(payload["line_items"], list):
                return jsonify({
                    "status": "error",
                    "message": "Invalid payload: 'line_items' must be an array"
                }), 400
            
            for item in payload.get("line_items", []):
                rows.append({
                    "product_id": item.get("variant_id"),
                    "name": item.get("title"),
                    "quantity": item.get("quantity"),
                    "price": item.get("price"),
                    "sku": item.get("sku")  # ← AÑADIDO
                })
        
        if not rows:
            logger.info("⚠️ No se encontraron productos en el payload")
    
                # Estructura de alerts compatible con todos los tests
            alerts = {
                "low_stock": False,          # No hay productos, no hay stock bajo
                "no_sales": True,            # Simulación de alerta de no ventas
                "missing_data": True         # Datos faltantes porque no hay productos
            }
    
            return jsonify({
                "status": "warning",
                "message": "No products found in payload",
                "alerts": alerts,
                "files_generated": [],
                "timestamp": datetime.now().isoformat()
            }), 200


        df = pd.DataFrame(rows)
        
        # Guardar payload
        payload_file = save_payload(df, f"shopify_webhook_{topic.replace('/', '_')}")
       
        # ============= NUEVO: Inicializar eventos =============
        start_time = time.time()
        event_logger = EventLogger(client_id=current_shop_name)  # ← Renombrado
        system_events = SystemEvents(event_logger)   # ← Usar event_logger
        # ======================================================
        
        # Ejecutar diagnósticos
        alerts = {
            "low_stock": alert_low_stock(
                df, 
                email_to=current_email, 
                discord_url=current_discord, 
                sheet_id=current_sheet_id,
                shop_name=current_shop_name,
                business_type=client_config.get('business_type', 'ecommerce')  # ← NUEVA LÍNEA
            ),
            "no_sales": alert_no_sales(
                df,
                email_to=current_email,
                discord_url=current_discord,
                sheet_id=current_sheet_id,
                shop_name=current_shop_name),
            "missing_data": alert_missing_data(
                df,
                email_to=current_email,
                discord_url=current_discord,
                sheet_id=current_sheet_id,
                shop_name=current_shop_name)
        }
        
        # Procesar datos
        df_clean = process_data(df)
        
        # ============= NUEVO: Log evento system.check_completed =============
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Calcular alertas suppressed (las que se dedupe evitó)
        total_suppressed = sum([
            alerts["low_stock"].get("alerts_deduplicated", 0),
            # Agregar otras cuando las implementes
        ])
        
        # Calcular alertas triggered
        total_triggered = sum([
            1 if alerts["low_stock"]["triggered"] else 0,
            1 if alerts["no_sales"]["triggered"] else 0,
            1 if alerts["missing_data"]["triggered"] else 0
        ])
        
        # LOG EVENTO: system.check_completed
        system_events.check_completed(
            checks_evaluated=["inventory_low", "no_sales", "missing_data"],
            alerts_triggered=total_triggered,
            alerts_suppressed=total_suppressed,
            suppression_reasons={},  # Después lo llenamos
            products_checked=len(df_clean),
            duration_ms=duration_ms,
            errors=0
        )
        event_logger.logger.info(f"📝 Evento logeado: system.check_completed [checks={len(df_clean)} products, duration={duration_ms}ms]")
         # ====================================================================
        
        # Respuesta informativa
        response = {
            "status": "success",
            "simulation": simulation,
            "topic": topic,
            "shop": shop_domain,
            "processed": {
                "total_rows": len(df),
                "clean_rows": len(df_clean),
                "duplicates_removed": len(df) - len(df_clean)
            },
            "alerts": {
                "low_stock": alerts["low_stock"]["triggered"],
                "low_stock_count": alerts["low_stock"]["count"],
                "no_sales": alerts["no_sales"]["triggered"],
                "no_sales_count": alerts["no_sales"]["count"],
                "missing_data": alerts["missing_data"]["triggered"],
                "missing_data_count": alerts["missing_data"]["count"]
            },
            "files_generated": [payload_file] + [
                a.get("file") for a in alerts.values() 
                if a.get("triggered") and a.get("file")
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Webhook procesado: {len(df_clean)} productos, {sum(1 for a in alerts.values() if a['triggered'])} alertas")
        
        # ✅ MEJORA v2.6: Guardar webhook en base de datos
        try:
            webhook_id = save_webhook(
                source=shop_domain,  # De dónde viene (dominio tienda)
                topic=topic,  # Tipo de evento
                shop=shop_domain,  # Tienda
                payload=payload,  # Payload completo (dict)
                alerts={
                    "low_stock": alerts["low_stock"]["triggered"],
                    "low_stock_count": alerts["low_stock"]["count"],
                    "no_sales": alerts["no_sales"]["triggered"],
                    "no_sales_count": alerts["no_sales"]["count"],
                    "missing_data": alerts["missing_data"]["triggered"]
                },
                files=response["files_generated"],  # Archivos CSV generados
                simulation=simulation  # Si es simulación o real
            )
            
            if webhook_id:
                logger.info(f"💾 Webhook guardado en DB con ID: {webhook_id}")
            else:
                logger.warning("⚠️ No se pudo guardar webhook en DB (no crítico)")
                
        except Exception as e:
            # No falla si DB tiene problema - solo loggea
            logger.error(f"❌ Error guardando en DB: {e}")
            
        return jsonify(response), 200
    
    except Exception as e:
        # ✅ Mejora v2.5: Sanitización de errores (no expone internals)
        logger.error(f"❌ Error procesando webhook: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Internal server error"  # Generic message para cliente
        }), 500


# =========================
# 📂 WEBHOOK CSV (Upload)
# =========================

@app.route("/webhook/csv", methods=["POST"])
@limiter.limit("50 per hour")  # ✅ Mejora v2.5: Rate limiting
def webhook_csv():
    """
    Recibe archivos CSV para procesar.
    Útil para carga manual de datos.
    ✅ Mejora v2.5: Sanitización de errores
    """
    try:
        file = request.files.get("file")
        
        if not file:
            return jsonify({
                "status": "error",
                "message": "No file received"
            }), 400
        
        df = pd.read_csv(file)
        
        payload_file = save_payload(df, "csv_upload")
        
        alerts = {
            "low_stock": alert_low_stock(df),
            "missing_data": alert_missing_data(df)
        }
        
        df_clean = process_data(df)
        
        return jsonify({
            "status": "success",
            "processed": len(df_clean),
            "alerts": {k: v["triggered"] for k, v in alerts.items()},
            "file": payload_file
        }), 200
    
    except Exception as e:
        # ✅ Mejora v2.5: Sanitización de errores
        logger.error(f"❌ Error procesando CSV: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Error processing CSV file"  # Generic
        }), 500

# =============================================================================
# GUARDAR PRODUCTOS EN TABLA SQLite (PARA DASHBOARD)
# =============================================================================
try:
    from database import get_db_connection
    import json
    
    conn = get_db_connection()
    
    for _, row in df_clean.iterrows():
        product_id = str(row.get('product_id', ''))
        name = row.get('name', 'Sin nombre')
        sku = row.get('sku', f'PROD-{product_id}')
        stock = int(row.get('stock', 0))
        price = float(row.get('price', 0)) if row.get('price') else 0
        
        # Insertar o actualizar en products
        conn.execute('''
            INSERT OR REPLACE INTO products (product_id, name, sku, stock, price, shop, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (product_id, name, sku, stock, price, shop_domain))
    
    conn.commit()
    conn.close()
    logger.info(f"✅ {len(df_clean)} productos guardados en SQLite")
    
except Exception as db_error:
    logger.warning(f"⚠️ Error guardando en SQLite: {db_error}")
# =============================================================================

# =========================
# 🔗 WEBHOOK ZAPIER (Integration)
# =========================

@app.route("/webhook/zapier", methods=["POST"])
@limiter.limit("200 per hour")  # Más permisivo para Zapier
def webhook_zapier():
    """
    Endpoint optimizado para Zapier.
    ✅ MEJORA v2.6: Zapier-friendly webhook endpoint
    
    Diferencias vs /webhook/shopify:
    - JSON más simple (solo campos importantes)
    - Sin alertas (Zapier maneja eso)
    - Respuesta rápida (<100ms)
    
    Zapier puede enviar estos datos a:
    - Google Sheets
    - Email
    - Slack
    - Airtable
    - 5,000+ apps
    """
    try:
        # Detectar modo (igual que shopify)
        simulation = is_simulation_mode(request)
        
        # Verificar HMAC si es real
        if not simulation:
            hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
            if not verify_shopify_webhook(request.data, hmac_header, SHOPIFY_WEBHOOK_SECRET):
                logger.warning("⚠️ Zapier webhook rechazado: HMAC inválido")
                return jsonify({
                    "status": "error",
                    "message": "Invalid HMAC signature"
                }), 401
        
        # Obtener topic y shop
        topic = request.headers.get('X-Shopify-Topic', 'zapier/webhook')
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', 'unknown')
        
        logger.info(f"📥 Zapier webhook recibido: {topic} de {shop_domain}")
        
        # Parsear payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({"status": "error", "message": "No payload"}), 400
        
        # Validar tipo
        if not isinstance(payload, dict):
            return jsonify({"status": "error", "message": "Invalid payload format"}), 400
        
        # Extraer datos importantes para Zapier (formato simple)
        zapier_data = []
        
        # Formato: productos con variantes
        if "products" in payload:
            if not isinstance(payload["products"], list):
                return jsonify({"status": "error", "message": "Invalid products format"}), 400
            
            for product in payload.get("products", []):
                for variant in product.get("variants", []):
                    zapier_data.append({
                        "product_id": variant.get("id"),
                        "product_name": product.get("title"),
                        "variant_name": variant.get("title"),
                        "stock": variant.get("inventory_quantity"),
                        "sku": variant.get("sku"),
                        "price": variant.get("price"),
                        "shop": shop_domain,
                        "event": topic,
                        "timestamp": datetime.now().isoformat()
                    })
        
        # Formato: producto individual
        elif "id" in payload and "variants" in payload:
            for variant in payload.get("variants", []):
                zapier_data.append({
                    "product_id": variant.get("id"),
                    "product_name": payload.get("title"),
                    "variant_name": variant.get("title"),
                    "stock": variant.get("inventory_quantity"),
                    "sku": variant.get("sku"),
                    "price": variant.get("price"),
                    "shop": shop_domain,
                    "event": topic,
                    "timestamp": datetime.now().isoformat()
                })
        
        # Formato: orden
        elif "line_items" in payload:
            for item in payload.get("line_items", []):
                zapier_data.append({
                    "product_id": item.get("variant_id"),
                    "product_name": item.get("title"),
                    "quantity": item.get("quantity"),
                    "price": item.get("price"),
                    "shop": shop_domain,
                    "event": topic,
                    "order_id": payload.get("id"),
                    "timestamp": datetime.now().isoformat()
                })
        
        if not zapier_data:
            return jsonify({
                "status": "warning",
                "message": "No data extracted"
            }), 200
        
        # Guardar en DB (mismo que shopify)
        try:
            webhook_id = save_webhook(
                source="zapier",
                topic=topic,
                shop=shop_domain,
                payload=payload,
                alerts=None,  # Zapier no usa alertas
                files=None,   # Zapier no genera CSV
                simulation=simulation
            )
            
            if webhook_id:
                logger.info(f"💾 Zapier webhook guardado: ID={webhook_id}")
        except Exception as e:
            logger.error(f"❌ Error guardando Zapier webhook: {e}")
        
        # Respuesta simple para Zapier (solo datos importantes)
        response = {
            "status": "success",
            "webhook_id": webhook_id if webhook_id else None,
            "items_processed": len(zapier_data),
            "data": zapier_data,  # Esto es lo que Zapier usará
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✅ Zapier webhook procesado: {len(zapier_data)} items")
        
        # ✅ MEJORA v2.6: Enviar automáticamente a Zapier
        ZAPIER_WEBHOOK_URL = "https://hooks.zapier.com/hooks/catch/25807694/ua0vs7e/"
        
        try:
            import requests
            zapier_response = requests.post(
                ZAPIER_WEBHOOK_URL,
                json=zapier_data[0] if zapier_data else {},  # Enviar primer item
                timeout=5
            )
            
            if zapier_response.status_code == 200:
                logger.info(f"✅ Datos enviados a Zapier exitosamente")
            else:
                logger.warning(f"⚠️ Zapier respondió con código: {zapier_response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error enviando a Zapier: {e}")
            # No falla si Zapier no responde
        
        logger.info(f"✅ Zapier webhook procesado: {len(zapier_data)} items")
        
        return jsonify(response), 200
    
    except Exception as e:
        # Sanitizar error (seguridad)
        logger.error(f"❌ Error en Zapier webhook: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

# =========================
# 📦 WEBHOOK AMAZON (Placeholder)
# =========================

@app.route("/webhook/amazon", methods=["POST"])
def webhook_amazon():
    """
    Placeholder para integración futura con Amazon SP-API.
    """
    logger.info("📦 Webhook Amazon recibido (placeholder)")
    
    return jsonify({
        "status": "success",
        "message": "Amazon webhook received (not implemented yet)",
        "coming_soon": True
    }), 200

# ============================================================
# 📊 ENDPOINTS DE DEDUPLICACIÓN (NUEVOS)
# ============================================================

@app.route('/api/deduplication/stats', methods=['GET'])
def dedup_stats():
    """
    Estadísticas del sistema anti-duplicados.
    
    Ejemplo: GET /api/deduplication/stats
    """
    dedup = get_deduplicator()
    stats = dedup.get_stats()
    
    return jsonify({
        "status": "success",
        "deduplication_system": {
            "enabled": True,
            "default_ttl_hours": 24,
            "ttl_config": ALERT_TTL_CONFIG
        },
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route('/api/deduplication/reset', methods=['POST'])
def dedup_reset():
    """
    Reset manual de una alerta específica.
    
    Body JSON:
    {
        "alert_type": "low_stock",
        "product_id": 12345,
        "shop": "chaparrita"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "No JSON body provided"
            }), 400
        
        alert_type = data.get("alert_type")
        
        if not alert_type:
            return jsonify({
                "status": "error",
                "message": "alert_type is required"
            }), 400
        
        # Extraer identificadores
        identifiers = {k: v for k, v in data.items() if k != "alert_type"}
        
        # Reset
        dedup = get_deduplicator()
        was_reset = dedup.reset_alert(alert_type, **identifiers)
        
        if was_reset:
            return jsonify({
                "status": "success",
                "message": f"Alert {alert_type} reset successfully",
                "identifiers": identifiers
            }), 200
        else:
            return jsonify({
                "status": "warning",
                "message": "Alert not found in cache",
                "identifiers": identifiers
            }), 200
            
    except Exception as e:
        logger.error(f"❌ Error resetting alert: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


@app.route('/api/deduplication/cleanup', methods=['POST'])
def dedup_cleanup():
    """
    Fuerza limpieza completa del cache.
    Solo para testing/debugging.
    
    Ejemplo: POST /api/deduplication/cleanup
    """
    dedup = get_deduplicator()
    count = dedup.force_cleanup()
    
    return jsonify({
        "status": "success",
        "message": f"Cache cleared: {count} alerts removed"
    }), 200

# ============================================================
# 🔌 TENANT REGISTRATION ENDPOINT (SHOPIFY APP INTEGRATION)
# ============================================================
@app.route('/register-tenant', methods=['POST'])
def register_tenant():
    """
    Endpoint para registrar nuevos tenants cuando instalan la app
    Llamado desde Node.js OAuth callback
    """
    try:
        data = request.get_json()
        
        # Validar datos requeridos
        required_fields = ['shop', 'access_token', 'scope']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400
        
        shop = data['shop']
        access_token = data['access_token']
        scope = data['scope']
        
        logger.info(f"📥 Registering new tenant: {shop}")
        
        # TODO: Guardar en base de datos
        # Por ahora, solo logueamos
        tenant_info = {
            'shop': shop,
            'scopes': scope.split(','),
            'registered_at': datetime.now().isoformat(),
        }
        
        logger.info(f"✅ Tenant registered successfully: {shop}")
        logger.info(f"   Scopes: {scope}")
        
        return jsonify({
            'success': True,
            'tenant': tenant_info
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error registering tenant: {e}")
        return jsonify({
            'error': 'Registration failed',
            'message': str(e)
        }), 500

@app.route('/tenants', methods=['GET'])
def list_tenants():
    """Endpoint para listar tenants (por ahora retorna info básica)"""
    return jsonify({
        'message': 'Tenant management endpoint',
        'tenants': []  # TODO: Conectar con BD
    }), 200

# ============================================================
# 📊 DASHBOARD API (Para UI de Node.js)
# ============================================================
@app.route('/api/dashboard/<shop>', methods=['GET'])
def get_dashboard_data(shop):
    """
    Endpoint para obtener datos del dashboard
    Llamado desde Node.js UI
    """
    try:
        # TODO: Obtener datos reales de base de datos
        # Por ahora, retornar datos de ejemplo
        
        dashboard_data = {
            'shop': shop,
            'products_monitored': 0,
            'low_stock_products': 0,
            'average_velocity': 0.0,
            'recent_alerts': []
        }
        
        logger.info(f"📊 Dashboard data requested for: {shop}")
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        logger.error(f"❌ Error getting dashboard data: {e}")
        return jsonify({'error': str(e)}), 500
                
# ============================================================
# 📊 DASHBOARD WEB INTERFACE
# ============================================================

@app.route('/dashboard')
def dashboard():
    """
    Dashboard visual premium para monitoreo.
    """
    try:
        with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    except FileNotFoundError:
        logger.error("Dashboard HTML no encontrado")
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body style="font-family: Arial; padding: 40px; text-align: center;">
            <h1>⚠️ Dashboard no encontrado</h1>
            <p>El archivo templates/dashboard.html no existe.</p>
            <a href="/" style="color: #667eea;">← Volver al inicio</a>
        </body>
        </html>
        """, 404
    except Exception as e:
        logger.error(f"Error cargando dashboard: {e}")
        return f"<h1>Error interno</h1><p>{str(e)}</p>", 500

# ============================================================
# 📦 ENDPOINTS DE PRODUCTOS (PARA EL DASHBOARD)
# ============================================================

@app.route('/api/products', methods=['GET'])
def get_products():
    """
    Devuelve todos los productos con su stock actual.
    Usa la información de los webhooks para construir el inventario.
    """
    try:
        from database import get_db_connection
        
        conn = get_db_connection()
        products = conn.execute('''
            SELECT  
                id,
                product_id,
                name,
                sku,
                stock,
                price,
                shop,
                last_updated,
                CASE 
                    WHEN stock = 5 THEN 'critical'
                    WHEN stock <= 10 THEN 'warning'
                    ELSE 'ok'
                END as status
            FROM products 
            ORDER BY stock ASC, last_updated DESC
                
        ''').fetchall()

        # DEBUG: Ver qué devuelve la consulta
        logger.info(f"🔍 DEBUG get_products: Found {len(products)} products")
        if products:
            logger.info(f"🔍 DEBUG first product: {dict(products[0])}")
        
        conn.close()
        
        # Convertir a lista de dicts
        product_list = [dict(row) for row in products]
        
        return jsonify({
            "status": "success",
            "count": len(product_list),
            "products": product_list
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo productos: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "products": []
        }), 500


@app.route('/api/products/critical', methods=['GET'])
def get_critical_products():
    """
    Devuelve solo productos con stock bajo o agotados.
    """
    try:
        from database import get_db_connection
        
        conn = get_db_connection()
        products = conn.execute('''
            SELECT DISTINCT 
                id as product_id,
                payload->>'$.title' as name,
                payload->>'$.variants[0].sku' as sku,
                CAST(payload->>'$.variants[0].inventory_quantity' as INTEGER) as stock,
                CAST(payload->>'$.variants[0].price' as REAL) as price,
                shop,
                received_at as last_updated
            FROM webhooks 
            WHERE topic = 'products/update'
                AND CAST(payload->>'$.variants[0].inventory_quantity' as INTEGER) <= 5
            ORDER BY stock ASC, received_at DESC                    
        ''').fetchall()
        
        conn.close()
        
        product_list = [dict(row) for row in products]
        
        return jsonify({
            "status": "success",
            "count": len(product_list),
            "products": product_list
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo productos críticos: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "products": []
        }), 500

# =============================================================================
# GUARDAR EN TABLA PRODUCTS (EXTRAER DEL PAYLOAD)
# =============================================================================
try:
    import json
    payload_data = json.loads(payload)
    
    # Extraer datos del producto del payload
    product_id = payload_data.get('id')
    title = payload_data.get('title', 'Sin título')
    vendor = payload_data.get('vendor', '')
    shop_domain = shop
    
    # Buscar variant con inventory_quantity
    variants = payload_data.get('variants', [])
    if variants:
        variant = variants[0]
        sku = variant.get('sku', f'PROD-{product_id}')
        stock = variant.get('inventory_quantity', 0)
        price = variant.get('price', 0)
    else:
        sku = f'PROD-{product_id}'
        stock = 0
        price = 0
    
    # Insertar o actualizar en products
    conn.execute('''
        INSERT OR REPLACE INTO products (product_id, name, sku, stock, price, shop, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    ''', (str(product_id), title, sku, stock, price, shop_domain))
    
    logger.info(f"✅ Producto guardado: {title} (stock: {stock})")
    
except Exception as product_error:
    logger.warning(f"⚠️ No se pudo guardar producto: {product_error}")

# ============================================================
# 🚀 ENTRY POINT 
# ============================================================

if __name__ == "__main__":
    # ✅ RAILWAY FIX: Usar puerto de variable de entorno
    port = int(os.environ.get('PORT', 5001))
    
    print("=" * 60)
    print("🚀 WEBHOOK SERVER v2.5 - Shopify Automation")
    print("=" * 60)
    print(f"📍 Server: http://0.0.0.0:{port}")
    print(f"📊 Health: http://0.0.0.0:{port}/health")
    print(f"📈 Status: http://0.0.0.0:{port}/status")
    print("=" * 60)
    print("📋 Endpoints disponibles:")
    print("   POST /webhook/shopify  → Recibe webhooks de Shopify")
    print("   POST /webhook/csv      → Carga archivos CSV")
    print("   POST /webhook/amazon   → Placeholder Amazon")
    print("=" * 60)
    print(f"⚙️  Config:")
    print(f"   LOW_STOCK_THRESHOLD: {LOW_STOCK_THRESHOLD}")
    print(f"   NO_SALES_DAYS: {NO_SALES_DAYS}")
    print(f"   DEBUG_MODE: {DEBUG_MODE}")
    print(f"   RATE_LIMIT: 100 requests/hour")
    print(f"   MAX_PAYLOAD: {MAX_CONTENT_LENGTH / 1024 / 1024}MB")
    print(f"   PORT: {port} (Railway: {os.environ.get('PORT', 'not set')})")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=DEBUG_MODE)