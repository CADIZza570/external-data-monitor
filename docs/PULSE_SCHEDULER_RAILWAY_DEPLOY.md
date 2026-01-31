# 🕐 PULSE SCHEDULER - RAILWAY DEPLOYMENT GUIDE

Guía completa para deployar `pulse_scheduler.py` como servicio separado en Railway.

---

## 📋 PRE-REQUISITOS

1. **Cuenta Railway**: https://railway.app
2. **Repo GitHub**: `external-data-monitor` con código en `main` branch
3. **Discord Webhook URL**: Para envío de Stickers
4. **API Base URL**: URL del servicio cashflow API en Railway

---

## 🚀 PASO 1: CREAR SERVICIO EN RAILWAY

### 1.1 Nuevo Proyecto o Servicio

**Opción A: Proyecto nuevo separado**
```
1. Railway Dashboard → New Project
2. Seleccionar: Deploy from GitHub repo
3. Repo: CADIZza570/external-data-monitor
4. Branch: main
5. Nombre: "pulse-scheduler-tiburon"
```

**Opción B: Servicio dentro del proyecto existente** (Recomendado)
```
1. Ir a proyecto existente: tranquil-freedom-production
2. Click "+ New Service"
3. GitHub Repo → external-data-monitor
4. Branch: main
5. Nombre: "pulse-scheduler"
```

---

## ⚙️ PASO 2: CONFIGURAR START COMMAND

En Railway Dashboard → Service Settings → Deploy:

**Start Command:**
```bash
python3 pulse_scheduler.py
```

**Root Directory:** (dejar vacío, usa raíz del repo)

**Builder:** Nixpacks (auto-detecta Python)

---

## 🔐 PASO 3: VARIABLES DE ENTORNO

Railway Dashboard → Service → Variables:

### Variables Obligatorias:

```bash
# API Base URL (URL del servicio cashflow_api en Railway)
API_BASE_URL=https://tranquil-freedom-production.up.railway.app

# Discord Webhook para envío de Stickers
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN

# Hora del pulso diario (24h format, default: 8 = 8:00 AM)
PULSE_SCHEDULE_HOUR=8
```

### Variables Opcionales:

```bash
# OpenWeather API Key (si quieres clima real, sino usa mock)
OPENWEATHER_API_KEY=your_api_key_here

# Timezone (default: UTC)
TZ=America/New_York
```

### Cómo obtener DISCORD_WEBHOOK_URL:

1. Discord Server → Server Settings → Integrations
2. Webhooks → New Webhook
3. Nombre: "Tiburón Predictivo"
4. Channel: #cash-flow (o el que prefieras)
5. Copy Webhook URL

---

## 📦 PASO 4: CONFIGURAR DEPENDENCIAS

Railway auto-detecta `requirements.txt` del repo. Asegurate que incluya:

```txt
flask==3.0.0
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
```

Si no existe, crear en raíz del repo:

```bash
# En tu máquina local
cd /Users/constanzaaraya/Documents/python-automation
cat > requirements.txt << 'EOF'
flask==3.0.0
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.2.0
pytz==2023.3
EOF

git add requirements.txt
git commit -m "Add: requirements.txt para Railway"
git push origin main
```

---

## 🧪 PASO 5: TESTING MANUAL (antes de activar scheduler)

### 5.1 Test Local (desde tu máquina):

```bash
# Export env vars
export API_BASE_URL="https://tranquil-freedom-production.up.railway.app"
export DISCORD_WEBHOOK_URL="your_webhook_url"
export PULSE_SCHEDULE_HOUR=8

# Test dry-run (NO envía a Discord)
python3 pulse_scheduler.py --now --dry-run

# Test real (envía a Discord)
python3 pulse_scheduler.py --now
```

**Salida esperada (dry-run):**
```
2026-01-31 03:00:00 - INFO - 🦈 Iniciando Pulso Tiburón Predictivo...
2026-01-31 03:00:01 - INFO - Obteniendo datos...
2026-01-31 03:00:02 - INFO - Generando Sticker...
2026-01-31 03:00:02 - INFO - Enviando a Discord...
2026-01-31 03:00:02 - INFO - 🧪 DRY RUN - No se envió a Discord
2026-01-31 03:00:02 - INFO - Mensaje:
🦈 **TIBURÓN PREDICTIVO - PULSO DIARIO**
⏰ 2026-01-31 03:00
🌡️ **Columbus, Ohio:** -22.0°C, Snow
...
2026-01-31 03:00:02 - INFO - ✅ Pulso completado exitosamente
```

### 5.2 Test en Railway (sin scheduler activo):

1. Railway Dashboard → Service → Deployments
2. Click en deployment activo → Logs
3. Deberías ver: `🕐 Scheduler iniciado - Pulso diario a las 8:00`

**Para forzar envío manual desde Railway:**

Railway Dashboard → Service → Settings → Start Command (temporal):

