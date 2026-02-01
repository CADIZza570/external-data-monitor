# 🦈🚨 WHATSAPP ALERTS - Sistema de Notificaciones Inteligente

## Alertas Proactivas que Despiertan al Director

---

## 🎯 **VISIÓN**

**El Tiburón te despierta cuando HAY que actuar.**

No más dashboards pasivos. El sistema detecta 4 condiciones críticas y te alerta vía WhatsApp con **acciones one-click** para ejecutar inmediatamente.

---

## 🔥 **4 TIPOS DE ALERTAS**

### **1. 🚨 STOCK CRÍTICO / STOCKOUT INMINENTE**

**Trigger:** Producto A/B con stock < 10 unidades Y días hasta stockout < 3

**Ejemplo:**
```
🚨 ALERTA ROJA - STOCKOUT INMINENTE

Producto: Boots Waterproof Premium
SKU: BOOTS-WP-01
Stock Actual: 8 unidades
Velocity: 3.6/día
⏰ Stockout en: 2.2 días

💡 Acción Recomendada:
Reordenar 108 unidades (30 días stock)

¿Ejecutar reorden ahora?

[Reordenar 108u] [Ver detalles] [Ignorar 24h]
```

**Quick Replies:**
- `Reordenar Xu` → POST `/api/v1/whatsapp-action` (`action=reorden`)
- `Ver detalles` → POST (`action=inventory`)
- `Ignorar 24h` → POST (`action=snooze`)

**Criterios:**
- `stock < 10`
- `velocity_daily > 0.5`
- `category IN ('A', 'B')`
- `days_to_stockout < 3`

---

### **2. ⚰️ DEAD STOCK CRECIENDO**

**Trigger:** Dead stock total > $2,000 O incremento +20% en 7 días

**Ejemplo:**
```
⚰️ ALERTA MUERTE LENTA

Dead Stock Total: $5,160.00
Productos Afectados: 5

Top Dead Stock:
1. Sandalias Beach Summer
   150u × $32.40 = $4,860.00
2. Shorts Denim Light
   80u × $28.00 = $2,240.00
3. Gafas Sol UV Protection
   45u × $18.50 = $832.50

💡 Acción Recomendada:
Lanzar Parasite Bundle con producto estrella

¿Ejecutar Bundle ahora?

[Lanzar Bundle] [Liquidar 50% off] [Ignorar]
```

**Quick Replies:**
- `Lanzar Bundle` → POST (`action=bundle`)
- `Liquidar 50% off` → POST (`action=liquidate`)
- `Ignorar` → POST (`action=snooze`)

**Criterios:**
- `stock > 50`
- `velocity_daily < 0.5`
- `total_value = SUM(stock * price) > $2,000`

---

### **3. 💹 PRICE SURGE OPORTUNIDAD**

**Trigger:** Temp Columbus < -10°C Y producto winter estrella sin surge

**Ejemplo:**
```
💹 OPORTUNIDAD FUEGO

Temperatura: -15.3°C ❄️
Producto: Chaquetas Arctic Premium
SKU: JACKET-ARC-01

Precio Actual: $89.99
Precio Surge: $103.49 (+15%)
Profit Proyectado: +$567.00

💡 Condición óptima para surge
Temp extrema + producto estrella

¿Activar Surge ahora?

[Activar Surge +15%] [Ver proyección] [No]
```

**Quick Replies:**
- `Activar Surge +15%` → POST (`action=surge`)
- `Ver proyección` → POST (`action=analyze`)
- `No` → POST (`action=snooze`)

**Criterios:**
- `temperature < -10°C`
- `velocity_daily >= 2.0`
- `stock > 20`
- `price > $30`
- `name LIKE '%boot%' OR '%jacket%' OR '%winter%'`

---

### **4. 📊 POST-MORTEM AUTOMÁTICA**

**Trigger:** 24h después de desactivar Escudo (thaw) → análisis opportunity cost

**Ejemplo:**
```
📊 POST-MORTEM AUTOMÁTICO

Freeze Duration: 2 días
Opportunity Cost: $915.00

Análisis:
• Congelaste precios 2d
• Perdimos $915 en surges
• Recomendación: Subir umbral Escudo

¿Ajustar configuración?

[Subir umbral] [Mantener] [Ver detalles]
```

**Quick Replies:**
- `Subir umbral` → POST (`action=config`)
- `Mantener` → POST (`action=snooze`)
- `Ver detalles` → POST (`action=analyze`)

**Criterios:**
- `freeze_event EXISTS`
- `thaw_timestamp < NOW() - 24h`
- `opportunity_cost > $500`

---

## 📡 **ENDPOINT**

### **GET `/api/v1/whatsapp-alerts`**

**Descripción:** Verifica todas las condiciones de alerta y retorna alertas activas

**Response:**
```json
{
  "success": true,
  "timestamp": "2026-02-01T12:00:00",
  "summary": {
    "total": 1,
    "critical": 1,
    "high": 0,
    "opportunity": 0,
    "alerts": [...]
  },
  "alerts": [
    {
      "type": "stock_critical",
      "severity": "CRÍTICO",
      "emoji": "🚨",
      "product": "Boots Waterproof Premium",
      "sku": "BOOTS-WP-01",
      "stock": 8,
      "days_to_stockout": 2.2,
      "reorder_qty": 108,
      "message": "🚨 ALERTA ROJA - STOCKOUT INMINENTE\n\nProducto: Boots Waterproof Premium\n...",
      "quick_replies": [
        {"title": "Reordenar 108u", "action": "reorden", "sku": "BOOTS-WP-01"},
        {"title": "Ver detalles", "action": "inventory", "sku": "BOOTS-WP-01"},
        {"title": "Ignorar 24h", "action": "snooze", "sku": "BOOTS-WP-01"}
      ]
    }
  ]
}
```

