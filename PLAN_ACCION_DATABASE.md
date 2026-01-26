# 🎯 PLAN DE ACCIÓN: DATABASE STRATEGY

**Fecha:** 24 Enero 2026
**Basado en:** ANALISIS_MIGRACION_POSTGRESQL.md
**Recomendación:** OPCIÓN B (90% confianza)

---

## OPCIÓN B: OPTIMIZAR SQLite (RECOMENDADO)

### ⏱️ Tiempo Total: 2-4 horas
### 💰 Costo: $0
### 🎯 Riesgo: BAJO
### ✅ Probabilidad de éxito: 95%

---

## FASE 1: OPTIMIZACIONES INMEDIATAS (1 hora)

### Paso 1.1: Agregar Índices Estratégicos

**Archivo:** `/Users/constanzaaraya/.claude-worktrees/python-automation/relaxed-elion/database.py`

**Modificar función `init_database()`:**

```python
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

    # Crear tabla products
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

    # ============= NUEVO: ÍNDICES PARA PERFORMANCE =============
    print("📊 Creando índices para optimización...")

    # Índice 1: Búsquedas por tienda (muy común en queries)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_shop
        ON webhooks(shop)
    ''')
    print("  ✅ Índice: webhooks.shop")

    # Índice 2: Ordenamiento por fecha (dashboard)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_received_at
        ON webhooks(received_at DESC)
    ''')
    print("  ✅ Índice: webhooks.received_at")

    # Índice 3: Filtros por fuente (analytics)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_webhooks_source_shop
        ON webhooks(source, shop)
    ''')
    print("  ✅ Índice: webhooks.source+shop")

    # Índice 4: Búsqueda de productos por SKU (muy común)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_shop_sku
        ON products(shop, sku)
    ''')
    print("  ✅ Índice: products.shop+sku")

    # Índice 5: Alertas de stock bajo (query frecuente)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_stock_low
        ON products(stock)
        WHERE stock < 10
    ''')
    print("  ✅ Índice parcial: products.stock<10")

    # Índice 6: Categorías ABC (analytics)
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_products_category
        ON products(category, shop)
    ''')
    print("  ✅ Índice: products.category+shop")

    print("📊 Índices creados exitosamente")
    # ===========================================================

    conn.commit()
    conn.close()
    print(f"✅ Base de datos inicializada: {DB_FILE}")
    print(f"📁 Directorio de datos: {DATA_DIR}")
```

**Beneficios:**
- Queries 10-100x más rápidos con índices
- Dashboard carga instantáneamente
- Búsquedas por SKU optimizadas
- Filtros de stock bajo ultra-rápidos

---

### Paso 1.2: VACUUM y Optimización Automática

**Crear archivo:** `/Users/constanzaaraya/.claude-worktrees/python-automation/relaxed-elion/optimize_db.py`

```python
#!/usr/bin/env python3
"""
Script de optimización de SQLite.
Ejecutar semanalmente o cuando DB > 50 MB.
"""

import sqlite3
import os
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = os.path.join(DATA_DIR, "webhooks.db")

def optimize_database():
    """
    Optimiza la base de datos SQLite:
    - VACUUM: Compacta DB, libera espacio no usado
    - ANALYZE: Actualiza estadísticas de query planner
    """
    print(f"🔧 Optimizando base de datos: {DB_FILE}")
    print(f"⏰ Timestamp: {datetime.now()}")

    # Tamaño antes
    size_before = os.path.getsize(DB_FILE) / (1024 * 1024)
    print(f"📊 Tamaño antes: {size_before:.2f} MB")

    conn = sqlite3.connect(DB_FILE)

    # VACUUM: Reconstruir DB para compactar
    print("🗜️  Ejecutando VACUUM...")
    conn.execute('VACUUM')

    # ANALYZE: Actualizar estadísticas para optimizar queries
    print("📈 Ejecutando ANALYZE...")
    conn.execute('ANALYZE')

    # Verificar integridad
    print("🔍 Verificando integridad...")
    result = conn.execute('PRAGMA integrity_check').fetchone()
    if result[0] == 'ok':
        print("✅ Integridad: OK")
    else:
        print(f"⚠️  Integridad: {result[0]}")

    conn.close()

    # Tamaño después
    size_after = os.path.getsize(DB_FILE) / (1024 * 1024)
    print(f"📊 Tamaño después: {size_after:.2f} MB")
    print(f"💾 Espacio liberado: {(size_before - size_after):.2f} MB")
    print("✅ Optimización completada")

if __name__ == "__main__":
    optimize_database()
```

**Dar permisos de ejecución:**
```bash
chmod +x optimize_db.py
```

**Ejecutar manualmente:**
```bash
python optimize_db.py
```

