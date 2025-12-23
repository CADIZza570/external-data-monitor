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

# Importamos config y la función de validación centralizada
from config_shared import (
    SHOPIFY_WEBHOOK_SECRET,
    LOW_STOCK_THRESHOLD,
    NO_SALES_DAYS,
    DEBUG_MODE,
    OUTPUT_DIR,
    LOG_DIR,
    LOG_FILE,
    validate_config  # ✅ Mejora v2.1: validación centralizada
)

# =========================
# ⚙️ CONFIGURACIÓN GLOBAL
# =========================

# ✅ Mejora v2.5: Límite máximo de payload (protección DoS)
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
MAX_PRODUCTS_PER_WEBHOOK = 10000  # Límite de productos por request

# Ejecutamos validación al iniciar el servidor
# Esto asegura que cualquier error de config se detecte antes de levantar Flask
validate_config()  # 🔧 Mejora: self-check automático al iniciar

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
    Detecta si es una llamada de simulación (desarrollo local).
    En simulación, no verificamos HMAC.
    """
    # Si viene el header de Shopify, es real
    if request.headers.get('X-Shopify-Hmac-Sha256'):
        return False
    # Si viene de localhost, probablemente es simulación
    if request.remote_addr in ['127.0.0.1', 'localhost']:
        return True
    # Header especial para forzar simulación
    if request.headers.get('X-Simulation-Mode') == 'true':
        return True
    return False

# =========================
# 📊 FUNCIONES DE DIAGNÓSTICO
# =========================

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


def alert_low_stock(df: pd.DataFrame, threshold: int = None) -> dict:
    """
    Detecta productos con stock bajo.
    ✅ Mejora v2.5: threshold evaluado en runtime, no al importar
    
    Returns:
        dict con información de la alerta
    """
    # ✅ Mejora: Evaluar default en runtime
    if threshold is None:
        threshold = LOW_STOCK_THRESHOLD
    
    if "stock" not in df.columns:
        return {"triggered": False, "count": 0, "products": []}
    
    low_stock = df[df["stock"] <= threshold]
    
    if not low_stock.empty:
        # ✅ Mejora v2.5: Usa helper DRY + retry logic
        path = _save_alert(
            low_stock, 
            "low_stock", 
            f"🚨 ALERTA: {len(low_stock)} productos con stock <= {threshold}"
        )
        
        products = low_stock[["product_id", "name", "stock"]].to_dict('records')
        
        return {
            "triggered": True,
            "count": len(low_stock),
            "threshold": threshold,
            "file": path,
            "products": products[:10]  # Máximo 10 para no saturar respuesta
        }
    
    return {"triggered": False, "count": 0, "products": []}


def alert_no_sales(df: pd.DataFrame, days_threshold: int = None) -> dict:
    """
    Detecta productos sin ventas recientes.
    ✅ Mejora v2.5: days_threshold evaluado en runtime
    
    Returns:
        dict con información de la alerta
    """
    # ✅ Mejora: Evaluar default en runtime
    if days_threshold is None:
        days_threshold = NO_SALES_DAYS
    
    if "last_sold_date" not in df.columns:
        return {"triggered": False, "count": 0, "products": []}
    
    df_copy = df.copy()
    df_copy['last_sold_date'] = pd.to_datetime(df_copy['last_sold_date'], errors='coerce')
    threshold_date = pd.Timestamp.now() - pd.Timedelta(days=days_threshold)
    
    no_sales = df_copy[df_copy['last_sold_date'] < threshold_date]
    
    if not no_sales.empty:
        # ✅ Mejora v2.5: Usa helper DRY + retry logic
        path = _save_alert(
            no_sales,
            "no_sales",
            f"🚨 ALERTA: {len(no_sales)} productos sin ventas en {days_threshold} días"
        )
        
        return {
            "triggered": True,
            "count": len(no_sales),
            "days_threshold": days_threshold,
            "file": path
        }
    
    return {"triggered": False, "count": 0}


def alert_missing_data(df: pd.DataFrame) -> dict:
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
        
        # Verificar HMAC si es webhook real
        if not simulation:
            hmac_header = request.headers.get('X-Shopify-Hmac-Sha256')
            if not verify_shopify_webhook(request.data, hmac_header, SHOPIFY_WEBHOOK_SECRET):
                logger.warning("⚠️ Webhook rechazado: HMAC inválido")
                return jsonify({
                    "status": "error",
                    "message": "Invalid HMAC signature"
                }), 401
        
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
                        "last_sold_date": variant.get("last_sold_date")
                    })
        
        # Formato webhook real de Shopify (producto individual)
        elif "id" in payload and "variants" in payload:
            for variant in payload.get("variants", []):
                rows.append({
                    "product_id": variant.get("id"),
                    "name": f"{payload.get('title')} - {variant.get('title')}",
                    "stock": variant.get("inventory_quantity"),
                    "last_sold_date": None
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
                    "price": item.get("price")
                })
        
        if not rows:
            logger.info("⚠️ No se encontraron productos en el payload")
            return jsonify({
                "status": "warning",
                "message": "No products found in payload"
            }), 200
        
        df = pd.DataFrame(rows)
        
        # Guardar payload
        payload_file = save_payload(df, f"shopify_webhook_{topic.replace('/', '_')}")
        
        # Ejecutar diagnósticos
        alerts = {
            "low_stock": alert_low_stock(df),
            "no_sales": alert_no_sales(df),
            "missing_data": alert_missing_data(df)
        }
        
        # Procesar datos
        df_clean = process_data(df)
        
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


# =========================
# 🚀 ENTRY POINT
# =========================

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 WEBHOOK SERVER v2.5 - Shopify Automation")
    print("=" * 60)
    print(f"📍 Server: http://127.0.0.1:5001")
    print(f"📊 Health: http://127.0.0.1:5001/health")
    print(f"📈 Status: http://127.0.0.1:5001/status")
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
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=5001, debug=DEBUG_MODE)