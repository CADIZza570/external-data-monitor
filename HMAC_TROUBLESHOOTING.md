# 🔐 HMAC TROUBLESHOOTING - Shopify Webhook

## Status Actual

**HMAC Fix Deployed:** ✅ Commit #15 (3eabbaa)
**Railway Status:** ✅ LIVE
**Logging Detallado:** ✅ Activado

---

## Cambios Implementados (Commit #15)

### 1. HMAC Base64 (Fix Principal)

**Problema anterior:**
```python
# ❌ INCORRECTO - Shopify usa base64, no hex
computed_hmac = hmac.new(...).hexdigest()
```

**Solución actual:**
```python
# ✅ CORRECTO - Base64 como Shopify
computed_hmac = base64.b64encode(
    hmac.new(
        self.shopify_secret.encode('utf-8'),
        data,
        hashlib.sha256
    ).digest()
).decode()
```

### 2. Logging Detallado Debug

**Ahora loguea en Railway:**
```
🔐 HMAC Debug:
  Secret configurado: ***<últimos 4 chars>
  Payload size: 1234 bytes
  HMAC recibido: abcd1234...
  HMAC calculado: abcd1234...
  Match: True/False
```

**Si HMAC falla:**
```
❌ HMAC INVÁLIDO - Webhook rechazado
📋 Headers recibidos:
  X-Shopify-Hmac-SHA256: <valor>...
  X-Shopify-Shop-Domain: <shop>...
💾 Payload preview: {"id": 123...
```

---

## Verificar SHOPIFY_WEBHOOK_SECRET en Railway

### 1. Copiar Secret de Shopify

**Ubicación en Shopify Admin:**
```
Settings → Notifications → Webhooks →
[Click en tu webhook] →
Signing secret (mostrar)
```

**Formato esperado:**
- String alfanumérico largo (~40-60 chars)
- Ejemplo: `shpss_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6`

### 2. Configurar en Railway

**Railway Dashboard:**
```
Project → Variables →
SHOPIFY_WEBHOOK_SECRET = <pegar secret exacto>
```

**IMPORTANTE:**
- ⚠️ NO agregar comillas ni espacios
- ⚠️ Copiar/pegar completo (sin truncar)
- ⚠️ Verificar que no haya saltos de línea

### 3. Redeploy Railway

**Después de agregar/modificar variable:**
1. Railway auto-redeploy (~60s)
2. O forzar: `railway up` (si usas CLI)

---

## Debugging Paso a Paso

### Paso 1: Verificar Secret Configurado

**Comando Railway CLI:**
```bash
railway variables
```

**Buscar:**
```
SHOPIFY_WEBHOOK_SECRET=shpss_...
```

**Si NO aparece:**
- Agregar variable en Railway Dashboard
- Redeploy

### Paso 2: Ver Logs en Tiempo Real

**Comando Railway CLI:**
```bash
railway logs --tail
```

**O en Railway Dashboard:**
```
Project → Deployments → [Latest] → View Logs
```

### Paso 3: Crear Orden Prueba Shopify

**Shopify Admin:**
1. Orders → Create order (draft order)
2. Agregar producto
3. Mark as paid
4. Shopify dispara webhook automáticamente

### Paso 4: Analizar Logs Railway

**Caso A: HMAC Válido (Éxito)**
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
✅ Webhook procesado: True
```

**Caso B: HMAC Inválido (Fallo)**
```
📥 Webhook recibido: order_id=123456, order_number=1001
🔐 Verificando HMAC Shopify...
🔐 HMAC Debug:
  Secret configurado: ***xyz789
  Payload size: 2345 bytes
  HMAC recibido: mNRP7rn/8wZU...
  HMAC calculado: AbCdEfGh1234...
  Match: False
❌ HMAC INVÁLIDO - Webhook rechazado
📋 Headers recibidos:
  X-Shopify-Hmac-SHA256: mNRP7rn/8wZU...
  X-Shopify-Shop-Domain: tu-tienda.myshopify.com