**Automatizar (opcional - agregar a cron local):**
```bash
# Ejecutar cada domingo a las 3 AM
0 3 * * 0 python /path/to/optimize_db.py >> /path/to/logs/optimize.log 2>&1
```

---

### Paso 1.3: Monitoreo de Salud

**Agregar a:** `/Users/constanzaaraya/.claude-worktrees/python-automation/relaxed-elion/webhook_server.py`

```python
# Agregar este endpoint después de /health

@app.route('/health/database', methods=['GET'])
def database_health():
    """
    Health check específico para base de datos.
    Retorna métricas de tamaño, performance y estado.
    """
    try:
        import sqlite3
        from database import DB_FILE

        # Tamaño del archivo
        db_size_mb = os.path.getsize(DB_FILE) / (1024 * 1024) if os.path.exists(DB_FILE) else 0

        # Contar registros
        conn = sqlite3.connect(DB_FILE)
        webhooks_count = conn.execute('SELECT COUNT(*) FROM webhooks').fetchone()[0]
        products_count = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0]

        # Verificar integridad
        integrity = conn.execute('PRAGMA integrity_check').fetchone()[0]

        # Estadísticas de última actividad
        last_webhook = conn.execute(
            'SELECT received_at FROM webhooks ORDER BY received_at DESC LIMIT 1'
        ).fetchone()

        conn.close()

        # Determinar estado
        status = 'healthy'
        warnings = []

        if db_size_mb > 100:
            warnings.append('DB size > 100 MB (consider optimization)')
        if db_size_mb > 500:
            status = 'warning'
            warnings.append('DB size > 500 MB (consider PostgreSQL migration)')
        if integrity != 'ok':
            status = 'critical'
            warnings.append(f'Integrity check failed: {integrity}')

        return jsonify({
            'status': status,
            'database': {
                'file': DB_FILE,
                'size_mb': round(db_size_mb, 2),
                'integrity': integrity,
                'webhooks_count': webhooks_count,
                'products_count': products_count,
                'last_webhook': last_webhook[0] if last_webhook else None
            },
            'thresholds': {
                'size_warning_mb': 100,
                'size_critical_mb': 500
            },
            'warnings': warnings,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500
```

**Testear:**
```bash
curl https://tranquil-freedom-production.up.railway.app/health/database
```

**Respuesta esperada:**
```json
{
  "status": "healthy",
  "database": {
    "file": "/data/webhooks.db",
    "size_mb": 0.02,
    "integrity": "ok",
    "webhooks_count": 0,
    "products_count": 0,
    "last_webhook": null
  },
  "thresholds": {
    "size_warning_mb": 100,
    "size_critical_mb": 500
  },
  "warnings": [],
  "timestamp": "2026-01-24T15:30:00"
}
```

---

## FASE 2: MONITOREO CONTINUO (30 min setup)

### Paso 2.1: Dashboard de Métricas

**Agregar a dashboard HTML:**

```html
<!-- Agregar en templates/dashboard.html -->
<div class="card">
    <h3>📊 Database Health</h3>
    <div id="db-metrics">
        <p>Size: <span id="db-size">--</span> MB</p>
        <p>Webhooks: <span id="db-webhooks">--</span></p>
        <p>Products: <span id="db-products">--</p>
        <p>Status: <span id="db-status" class="badge">--</span></p>
    </div>
</div>

<script>
// Fetch database health
fetch('/health/database')
    .then(res => res.json())
    .then(data => {
        document.getElementById('db-size').textContent = data.database.size_mb;
        document.getElementById('db-webhooks').textContent = data.database.webhooks_count;
        document.getElementById('db-products').textContent = data.database.products_count;

        const statusBadge = document.getElementById('db-status');
        statusBadge.textContent = data.status;
        statusBadge.className = `badge badge-${data.status}`;
    });
</script>
```

---

## FASE 3: DOCUMENTACIÓN (30 min)

### Paso 3.1: Crear Guía de Mantenimiento

**Archivo:** `DATABASE_MAINTENANCE.md`

```markdown
# Guía de Mantenimiento - SQLite

## Optimización Regular

**Frecuencia:** Mensual o cuando DB > 50 MB

```bash
python optimize_db.py
```

## Monitoreo

**Endpoint:** `/health/database`

**Métricas clave:**
- Size < 100 MB: OK
- Size 100-500 MB: Warning
- Size > 500 MB: Considerar PostgreSQL

## Backups

**Automático en Railway:** Volumen `/data/` tiene backups diarios

**Manual:**
```bash
# Copiar DB
cp /data/webhooks.db /data/webhooks_backup_$(date +%Y%m%d).db

