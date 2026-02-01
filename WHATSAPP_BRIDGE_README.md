# 🦈📱 WHATSAPP BRIDGE - Tiburón en Tu Bolsillo

## Mobile Pulse para Make + Twilio

---

## 🎯 **VISIÓN**

**Llevar el Sticker Predictivo a WhatsApp** para que La Chaparrita reciba el Pulso del Tiburón directamente en su móvil y pueda ejecutar acciones (Price Surge, Bundles, Reorden) con un solo mensaje.

---

## 🔥 **CARACTERÍSTICAS**

### **1. Mobile Pulse (Sticker Optimizado)**
- ✅ Sticker Predictivo en texto plano ASCII
- ✅ Cash Flow snapshot
- ✅ Clima Columbus real-time
- ✅ Feriados próximos
- ✅ Oportunidades Instinto Depredador
- ✅ Auto-generado cada vez que se llama

### **2. Quick Replies (Botones Interactivos)**
- ✅ Max 4 botones (límite Twilio WhatsApp)
- ✅ Botones dinámicos según oportunidades
- ✅ Si hay opport

unidades: "SURGE: Botas Waterproof", "BUNDLE: Estrella + Dead"
- ✅ Sin oportunidades: "Ver Inventario", "Forzar Análisis", "Ver War Room", "Freeze"

### **3. Action Handler (Respuestas Usuario)**
- ✅ Procesa respuesta usuario desde WhatsApp
- ✅ Ejecuta acción vía `interactive_handler.py`
- ✅ Retorna confirmación push para WhatsApp
- ✅ Tracking de todas las acciones

---

## 📡 **ARQUITECTURA**

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  WhatsApp    │────►│   Make.com   │────►│   Tiburón    │
│  (Usuario)   │     │   Workflow   │     │   Backend    │
└──────────────┘     └──────────────┘     └──────────────┘
       ▲                                          │
       │                                          │
       │              ┌──────────────┐            │
       └──────────────│    Twilio    │◄───────────┘
                      │   WhatsApp   │
                      └──────────────┘

Flujo:
1. Make.com (cron diario 8:00 AM) → GET /api/v1/mobile-pulse
2. Tiburón Backend → Genera Sticker + Quick Replies
3. Make.com → Twilio WhatsApp API → Envía mensaje
4. Usuario responde (click quick reply o texto)
5. Twilio → Make.com → POST /api/v1/whatsapp-action
6. Tiburón Backend → Ejecuta acción → Retorna confirmación
7. Make.com → Twilio → Envía confirmación a usuario
```

---

## 🔌 **ENDPOINTS**

### **GET `/api/v1/mobile-pulse`**

**Descripción:** Genera Mobile Pulse (Sticker + Quick Replies)

**Query Params:** Ninguno

**Response:**
```json
{
  "success": true,
  "message": "╔═══════════════════════════════════════╗\n║  🦈 PULSO PREDICTIVO - 31/01/2026\n╚═══════════════════════════════════════╝\n\n💰 CASH FLOW SNAPSHOT:\n├─ Inventario Total: $9,180.00\n├─ Productos: 28\n├─ Stock Crítico: 3\n└─ Stockouts: 0\n\n🌡️ CONTEXTO CLIMÁTICO:\n├─ Columbus, OH: -9.6°C\n├─ Condición: Parcialmente nublado\n└─ Próximo Feriado: Valentine's Day (14 días)\n\n🎯 OPORTUNIDADES ACTIVAS:\n└─ Sin oportunidades activas (Tiburón en espera)\n\n╔═══════════════════════════════════════╗\n║  🦈 TIBURÓN LISTO PARA CAZAR\n╚═══════════════════════════════════════╝",
  "quick_replies": [
    {"title": "📊 Ver Inventario", "action": "inventory", "sku": ""},
    {"title": "🔥 Forzar Análisis", "action": "analyze", "sku": ""},
    {"title": "📈 Ver War Room", "action": "warroom", "sku": ""},
    {"title": "❄️ Freeze Precios", "action": "freeze", "sku": ""}
  ],
  "opportunities": [],
  "metadata": {
    "timestamp": "2026-01-31T12:00:00",
    "temperature": "-9.6°C",
    "inventory_value": 9180.0,
    "opportunities_count": 0,
    "critical_stock": 3
  }
}
```

**Ejemplo cURL:**
```bash
curl https://tranquil-freedom-production.up.railway.app/api/v1/mobile-pulse
```

---

### **POST `/api/v1/whatsapp-action`**

**Descripción:** Procesa acción de usuario desde WhatsApp

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "action": "surge",
  "sku": "BOOTS-WP-01",
  "user": "+1234567890"
}
```