💾 Payload preview: {"id": 123456...
```

**Si ves "Match: False":**
- ✅ HMAC recibido ≠ HMAC calculado
- 🔍 Problema: Secret en Railway NO coincide con Shopify
- 🔧 Solución: Re-copiar secret de Shopify → Railway

---

## Casos Comunes de Fallo

### Caso 1: Secret Incorrecto

**Síntoma:**
```
Match: False
HMAC recibido: abc123...
HMAC calculado: xyz789...
```

**Causa:**
- Secret en Railway ≠ Secret en Shopify webhook

**Solución:**
1. Shopify Admin → Webhook → Copiar signing secret
2. Railway → Variables → SHOPIFY_WEBHOOK_SECRET → Actualizar
3. Redeploy
4. Test nueva orden

### Caso 2: Secret con Espacios/Saltos de Línea

**Síntoma:**
```
Secret configurado: ***\n
Match: False
```

**Causa:**
- Secret tiene espacios o \n al copiar/pegar

**Solución:**
1. Eliminar variable en Railway
2. Copiar secret limpio (sin espacios)
3. Pegar en Railway sin modificar
4. Save → Redeploy

### Caso 3: Múltiples Webhooks con Diferentes Secrets

**Síntoma:**
- Webhook A funciona, Webhook B falla

**Causa:**
- Shopify genera 1 secret por webhook
- Railway solo tiene 1 SHOPIFY_WEBHOOK_SECRET

**Solución:**
- Usar 1 solo webhook orders/create
- O crear endpoints separados con secrets distintos

### Caso 4: Secret No Configurado

**Síntoma:**
```
⚠️ SHOPIFY_WEBHOOK_SECRET no configurado - saltando verificación
✅ Webhook procesado sin verificar HMAC
```

**Causa:**
- Variable no existe en Railway

**Solución:**
1. Agregar SHOPIFY_WEBHOOK_SECRET en Railway
2. Redeploy
3. Test webhook

---

## Test Manual HMAC (Sin Shopify)

**Si quieres probar HMAC localmente:**

```python
import requests
import hmac
import hashlib
import base64
import json

# Tu secret de Railway (verificar con: railway variables)
secret = 'shpss_your_secret_here'

# Payload simulado
payload = {
    'id': 999999,
    'order_number': 999,
    'total_price': '100.00',
    'customer': {'first_name': 'Test'},
    'line_items': []
}

payload_json = json.dumps(payload)
payload_bytes = payload_json.encode('utf-8')

# Calcular HMAC (simular Shopify)
hmac_signature = base64.b64encode(
    hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).digest()
).decode()

print(f'HMAC: {hmac_signature}')

# Enviar a Railway
response = requests.post(
    'https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders',
    data=payload_json,  # raw bytes, no json=
    headers={
        'Content-Type': 'application/json',
        'X-Shopify-Hmac-SHA256': hmac_signature
    }
)

print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
```

**Resultado esperado:**
```
Status: 200
Response: {"success": true, "order_number": 999, ...}
```

---

## Checklist de Verificación

Antes de crear orden Shopify de prueba:

- [ ] Variable `SHOPIFY_WEBHOOK_SECRET` existe en Railway
- [ ] Secret coincide EXACTAMENTE con Shopify webhook signing secret
- [ ] Railway redeploy completado (~60s después de cambiar variable)
- [ ] Logs Railway accesibles (`railway logs --tail`)
- [ ] Webhook Shopify configurado en: orders/create
- [ ] URL webhook: `https://tranquil-freedom-production.up.railway.app/api/webhook/shopify/orders`
- [ ] Webhook status: Active (verde)

---

## Próximos Pasos

**Una vez HMAC funcionando:**

1. ✅ Orden real Shopify → Logs mostrarán "Match: True"
2. ✅ Stock actualizado en DB
3. ✅ Alertas generadas si aplica
4. ✅ Message WhatsApp listo
5. 🔜 Configurar Make.com + Twilio
6. 🔜 Recibir alertas WhatsApp en tiempo real

---

**🔐 HMAC FIX DEPLOYED - READY FOR SHOPIFY WEBHOOKS**

**Updated:** 2026-02-01 18:30 EST
**Commit:** #15 (3eabbaa)
**Status:** ✅ Base64 HMAC + Logging Activado
