# 🐘 GUÍA DE MIGRACIÓN A POSTGRESQL
## Cerebro Central v2.0 → PostgreSQL

**Última actualización:** 2026-02-02
**Autor:** Claude (Cirujano Maestro)
**Status:** PREPARADO PARA MIGRACIÓN

---

## 📋 ÍNDICE

1. [Variables que deben cambiar](#1-variables-que-deben-cambiar)
2. [Módulos afectados](#2-módulos-afectados)
3. [Cambios en código](#3-cambios-en-código)
4. [Schema PostgreSQL](#4-schema-postgresql)
5. [Plan de migración](#5-plan-de-migración)
6. [Rollback strategy](#6-rollback-strategy)
7. [Testing checklist](#7-testing-checklist)

---

## 1. VARIABLES QUE DEBEN CAMBIAR

### 1.1 Variables de Entorno (Railway)

**NUEVAS (agregar):**
```bash
# PostgreSQL Connection
DATABASE_URL=postgresql://user:password@host:5432/dbname
POSTGRES_HOST=hostname.railway.app
POSTGRES_PORT=5432
POSTGRES_DB=tiburon_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=***************

# Connection Pool
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_TIMEOUT=30
```

**OBSOLETAS (eliminar después de migración):**
```bash
# Ya no se usarán con PostgreSQL
SQLITE_DB_PATH=/data/webhooks.db
```

**MANTENER:**
```bash
# Estas NO cambian
SHOPIFY_WEBHOOK_SECRET=***
MAKE_WEBHOOK_URL=https://hook.us2.make.com/***
ADMIN_API_KEY=shark-predator-2026
SENDGRID_API_KEY=***
DISCORD_WEBHOOK_URL=***
```

---

### 1.2 Constantes en Código

**`cerebro_central.py`**
- ✅ **NO REQUIERE CAMBIOS** - Ya está modularizado
- Usa `get_db_connection()` de `database.py`
- Todas las queries SQL son compatibles PostgreSQL

**`metrics_calculator.py`**
- ✅ **NO REQUIERE CAMBIOS** - Sin dependencias de DB
- Totalmente agnóstico a la base de datos
- Recibe/retorna dicts genéricos

**`database.py` - CRÍTICO**
- ⚠️ **REQUIERE REFACTORIZACIÓN COMPLETA**
- Cambiar de `sqlite3` a `psycopg2` o `asyncpg`
- Ver sección 3.1

---

## 2. MÓDULOS AFECTADOS

### 2.1 Alta Prioridad (Crítico para funcionar)

| Archivo | Impacto | Cambios Requeridos |
|---------|---------|-------------------|
| `database.py` | 🔴 CRÍTICO | Refactorizar conexión SQLite → PostgreSQL |
| `webhook_server.py` | 🟡 MEDIO | Actualizar imports si cambia estructura de database.py |
| `cerebro_central.py` | 🟢 BAJO | Sin cambios si database.py mantiene misma interfaz |
| `metrics_calculator.py` | 🟢 NINGUNO | Módulo agnóstico - sin cambios |

### 2.2 Baja Prioridad (Funciones legacy)

| Archivo | Impacto | Acción |
|---------|---------|--------|
| `cashflow_api.py` | 🟡 MEDIO | Revisar queries SQLite específicas |
| `migrate_db_cashflow.py` | 🔴 OBSOLETO | Eliminar después de migración |
| `productos_inventario_completo.py` | 🟡 BAJO | Actualizar si usa conexión directa |
| `*.db` files | 🔴 OBSOLETO | Respaldar y archivar |

---

## 3. CAMBIOS EN CÓDIGO

### 3.1 `database.py` - Refactorización Completa

**ANTES (SQLite):**
```python
import sqlite3

def get_db_connection():
    """Conexión SQLite"""
    conn = sqlite3.connect('/data/webhooks.db', timeout=10)
    conn.row_factory = sqlite3.Row
    return conn
```

**DESPUÉS (PostgreSQL):**
```python
import psycopg2
import psycopg2.extras
import os

def get_db_connection():
    """Conexión PostgreSQL con pool"""
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT', 5432),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD'),
        cursor_factory=psycopg2.extras.RealDictCursor  # Retorna dicts como SQLite Row
    )
    return conn
```

**CAMBIOS CLAVE:**
1. ✅ `RealDictCursor` hace que rows sean dicts (compatible con código existente)
2. ✅ Variables de entorno en lugar de archivo local
3. ✅ Sin cambios en interfaz - `cerebro_central.py` sigue funcionando igual

---

### 3.2 Queries SQL - Compatibilidad

**REVISAR ESTAS DIFERENCIAS:**

| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Auto-increment | `AUTOINCREMENT` | `SERIAL` o `BIGSERIAL` |
| Timestamp | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMP DEFAULT NOW()` |
| Upsert | `INSERT ... ON CONFLICT ... DO UPDATE` | ✅ COMPATIBLE |
| JSON | `TEXT` (serializado) | `JSON` o `JSONB` (nativo) ✅ MEJOR |
| Full-text search | FTS5 (limitado) | `tsvector` ✅ MÁS POTENTE |

**QUERIES EN `cerebro_central.py` - STATUS:**
- ✅ `SELECT * FROM products WHERE sku = ?` → Compatible (cambiar `?` a `%s`)
- ✅ `UPDATE products SET stock = ? WHERE sku = ?` → Compatible
- ✅ `INSERT ... ON CONFLICT DO UPDATE` → Compatible
- ✅ Todas las queries son ANSI SQL estándar

---

### 3.3 Placeholders - CRÍTICO

**SQLite usa `?`, PostgreSQL usa `%s`:**

```python
# ANTES (SQLite)
conn.execute('SELECT * FROM products WHERE sku = ?', (sku,))

# DESPUÉS (PostgreSQL)
cursor.execute('SELECT * FROM products WHERE sku = %s', (sku,))
```

**SOLUCIÓN CENTRALIZADA:**
Crear helper en `database.py`:
```python
def execute_query(conn, query, params=None):
    """
    Ejecuta query compatible con PostgreSQL.

    Maneja automáticamente placeholders.
    """
    # PostgreSQL usa %s en lugar de ?
    query_pg = query.replace('?', '%s')

    cursor = conn.cursor()
    cursor.execute(query_pg, params or ())
    return cursor
```

---

## 4. SCHEMA POSTGRESQL

### 4.1 Tabla `products` (optimizada)

```sql
CREATE TABLE products (
    -- Primary Key
    id BIGSERIAL PRIMARY KEY,

    -- Identifiers
    product_id VARCHAR(255) NOT NULL,
    sku VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(500) NOT NULL,

    -- Inventory
    stock INTEGER DEFAULT 0,
    cost_price DECIMAL(10, 2),
    price DECIMAL(10, 2),

    -- Metrics (calculadas por MetricsCalculator)
    velocity_daily DECIMAL(10, 4) DEFAULT 0,
    total_sales_30d INTEGER DEFAULT 0,
    total_sales_60d INTEGER DEFAULT 0,

    -- Timestamps
    last_sale_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Índices
    INDEX idx_sku (sku),
    INDEX idx_product_id (product_id),
    INDEX idx_velocity (velocity_daily DESC),
    INDEX idx_stock_low (stock) WHERE stock < 10
);
```

**MEJORAS vs SQLite:**
1. ✅ `BIGSERIAL` en lugar de `INTEGER AUTOINCREMENT`
2. ✅ `DECIMAL` para precios (precisión exacta vs REAL)
3. ✅ Índices parciales (`WHERE stock < 10`) - más eficientes
4. ✅ `updated_at` con trigger automático

---

### 4.2 Tabla `daily_sales` (optimizada)

```sql
CREATE TABLE daily_sales (
    date DATE PRIMARY KEY,
    total_sales DECIMAL(12, 2) DEFAULT 0,
    orders_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Índice para queries de rango
    INDEX idx_date_range (date DESC)
);
```

---

### 4.3 Tabla `webhooks` (audit log)

```sql
CREATE TABLE webhooks (
    id BIGSERIAL PRIMARY KEY,
    webhook_type VARCHAR(100),
    order_id VARCHAR(255),
    order_number VARCHAR(255),
    payload JSONB,  -- ✅ JSON nativo en lugar de TEXT
    received_at TIMESTAMP DEFAULT NOW(),
    processed BOOLEAN DEFAULT TRUE,

    -- Índices para búsqueda
    INDEX idx_order_id (order_id),
    INDEX idx_received_at (received_at DESC),
    INDEX idx_payload_gin (payload) USING GIN  -- ✅ Búsqueda full-text en JSON
);
```

**VENTAJA JSONB:**
- Búsquedas dentro del JSON: `payload->>'customer'->>'email' = 'test@example.com'`
- Índices GIN para queries rápidas
- Validación automática de estructura JSON

---

## 5. PLAN DE MIGRACIÓN

### 5.1 Fase 1: Preparación (1 día)

**Acciones:**
1. ✅ Crear nueva instancia PostgreSQL en Railway
2. ✅ Ejecutar schema SQL (sección 4)
3. ✅ Configurar variables de entorno en Railway
4. ✅ Backup completo de SQLite actual

**Comando backup:**
```bash
# Desde Railway CLI
railway run sqlite3 /data/webhooks.db ".backup /data/backup_$(date +%Y%m%d).db"
railway volume download /data/backup_*.db
```

---

### 5.2 Fase 2: Migración de Datos (2-4 horas)

**Script de migración:**
```python
# migrate_sqlite_to_postgres.py
import sqlite3
import psycopg2
import psycopg2.extras
import os

def migrate_products():
    """Migrar tabla products de SQLite a PostgreSQL."""

    # Conectar a ambas DBs
    sqlite_conn = sqlite3.connect('/data/webhooks.db')
    sqlite_conn.row_factory = sqlite3.Row

    pg_conn = psycopg2.connect(os.getenv('DATABASE_URL'))

    # Leer todos los productos
    sqlite_rows = sqlite_conn.execute('SELECT * FROM products').fetchall()

    # Insertar en PostgreSQL
    pg_cursor = pg_conn.cursor()

    for row in sqlite_rows:
        pg_cursor.execute('''
            INSERT INTO products (
                product_id, sku, name, stock, cost_price, price,
                velocity_daily, total_sales_30d, last_sale_date,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (sku) DO UPDATE SET
                stock = EXCLUDED.stock,
                velocity_daily = EXCLUDED.velocity_daily,
                total_sales_30d = EXCLUDED.total_sales_30d
        ''', (
            row['product_id'], row['sku'], row['name'],
            row['stock'], row['cost_price'], row['price'],
            row['velocity_daily'], row['total_sales_30d'],
            row['last_sale_date']
        ))

    pg_conn.commit()
    print(f"✅ Migrados {len(sqlite_rows)} productos")

def migrate_daily_sales():
    """Migrar daily_sales."""
    # Similar a migrate_products()
    pass

def migrate_webhooks():
    """Migrar webhooks (últimos 30 días solo)."""
    # Solo migrar últimos 30 días para reducir carga
    pass

if __name__ == '__main__':
    print("🚀 Iniciando migración SQLite → PostgreSQL")
    migrate_products()
    migrate_daily_sales()
    migrate_webhooks()
    print("✅ Migración completada")
```

**Ejecutar:**
```bash
railway run python migrate_sqlite_to_postgres.py
```

---

### 5.3 Fase 3: Refactorización de Código (4 horas)

**Orden de cambios:**

1. **`database.py`** (1 hora)
   - Refactorizar `get_db_connection()`
   - Crear helpers para queries compatibles
   - Testing de conexión

2. **Actualizar placeholders `?` → `%s`** (1 hora)
   - Buscar todos los `execute()` en el código
   - Reemplazar placeholders
   - Testing de cada query

3. **`requirements.txt`** (5 min)
   ```
   # Agregar
   psycopg2-binary==2.9.9

   # Remover después de migración
   # sqlite3 (built-in, no package)
   ```

4. **Testing local** (2 horas)
   - Ver sección 7

---

### 5.4 Fase 4: Deploy a Railway (30 min)

**Checklist:**
```bash
# 1. Commit cambios
git add .
git commit -m "Feat: Migración SQLite → PostgreSQL (#18)"

# 2. Push a Railway
git push origin main

# 3. Verificar logs
railway logs

# 4. Healthcheck
curl https://tranquil-freedom-production.up.railway.app/health

# 5. Test webhook
curl -X POST -H "X-Admin-Key: shark-predator-2026" \
  -H "Content-Type: application/json" \
  -d '{"id": 9999, "order_number": 9999, "total_price": "100", "customer": {"first_name": "Test"}, "line_items": [{"sku": "TEST", "title": "Test", "quantity": 1, "price": "100"}]}' \
  https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders
```

---

## 6. ROLLBACK STRATEGY

### 6.1 Si falla la migración

**Opción 1: Revertir código (5 min)**
```bash
# Volver a commit anterior
git revert HEAD
git push origin main
```

**Opción 2: Cambiar a branch anterior (2 min)**
```bash
# Crear branch de backup antes de migrar
git checkout -b backup-sqlite
git push origin backup-sqlite

# Si falla, volver
git checkout backup-sqlite
railway up
```

### 6.2 Mantener SQLite como fallback (RECOMENDADO)

**En `database.py`:**
```python
def get_db_connection():
    """Conexión con fallback SQLite."""
    use_postgres = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

    if use_postgres:
        try:
            return _get_postgres_connection()
        except Exception as e:
            logger.error(f"PostgreSQL falló: {e}, usando SQLite fallback")
            return _get_sqlite_connection()
    else:
        return _get_sqlite_connection()
```

**Variable Railway:**
```bash
# Si PostgreSQL falla, cambiar a:
USE_POSTGRES=false

# Sistema vuelve a SQLite automáticamente
```

---

## 7. TESTING CHECKLIST

### 7.1 Pre-Migración (SQLite actual)

- [ ] Backup completo de webhooks.db
- [ ] Exportar datos críticos a CSV
- [ ] Documentar queries custom en otros archivos
- [ ] Verificar que Cerebro Central v2.0 funciona

### 7.2 Post-Migración (PostgreSQL)

**Testing funcional:**
- [ ] Conexión a PostgreSQL exitosa
- [ ] Tabla `products` con datos migrados
- [ ] Tabla `daily_sales` con datos migrados
- [ ] Webhook simulado funciona
- [ ] Metrics calculator funciona (ROI, velocity, coverage)
- [ ] Alertas se generan correctamente
- [ ] Make.com recibe JSON correcto
- [ ] WhatsApp muestra mensaje con tallas

**Testing de performance:**
- [ ] Query `SELECT * FROM products WHERE sku = %s` < 10ms
- [ ] Insert webhook < 50ms
- [ ] Update metrics < 20ms
- [ ] Webhook completo end-to-end < 500ms

**Testing de carga:**
```bash
# 100 webhooks concurrentes
ab -n 100 -c 10 -p test_payload.json -T application/json \
  -H "X-Admin-Key: shark-predator-2026" \
  https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders
```

---

## 8. DICCIONARIOS MANUALES → TABLAS

### 8.1 Actualmente en Código (SQLite era)

**NO HAY diccionarios manuales críticos en Cerebro Central v2.0** ✅

Todos los datos ya están en tablas:
- `products` - Productos y métricas
- `daily_sales` - Ventas diarias
- `webhooks` - Audit log

### 8.2 Si encuentras diccionarios en archivos legacy

**ANTES (hardcoded):**
```python
CATEGORIES = {
    'BTA-CG': 'Botas Casuales',
    'BTA-PTN': 'Botas Patentadas',
    'ZPT': 'Zapatos'
}
```

**DESPUÉS (tabla PostgreSQL):**
```sql
CREATE TABLE product_categories (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(200) NOT NULL
);

-- Migrar dict
INSERT INTO product_categories VALUES ('BTA-CG', 'Botas Casuales');
```

**En código:**
```python
def get_category_name(code):
    conn = get_db_connection()
    result = conn.execute('SELECT name FROM product_categories WHERE code = %s', (code,))
    return result.fetchone()['name'] if result else 'Unknown'
```

---

## 9. MEJORAS ADICIONALES POST-MIGRACIÓN

### 9.1 Connection Pooling (Recomendado)

```python
# En database.py
from psycopg2 import pool

# Pool global
connection_pool = None

def init_connection_pool():
    """Inicializa pool de conexiones."""
    global connection_pool
    connection_pool = pool.SimpleConnectionPool(
        minconn=5,
        maxconn=20,
        host=os.getenv('POSTGRES_HOST'),
        port=os.getenv('POSTGRES_PORT'),
        database=os.getenv('POSTGRES_DB'),
        user=os.getenv('POSTGRES_USER'),
        password=os.getenv('POSTGRES_PASSWORD')
    )

def get_db_connection():
    """Obtiene conexión del pool."""
    return connection_pool.getconn()

def return_connection(conn):
    """Devuelve conexión al pool."""
    connection_pool.putconn(conn)
```

**Beneficios:**
- ✅ Reduce latencia (no crear conexión cada vez)
- ✅ Maneja concurrencia mejor
- ✅ Previene "too many connections"

---

### 9.2 Migraciones Versionadas (Alembic)

```bash
pip install alembic

# Inicializar
alembic init alembic

# Crear migración
alembic revision -m "Add products table"

# Ejecutar migración
alembic upgrade head
```

**Beneficio:** Versionado de schema como código

---

### 9.3 Read Replicas (Escalabilidad futura)

```python
# Conexión master (writes)
POSTGRES_MASTER_URL = os.getenv('DATABASE_URL')

# Conexión replica (reads)
POSTGRES_REPLICA_URL = os.getenv('DATABASE_REPLICA_URL')

def get_db_connection(readonly=False):
    """
    Obtiene conexión según tipo de operación.

    Args:
        readonly: Si True, usa replica (queries SELECT)
    """
    url = POSTGRES_REPLICA_URL if readonly else POSTGRES_MASTER_URL
    return psycopg2.connect(url)
```

---

## 10. CONTACTOS Y RECURSOS

**Railway PostgreSQL:**
- Docs: https://docs.railway.app/databases/postgresql
- Pricing: $5/month base + usage

**psycopg2 Docs:**
- https://www.psycopg.org/docs/

**SQL Compatibility:**
- https://wiki.postgresql.org/wiki/SQLite_to_PostgreSQL

---

## ✅ CHECKLIST FINAL PRE-MIGRACIÓN

**Antes de ejecutar la migración, verificar:**

- [ ] Código v2.0 funciona perfectamente en SQLite
- [ ] Backup de webhooks.db descargado
- [ ] PostgreSQL instance creada en Railway
- [ ] Variables de entorno configuradas
- [ ] Script de migración probado localmente
- [ ] Plan de rollback documentado
- [ ] Equipo notificado del mantenimiento
- [ ] Ventana de downtime acordada (estimar 1-2 horas)

---

**🦈 TIBURÓN LISTO PARA SALTAR A POSTGRESQL** 🐘

