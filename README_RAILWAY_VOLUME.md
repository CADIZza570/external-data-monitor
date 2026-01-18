# 📦 Configurar Volumen Persistente en Railway

## 🎯 Objetivo
Hacer que la base de datos `webhooks.db` NO se borre entre deploys.

---

## ✅ Cambios en el código (ya hechos)

1. **`database.py`**: Ahora usa `DATA_DIR` environment variable
2. **`railway.json`**: Define `DATA_DIR=/data`
3. Base de datos se guardará en `/data/webhooks.db` (volumen persistente)

---

## 🔧 Pasos en Railway Dashboard

### 1. Ir a tu proyecto en Railway
- URL: https://railway.app/dashboard
- Proyecto: `tranquil-freedom-production`

### 2. Crear un Volume
1. Click en tu servicio (webhook server)
2. Click en pestaña **"Variables"**
3. Scroll abajo hasta **"Volumes"**
4. Click **"+ New Volume"**

### 3. Configurar el Volume
```
Mount Path: /data
```

### 4. Redeploy
Railway automáticamente redeployará con el volumen montado.

---

## 🧪 Verificar que funciona

### 1. Enviar un webhook de prueba
```bash
curl -X POST https://tranquil-freedom-production.up.railway.app/webhook/shopify \
  -H "Content-Type: application/json" \
  -H "X-Shopify-Topic: products/update" \
  -d '{"id": 123, "title": "Test Persistencia"}'
```

### 2. Ver que se guardó
```bash
curl https://tranquil-freedom-production.up.railway.app/api/debug/webhooks
```

### 3. Forzar un redeploy
```bash
git commit --allow-empty -m "Test volume persistence"
git push origin main
```

### 4. Verificar que los datos siguen ahí
```bash
curl https://tranquil-freedom-production.up.railway.app/api/debug/webhooks
```

Si ves el webhook "Test Persistencia" después del redeploy = ✅ Volumen funciona

---

## 📊 Comparación

### ❌ ANTES (sin volumen)
```
Deploy 1: webhooks.db existe → guarda datos
Deploy 2: webhooks.db SE BORRA → empieza vacío
```

### ✅ DESPUÉS (con volumen)
```
Deploy 1: /data/webhooks.db existe → guarda datos
Deploy 2: /data/webhooks.db PERSISTE → datos intactos
```

---

## 🚨 Notas importantes

1. **Backups**: Railway NO hace backups automáticos del volumen
   - Solución: Exportar datos periódicamente via API

2. **Tamaño**: Volumen empieza con 1GB (gratis)
   - Monitorear con: `du -sh /data/webhooks.db`

3. **Performance**: SQLite es perfecto hasta ~100K webhooks/día
   - Si creces más: migrar a PostgreSQL

---

## 🐛 Troubleshooting

### Error: "Permission denied /data"
- Railway aún no montó el volumen
- Esperar 1-2 minutos después de crear el volume

### DB sigue borrándose
- Verificar que `DATA_DIR=/data` en Variables
- Verificar logs: debe decir "📁 Directorio de datos: /data"

### Volumen lleno
- Ver tamaño: Logs de Railway
- Limpiar webhooks viejos: endpoint de limpieza