**Acciones Disponibles:**

| Action | Descripción | SKU Required |
|--------|-------------|--------------|
| `surge` | Ejecutar Price Surge | ✅ Yes |
| `bundle` | Ejecutar Parasite Bundle | ✅ Yes (formato: "SKU1+SKU2") |
| `reorden` | Ejecutar Reorden Automático | ✅ Yes |
| `freeze` | Freeze todos los precios | ❌ No |
| `inventory` | Ver snapshot inventario | ❌ No |
| `analyze` | Forzar análisis Market Predator | ❌ No |
| `warroom` | Link al War Room | ❌ No |

**Response (Ejemplo Price Surge):**
```json
{
  "success": true,
  "message": "✅ PRICE SURGE ACTIVADO\n\nSKU: BOOTS-WP-01\nPrecio Nuevo: $52.89\nDuración: 48h\nROI Proyectado: +18.2%\n\n🦈 Tiburón cazando...",
  "details": {
    "success": true,
    "new_price": 52.89,
    "duration_hours": 48,
    "roi": 18.2
  }
}
```

**Ejemplo cURL:**
```bash
curl -X POST https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-action \
  -H "Content-Type: application/json" \
  -d '{
    "action": "surge",
    "sku": "BOOTS-WP-01",
    "user": "+1234567890"
  }'
```

---

## 🛠️ **SETUP MAKE.COM**

### **Workflow 1: Daily Pulse (Automático)**

```
[1] Schedule (Cron)
    ├─ Trigger: Every day 8:00 AM (Columbus timezone)
    └─ Frequency: Daily

[2] HTTP Request
    ├─ Method: GET
    ├─ URL: https://tranquil-freedom-production.up.railway.app/api/v1/mobile-pulse
    └─ Parse Response: Yes

[3] Set Variables
    ├─ message: {{2.message}}
    ├─ quick_replies: {{2.quick_replies}}
    └─ opportunities_count: {{2.metadata.opportunities_count}}

[4] Twilio - Send WhatsApp Message
    ├─ To: +1234567890 (La Chaparrita)
    ├─ From: whatsapp:+14155238886 (Twilio Sandbox)
    ├─ Body: {{3.message}}
    └─ MediaURL: (opcional: imagen War Room)

[5] Iterator (Quick Replies)
    ├─ Array: {{3.quick_replies}}
    └─ For each reply: Store en variable para respuestas

[6] Datastore - Log Pulse
    ├─ Timestamp: {{now}}
    ├─ Opportunities: {{3.opportunities_count}}
    └─ Sent: Success
```

### **Workflow 2: Action Handler (Reactivo)**

```
[1] Webhook Trigger
    ├─ URL: https://hook.make.com/xxxxxxxxxxxxx
    └─ Method: POST (recibe desde Twilio)

[2] Parse Twilio Payload
    ├─ From: {{1.From}} (número usuario)
    ├─ Body: {{1.Body}} (texto mensaje o quick reply)
    └─ Extract action + SKU

[3] Router
    ├─ Route 1: Si body contiene "surge" → action="surge"
    ├─ Route 2: Si body contiene "bundle" → action="bundle"
    ├─ Route 3: Si body contiene "inventory" → action="inventory"
    └─ Route 4: Else → action="analyze"

[4] HTTP Request - Action
    ├─ Method: POST
    ├─ URL: https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-action
    ├─ Headers: Content-Type: application/json
    └─ Body: {
         "action": "{{3.action}}",
         "sku": "{{3.sku}}",
         "user": "{{2.From}}"
       }

[5] Twilio - Send Confirmation
    ├─ To: {{2.From}}
    ├─ From: whatsapp:+14155238886
    └─ Body: {{4.message}}
```

---

## 🔐 **SETUP TWILIO**

