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
        
        # Query base
        query = "SELECT * FROM webhooks"
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
            SELECT * FROM webhooks 
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

def save_product(product_id, name, sku, stock, price, shop):
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
    
    Returns:
        True si se guardó exitosamente, False si hubo error
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.execute('''
            INSERT INTO products (product_id, name, sku, stock, price, shop, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(product_id, shop) 
            DO UPDATE SET 
                name = excluded.name,
                sku = excluded.sku,
                stock = excluded.stock,
                price = excluded.price,
                last_updated = CURRENT_TIMESTAMP
        ''', (product_id, name, sku, stock, price, shop))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Error guardando producto {product_id}: {e}")
        return False

# ============================================================
# AUTO-INICIALIZACIÓN
# ============================================================

# Cuando importes este módulo, la DB se inicializa automáticamente
init_database()
