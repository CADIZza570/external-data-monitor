# 🔧 MAKE.COM TWILIO FIX - BundleValidationError

## Problema Actual

**Error:** `BundleValidationError: Missing value of required parameter 'body'`

**Causa:** Mapeo incorrecto en módulo Twilio de Make.com

**Status:** Scenario desactivado automáticamente

---

## ✅ Confirmación: Campo "message" Existe

**Estructura JSON enviada a Make.com:**

```json
{
  "success": true,
  "order_id": 1028,
  "order_number": 1028,
  "total_price": 260.0,
  "message": "🛒 NUEVA VENTA - Orden #1028\n\n👤 Cliente: Mario Castaneda\n💰 Total: $260.00\n\n📦 Productos (1):\n• Botas Camping\n  1u × $260.00\n  Stock: 0→0\n\n🚨 ALERTAS (1):\n🎉 MILESTONE_1K_DAY\n  Ventas hoy: $2,242.87\n\n🦈 Tiburón procesó orden en tiempo real",
  "alerts": [
    {
      "type": "milestone_1k_day",
      "severity": "CELEBRACIÓN",
      "emoji": "🎉",
      "amount": 2242.87,
      "message": "🎉 MILESTONE ALCANZADO\n\nVentas hoy: $2,242.87\n¡Superamos $1,000 en 1 día!"
    }
  ],
  "metrics_updated": [
    {
      "sku": "BTA-CG-PTN-NAT-065",
      "product_name": "Botas Camping",
      "quantity": 1,
      "price": 260.0,
      "old_stock": 0,
      "new_stock": 0,
      "new_velocity": 0.03333333333333333,
      "roi": 100.0
    }
  ]
}
```

**Campo `message` confirmado:** ✅ Línea 7 del JSON

---

## 🔧 Solución: Corregir Mapeo Make.com

### Paso 1: Re-Determinar Estructura Datos (CRÍTICO)

**Make.com Scenario:**
1. Click en módulo **Webhooks** (primer módulo)
2. Click botón **Re-determine data structure**
3. Make.com mostrará: "Waiting for webhook data..."

**Enviar test payload:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: shark-predator-2026" \
  -d '{
    "id": 9999,
    "order_number": 9999,
    "total_price": "100.00",
    "customer": {"first_name": "Test", "last_name": "Make"},
    "line_items": [
      {"sku": "TEST-SKU", "title": "Test Product", "quantity": 1, "price": "100.00"}
    ]
  }' \
  https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders
```

**Make.com capturará:**
- `success`
- `order_number`
- `total_price`
- `message` ← **ESTE CAMPO ES CLAVE**
- `alerts[]`
- `metrics_updated[]`

### Paso 2: Configurar Módulo Twilio Correctamente

**Twilio → Send WhatsApp Message**

**Campos requeridos:**

| Campo | Valor | Descripción |
|-------|-------|-------------|
| **Account SID** | Tu SID Twilio | Copiar de Twilio Console |
| **Auth Token** | Tu token Twilio | Copiar de Twilio Console |
| **From** | `whatsapp:+14155238886` | Número Twilio Sandbox |
| **To** | `whatsapp:+1XXXXXXXXXX` | Tu número WhatsApp |
| **Body** | `{{message}}` | **SIN prefijo 1.** |

**IMPORTANTE - Mapeo Body:**

❌ **INCORRECTO:**
- `{{1.message}}` (con prefijo de módulo)
- `{{data.message}}` (path incorrecto)
- Texto hardcodeado

✅ **CORRECTO:**
- `{{message}}` (sin prefijo, Make.com auto-detecta del webhook)

**Visual en Make.com:**
```
Body: [Click para mapear]
  └─ Seleccionar de lista: "message"
  └─ NO escribir manualmente "{{1.message}}"
```

### Paso 3: Verificar Conexión Twilio

**Twilio Console:**
1. Ir a: https://console.twilio.com/
2. Verificar Account SID y Auth Token coinciden
3. Verificar número WhatsApp registrado en Sandbox
4. Test: Enviar "join <sandbox-code>" a Twilio número

**Si no recibes código:**
- WhatsApp Sandbox → Manage → Ver join code
- Enviar mensaje a `+1 415 523 8886`
- Esperar confirmación "You are all set!"

### Paso 4: Activar Scenario

**Make.com:**
1. Verificar módulo Webhooks: Estructura determinada ✅
2. Verificar módulo Twilio: Body mapeado a `{{message}}` ✅
3. Toggle scenario: **ON** (activar)
4. Click **Run once** para test

---

## 🧪 Test Completo End-to-End

### Test 1: Enviar Orden a Railway

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: shark-predator-2026" \
  -d '{
    "id": 8888,
    "order_number": 8888,
    "total_price": "89.99",
    "customer": {
      "first_name": "WhatsApp",
      "last_name": "Test"
    },
    "line_items": [
      {
        "sku": "BOOTS-WP-01",
        "title": "Boots Waterproof Premium",
        "quantity": 1,
        "price": "89.99"
      }
    ]
  }' \
  https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders
```

### Test 2: Verificar Logs Railway

**Railway logs:**
```
📥 Webhook recibido: order_id=8888, order_number=8888
✅ X-Admin-Key verificado - llamada manual
🧠 Cerebro Central: Procesando orden...
✅ Orden procesada: 1 alertas generadas
✅ Webhook procesado: True
📤 Enviando a Make.com webhook...
✅ Make.com webhook enviado exitosamente
```

