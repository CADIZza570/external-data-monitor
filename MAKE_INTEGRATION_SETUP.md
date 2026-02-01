# 🔗 MAKE.COM INTEGRATION - Setup Guide

## Status: DEPLOYED ✅

**Commit:** #16 (896de61)
**Feature:** Auto-envío a Make.com después de procesar orden Shopify
**Railway:** ✅ LIVE (esperando env var)

---

## Flujo Completo End-to-End

```
SHOPIFY ORDER
    ↓ (webhook POST)
CEREBRO CENTRAL (Railway)
    ↓ (procesa orden, detecta alertas)
MAKE.COM WEBHOOK
    ↓ (recibe JSON con message)
TWILIO WHATSAPP
    ↓ (envía message)
TU TELÉFONO 📱
```

---

## 1. Configurar Variable en Railway (2 min)

### URL Make.com Webhook

**Tu webhook URL:**
```
https://hook.us2.make.com/9ltd4s2fbwslwp2o3qgswysapaw3973f
```

### Pasos Railway:

1. **Railway Dashboard** → Tu proyecto
2. **Variables** → Add Variable
3. **Name:** `MAKE_WEBHOOK_URL`
4. **Value:** `https://hook.us2.make.com/9ltd4s2fbwslwp2o3qgswysapaw3973f`
5. **Save** → Railway auto-redeploy (~60s)

---

## 2. Payload JSON Enviado a Make.com

**Formato completo:**

```json
{
  "success": true,
  "order_id": 123456789,
  "order_number": 1001,
  "total_price": 145.99,
  "message": "🛒 NUEVA VENTA - Orden #1001\n\n👤 Cliente: María González\n💰 Total: $145.99\n\n📦 Productos (2):\n• Boots Waterproof Premium\n  1u × $89.99\n  Stock: 8→7\n• Chaquetas Arctic Premium\n  1u × $56.00\n  Stock: 15→14\n\n🚨 ALERTAS (1):\n🚨 STOCK_CRITICAL_POST_SALE\n  Boots: 7u (Stockout 2.3d)\n\n🦈 Tiburón procesó orden en tiempo real",
  "alerts": [
    {
      "type": "stock_critical_post_sale",
      "severity": "CRÍTICO",
      "emoji": "🚨",
      "product": "Boots Waterproof Premium",
      "sku": "BOOTS-WP-01",
      "stock": 7,
      "days_to_stockout": 2.3,
      "message": "🚨 ALERTA POST-VENTA\n\nBoots Waterproof Premium\nStock: 7u → Stockout en 2.3 días"
    }
  ],
  "metrics_updated": [
    {
      "sku": "BOOTS-WP-01",
      "product_name": "Boots Waterproof Premium",
      "quantity": 1,
      "price": 89.99,
      "old_stock": 8,
      "new_stock": 7,
      "new_velocity": 3.2,
      "roi": 24.99
    }
  ]
}
```

**Campo clave para WhatsApp:**
- `message` → Texto formateado listo para enviar

---

## 3. Configurar Scenario Make.com (5 min)

### Módulos Necesarios:

#### Módulo 1: Webhooks (Trigger)
- **Tool:** Webhooks → Custom Webhook
- **URL:** `https://hook.us2.make.com/9ltd4s2fbwslwp2o3qgswysapaw3973f`
- **Determinar estructura de datos:** Run Once (para capturar payload)

#### Módulo 2: Router (Opcional - Filter)
- **Condition:** `{{alerts.length}} > 0`
- **Solo envía WhatsApp si hay alertas**
- Si quieres recibir TODAS las órdenes, salta este módulo

#### Módulo 3: Twilio → Send WhatsApp Message
- **Account SID:** Tu SID Twilio
- **Auth Token:** Tu token Twilio
- **From:** `whatsapp:+14155238886` (Twilio Sandbox)
- **To:** `whatsapp:+1XXXXXXXXXX` (tu número)
- **Body:** `{{message}}`

**IMPORTANTE:** Usa `{{message}}` del payload, NO manualmente construir

---

## 4. Verificar Configuración

### Checklist Pre-Test:

- [ ] Variable `MAKE_WEBHOOK_URL` configurada en Railway
- [ ] Railway redeploy completado (~60s)
- [ ] Make.com Scenario creado con 3 módulos
- [ ] Twilio WhatsApp configurado (Account SID + Token)
- [ ] Tu número WhatsApp registrado en Twilio Sandbox
- [ ] Scenario Make.com status: **Active** (toggle ON)

---

## 5. Test End-to-End

### Paso 1: Test Manual con X-Admin-Key

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: shark-predator-2026" \
  -d '{
    "id": 888888888,
    "order_number": 888,
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

**Resultado esperado:**
1. Railway logs: `📤 Enviando a Make.com webhook...`
2. Railway logs: `✅ Make.com webhook enviado exitosamente`
3. Make.com recibe payload
4. Twilio envía WhatsApp
5. ✅ **Recibes mensaje en tu teléfono**

