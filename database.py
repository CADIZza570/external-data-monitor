# database.py
"""
Sistema de base de datos SQLite para webhooks.
Guarda historial completo de todos los eventos recibidos.

Tabla: webhooks
- Almacena cada webhook recibido
- Permite consultas y analytics
- Persistente (no se pierde al reiniciar)
"""

import sqlite3
import json
from datetime import datetime
import os

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Ruta de la base de datos
# En Railway con volumen: /data/webhooks.db
# En local: ./webhooks.db
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = os.path.join(DATA_DIR, "webhooks.db")

# ============================================================
# FUNCIONES DE INICIALIZACIÓN
# ============================================================

def init_database():
    """
    Inicializa la base de datos y crea tabla si no existe.
    Se ejecuta automáticamente al importar este módulo.
    """
    # Crear directorio de datos si no existe
    os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Crear tabla webhooks
    # IF NOT EXISTS = solo crea si no existe (seguro ejecutar múltiples veces)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS webhooks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            topic TEXT,
            shop TEXT,
            payload TEXT NOT NULL,
            alerts_triggered TEXT,
            files_generated TEXT,
            simulation BOOLEAN DEFAULT 0,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ============= MIGRACIÓN: Agregar columnas faltantes =============
    # Fix: Loop de errores "no such column: processed"
    # Migración idempotente (safe ejecutar múltiples veces)
    print("🔧 Verificando columnas en webhooks...")
    try:
        cursor.execute("ALTER TABLE webhooks ADD COLUMN processed INTEGER DEFAULT 0")
        print("✅ Columna 'processed' agregada a webhooks")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Columna 'processed' ya existe")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE webhooks ADD COLUMN error_message TEXT")
        print("✅ Columna 'error_message' agregada a webhooks")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Columna 'error_message' ya existe")
        else:
            raise

    try:
        cursor.execute("ALTER TABLE webhooks ADD COLUMN retry_count INTEGER DEFAULT 0")
        print("✅ Columna 'retry_count' agregada a webhooks")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print("✓ Columna 'retry_count' ya existe")
        else:
            raise
    # ================================================================

    # ============= NUEVO: Crear tabla products =============
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            sku TEXT,
            stock INTEGER DEFAULT 0,
            price REAL,
            shop TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(product_id, shop)
        )
    ''')
    # =======================================================

    # ============= ÍNDICES PARA PERFORMANCE =============
    print("📊 Creando índices para optimización...")

    # Índice 1: Búsquedas por tienda (muy común en queries)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_shop
        ON webhooks(shop)
    ''')

    # Índice 2: Ordenamiento por fecha (dashboard)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_received_at
        ON webhooks(received_at DESC)
    ''')

    # Índice 3: Filtros por fuente (analytics)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_source_shop
        ON webhooks(source, shop)
    ''')

    # Índice 4: Búsqueda de productos por SKU (muy común)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_shop_sku
        ON products(shop, sku)
    ''')

    # Índice 5: Alertas de stock bajo (query frecuente)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_stock_low
        ON products(stock)
        WHERE stock < 10
    ''')

    # Índice 6: Categorías ABC (analytics)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_category
        ON products(category, shop)
    ''')

    print("✅ 6 índices creados exitosamente")
    # ===========================================================

    conn.commit()
    conn.close()
    print(f"✅ Base de datos inicializada: {DB_FILE}")
    print(f"📁 Directorio de datos: {DATA_DIR}")

# ============================================================
# FUNCIÓN DE CONEXIÓN
# ============================================================

def get_db_connection():
    """
    Crea y retorna una conexión a la base de datos.
    Configura row_factory para retornar diccionarios.
    
    Returns:
        sqlite3.Connection con row_factory configurado
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# FUNCIONES CRUD (Create, Read, Update, Delete)
# ============================================================

def save_webhook(source, topic, shop, payload, alerts=None, files=None, simulation=False):
    """
    Guarda un webhook en la base de datos.
    
    Args:
        source (str): Origen del webhook (shopify, amazon, ebay)
        topic (str): Tipo de evento (products/update, orders/create, etc)
        shop (str): Dominio de la tienda
        payload (dict): Payload completo del webhook (se convierte a JSON)
        alerts (dict): Alertas que se activaron (opcional)
        files (list): Archivos CSV generados (opcional)
        simulation (bool): Si fue simulación o webhook real
    
    Returns:
        int: ID del webhook guardado, o None si falla
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Convertir payload (dict) a JSON string para guardar
        payload_json = json.dumps(payload)
        
        # Convertir alerts a JSON string si existe
        alerts_json = json.dumps(alerts) if alerts else None
        
        # Convertir files (lista) a JSON string si existe
        files_json = json.dumps(files) if files else None
        
        # INSERT: agregar nuevo registro
        cursor.execute('''
            INSERT INTO webhooks 
            (source, topic, shop, payload, alerts_triggered, files_generated, simulation)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (source, topic, shop, payload_json, alerts_json, files_json, simulation))
        
        conn.commit()
        webhook_id = cursor.lastrowid  # ID del registro recién insertado
        conn.close()
        
        print(f"💾 Webhook guardado en DB: ID={webhook_id}, source={source}, topic={topic}")
        return webhook_id
        
    except Exception as e:
        print(f"❌ Error guardando webhook en DB: {e}")
        return None