```bash
python3 pulse_scheduler.py --now
```

Esto enviará UN pulso inmediato. Luego revertir a:

```bash
python3 pulse_scheduler.py
```

---

## 🔄 PASO 6: ACTIVAR SCHEDULER DIARIO

Una vez verificado que funciona con `--now`:

**Start Command final:**
```bash
python3 pulse_scheduler.py
```

**Comportamiento:**
- El servicio corre 24/7 en Railway
- Cada día a las `PULSE_SCHEDULE_HOUR`:00 envía Sticker a Discord
- Logs: `⏳ Próximo pulso en X.X horas`

---

## 📊 PASO 7: VERIFICAR LOGS

Railway Dashboard → Service → Logs:

**Logs normales (esperando próximo pulso):**
```
2026-01-31 00:00:00 - INFO - 🕐 Scheduler iniciado - Pulso diario a las 8:00
2026-01-31 00:00:01 - INFO - ⏳ Próximo pulso en 8.0 horas (2026-01-31 08:00)
```

**Logs al ejecutar pulso (8:00 AM):**
```
2026-01-31 08:00:00 - INFO - ⏰ Hora del pulso: 08:00
2026-01-31 08:00:00 - INFO - 🦈 Iniciando Pulso Tiburón Predictivo...
2026-01-31 08:00:01 - INFO - Obteniendo datos...
2026-01-31 08:00:02 - INFO - Generando Sticker...
2026-01-31 08:00:02 - INFO - Enviando a Discord...
2026-01-31 08:00:03 - INFO - ✅ Sticker enviado a Discord exitosamente
2026-01-31 08:00:03 - INFO - ✅ Pulso completado exitosamente
```

---

## 🚨 TROUBLESHOOTING

### Error: "DISCORD_WEBHOOK_URL no configurado"

**Causa:** Falta env var

**Solución:**
```
Railway → Service → Variables → Add Variable
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Error: "Error fetching summary: 404"

**Causa:** API_BASE_URL incorrecto o servicio cashflow no está corriendo

**Solución:**
1. Verificar URL: `curl https://tranquil-freedom-production.up.railway.app/health`
2. Actualizar `API_BASE_URL` si cambió

### Pulso no se envía a la hora correcta

**Causa:** Timezone incorrecto

**Solución:**
```
Railway → Variables → Add:
TZ=America/New_York
PULSE_SCHEDULE_HOUR=8  # 8:00 AM Eastern Time
```

### "No products available for ROI simulation"

**Causa:** DB vacía, no hay productos

**Solución:**
- Esperar a que lleguen webhooks de Shopify
- O hacer seed manual: `python3 seed_test_data.py`

---

## 📈 MÉTRICAS Y MONITORING

### Health Check (si quieres agregar endpoint):

Agregar a `pulse_scheduler.py`:

```python
from flask import Flask
app = Flask(__name__)

@app.route('/health')
def health():
    return {"status": "scheduler_running", "next_pulse": "..."}

# Run Flask en thread separado mientras scheduler corre
```

### Logs de Discord:

Cada Sticker enviado debería aparecer en el canal Discord configurado.

---

## 🎯 CHECKLIST FINAL

- [ ] Servicio creado en Railway
- [ ] Start command: `python3 pulse_scheduler.py`
- [ ] Variables de entorno configuradas (API_BASE_URL, DISCORD_WEBHOOK_URL)
- [ ] Test manual exitoso: `--now --dry-run`
- [ ] Primer pulso real enviado: `--now` (sin dry-run)
- [ ] Sticker recibido en Discord con clima + ROI predictivo
- [ ] Logs muestran: `🕐 Scheduler iniciado`
- [ ] Verificar próximo pulso automático a las 8:00 AM

---

## 📝 NOTAS IMPORTANTES

1. **Railway Free Tier**: Servicio duerme después de 500 horas/mes. Para producción real, usar plan pago ($5/mes).

2. **Timezone**: Railway usa UTC por default. Configurar `TZ` env var si quieres otro timezone.

3. **Cron alternativo**: Si prefieres usar cron externo (GitHub Actions, cron-job.org):
   ```bash
   # GitHub Actions workflow
   - name: Trigger Pulse
     run: |
       curl -X GET "https://pulse-scheduler.railway.app/trigger-pulse"
   ```

4. **Discord Rate Limits**: No enviar más de 1 pulso cada 10 min para evitar bans.

5. **Backup**: Scheduler guarda logs en Railway. Para persistencia, integrar con DB.

---

## 🔗 RECURSOS

- **Railway Docs**: https://docs.railway.app/
- **Discord Webhooks**: https://discord.com/developers/docs/resources/webhook
- **OpenWeather API**: https://openweathermap.org/api (clima real)
- **Python schedule lib**: (alternativa a loop manual) https://pypi.org/project/schedule/

---

**Última actualización:** 2026-01-31
**Autor:** Claude Code
**Status:** ✅ Ready for Production