**Si ves:** `⚠️ MAKE_WEBHOOK_URL no configurado`
- Agregar variable en Railway (ver abajo)

### Test 3: Verificar Make.com Execution

**Make.com → History:**
- Ver ejecución más reciente
- Verificar módulo Webhooks: Data received ✅
- Verificar módulo Twilio: Executed successfully ✅

### Test 4: Verificar WhatsApp

**Tu teléfono:**
```
🛒 NUEVA VENTA - Orden #8888

👤 Cliente: WhatsApp Test
💰 Total: $89.99

📦 Productos (1):
• Boots Waterproof Premium
  1u × $89.99
  Stock: X→Y

🚨 ALERTAS (1):
🚨 STOCK_CRITICAL_POST_SALE
  Boots: Yu (Stockout Zd)

🦈 Tiburón procesó orden en tiempo real
```

---

## 🔍 Debugging Paso a Paso

### Si Make.com NO Recibe Webhook

**Verificar Variable Railway:**
```bash
railway variables | grep MAKE_WEBHOOK_URL
```

**Debe mostrar:**
```
MAKE_WEBHOOK_URL=https://hook.us2.make.com/9ltd4s2fbwslwp2o3qgswysapaw3973f
```

**Si NO aparece:**
1. Railway Dashboard → Variables → Add Variable
2. Name: `MAKE_WEBHOOK_URL`
3. Value: `https://hook.us2.make.com/9ltd4s2fbwslwp2o3qgswysapaw3973f`
4. Save → Auto-redeploy (~60s)

### Si Make.com Recibe pero Twilio Falla

**Error: Missing parameter 'body'**

**Solución:**
1. Make.com → Scenario → Click módulo Twilio
2. Body field → Borrar contenido actual
3. Click en Body field → Seleccionar de lista: `message`
4. Verificar que aparezca solo: `{{message}}`
5. Save scenario
6. Run once

**Error: Account SID/Token inválido**

**Solución:**
1. Twilio Console → Copiar SID y Token nuevos
2. Make.com → Módulo Twilio → Re-ingresar credenciales
3. Save → Run once

**Error: Phone number not registered**

**Solución:**
1. WhatsApp: Enviar `join <code>` a +1 415 523 8886
2. Esperar confirmación Twilio
3. Retry Make.com scenario

---

## 📋 Checklist Pre-Test

- [ ] Variable `MAKE_WEBHOOK_URL` en Railway
- [ ] Railway redeploy completado
- [ ] Make.com: Webhooks data structure determinada
- [ ] Make.com: Twilio Body mapeado a `{{message}}`
- [ ] Make.com: Account SID configurado
- [ ] Make.com: Auth Token configurado
- [ ] Make.com: From = `whatsapp:+14155238886`
- [ ] Make.com: To = tu número WhatsApp
- [ ] Make.com: Scenario status = **ON**
- [ ] Twilio: WhatsApp Sandbox activo
- [ ] Twilio: Tu número registrado (join enviado)

---

## 💡 Tips Make.com

### Mapeo Correcto de Campos

**Para acceder a campos del webhook:**
- Nivel raíz: `{{message}}`, `{{success}}`, `{{order_number}}`
- Array: `{{alerts[].type}}`, `{{metrics_updated[].sku}}`
- NO usar prefijos como `1.` a menos que sea otro módulo

### Router Condicional (Opcional)

**Si solo quieres alertas críticas:**

**Router → Filter:**
```
Condition: {{length(alerts)}} > 0
```

**O filtrar por severity:**
```
Condition: {{alerts[1].severity}} = "CRÍTICO"
```

### Multiple Actions (Avanzado)

**Puedes agregar más módulos:**
```
Webhook
  ↓
Router
  ├─ Si crítico → Twilio WhatsApp
  ├─ Si medio → Email
  └─ Siempre → Google Sheets log
```

---

## 🎯 Resultado Esperado

**Flujo completo exitoso:**

1. ✅ Shopify order created
2. ✅ Webhook → Railway Cerebro
3. ✅ Cerebro procesa (stock, velocity, alertas)
4. ✅ Cerebro → Make.com POST
5. ✅ Make.com recibe JSON con `message`
6. ✅ Make.com ejecuta Twilio
7. ✅ Twilio envía WhatsApp
8. ✅ **Recibes mensaje en < 5 segundos**

**Latencia total esperada:** 2-5 segundos

---

## 📱 Ejemplo Mensaje Real

```
🛒 NUEVA VENTA - Orden #1028

👤 Cliente: Mario Castaneda
💰 Total: $260.00

📦 Productos (1):
• BTA-CG-PTN-NAT-065
  1u × $260.00
  Stock: 0→0

🚨 ALERTAS (1):
🎉 MILESTONE_1K_DAY
  Ventas hoy: $2,242.87

🦈 Tiburón procesó orden en tiempo real
```

---

**🔧 MAKE.COM TWILIO FIX READY**

**Updated:** 2026-02-01 21:00 EST
**Key Fix:** Mapear Body a `{{message}}` (sin prefijo)
**Status:** ✅ Instrucciones completas
**Next:** Re-determinar estructura → Mapear Body → Activar