def get_webhooks(limit=50, offset=0, source=None):
    """
    Obtiene webhooks de la base de datos.
    
    Args:
        limit (int): Cuántos webhooks retornar (default 50)
        offset (int): Desde qué posición empezar (para paginación)
        source (str): Filtrar por fuente (shopify, amazon, etc) - opcional
    
    Returns:
        list: Lista de webhooks como diccionarios
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
        cursor = conn.cursor()
        
        # Query base - Solo columnas necesarias (omitir payload que puede ser grande)
        query = """
            SELECT id, shop, topic, received_at, processed,
                   error_message, retry_count
            FROM webhooks
        """
        params = []
        
        # Agregar filtro si se especifica source
        if source:
            query += " WHERE source = ?"
            params.append(source)
        
        # Ordenar por más reciente primero
        query += " ORDER BY received_at DESC"
        
        # Paginación
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convertir a lista de diccionarios
        webhooks = []
        for row in rows:
            webhook = {
                "id": row["id"],
                "source": row["source"],
                "topic": row["topic"],
                "shop": row["shop"],
                "payload": json.loads(row["payload"]) if row["payload"] else None,
                "alerts_triggered": json.loads(row["alerts_triggered"]) if row["alerts_triggered"] else None,
                "files_generated": json.loads(row["files_generated"]) if row["files_generated"] else None,
                "simulation": bool(row["simulation"]),
                "received_at": row["received_at"]
            }
            webhooks.append(webhook)
        
        conn.close()
        return webhooks
        
    except Exception as e:
        print(f"❌ Error obteniendo webhooks de DB: {e}")
        return []


def get_webhook_count(source=None):
    """
    Cuenta total de webhooks en la base de datos.
    
    Args:
        source (str): Filtrar por fuente (opcional)
    
    Returns:
        int: Número total de webhooks
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        if source:
            cursor.execute("SELECT COUNT(*) FROM webhooks WHERE source = ?", (source,))
        else:
            cursor.execute("SELECT COUNT(*) FROM webhooks")
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
        
    except Exception as e:
        print(f"❌ Error contando webhooks: {e}")
        return 0


