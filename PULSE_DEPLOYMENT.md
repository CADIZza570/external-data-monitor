# 🗓️ PULSE SCHEDULER - Deployment Guide

## Track 3.0: "El Primer Pulso" - Sistema Narrativo Diario

### ✅ Archivos Implementados

1. **narrative_engine.py** - Motor de narrativa con personalidad chilena/callejera
2. **pulse_scheduler.py** - Scheduler que envía pulso diario a Discord

### 🔧 Variables de Entorno (Railway)

Agregar estas variables en Railway dashboard:

```bash
# Ya existentes (verificar)
DISCORD_WEBHOOK_URL_CHAPARRITA=https://discord.com/api/webhooks/...
SHOPIFY_API_KEY=tu_api_key_aqui

# Nuevas (opcionales)
API_BASE_URL=https://tu-app.railway.app  # URL de tu deploy Railway
PULSE_SEND_TIME=08:00                     # Hora de envío (formato 24h)
```

### 📦 Dependencias

Agregar a `requirements.txt`:

```
schedule==1.2.0
```

### 🚀 Opciones de Deploy

#### Opción 1: Proceso Separado (RECOMENDADO)

Crear nuevo servicio en Railway para el scheduler:

1. **Procfile.scheduler**:
```
worker: python pulse_scheduler.py
```

2. En Railway dashboard:
   - Crear nuevo servicio desde mismo repo
   - Configurar start command: `python pulse_scheduler.py`
   - Agregar variables de entorno
   - Deploy!

**Ventajas:**
- Proceso independiente (no afecta API)
- Fácil restart/monitoring
- Logs separados

#### Opción 2: Background Thread en Main App

Modificar `webhook_server.py` para iniciar scheduler en background:

```python
# Al final de webhook_server.py
if __name__ == '__main__':
    # Iniciar scheduler en thread separado
    from pulse_scheduler import run_scheduler
    import threading

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()

    # Iniciar Flask app normal
    app.run(...)
```

**Ventajas:**
- Un solo deploy
- Mismo proceso

**Desventajas:**
- Si API crashea, scheduler también
- Logs mezclados

### 🧪 Testing Local

```bash
# Test inmediato (envía a Discord)
python3 pulse_scheduler.py --now

# Dry-run (preview sin enviar)
python3 pulse_scheduler.py --now --dry-run

# Scheduler normal (loop infinito)
python3 pulse_scheduler.py
```

### 📊 Endpoints que Consume

El scheduler hace requests a tu propia API:

- `GET /api/cashflow/summary?shop=la-chaparrita`
- `GET /api/reorder-calculator?shop=la-chaparrita&top_n=3&min_priority=B`

Ambos requieren header `X-API-Key` si auth está habilitado.

### 🔐 Seguridad

- Usa retry logic (3 intentos con backoff)
- Auth con API key en headers
- Timeout de 10s por request
- Logging de errores sin exponer secrets

### 📝 Mensaje de Ejemplo

```
☀️ Buenos días, socio!

📊 **PULSO DE LA CHAPARRITA** (29 Ene 2026)

💰 **Inventario:** $45.2K en 150 productos
🔴 **Stockouts:** 3 productos agotados (-$1.2K perdidos)
🟡 **Stock crítico:** 12 productos con menos de 7 días

🔥 **LO QUE PIDE ACCIÓN:**
🔴 **Sombrero Arcoiris** (SOMB-ARCO-09): 25 unidades
   Con 30°C en Los Andes, esto vuela - dale ya! (quedan 3 días)

💡 **Recomendación:**
🔴 URGENTE wn, esto no puede esperar!
Dale 40 unidades totales o lloramos después? 😅

---
🤖 Pulso automático del Centinela
```

### 🎯 Próximos Pasos (Futuro)

- [ ] Interactividad: Botones Discord para "Reordenar ahora"
- [ ] Susurros de seguridad: "Alguien miró demasiado /api/cashflow"
- [ ] Resumen semanal: Comparativa semana vs semana
- [ ] ABC breakdown en mensaje
- [ ] Alertas de spike en tiempo real (no solo diarias)

### 🐛 Troubleshooting

**Error: "Connection refused localhost:5001"**
- Configurar `API_BASE_URL` a URL de Railway
- Verificar que API esté corriendo

**Error: "Discord webhook no configurado"**
- Agregar `DISCORD_WEBHOOK_URL_CHAPARRITA` en Railway

**Error: 401 Unauthorized**
- Configurar `SHOPIFY_API_KEY` en Railway
- Verificar que key sea la misma en API y scheduler

**Scheduler no envía a la hora correcta**
- Verificar timezone del servidor Railway
- Ajustar `PULSE_SEND_TIME` según UTC offset

### 📈 Monitoring

Logs a revisar:

```bash
# En Railway logs
✅ PULSO ENVIADO EXITOSAMENTE en 2.34s
❌ PULSO FALLÓ después de 5.12s
```

### 🎉 Readiness Update

**Track 3.0 agregado:**
- ✅ Motor narrativo con personalidad
- ✅ Scheduler diario
- ✅ Integración Discord + Retry
- ✅ Testing modes
- ✅ Docs deployment

**Sistema actual: 75% → 80% Production-Ready** 🔥
