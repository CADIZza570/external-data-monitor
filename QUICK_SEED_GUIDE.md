# 🦈 QUICK SEED - Producción Railway YA

## ⚡ SOLUCIÓN RÁPIDA (Sin CLI, Sin Endpoint complicado)

El endpoint `/api/admin/seed-columbus` tiene un bug (Error 500). Aquí está la solución **MÁS RÁPIDA** para seed en producción:

---

## 🎯 OPCIÓN ULTRA-RÁPIDA: SQL Directo via Railway Dashboard

### Paso 1: Acceder a Railway Database

1. Ir a https://railway.app
2. Tu proyecto → Service `main`
3. Click **Data** tab (si existe DB PostgreSQL/MySQL)
   O **Variables** → Encontrar `DATABASE_URL`

### Paso 2: Railway No Usa DB Relacional Externa

Railway usa **SQLite local** (`webhooks.db` en el filesystem del contenedor).

**Problema:** No hay acceso directo SQL sin Railway CLI.

---

## 🚀 SOLUCIÓN DEFINITIVA: Railway CLI (5 min setup)

Ya que el endpoint tiene bugs, la forma MÁS CONFIABLE es Railway CLI:

### Instalación

```bash
# Mac/Linux
curl -fsSL https://railway.app/install.sh | sh

# O con npm (si tenés Node.js)
npm install -g @railway/cli

# Verificar
railway --version
```

### Seed Paso a Paso

```bash
# 1. Login
railway login
# (Abre browser, autorizar)

# 2. Link al proyecto
cd /Users/constanzaaraya/.claude-worktrees/python-automation/laughing-bose
railway link
# Elegir: "external-data-monitor"
# Service: "tranquil-freedom-production"

# 3. Copiar script seed a Railway
railway run bash

# Dentro del shell Railway:
# Ver si seed_real_data.py existe
ls -la | grep seed

# Si NO existe, crear manualmente:
cat > seed_columbus_simple.py << 'EOF'
#!/usr/bin/env python3
import sqlite3
from datetime import datetime, timedelta

DB_FILE = "./webhooks.db"

products = [
    ("WINTER-001", "Chaqueta Térmica Winter Pro", "JACKET-WINTER-01", 12, 189.99, 95.00, 3.2, 96, "A", "columbus-shop"),
    ("WINTER-002", "Boots Waterproof Premium", "BOOTS-WP-01", 8, 159.99, 80.00, 2.8, 84, "A", "columbus-shop"),
    ("WINTER-003", "Guantes Térmicos Arctic", "GLOVES-ARC-01", 25, 45.99, 18.00, 4.5, 135, "A", "columbus-shop"),
]

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

for p in products:
    cursor.execute("""
        INSERT OR REPLACE INTO products
        (product_id, name, sku, stock, price, cost_price, velocity_daily, total_sales_30d, category, shop, last_updated, last_sale_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (*p, datetime.now().isoformat(), (datetime.now() - timedelta(days=1)).isoformat()))

conn.commit()
print(f"✅ {len(products)} productos insertados")
conn.close()
EOF

# 4. Ejecutar seed
python3 seed_columbus_simple.py

# 5. Verificar
python3 -c "import sqlite3; conn=sqlite3.connect('webhooks.db'); cursor=conn.cursor(); cursor.execute('SELECT COUNT(*) FROM products WHERE shop=\"columbus-shop\"'); print(f'Productos Columbus: {cursor.fetchone()[0]}')"

# 6. Salir
exit
```

---

## ✅ VERIFICAR SEED EXITOSO

Después de ejecutar seed:

```bash
# 1. Cash flow summary
curl https://tranquil-freedom-production.up.railway.app/api/cashflow/summary | python3 -m json.tool | grep -A5 total_inventory_value

# Debe mostrar total_inventory_value > 0

# 2. External signals con producto real
curl "https://tranquil-freedom-production.up.railway.app/api/debug/external-signals?product_name=Chaqueta" | python3 -m json.tool | grep -A3 weather_impact

# Debe mostrar multiplicador por frío Columbus

# 3. Ver próximo Pulso diario (8:00 AM)
# Discord debe recibir Sticker con productos Columbus
```

---

## 🔧 TROUBLESHOOTING Endpoint /api/admin/seed-columbus

### Error 500 Persistente

**Causa probable:** Schema mismatch o error en INSERT.

**Debug en Railway:**

```bash
railway logs
# Buscar líneas con "Error seeding" o traceback
```

**Fix temporal:** Usar Railway CLI en lugar de endpoint.

---

## 📊 RESULTADO ESPERADO

Una vez seeded:

**Cash Flow API:**
```json
{
  "total_inventory_value": 1415.97,  // ~3 productos
  "stockout_opportunity_cost": 800,
  "category_breakdown": {
    "A": 3  // Chaqueta, Boots, Guantes
  }
}
```

**Sticker Discord (8:00 AM):**
```
🦈 TIBURÓN PREDICTIVO
🌡️ Columbus: -20.6°C, Clear

📊 TOP OPORTUNIDADES:
1. Guantes Arctic: ROI 155% (31 units)
   🌡️ Frío extremo → spike
2. Chaqueta Térmica: ROI 100% (22 units)
   🌡️ Frío extremo → spike
```

---

## 🎯 DECISIÓN RÁPIDA

**Opción A: Instalar Railway CLI** (5 min)
- Más control
- Más confiable
- Seed completo (8 productos + ventas)

**Opción B: Fix endpoint + retry** (10-15 min)
- Debuggear error 500
- Arreglar schema mismatch
- Testear nuevamente

**Opción C: Seed manual minimal** (2 min via Railway dashboard)
- Solo 2-3 productos
- Sin Railway CLI
- Suficiente para testear Pulso

---

**Recomendación:** **Opción A** (Railway CLI) - Setup 1 vez, usar siempre.

¡Dale gas! 🦈🔥