### **1. Crear Cuenta Twilio**
1. Ir a https://www.twilio.com/
2. Sign up (Free trial $15 crédito)
3. Verificar número telefónico

### **2. Activar WhatsApp Sandbox**
1. Ir a Console → Messaging → Try it out → Try WhatsApp
2. Copiar número sandbox: `+1 415 523 8886`
3. Enviar mensaje desde WhatsApp: `join <codigo-sandbox>`
4. Ejemplo: `join shark-predator`

### **3. Configurar Webhook**
1. Console → Messaging → Settings → WhatsApp Sandbox Settings
2. **When a message comes in:**
   - URL: `https://hook.make.com/xxxxxxxxxxxxx` (Make webhook)
   - Method: POST
3. Save

### **4. (Opcional) Número Dedicado**
Para producción, comprar número dedicado:
- Costo: ~$1/mes + $0.005/mensaje
- WhatsApp Business API approval requerido
- Templates pre-aprobados por WhatsApp

---

## 📱 **EJEMPLO USO REAL**

### **Escenario 1: Pulse Diario**

**8:00 AM** → Make.com ejecuta cron → GET `/api/v1/mobile-pulse`

**WhatsApp recibe:**
```
╔═══════════════════════════════════════╗
║  🦈 PULSO PREDICTIVO - 31/01/2026
╚═══════════════════════════════════════╝

💰 CASH FLOW SNAPSHOT:
├─ Inventario Total: $9,180.00
├─ Productos: 28
├─ Stock Crítico: 3
└─ Stockouts: 0

🌡️ CONTEXTO CLIMÁTICO:
├─ Columbus, OH: -15.3°C
├─ Condición: Nieve ligera
└─ Próximo Feriado: Valentine's Day (14 días)

🎯 OPORTUNIDADES ACTIVAS:
├─ [1] SURGE: Botas Waterproof
│   $45.99 → $52.89 | ROI +18.2%
├─ [2] SURGE: Chaquetas Arctic
│   $89.99 → $102.49 | ROI +22.5%
└─ Total: 2 oportunidades

╔═══════════════════════════════════════╗
║  🦈 TIBURÓN LISTO PARA CAZAR
╚═══════════════════════════════════════╝

[Botones Quick Reply]
🚀 S: Botas Waterproof
🚀 S: Chaquetas Arctic
📊 Ver Inventario
❄️ Freeze Precios
```

**Usuario click:** `🚀 S: Botas Waterproof`

**Twilio envía a Make:** `{"Body": "surge", "sku": "BOOTS-WP-01"}`

**Make ejecuta:** POST `/api/v1/whatsapp-action`

**WhatsApp recibe confirmación:**
```
✅ PRICE SURGE ACTIVADO

SKU: BOOTS-WP-01
Precio Nuevo: $52.89
Duración: 48h
ROI Proyectado: +18.2%

🦈 Tiburón cazando...
```

---

### **Escenario 2: Forzar Análisis**

**Usuario envía:** `"analyze"` (o click botón "Forzar Análisis")

**Make ejecuta:** POST `/api/v1/whatsapp-action` con `action=analyze`

**WhatsApp recibe:**
```
🔍 ANÁLISIS FORZADO

Oportunidades encontradas: 3
• Price Surges: 2
• Bundles: 1

🦈 Envía 'Pulse' para ver detalles
```

---

## 🔒 **SEGURIDAD**

### **Validación Usuario**
```python
# En whatsapp_bridge.py
ALLOWED_NUMBERS = [
    '+1234567890',  # La Chaparrita
    '+0987654321'   # Admin
]

def process_whatsapp_action(action, sku, user):
    if user not in ALLOWED_NUMBERS:
        return {
            'success': False,
            'message': '🚫 Número no autorizado'
        }
    # ... resto del código
```

### **Rate Limiting**
```python
# Máximo 10 acciones por usuario por hora
from collections import defaultdict
from datetime import datetime

action_log = defaultdict(list)

def check_rate_limit(user):
    now = datetime.now()
    # Limpiar acciones > 1h
    action_log[user] = [t for t in action_log[user]
                        if (now - t).seconds < 3600]

    if len(action_log[user]) >= 10:
        return False  # Rate limit exceeded

    action_log[user].append(now)
    return True
```