### Paso 2: Test con Orden Real Shopify

1. Crear orden prueba en Shopify
2. Completar pago
3. Shopify dispara webhook
4. Cerebro procesa orden
5. Make.com recibe JSON
6. ✅ **Recibes alerta WhatsApp instantánea**

---

## 6. Debugging

### Caso 1: Make.com NO Recibe Payload

**Síntoma:**
- Railway logs: `📤 Enviando a Make.com webhook...`
- Railway logs: `⚠️ Make.com respondió con status 400/500`

**Solución:**
1. Verificar URL Make.com (copiar/pegar exactamente)
2. Make.com → Scenario → Run Once (capturar estructura)
3. Verificar Scenario status: Active

### Caso 2: WhatsApp NO Llega

**Síntoma:**
- Make.com recibe payload OK
- Twilio módulo ejecuta OK
- No llega mensaje

**Solución:**
1. Verificar número registrado en Twilio Sandbox
2. Enviar mensaje "join <sandbox-code>" a Twilio
3. Verificar formato número: `whatsapp:+1XXXXXXXXXX`
4. Ver logs Twilio para errores

### Caso 3: Railway Timeout Make.com

**Síntoma:**
- Railway logs: `❌ Timeout enviando a Make.com (>5s)`

**Causa:**
- Make.com scenario lento (>5s)

**Solución:**
- OK, timeout no bloquea respuesta a Shopify
- Make.com ejecutará cuando pueda
- Considerar simplificar scenario

---

## 7. Logs Esperados Railway

**Flujo exitoso completo:**

```
📥 Webhook recibido: order_id=123456, order_number=1001
🔐 Verificando HMAC Shopify...
🔐 HMAC Debug:
  Secret configurado: ***abc123
  Payload size: 2345 bytes
  HMAC recibido: mNRP7rn/8wZU...
  HMAC calculado: mNRP7rn/8wZU...
  Match: True
✅ HMAC verificado - webhook Shopify auténtico
🧠 Cerebro Central: Procesando orden...
📦 Orden #1001 - María González - $145.99
  📊 BOOTS-WP-01: stock 8→7, velocity 3.2/día
🚨 Alerta detectada: Stock crítico (stockout 2.3d)
✅ Orden procesada: 1 alertas generadas
✅ Webhook procesado: True
📤 Enviando a Make.com webhook...
✅ Make.com webhook enviado exitosamente
```

---

## 8. Payload Fields Disponibles en Make.com

**Mapeo para Twilio/otros módulos:**

| Campo | Tipo | Descripción | Uso |
|-------|------|-------------|-----|
| `message` | string | WhatsApp formatted message | Twilio body |
| `success` | boolean | Si procesamiento OK | Filter condition |
| `order_number` | integer | # orden Shopify | Logging/tracking |
| `total_price` | float | Total venta USD | Analytics |
| `alerts` | array | Alertas generadas | Filter/routing |
| `alerts[0].type` | string | Tipo alerta | Conditional logic |
| `alerts[0].severity` | string | CRÍTICO/ALTO/etc | Priority routing |
| `metrics_updated` | array | Productos actualizados | Detail tracking |

---

## 9. Próximos Pasos

**Una vez Make.com funcionando:**

### Opción A: Solo Alertas Críticas
```
Router → Filter: {{alerts.length}} > 0 AND {{alerts[0].severity}} == "CRÍTICO"
    ↓
Twilio WhatsApp (solo críticas)
```

### Opción B: Todas las Órdenes
```
Webhook → Twilio (sin filter)
```

### Opción C: Router Multi-Path
```
Webhook
    ↓
Router
    ├─ Si alertas críticas → WhatsApp urgente
    ├─ Si alertas medias → Email resumen
    └─ Siempre → Google Sheets tracking
```

---

## 10. Variables Entorno Railway Requeridas

**Checklist completo:**

- [x] `SHOPIFY_WEBHOOK_SECRET` - HMAC verification
- [x] `ADMIN_API_KEY` - Test manual endpoints
- [ ] `MAKE_WEBHOOK_URL` - **AGREGAR AHORA**
- [x] `OPENWEATHER_API_KEY` - Mobile Pulse clima
- [x] Database env vars (Railway automático)

---

## Success Metrics

**Flujo considerado exitoso si:**

- [x] Variable `MAKE_WEBHOOK_URL` configurada ✅
- [ ] Railway logs: `✅ Make.com webhook enviado`
- [ ] Make.com scenario ejecuta sin errores
- [ ] Twilio envía WhatsApp
- [ ] Recibes mensaje en teléfono
- [ ] Message WhatsApp tiene formato correcto
- [ ] Alertas aparecen inline en mensaje

---

**🔗 MAKE.COM INTEGRATION READY**

**Deployed:** 2026-02-01 19:30 EST
**Commit:** #16 (896de61)
**Status:** ✅ Code deployed, esperando env var
**Next:** Configurar MAKE_WEBHOOK_URL → Test orden real
