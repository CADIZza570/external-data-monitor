# 🦈 SHOPIFY WEBHOOK SETUP - Cerebro Central

## Configuración Rápida (5 minutos)

### Paso 1: Acceder a Shopify Admin

1. Ir a: **Shopify Admin** → **Settings** → **Notifications**
2. Scroll down hasta sección **Webhooks**
3. Click **Create webhook**

### Paso 2: Configurar Webhook orders/create

**Event:** `Order creation`

**Format:** `JSON`

**URL:**
```
https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders
```

**API Version:** `2024-10` (o la más reciente disponible)

**Webhook HMAC:** ✅ Activado (Shopify lo hace automáticamente)

### Paso 3: Guardar y Activar

1. Click **Save webhook**
2. Webhook aparecerá en lista con status **Active**
3. Copiar el **Signing secret** (para configurar en Railway si es necesario)

---

## Verificación Post-Configuración

### Test Manual desde Shopify Admin

1. En la lista de webhooks, click en el webhook recién creado
2. Click **Send test notification**
3. Shopify enviará payload de prueba al endpoint

**Resultado esperado:**
- Status: `200 OK`
- Response body: JSON con `"success": true`

### Test con Orden Real

1. Crear orden de prueba en Shopify (draft order o checkout real)
2. Completar el pago
3. Verificar logs en Railway:

```bash
railway logs --tail
```

**Logs esperados:**
```
📥 Webhook recibido: order_id=XXXXXX, order_number=YYYY
✅ HMAC verificado - webhook Shopify auténtico
✅ Webhook procesado: True
```

---

## Debugging si Webhook Falla

### Caso 1: Status 403 "Invalid HMAC signature"

**Problema:** Secret en Railway no coincide con Shopify

**Solución:**
1. Copiar Signing Secret de Shopify webhook
2. Ir a Railway → Variables → Editar `SHOPIFY_WEBHOOK_SECRET`
3. Pegar el secret de Shopify
4. Redeploy

### Caso 2: Status 500 "Error procesando webhook"

**Problema:** Error en procesamiento de orden

**Solución:**
1. Ver logs Railway: `railway logs --tail`
2. Buscar línea `❌ Error procesando orden: ...`
3. Verificar que productos existen en DB
4. Verificar estructura del payload Shopify

### Caso 3: Webhook no aparece en Railway logs

**Problema:** URL incorrecta o webhook desactivado

**Solución:**
1. Verificar URL en Shopify (copiar/pegar exactamente)
2. Verificar status webhook = **Active** en Shopify
3. Test manual "Send test notification"

---

## Payload Shopify Esperado

```json
{
  "id": 123456789,
  "order_number": 1001,
  "created_at": "2026-02-01T12:00:00-05:00",
  "total_price": "145.99",
  "customer": {
    "first_name": "María",
    "last_name": "González"
  },
  "line_items": [
    {
      "sku": "BOOTS-WP-01",
      "title": "Boots Waterproof Premium",
      "quantity": 1,
      "price": "89.99"
    }
  ]
}
```

---

## Respuesta Cerebro Central

```json
{
  "success": true,
  "order_id": 123456789,
  "order_number": 1001,
  "total_price": 145.99,
  "alerts": [
    {
      "type": "stock_critical_post_sale",
      "severity": "CRÍTICO",
      "emoji": "🚨",
      "product": "Boots Waterproof Premium",
      "sku": "BOOTS-WP-01",
      "stock": 7,
      "days_to_stockout": 1.9,
      "message": "🚨 ALERTA POST-VENTA\n\nBoots...\nStockout en 1.9 días"
    }
  ],
  "message": "🛒 NUEVA VENTA - Orden #1001\n\n👤 Cliente: María González\n💰 Total: $145.99...",
  "metrics_updated": [...]
}
```

---

## Próximos Pasos

Una vez webhook Shopify funcionando:

### 1. Configurar Make.com para WhatsApp Alerts

**Scenario:** Shopify → Cerebro → Make.com → Twilio WhatsApp

**Modules:**
1. **Webhooks** → Custom Webhook (escuchar respuesta Cerebro)
2. **Router** → Si `alerts.length > 0` → enviar alerta
3. **Twilio** → Send WhatsApp Message
   - Body: `{{message}}`
   - To: Tu número WhatsApp

### 2. Test End-to-End

1. Crear orden real en Shopify
2. Shopify dispara webhook → Cerebro procesa
3. Cerebro actualiza DB + detecta alertas
4. Make.com recibe respuesta
5. Twilio envía WhatsApp
6. ✅ Recibes alerta instantánea en tu teléfono

---

## Security Notes

- ✅ HMAC signature verification activo
- ✅ Shopify signing secret en Railway env vars
- ✅ Logs de autenticación para debugging
- ✅ Fallback a X-Admin-Key para testing manual

---

**🦈 CEREBRO CENTRAL READY - SHOPIFY WEBHOOK LIVE**

**Deployed:** 2026-02-01
**Status:** ✅ PRODUCTION READY
**Endpoint:** `POST /api/webhook/shopify/orders`
