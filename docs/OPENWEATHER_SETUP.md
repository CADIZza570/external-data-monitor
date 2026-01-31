# 🌡️ OpenWeather API - Setup Guía Completa

## ✅ Estado Actual
- ❌ API key inválida: `255c554b4657f6c0b1b1c3cd04ac7` (incompleta)
- ⚠️ Tiburón usando datos MOCK (-22°C fijo)
- ✅ Código listo para usar API real (fallback automático a mock)

---

## 🎯 Objetivo
Configurar API key válida de OpenWeather para que Tiburón Predictivo lea clima REAL de Columbus, Ohio.

---

## 📋 Paso a Paso: Obtener API Key

### 1. Crear Cuenta OpenWeather (GRATIS)

**URL**: https://openweathermap.org/api

1. Click **"Sign Up"** (esquina superior derecha)
2. Completar formulario:
   - Username
   - Email
   - Password
3. **Verificar email** (check inbox/spam)
4. **Login** en https://home.openweathermap.org/

---

### 2. Obtener API Key

1. **Ir a**: https://home.openweathermap.org/api_keys
2. Vas a ver una **API key default** ya creada
3. **Copiar la key** (32 caracteres hexadecimales)
   - Formato: `a1b2c3d4e5f6789012345678abcdef12`
   - Ejemplo: `9f8e7d6c5b4a3210fedcba9876543210`

⚠️ **IMPORTANTE**: La key puede tardar **5-10 minutos** en activarse después de crear la cuenta.

---

### 3. Testear API Key Localmente

```bash
cd /Users/constanzaaraya/.claude-worktrees/python-automation/laughing-bose

# Exportar key temporal (REEMPLAZAR con tu key)
export OPENWEATHER_API_KEY="tu_key_de_32_caracteres"

# Testear
python3 test_api_key.py
```

**Output esperado** (si key válida):
```
✅ API KEY VÁLIDA!

🌡️ Temperatura: -8.3°C
🌤️ Condición: Clear
📝 Descripción: clear sky
💧 Humedad: 67%
🌬️ Viento: 3.1 m/s
🥶 Sensación térmica: -12.5°C
```

**Error común** (si key inválida):
```
❌ API KEY INVÁLIDA
Respuesta: {"cod":401, "message": "Invalid API key..."}
```

---

### 4. Configurar en Railway (Pulse Scheduler)

Una vez que `test_api_key.py` **pasa exitosamente**:

1. **Ir a**: https://railway.app
2. **Tu proyecto** → `pulse-scheduler` service
3. **Variables** tab (⚙️ Settings → Variables)
4. **Editar variable existente**:
   ```
   OPENWEATHER_API_KEY=<tu_key_de_32_caracteres>
   ```
5. **Save Changes**
6. Railway **auto-redeploya** (tarda ~1 min)

---

### 5. Configurar en Railway (Main Service)

Repetir en el servicio **main** (tranquil-freedom-production):

1. **Tu proyecto** → servicio main
2. **Variables** → Add Variable:
   ```
   OPENWEATHER_API_KEY=<tu_key_de_32_caracteres>
   ```
3. **Save** → Railway auto-redeploya

---

### 6. Verificar Deploy

Esperar 1-2 minutos después del deploy, luego:

```bash
# Test endpoint
curl "https://tranquil-freedom-production.up.railway.app/api/debug/external-signals?product_name=Chaqueta" | python3 -m json.tool | grep -A5 weather_data
```

**Output esperado** (clima REAL):
```json
"weather_data": {
    "condition": "Clear",
    "description": "clear sky",
    "feels_like": -12.5,
    "humidity": 67,
    "temp_celsius": -8.3,
    "wind_speed": 3.1
}
```

❌ **Si sigue mostrando -22.0°C**:
- Verificar que la key esté configurada en **AMBOS servicios** (pulse-scheduler + main)
- Revisar logs de Railway para errores
- La key puede tardar 5-10 min en activarse (OpenWeather)