**Ejemplo cURL:**
```bash
curl https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-alerts
```

---

## 🛠️ **SETUP MAKE.COM**

### **Workflow 3: Alerts Checker (Cron cada 1h)**

```
[1] Schedule (Cron)
    ├─ Trigger: Every 1 hour
    └─ Run: 24/7

[2] HTTP Request - Check Alerts
    ├─ Method: GET
    ├─ URL: https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-alerts
    └─ Parse Response: Yes

[3] Filter
    ├─ Condition: {{2.summary.total}} > 0
    └─ If NO alerts: Stop workflow

[4] Iterator (Alerts)
    ├─ Array: {{2.alerts}}
    └─ For each alert: Process

[5] Twilio - Send WhatsApp Alert
    ├─ To: +1234567890 (La Chaparrita)
    ├─ From: whatsapp:+14155238886
    ├─ Body: {{4.message}}
    └─ Quick Replies: {{4.quick_replies}}

[6] Datastore - Log Alert Sent
    ├─ Timestamp: {{now}}
    ├─ Type: {{4.type}}
    ├─ Severity: {{4.severity}}
    └─ SKU: {{4.sku}}
```

### **Configuración Recomendada:**

| Tipo Alerta | Frecuencia Check | Horario |
|-------------|------------------|---------|
| Stock Crítico | Cada 1h | 8am - 10pm |
| Dead Stock | Cada 6h | 9am, 3pm, 9pm |
| Price Surge | Cada 30min | 6am - 8pm |
| Post-Mortem | Daily | 10am |

---

## 🔒 **SNOOZE MECHANISM**

Para evitar spam, implementar snooze (silenciar 24h):

```python
# En whatsapp_action_endpoint()
if action == 'snooze':
    # Guardar en DB: snooze hasta mañana
    conn.execute('''
        INSERT INTO alert_snoozes (sku, type, snooze_until)
        VALUES (?, ?, datetime('now', '+24 hours'))
    ''', (sku, alert_type))

# En WhatsAppAlertEngine.check_stock_critical()
# Verificar si está snoozed
snoozed = conn.execute('''
    SELECT 1 FROM alert_snoozes
    WHERE sku = ? AND type = 'stock_critical'
      AND snooze_until > datetime('now')
''', (sku,)).fetchone()

if snoozed:
    continue  # Skip esta alerta
```

---

## 📊 **MÉTRICAS & TRACKING**

### **Tabla DB: `alert_history`**
```sql
CREATE TABLE alert_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL,           -- stock_critical, dead_stock, etc.
    severity TEXT NOT NULL,        -- CRÍTICO, ALTO, OPORTUNIDAD
    sku TEXT,
    product_name TEXT,
    message TEXT,
    sent_whatsapp BOOLEAN DEFAULT 0,
    action_taken TEXT,             -- reorden, bundle, surge, snooze
    action_timestamp DATETIME
);
```

### **Tabla DB: `alert_snoozes`**
```sql
CREATE TABLE alert_snoozes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT NOT NULL,
    type TEXT NOT NULL,
    snooze_until DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### **Dashboard Analytics**
- 📊 Total alertas enviadas (por tipo)
- ✅ Tasa acción (% alertas con acción ejecutada)
- ⏱️ Tiempo promedio respuesta (alerta → acción)
- 💰 ROI alertas (profit de acciones ejecutadas)

---

## 🚀 **TESTING**

### **Test Local:**
```python
from whatsapp_alerts import WhatsAppAlertEngine

engine = WhatsAppAlertEngine()
engine.check_all_alerts()
summary = engine.get_alerts_summary()

print(f"Total Alertas: {summary['total']}")
for alert in engine.alerts:
    print(f"{alert['emoji']} {alert['type']} - {alert['product']}")
```

### **Test Producción:**
```bash
# Verificar alertas activas
curl https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-alerts | jq '.summary'

# Ver detalle alertas
curl -s https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-alerts | jq '.alerts[0].message'
```

---

## 🎯 **PRÓXIMOS NIVELES**

### **Fase 1: Smart Snooze** ✅ CURRENT
- Snooze 24h por SKU + tipo
- Auto-clear snooze si condición empeora

### **Fase 2: Severity Escalation**
- Alerta Stock Crítico → Si no acción en 6h → Escalar severidad
- "🚨🚨 URGENTE: Boots ahora 1.5 días stockout"

### **Fase 3: Multi-Channel**
- WhatsApp (principal)
- Email (backup si no responde 12h)
- SMS (crítico si no responde 24h)

### **Fase 4: AI Predictions**
- "📊 Predicción: En 3 días stockout Chaquetas"
- "💹 Temp bajará a -18°C mañana → Preparar surge"

### **Fase 5: Auto-Execute**
- Director configura: "Auto-reorden si stock < 5"
- Sistema ejecuta + notifica: "✅ Reorden auto: 108u Boots"

---

## 🦈 **FILOSOFÍA**

> **"El Tiburón te despierta cuando HAY sangre en el agua."**

**WhatsApp Alerts NO es:**
- ❌ Spam de notificaciones
- ❌ Resumen diario pasivo
- ❌ Métricas sin acción

**WhatsApp Alerts ES:**
- ✅ **Alarma inteligente** para condiciones críticas
- ✅ **Acción inmediata** con un click
- ✅ **Opportunity radar** 24/7

---

**🦈🚨 ALERTAS LIVE - EL TIBURÓN NUNCA DUERME**

*Desarrollado con visión de Gemini*
*Ejecutado por Claude*
*Powered by La Chaparrita*
