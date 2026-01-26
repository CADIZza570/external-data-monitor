# 📚 GUÍA DE MIGRACIÓN DE BASE DE DATOS EN RAILWAY

## Contexto del Problema
Cuando necesitas agregar nuevas columnas a una base de datos que ya está en producción en Railway, debes coordinar la migración para que ocurra **ANTES** de que el servidor Flask inicie.

---

## ⚠️ El Error Común

**Problema:** La migración falla porque intenta agregar columnas a una tabla que aún no existe.

**Orden incorrecto:**
```
1. start.sh ejecuta migrate_db_cashflow.py ❌ (tabla no existe)
2. webhook_server.py importa database.py ✅ (crea tabla)
```

**Resultado:** ERROR - "no such table: products"

---

## ✅ La Solución Correcta

**Orden correcto:**
```
1. Migración crea la tabla primero (CREATE TABLE IF NOT EXISTS)
2. Migración agrega columnas nuevas (ALTER TABLE ADD COLUMN)
3. Servidor Flask inicia
```

---

## 📝 Pasos para Implementar Migración en Railway

### **PASO 1: Crear el script de migración**

Archivo: `migrate_db_cashflow.py`

```python
#!/usr/bin/env python3
import sqlite3
import os

# Usar el mismo DATA_DIR que database.py
DATA_DIR = os.getenv("DATA_DIR", ".")
DB_FILE = f"{DATA_DIR}/webhooks.db"

# Crear directorio si no existe
os.makedirs(DATA_DIR, exist_ok=True)

def migrate_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # ============= CRÍTICO: CREAR TABLA PRIMERO =============
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
    conn.commit()
    print("✅ Tabla 'products' verificada/creada")
    # ====================================================

    # Ahora agregar columnas nuevas
    migrations = [
        ("cost_price", "REAL DEFAULT 0", "Costo de adquisición"),
        ("last_sale_date", "TIMESTAMP", "Última fecha de venta"),
        # ... más columnas
    ]

    # Verificar columnas existentes
    cursor.execute("PRAGMA table_info(products)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    # Agregar solo las que faltan
    for column_name, column_type, description in migrations:
        if column_name not in existing_columns:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {column_name} {column_type}")
            print(f"✅ Columna agregada: {column_name}")

    conn.commit()
    conn.close()
    return True

if __name__ == "__main__":
    migrate_database()
```

**⚠️ Puntos críticos:**
- `CREATE TABLE IF NOT EXISTS` debe estar PRIMERO
- Usar `PRAGMA table_info()` para verificar columnas existentes
- Solo agregar columnas que no existen (idempotencia)

---

### **PASO 2: Crear script de inicio**

Archivo: `start.sh`

```bash
#!/bin/bash
set -e  # Exit on error

echo "============================================================"
echo "🚀 INICIANDO SERVIDOR"
echo "============================================================"

# PASO 1: MIGRACIÓN DE BASE DE DATOS
echo "📊 PASO 1: Verificando migración de base de datos..."

if python3 migrate_db_cashflow.py; then
    echo "✅ Migración completada exitosamente"
else
    echo "⚠️  Migración falló (continuando...)"
fi

# PASO 2: LEVANTAR SERVIDOR FLASK
echo "🌐 PASO 2: Levantando servidor Flask..."

exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 webhook_server:app
```

**⚠️ Puntos críticos:**
- `set -e` detiene todo si hay error
- Migración se ejecuta ANTES de gunicorn
- `exec` reemplaza el proceso para que Railway lo maneje correctamente

---

### **PASO 3: Configurar Railway**

Archivo: `railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "numReplicas": 1,
    "startCommand": "bash start.sh",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10,
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30
  },
  "environments": {
    "production": {
      "variables": {
        "DATA_DIR": "/data"
      }
    }
  }
}
```

**⚠️ Puntos críticos:**
- `"startCommand": "bash start.sh"` (NO usar gunicorn directamente)
- `DATA_DIR` debe coincidir con el usado en `migrate_db_cashflow.py`