---

### 7. Test Pulse Manual

Desde Railway logs del servicio `pulse-scheduler`:

```bash
# Trigger manual (si configuraste botón/trigger en Railway)
# O esperar a las 8:00 AM (hora configurada)
```

**Output esperado en Discord**:
```
🦈 TIBURÓN PREDICTIVO - PULSO DIARIO
⏰ 2026-01-31 08:00

🌡️ Columbus, Ohio: -8.3°C, Clear  ← ✅ CLIMA REAL
🎉 Próximo feriado: Valentine's Day (en 14 días)
...
```

---

## 🔍 Troubleshooting

### Error: "Invalid API key"

**Causas**:
1. Key copiada incorrectamente (falta caracteres)
2. Key recién creada (tarda 5-10 min en activarse)
3. Plan gratuito excedió límite (60 requests/min)

**Solución**:
- Verificar key completa (32 caracteres)
- Esperar 10 minutos y reintentar
- Revisar en https://home.openweathermap.org/api_keys

---

### Error: "Too many requests" (429)

**Causa**: Plan gratuito tiene límite de 60 requests/minuto.

**Solución**:
- Tiburón hace ~1 request cada 24h → OK
- Si testeas mucho, esperar 1 minuto entre requests

---

### Sigue mostrando -22°C (mock)

**Diagnóstico**:
```bash
# Revisar logs del servicio en Railway
# Buscar línea: "⚠️ Usando datos MOCK de clima"
```

**Causas**:
1. Variable `OPENWEATHER_API_KEY` no configurada en Railway
2. Key inválida → fallback automático a mock
3. Deploy no completado (Railway tarda ~1 min)

**Solución**:
- Verificar variable en **Variables** tab de Railway
- Esperar 2 minutos después de cambiar variable
- Testear con `test_api_key.py` primero

---

## 📊 Plan Gratuito OpenWeather

✅ **Incluido**:
- 60 requests/minuto
- 1,000,000 requests/mes
- Current weather data
- 5-day forecast

❌ **NO incluido** (planes pagos):
- Historical data
- Minutely forecast
- Air pollution data

**Suficiente para Tiburón**: ✅ SÍ
- Tiburón hace 1 request cada 24h = ~30 requests/mes
- Muy por debajo del límite gratuito

---

## 🎯 Checklist Final

Antes de declarar victoria:

- [ ] API key obtenida de OpenWeather
- [ ] `test_api_key.py` pasa exitosamente (clima real mostrado)
- [ ] Variable configurada en Railway (pulse-scheduler)
- [ ] Variable configurada en Railway (main service)
- [ ] Deploy completado (logs sin errores)
- [ ] Endpoint `/api/debug/external-signals` muestra clima REAL (no -22°C)
- [ ] Pulse manual enviado a Discord con clima real
- [ ] Clima actualiza diariamente a las 8:00 AM

---

## 🔗 Links Útiles

- **OpenWeather API**: https://openweathermap.org/api
- **API Keys Dashboard**: https://home.openweathermap.org/api_keys
- **Documentación**: https://openweathermap.org/current
- **FAQ Error 401**: https://openweathermap.org/faq#error401
- **Railway Dashboard**: https://railway.app

---

## 🦈 Próximos Pasos

Una vez que clima REAL funciona:

1. ✅ Monitorear Pulso diario a las 8:00 AM
2. ✅ Verificar predicciones por clima (frío → chaquetas)
3. ✅ Ajustar multiplicadores si necesario
4. ✅ Agregar más correlaciones clima-producto
5. ✅ Considerar forecast 5-day (próxima iteración)

---

**Estado Target**:
```
🌡️ Columbus, Ohio: <TEMP_REAL>°C, <CONDICION_REAL>
📊 Chaqueta Térmica: ROI 55.3% (clima contextual)
```

¡Dale gas! 🔥🦈