def get_recent_webhooks(hours=24):
    """
    Obtiene webhooks de las últimas X horas.
    
    Args:
        hours (int): Últimas cuántas horas (default 24)
    
    Returns:
        list: Lista de webhooks recientes
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # SQLite: datetime('now', '-24 hours') = hace 24 horas
        cursor.execute('''
            SELECT id, shop, topic, received_at, processed
            FROM webhooks
            WHERE received_at >= datetime('now', ? || ' hours')
            ORDER BY received_at DESC
        ''', (f'-{hours}',))
        
        rows = cursor.fetchall()
        
        webhooks = []
        for row in rows:
            webhook = {
                "id": row["id"],
                "source": row["source"],
                "topic": row["topic"],
                "shop": row["shop"],
                "received_at": row["received_at"]
            }
            webhooks.append(webhook)
        
        conn.close()
        return webhooks
        
    except Exception as e:
        print(f"❌ Error obteniendo webhooks recientes: {e}")
        return []

# ============================================================
# FUNCIONES PARA TABLA PRODUCTS
# ============================================================

def calculate_velocity_and_category(sku, total_sales_30d=None):
    """
    Calcula velocity_daily y category automáticamente basado en historial.

    Args:
        sku: SKU del producto
        total_sales_30d: Ventas de últimos 30 días (si ya se conoce)

    Returns:
        tuple: (velocity_daily, category)
    """
    # Si no hay datos de ventas, calcular desde orders_history
    if total_sales_30d is None:
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE)
            result = conn.execute('''
                SELECT SUM(quantity) as total_sales
                FROM orders_history
                WHERE sku = ?
                  AND order_date >= datetime('now', '-30 days')
            ''', (sku,)).fetchone()

            total_sales_30d = result[0] if result and result[0] else 0
        except Exception as e:
            total_sales_30d = 0
        finally:
            if conn:
                conn.close()

    # Calcular velocity (ventas por día)
    velocity_daily = round(total_sales_30d / 30.0, 2) if total_sales_30d > 0 else 0

    # Clasificar en categoría ABC basado en velocity
    # A: Alta rotación (>= 2 unidades/día)
    # B: Rotación media (>= 0.5 y < 2 unidades/día)
    # C: Baja rotación (< 0.5 unidades/día)
    if velocity_daily >= 2.0:
        category = 'A'
    elif velocity_daily >= 0.5:
        category = 'B'
    else:
        category = 'C'

    return velocity_daily, category

def save_product(product_id, name, sku, stock, price, shop, cost_price=None,
                 total_sales_30d=None, velocity_daily=None, category=None):
    """
    Guarda o actualiza un producto en la tabla products.
    Usa UPSERT (INSERT ON CONFLICT) para actualizar si ya existe.

    Args:
        product_id: ID del producto (variant_id de Shopify)
        name: Nombre del producto + variante
        sku: SKU del producto
        stock: Cantidad en inventario
        price: Precio del producto
        shop: Dominio de la tienda
        cost_price: Costo de adquisición (opcional, para Cash Flow)
        total_sales_30d: Total de ventas en últimos 30 días (opcional)
        velocity_daily: Velocidad de ventas diaria (opcional)
        category: Clasificación ABC (opcional: A, B, C)

    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    try:
        # Auto-calcular velocity y category si no se proporcionan
        if velocity_daily is None or category is None:
            calc_velocity, calc_category = calculate_velocity_and_category(sku, total_sales_30d)
            if velocity_daily is None:
                velocity_daily = calc_velocity
            if category is None:
                category = calc_category

        conn = sqlite3.connect(DB_FILE)

        # Si hay ventas recientes, actualizar last_sale_date
        # Si total_sales_30d > 0, asumimos que hubo venta hoy
        last_sale_date = datetime.now().isoformat() if total_sales_30d and total_sales_30d > 0 else None

        conn.execute('''
            INSERT INTO products (
                product_id, name, sku, stock, price, shop, last_updated,
                cost_price, last_sale_date, total_sales_30d, velocity_daily, category
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
            ON CONFLICT(product_id, shop)
            DO UPDATE SET
                name = excluded.name,
                sku = excluded.sku,
                stock = excluded.stock,
                price = excluded.price,
                cost_price = COALESCE(excluded.cost_price, cost_price),
                last_sale_date = COALESCE(excluded.last_sale_date, last_sale_date),
                total_sales_30d = COALESCE(excluded.total_sales_30d, total_sales_30d),
                velocity_daily = COALESCE(excluded.velocity_daily, velocity_daily),
                category = COALESCE(excluded.category, category),
                last_updated = CURRENT_TIMESTAMP
        ''', (product_id, name, sku, stock, price, shop,
              cost_price, last_sale_date, total_sales_30d, velocity_daily, category))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        # ✅ MEJORADO: Log detallado del error
        print(f"❌ Error guardando producto {product_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_trending_rank(sku, days=30):
    """
    Obtiene el ranking de trending de un SKU.

    Args:
        sku: SKU del producto
        days: Días de historial a considerar (default 30)

    Returns:
        Ranking (1 = más vendido, None = sin ventas)
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Obtener ranking basado en ventas
        cursor.execute('''
            WITH ranked_sales AS (
                SELECT
                    sku,
                    SUM(quantity) as total_sales,
                    RANK() OVER (ORDER BY SUM(quantity) DESC) as ranking
                FROM sales_history
                WHERE sale_date >= datetime('now', '-' || ? || ' days')
                GROUP BY sku
            )
            SELECT ranking FROM ranked_sales WHERE sku = ?
        ''', (days, sku))

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    except Exception as e:
        print(f"❌ Error obteniendo trending rank {sku}: {e}")
        return None


def calculate_alert_priority(velocity, stock, price, trending_rank=None):
    """
    Calcula prioridad de alerta basada en impacto real del negocio.
    Sistema que aprende: usa velocidad actual + trending histórico.

    Args:
        velocity: Velocidad de ventas diaria (VDP)
        stock: Stock actual
        price: Precio del producto
        trending_rank: Ranking en trending (1=top, None=sin datos)

    Returns:
        Score 0-100 (100 = máxima prioridad)

    Criterios:
        - Velocidad alta + stock bajo = prioridad CRÍTICA
        - Trending top (rank 1-3) = boost +30 puntos
        - Precio alto = boost proporcional
        - Stock 0 = siempre prioridad 100
    """
    # Stock 0 = siempre crítico
    if stock <= 0:
        return 100

    # Base: velocidad vs stock (días hasta stockout)
    if velocity > 0:
        days_to_stockout = stock / velocity

        # Menos de 3 días = crítico
        if days_to_stockout <= 3:
            urgency_score = 80
        # Menos de 7 días = alto
        elif days_to_stockout <= 7:
            urgency_score = 60
        # Menos de 14 días = medio
        elif days_to_stockout <= 14:
            urgency_score = 40
        else:
            urgency_score = 20
    else:
        # Sin velocidad = baja prioridad base
        urgency_score = 10

    # Boost por trending (productos HOT = más prioridad)
    trending_boost = 0
    if trending_rank:
        if trending_rank == 1:
            trending_boost = 30  # Top 1 = +30 puntos
        elif trending_rank == 2:
            trending_boost = 20  # Top 2 = +20 puntos
        elif trending_rank == 3:
            trending_boost = 15  # Top 3 = +15 puntos
        elif trending_rank <= 10:
            trending_boost = 5   # Top 10 = +5 puntos

    # Boost por valor monetario (productos caros = más impacto)
    value_boost = 0
    if price >= 100:
        value_boost = 15
    elif price >= 50:
        value_boost = 10
    elif price >= 25:
        value_boost = 5

    # Score final (max 100)
    priority = min(100, urgency_score + trending_boost + value_boost)

    return priority


def save_sale(sku, product_name, quantity, order_id, shop):
    """
    Guarda venta en sales_history para trending.

    Args:
        sku: SKU del producto vendido
        product_name: Nombre del producto
        quantity: Cantidad vendida
        order_id: ID de la orden
        shop: Tienda

    Returns:
        True si exitoso, False si falla
    """
    try:
        conn = sqlite3.connect(DB_FILE)

        conn.execute('''
            INSERT INTO sales_history (sku, product_name, quantity, sale_date, order_id, shop)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        ''', (sku, product_name, quantity, order_id, shop))

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"❌ Error guardando venta {sku}: {e}")
        import traceback
        traceback.print_exc()
        return False

# ============================================================
# AUTO-INICIALIZACIÓN
# ============================================================

# Cuando importes este módulo, la DB se inicializa automáticamente
init_database()