# O desde local
scp user@railway:/data/webhooks.db ./backups/
```

## Troubleshooting

**Error: database is locked**
- Causa: Escrituras concurrentes
- Solución temporal: Reintentar
- Solución permanente: Migrar a PostgreSQL si frecuente

**DB crece muy rápido**
- Verificar: ¿Payloads muy grandes?
- Ejecutar: `optimize_db.py`
- Considerar: Limitar retención a 90 días
```

---

## FASE 4: TESTING (1 hora)

### Paso 4.1: Verificar Índices

```python
# test_db_optimization.py
import sqlite3
from database import DB_FILE

def test_indexes():
    """Verificar que índices se crearon correctamente"""
    conn = sqlite3.connect(DB_FILE)

    # Listar todos los índices
    indexes = conn.execute('''
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index' AND sql IS NOT NULL
    ''').fetchall()

    print("📊 Índices creados:")
    for name, table, sql in indexes:
        print(f"  ✅ {name} (tabla: {table})")

    # Verificar índices esperados
    expected_indexes = [
        'idx_webhooks_shop',
        'idx_webhooks_received_at',
        'idx_webhooks_source_shop',
        'idx_products_shop_sku',
        'idx_products_stock_low',
        'idx_products_category'
    ]

    existing = [idx[0] for idx in indexes]

    for expected in expected_indexes:
        if expected in existing:
            print(f"  ✅ {expected} encontrado")
        else:
            print(f"  ❌ {expected} FALTANTE")

    conn.close()

if __name__ == "__main__":
    test_indexes()
```

### Paso 4.2: Benchmark de Performance

```python
# benchmark_queries.py
import sqlite3
import time
from database import DB_FILE

def benchmark_query(query, description):
    """Ejecutar query y medir tiempo"""
    conn = sqlite3.connect(DB_FILE)

    start = time.time()
    result = conn.execute(query).fetchall()
    elapsed = (time.time() - start) * 1000  # ms

    conn.close()

    print(f"{description}: {elapsed:.2f}ms ({len(result)} resultados)")
    return elapsed

# Tests
print("🚀 Benchmark de Queries")
benchmark_query('SELECT * FROM webhooks ORDER BY received_at DESC LIMIT 50',
                'Dashboard webhooks recientes')
benchmark_query('SELECT * FROM products WHERE stock < 10',
                'Alertas stock bajo')
benchmark_query('SELECT * FROM products WHERE shop = "chaparrita-boots.myshopify.com"',
                'Filtrar por tienda')
```

---

## CHECKLIST DE IMPLEMENTACIÓN

**Antes de empezar:**
- [ ] Backup actual de `webhooks.db`
- [ ] Git branch: `feature/sqlite-optimization`
- [ ] Testing local primero

**FASE 1: Optimizaciones (1h)**
- [ ] Agregar índices en `database.py`
- [ ] Crear `optimize_db.py`
- [ ] Agregar endpoint `/health/database`
- [ ] Testear localmente

**FASE 2: Monitoreo (30m)**
- [ ] Actualizar dashboard con métricas DB
- [ ] Verificar endpoint funciona

**FASE 3: Documentación (30m)**
- [ ] Crear `DATABASE_MAINTENANCE.md`
- [ ] Actualizar `README.md`

**FASE 4: Testing (1h)**
- [ ] Tests de índices
- [ ] Benchmark de queries
- [ ] Verificar que todo funciona

**Deploy:**
- [ ] Commit cambios
- [ ] Push a Railway
- [ ] Verificar logs
- [ ] Testear `/health/database` en producción

---

## RESULTADOS ESPERADOS

**Performance:**
- Queries 10-100x más rápidos
- Dashboard carga < 100ms
- Búsquedas instantáneas

**Mantenibilidad:**
- Monitoreo automático
- Alertas si DB crece mucho
- Guía de troubleshooting

**Escalabilidad:**
- Soporta 10-50 clientes fácilmente
- 6-12 meses antes de necesitar PostgreSQL
- Migración futura más fácil (datos limpios)

---

## COSTO TOTAL

- **Tiempo:** 2-4 horas
- **Dinero:** $0
- **Riesgo:** Mínimo
- **Beneficio:** Alto

---

## PRÓXIMOS PASOS (Post-Optimización)

1. **Resolver problema actual:** Por qué webhooks no se guardan
2. **Continuar Shopify App:** Completar FASE 2-3
3. **Conseguir clientes beta:** 5-10 tiendas
4. **Monitorear DB health:** Revisar cada semana

**Reconsiderar PostgreSQL cuando:**
- DB > 500 MB
- Locks concurrentes frecuentes
- 20+ clientes activos
- Cliente enterprise lo requiere

---

**Creado:** 24 Enero 2026
**Autor:** Claude Code + Constanza
**Basado en:** ANALISIS_MIGRACION_POSTGRESQL.md
**Estado:** LISTO PARA IMPLEMENTAR
