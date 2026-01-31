# 🚀 Railway Environment Variables - Configuración

## 📋 Variables Requeridas

### Servicio: `pulse-scheduler`

```bash
# Base URL del API main
API_BASE_URL=https://tranquil-freedom-production.up.railway.app

# Discord Webhook para Stickers Tiburón
DISCORD_WEBHOOK_URL=<tu_webhook_discord>

# OpenWeather API Key (REAL - 32 caracteres)
OPENWEATHER_API_KEY=255c554b4657f6c0b1b1c3cd04ac7506

# Hora del Pulso Diario (24h format, default: 8)
PULSE_SCHEDULE_HOUR=8

# Timezone (default: America/New_York para Columbus, OH)
TZ=America/New_York
```

---

### Servicio: `main` (tranquil-freedom-production)

```bash
# OpenWeather API Key (mismo que pulse-scheduler)
OPENWEATHER_API_KEY=255c554b4657f6c0b1b1c3cd04ac7506

# (resto de variables ya configuradas)
```

---

## ✅ Verificación Post-Deploy

Después de configurar las variables:

### 1. Test API Key
```bash
curl "https://api.openweathermap.org/data/2.5/weather?q=Columbus,OH,US&appid=255c554b4657f6c0b1b1c3cd04ac7506&units=metric" | python3 -m json.tool
```

**Expected**: Status 200, temp real de Columbus

---

### 2. Test Endpoint External Signals
```bash
curl "https://tranquil-freedom-production.up.railway.app/api/debug/external-signals?product_name=Chaqueta" | python3 -m json.tool | grep -A5 weather_data
```

**Expected**:
```json
"weather_data": {
    "condition": "Clear",
    "description": "clear sky",
    "temp_celsius": -20.34,  ← CLIMA REAL (no -22.0 fijo)
    ...
}
```

---

### 3. Test Pulse Manual
```bash
# Desde local (si tienes las env vars)
python3 pulse_scheduler.py --now --dry-run
```

**Expected**: Output muestra clima REAL de Columbus

---

## 🔧 Cómo Actualizar Variables en Railway

1. **Ir a**: https://railway.app
2. **Tu proyecto** → Seleccionar servicio
3. **⚙️ Settings** → **Variables** tab
4. **Editar o agregar** variable
5. **Save Changes**
6. Railway **auto-redeploya** (~1-2 min)

---

## 🎯 Status Actual

✅ **API Key validada**: 255c554b4657f6c0b1b1c3cd04ac7506
✅ **Clima real obtenido**: -20.34°C, Clear (Columbus, OH)
✅ **Código deployado**: Fallback automático a mock si falla
✅ **Logging mejorado**: ✅ REAL vs ⚠️ MOCK visible

📋 **Próximo paso**: Configurar variable en Railway para ambos servicios

---

## 📊 Límites API Gratuita

- **60 requests/min**
- **1,000,000 requests/mes**
- **Tiburón usa**: ~1 request/día = 30 requests/mes
- **Margen**: 99.997% disponible 🔥

---

¡Dale gas! 🦈