### **Signature Verification**
```python
# Verificar que request viene de Twilio real
from twilio.request_validator import RequestValidator

validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))

@app.route('/api/v1/whatsapp-action', methods=['POST'])
def whatsapp_action_route():
    # Validar signature Twilio
    signature = request.headers.get('X-Twilio-Signature', '')
    url = request.url
    params = request.form.to_dict()

    if not validator.validate(url, params, signature):
        return jsonify({'error': 'Invalid signature'}), 403

    # ... resto del código
```

---

## 📊 **MÉTRICAS & TRACKING**

### **Eventos a Trackear**

| Evento | Descripción | Datos |
|--------|-------------|-------|
| `pulse_sent` | Pulse enviado a WhatsApp | timestamp, opportunities_count |
| `action_requested` | Usuario click botón | action, sku, user |
| `action_executed` | Acción ejecutada exitosa | action, sku, result |
| `action_failed` | Acción falló | action, sku, error |

### **Tabla DB: `whatsapp_interactions`**
```sql
CREATE TABLE whatsapp_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    user_phone TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- pulse_sent, action_requested, etc.
    action TEXT,                -- surge, bundle, etc.
    sku TEXT,
    success BOOLEAN,
    details TEXT,               -- JSON con metadata
    response_time_ms INTEGER
);
```

### **Dashboard Analytics**
- 📊 Total pulses enviados (por día/semana)
- 🎯 Actions ejecutadas (por tipo)
- ✅ Success rate (% acciones exitosas)
- ⏱️ Tiempo promedio respuesta
- 📱 Usuario más activo

---

## 🚀 **DEPLOYMENT**

### **Checklist**

- [x] `whatsapp_bridge.py` creado
- [x] Rutas agregadas a `webhook_server.py`
- [ ] Testing local endpoints
- [ ] Deploy a Railway
- [ ] Setup Make.com workflows
- [ ] Setup Twilio sandbox
- [ ] Test end-to-end flujo completo
- [ ] Producción: Número Twilio dedicado

### **Deploy Railway**
```bash
git add whatsapp_bridge.py webhook_server.py WHATSAPP_BRIDGE_README.md
git commit -m "Feat: WhatsApp Bridge - Tiburón en móvil 📱🦈"
git push origin main
```

### **Verificación**
```bash
# Test Mobile Pulse
curl https://tranquil-freedom-production.up.railway.app/api/v1/mobile-pulse

# Test Action (surge)
curl -X POST https://tranquil-freedom-production.up.railway.app/api/v1/whatsapp-action \
  -H "Content-Type: application/json" \
  -d '{"action":"analyze","sku":"","user":"+1234567890"}'
```

---

## 🎯 **PRÓXIMOS NIVELES**

### **Fase 1: Voice Commands** 🎤
- Twilio Voice API
- Usuario llama → "Ejecutar surge Botas"
- Speech-to-text → acción

### **Fase 2: Imágenes War Room** 📸
- Screenshot automático War Room
- Enviar como imagen en WhatsApp
- Heatmap visual en móvil

### **Fase 3: Alertas Proactivas** 🔔
- Stockout detectado → Alert inmediato
- Temperatura < -15°C → "Spike oportunidad"
- Valentine's Day -3 días → "Last chance surge"

### **Fase 4: Conversational AI** 🤖
- Claude AI integrado
- Usuario: "¿Cuál es mi mejor producto?"
- Claude: "Botas Waterproof: 4.5 velocity, $1,200 revenue 30d"

---

## 🦈 **FILOSOFÍA**

> **"El Tiburón siempre en tu bolsillo. Un mensaje para dominar Ohio."**

**WhatsApp Bridge NO es:**
- ❌ Un chatbot genérico
- ❌ Notificaciones spam
- ❌ Dashboard móvil

**WhatsApp Bridge ES:**
- ✅ **Pulso diario** del negocio en texto
- ✅ **Acción inmediata** con un click
- ✅ **Poder táctico** sin abrir laptop

---

**🦈📱 TIBURÓN EN TU BOLSILLO - READY TO EXECUTE**

*Desarrollado con visión de Gemini*
*Ejecutado por Claude*
*Powered by La Chaparrita*
