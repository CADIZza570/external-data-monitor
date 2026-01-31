# 🌱 Seed Production - Guía para Deployar Datos Reales

## ✅ STATUS ACTUAL

- ✅ Seed local ejecutado: 10 productos Columbus
- ✅ DB local poblada: `webhooks.db` (14KB datos)
- ✅ Test local exitoso: ROI 100-155% calculado
- ⚠️ Endpoint API seed: Tiene issues con schema DB Railway

---

## 🎯 OPCIÓN 1: Endpoint API (Cuando se fixee)

```bash
curl -X POST https://tranquil-freedom-production.up.railway.app/api/admin/seed-columbus \
  -H "Content-Type: application/json" \
  -d '{"admin_key":"tiburon-seed-2026"}'
```

**Status:** ⚠️ Error 500 (schema mismatch)

---

## 🎯 OPCIÓN 2: Railway CLI (RECOMENDADO)

### Prerequisitos
```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link al proyecto
railway link
```

### Seed via Railway Shell

```bash
# 1. Copiar seed script a Railway
railway run python3 seed_real_data.py

# O manual:
railway shell

# Dentro del shell:
python3
>>> from seed_real_data import main
>>> main()
```

---

## 🎯 OPCIÓN 3: Copy DB Local → Railway (Manual)

### Paso 1: Exportar datos locales

```bash
# Exportar productos a SQL
sqlite3 webhooks.db << EOF
.mode insert products
.output /tmp/products_export.sql
SELECT * FROM products WHERE category IN ('A', 'B', 'C', 'Dead');
.quit
EOF

# Exportar ventas
sqlite3 webhooks.db << EOF
.mode insert sales_history
.output /tmp/sales_export.sql
SELECT * FROM sales_history WHERE shop = 'columbus-shop';
.quit
EOF
```

### Paso 2: SSH Railway y ejecutar SQL

```bash
railway shell

# Copiar contenido de /tmp/products_export.sql y ejecutar
# Copiar contenido de /tmp/sales_export.sql y ejecutar
```

---

## 🎯 OPCIÓN 4: Usar Script Python Helper

Ya tenés `deploy_seed_columbus.py`:

```bash
python3 deploy_seed_columbus.py
# Elegir opción 2: Seed REAL
```

**Status:** ⚠️ Depende del endpoint API (mismo issue)

---

## 📊 VERIFICAR SEED EXITOSO

Una vez seeded en Railway:

```bash
# 1. Cash flow summary
curl https://tranquil-freedom-production.up.railway.app/api/cashflow/summary | python3 -m json.tool

# Debe mostrar:
# - total_inventory_value > 0
# - productos Columbus presentes

# 2. External signals con producto real
curl "https://tranquil-freedom-production.up.railway.app/api/debug/external-signals?product_name=Chaqueta" | python3 -m json.tool

# Debe mostrar multiplicador por frío

# 3. Trigger Pulse manual (si endpoint existe)
# Ver Sticker en Discord con productos Columbus
```

---

## 🔧 TROUBLESHOOTING

### Error: "column total_sales_60d not found"

**Fix:** Railway DB no tiene columna `total_sales_60d`.

**Solución A** (ALTER TABLE vía Railway shell):
```sql
ALTER TABLE products ADD COLUMN total_sales_60d INTEGER DEFAULT 0;
```

**Solución B** (No usar esa columna):
- Ya aplicado en último commit
- Endpoint solo usa columnas existentes

### Error 500 en endpoint seed

**Causa:** Schema mismatch entre DB local y Railway.

**Solución:** Usar Railway CLI (Opción 2) en lugar de endpoint API.

### Productos no aparecen en cash flow

**Verificar:**
```bash
# Railway shell
railway shell

# Python interactivo
python3
>>> import sqlite3
>>> conn = sqlite3.connect('webhooks.db')
>>> cursor = conn.cursor()
>>> cursor.execute("SELECT COUNT(*) FROM products WHERE shop='columbus-shop'")
>>> print(cursor.fetchone())
# Debe mostrar: (8,) o más
```

---

## 🦈 RESULTADO ESPERADO

Una vez seeded correctamente:

**Sticker Discord (Pulso diario 8:00 AM):**
```
🦈 TIBURÓN PREDICTIVO - PULSO DIARIO
⏰ 2026-02-01 08:00

🌡️ Columbus, Ohio: -20.6°C, Clear
🎉 Próximo feriado: Valentine's Day (en 13 días)

💰 Cash Flow:
- Inventario: $14,515
- Stockout Cost: $2,400/mes
- Dead Stock: $5,160

📊 TOP OPORTUNIDADES (ROI Predictivo):
1. Boots Waterproof: ROI 100% (19 unidades)
   🌡️ Frío extremo Columbus → spike en Boots

2. Chaqueta Térmica: ROI 100% (22 unidades)
   🌡️ Frío extremo Columbus → spike en Chaqueta

3. Guantes Arctic: ROI 155% (31 unidades)
   🌡️ Frío extremo Columbus → spike en Guantes

Veredicto: 🛡️ Modo cautela - 35.5% inventario muerto
```

---

## 🚀 PRÓXIMOS PASOS POST-SEED

1. ✅ Verificar Pulso diario (8:00 AM) en Discord
2. ✅ Monitorear clima Columbus (spike en frío extremo)
3. ✅ Testear botones interactivos (reorder)
4. ✅ Ajustar multiplicadores si necesario
5. ✅ WhatsApp bridge (opcional)

---

¡El Tiburón está listo para cazar con datos Columbus! 🦈🔥