---

### **PASO 4: Dar permisos de ejecución**

```bash
chmod +x start.sh
```

---

### **PASO 5: Commit y Deploy**

```bash
# Agregar archivos
git add migrate_db_cashflow.py start.sh railway.json

# Commit descriptivo
git commit -m "Add database migration with start.sh

- Creates products table before adding columns
- Runs migration before Flask server starts
- Ensures idempotent migrations"

# Push a rama de desarrollo
git push origin nombre-rama

# Crear PR y mergear a main
gh pr create --title "Database migration" --base main --head nombre-rama
gh pr merge NUMERO --squash
```

---

## 🔍 Verificar que Funcionó

**Ver logs en Railway:**

Deberías ver:
```
✅ Tabla 'products' verificada/creada
✅ Columna agregada: cost_price
✅ Columna agregada: last_sale_date
📊 ESTADO FINAL DE LA TABLA 'products':
Total de columnas: 13
✅ Migración completada exitosamente
🌐 Levantando servidor Flask...
[INFO] Starting gunicorn
```

---

## 🚨 Troubleshooting

| Error | Causa | Solución |
|-------|-------|----------|
| `no such table: products` | Migración corre después del servidor | Usar `start.sh` con migración primero |
| `duplicate column name` | Columna ya existe | Usar `PRAGMA table_info()` para verificar |
| `Migration timeout` | Script de migración muy lento | Optimizar queries, aumentar timeout |
| `Permission denied: start.sh` | Falta permisos de ejecución | `chmod +x start.sh` |

---

## 📌 Checklist Pre-Deploy

- [ ] Script de migración tiene `CREATE TABLE IF NOT EXISTS` primero
- [ ] Script verifica columnas existentes antes de agregar
- [ ] `start.sh` ejecuta migración ANTES del servidor
- [ ] `railway.json` usa `"startCommand": "bash start.sh"`
- [ ] `start.sh` tiene permisos de ejecución (`chmod +x`)
- [ ] `DATA_DIR` coincide en todos los archivos
- [ ] Commit y push a rama, luego merge a `main`

---

## 💡 Buenas Prácticas

1. **Siempre crear tabla antes de modificarla**
2. **Usar `IF NOT EXISTS` para idempotencia**
3. **Verificar columnas existentes antes de agregar**
4. **Logs descriptivos para debugging**
5. **Mantener `start.sh` simple y enfocado**
6. **No usar `gunicorn` directamente en `railway.json`**

---

## 📖 Ejemplo Real: Migración Cash Flow System

Este fue el caso que resolvimos:

**Problema:** Al agregar el sistema de Cash Flow, necesitábamos 5 columnas nuevas en la tabla `products`:
- `cost_price`: Costo de adquisición
- `last_sale_date`: Última fecha de venta
- `total_sales_30d`: Ventas últimos 30 días
- `category`: Clasificación ABC
- `velocity_daily`: Velocidad de ventas diaria

**Solución implementada:**
1. Script `migrate_db_cashflow.py` crea tabla `products` primero
2. Luego agrega las 5 columnas nuevas
3. Crea tablas adicionales `product_costs` y `orders_history`
4. `start.sh` ejecuta migración antes de gunicorn
5. Deploy exitoso en Railway

**Resultado:**
```
✅ Tabla 'products' verificada/creada
✅ Columnas existentes: ['id', 'product_id', 'name', 'sku', 'stock', 'price', 'shop', 'last_updated']
✅ Columna agregada: cost_price (Costo de adquisición)
✅ Columna agregada: last_sale_date (Última fecha de venta)
✅ Columna agregada: total_sales_30d (Ventas últimos 30 días)
✅ Columna agregada: category (Clasificación ABC (A/B/C))
✅ Columna agregada: velocity_daily (Velocidad de ventas diaria (VDP))
📊 ESTADO FINAL: 13 columnas totales
```

---

**Creado:** 2026-01-18
**Última actualización:** 2026-01-18
**Autor:** Claude Code + Constanza
