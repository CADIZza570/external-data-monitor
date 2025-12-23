# NOTES.md - Registro del Proyecto Línea Base

## Weekly Post-Mortem - 16 Diciembre 2025

**¿Qué se rompió esta semana?**  
- La API original (fake-store-api) dio error 404 y falló la primera ejecución.

**¿Por qué?**  
- APIs gratuitas hospedadas en Render pueden apagarse o cambiar de URL sin aviso.

**¿Cómo lo evitaría la próxima?**  
- Preferir APIs estables y conocidas como JSONPlaceholder para desarrollo.  
- En el futuro (Mes 4), documentar siempre un "Plan B" con API alternativa.

**¿Cómo encaja esta semana en el plan completo?**  
- ¡Mes 1 casi completado en un solo día!  
- Script modular con logging, validación, guardado en output/ y manejo de errores funcionando al 100%.  
- Primera prueba real de resiliencia: detectó el fallo, lo logueó y seguimos adelante.  
- Proyecto Línea Base listo para evolucionar en los próximos meses.

**Próximos pasos inmediatos:**  
- Crear README.md profesional  
- Subir todo a GitHub público  
- Artefacto visible mensual (Capturas de consola y carpeta output/ con múltiples ejecuciones)

## Decision Log – Data Cleaning

Chose to keep all raw outputs in /output as execution evidence.
Introduced *_clean.csv as the canonical dataset for downstream systems.

## 🎉 Milestone: Repositorio limpio y .gitignore funcional - 18 Dic 2025 (tarde)

**Logros:**
- ✅ .gitignore creado y configurado
- ✅ 18 archivos generados removidos de Git
- ✅ Push exitoso sin outputs ni logs
- ✅ Repositorio profesional y mantenible

**Archivos removidos:**
- Logs: api_data_fetcher.log
- Outputs: 15+ CSVs/JSONs
- Sistema: .DS_Store

**Próximo sprint:**
- Validación de nicho (Columbus)
- Completar Mes 2 (read_excel, merge)
- Preparar para Mes 3 

# Exploración de Nicho - 19 Diciembre 2025

## E-commerce (Shopify / Inventory Automation)
- Job 1 (Upwork): "Senior Analytics Engineer – Shopify Inventory Forecasting" – Necesitan sistema automático para forecast demand, low-stock alerts, transfers entre locations. Stack: Shopify API + Python + BigQuery. Presupuesto implícito alto (proyecto producción).
- Job 2 (Upwork/LinkedIn): Múltiples para "Shopify Developer" – Custom apps, API integration para inventory sync, dropshipping automation, stock alerts.
- Job 3 (LinkedIn): +250 jobs Shopify Developer en USA – Temas recurrentes: custom themes, apps privadas, automation con React/Node/Python.
- Dolor común: Gestión manual de stock (low-stock, dead stock, transfers), pérdida de ventas por stockouts.
- Demanda: ALTA (decenas de jobs activos, presupuestos $200-400+).

## Inmobiliarias (Real Estate Leads / WhatsApp Automation)
- Jobs encontrados: Pocos específicos para automation. Algunos generales para CRM/property management, pero no alertas WhatsApp o leads automáticos recientes.
- Dolor común: Leads manuales de portales, seguimiento lento.
- Demanda: BAJA en búsquedas actuales (menos evidencia directa).

## Coaches / Consultores (Calendar / Onboarding Automation)
- Jobs encontrados: Casi nulos específicos. Algunos para virtual assistants o CRM general, pero no automation de calendarios/onboarding para coaches.
- Dolor común: Gestión manual de citas y clientes nuevos.
- Demanda: BAJA (poca evidencia en plataformas freelance).

## Nicho tentativo elegido: E-commerce (Shopify Inventory & Alerts)
Razones:
- Más jobs reales y activos.
- Encaja perfecto con tu Proyecto Línea Base (API data fetch, limpieza, alertas futuras).
- Presupuestos visibles y demanda creciente (retail multi-location necesita automation).
- Fácil evolución: Tu script ya maneja datos → agregar alertas stock bajo, forecast simple con Pandas.

Próximo: Evolucionar script para "low-stock alert" demo (Mes 3-4).

¡Sistemas vivos en acción! 🔥

# Weekly Post-Mortem - 19 Diciembre 2025 (Cierre Mes 2 / Inicio Mes 3)

¿Qué se rompió esta semana?
- Inicialmente planeábamos n8n como cerebro principal (Mes 3).
- Riesgo detectado: dependencia externa, límites gratis, menos control.

¿Por qué?
- n8n es rápido para prototipos, pero en producción real dependes de su pricing, estabilidad y límites.
- El PLAN busca "sistemas vivos que no mueren" y "control total".

¿Cómo lo evitaría la próxima?
- Priorizar siempre herramientas con control total (Python puro) antes de low-code externas.
- Evaluar dependencias externas con la pregunta: "¿Si esta herramienta desaparece mañana, mi sistema sigue vivo?"

¿Cómo encaja esta semana en el plan completo?
- Mes 2 cerrado al 100%: Pandas pipeline completo (limpieza, extracción city, reporte automático).
- Pivot inteligente a Python + schedule/cron como base (control total).
- Nicho tentativo elegido: E-commerce (Shopify inventory alerts) con evidencia real de Upwork.
- Artefacto visible: Daemon automático corriendo solo, CSV clean con city, requirements.txt actualizado.
- Decisión profesional: n8n queda como opción secundaria (solo si cliente lo pide y cobro extra).

Conclusión: El plan evoluciona a más resiliencia y monetización real.  
¡Sistemas vivos en acción – control total conseguido! ⚡

# Weekly Post-Mortem - 19 Diciembre 2025 (Cierre Mes 2 / Inicio Mes 3)

¿Qué se rompió esta semana?
- Warnings de Pandas (FutureWarning chained assignment).
- Dependencia inicial planeada en n8n (riesgo de límites y control bajo).

¿Por qué?
- Warnings: Uso de chained assignment (df["col"] = ...) que cambiará en pandas 3.0.
- n8n: Rápido para prototipos, pero dependes de pricing externo, límites gratis y menos control total.

¿Cómo lo evitaría la próxima?
- Warnings: Siempre usar df.loc[:, "col"] = ... para asignaciones seguras.
- Dependencias externas: Evaluar con "si desaparece mañana, ¿mi sistema vive?" → Priorizar Python puro.

¿Cómo encaja esta semana en el plan completo?
- Mes 2 cerrado al 100%: Pandas pipeline completo (limpieza, extracción city, reporte automático, warnings eliminados).
- Pivot inteligente: De n8n a Python + schedule/cron (control total, estabilidad profesional).
- Daemon automático corriendo en background (ejecuciones programadas reales).
- Nicho tentativo: E-commerce (Shopify inventory alerts) con evidencia Upwork.
- Artefactos visibles: CSV clean con city, daemon vivo, PDF del plan generado.
- requirements.txt actualizado con schedule.

Conclusión: El plan evoluciona a más resiliencia y monetización real.  
Sistemas vivos > herramientas externas frágiles.  
¡Control total conseguido! ⚡

# Weekly Post-Mortem - 20 Diciembre 2025 (Avance Mes 3)

¿Qué se rompió esta semana?
- Warnings de Pandas (chained assignment).
- Mezcla inicial de lógica y automatización en un solo archivo.

¿Por qué?
- Warnings: Asignación chained (df["col"] = ...) que cambiará en pandas 3.0.
- Mezcla: Integramos schedule directamente en api_data_fetcher.py (viola separación de responsabilidades).

¿Cómo lo evitaría la próxima?
- Warnings: Siempre usar df.loc[:, "col"] = ... para asignaciones seguras.
- Arquitectura: Separar lógica pura (api_data_fetcher.py) de automatización (automation_runner.py) desde el principio.

¿Cómo encaja esta semana en el plan completo?
- Mes 2 cerrado al 100%: Limpieza Pandas, extracción city segura (json.loads), reporte automático.
- Mes 3 avanzado: Runner automático separado con schedule (cada hora), fallback resiliencia.
- Arquitectura pro: Lógica pura + runner separado (ejecutable manual o automático).
- Nicho tentativo confirmado: E-commerce (Shopify inventory alerts).
- Artefactos visibles: Daemon corriendo, CSV clean con city, PDF del plan generado.

Conclusión: 
- Pivot a control total (Python puro > low-code).
- Código más mantenible, testeable y listo para cron real.
- Sistemas vivos en acción – separación limpia conseguida. ⚡

# Weekly Post-Mortem - 20 Diciembre 2025 (Avance Mes 3)

### 🚀 API DATA FETCHER – ALERTAS DOCUMENTADAS

Este bloque resume las alertas implementadas en el `api_data_fetcher.py`:

```python
### 1️⃣ ALERTA FILAS INCOMPLETAS (Missing Data)
# Revisa las columnas críticas: id, name, email
# Si hay NaNs, genera alerta y guarda CSV opcional
def alert_missing_data(df: pd.DataFrame):
    critical_cols = ["id", "name", "email"]
    missing_rows = df[df[critical_cols].isnull().any(axis=1)]

    if not missing_rows.empty:
        alert_msg = f"🚨 ALERTA: {len(missing_rows)} filas con datos críticos faltantes"
        print(alert_msg)
        print(missing_rows[critical_cols])
        logging.warning(alert_msg)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/missing_data_{ts}.csv"
        missing_rows.to_csv(path, index=False)
        print(f"💾 CSV de registros incompletos guardado: {path}")
    else:
        print("ℹ️ No se detectaron filas con datos críticos faltantes")

### 2️⃣ ALERTA DUPLICADOS POR EMAIL
# Detecta registros duplicados usando la columna 'email'
# Genera alerta en consola y log
duplicated_rows = df[df.duplicated(subset=["email"])]
if not duplicated_rows.empty:
    alert = f"🚨 ALERTA: {len(duplicated_rows)} duplicados detectados por email"
    print(alert)
    print(duplicated_rows[["email"]])
    logging.warning(alert)
else:
    print("ℹ️ No se detectaron duplicados")

### 3️⃣ ALERTA STOCK BAJO
# Revisa columnas 'stock' y 'product_id'
# Si stock <= threshold, genera alerta y guarda CSV automáticamente
def alert_low_stock(df: pd.DataFrame, threshold: int = 5):
    if "stock" not in df.columns or "product_id" not in df.columns:
        print("ℹ️ No se detectó columna 'stock' o 'product_id', alerta de stock ignorada")
        return

    low_stock = df[df["stock"] <= threshold]

    if not low_stock.empty:
        alert_msg = f"🚨 ALERTA: {len(low_stock)} productos con stock <= {threshold}"
        print(alert_msg)
        print(low_stock[["product_id", "name", "stock"]])
        logging.warning(alert_msg)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/low_stock_{ts}.csv"
        low_stock.to_csv(path, index=False)
        print(f"💾 CSV de stock crítico guardado: {path}")
    else:
        print("ℹ️ No hay productos con stock crítico")
        
### 4️⃣ ALERTA VENTAS INUSUALES / SIN VENTAS
# Revisa columnas 'product_id', 'name', 'last_sold_date'
# Si un producto no se ha vendido en más de X días, genera alerta y guarda CSV automáticamente
def alert_unusual_sales(df: pd.DataFrame, days_threshold: int = 30):
    if "last_sold_date" not in df.columns or "product_id" not in df.columns:
        print("ℹ️ No se detectó columna 'last_sold_date' o 'product_id', alerta de ventas ignorada")
        return

    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days_threshold)
    unsold_products = df[pd.to_datetime(df["last_sold_date"]) < cutoff_date]

    if not unsold_products.empty:
        alert_msg = f"🚨 ALERTA: {len(unsold_products)} productos sin ventas en los últimos {days_threshold} días"
        print(alert_msg)
        print(unsold_products[["product_id", "name", "last_sold_date"]])
        logging.warning(alert_msg)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{OUTPUT_DIR}/unsold_products_{ts}.csv"
        unsold_products.to_csv(path, index=False)
        print(f"💾 CSV de productos sin ventas guardado: {path}")
    else:
        print(f"ℹ️ Todos los productos tienen ventas recientes (<{days_threshold} días)")
        
### 🔹 Notas generales
# - Todos los CSV de alerta se guardan automáticamente en la carpeta output.
# - Las alertas se muestran en consola y también se registran en el log.
# - La limpieza final del CSV elimina duplicados y columnas pesadas para análisis.

# Weekly Post-Mortem - 20 Diciembre 2025 (Avance Mes 3)

## 🔹 Cron / Automización

- Se configuró `run_api_data_fetcher.py` como job de cron.
- Prueba rápida: cada minuto (`* * * * *`) para validar ejecución.
- Logs revisados con `tail -f .../logs/cron.log`.
- CSV y JSON se generan correctamente en carpeta `output/`.
- Alertas visibles en log: stock crítico, ventas inusuales, filas incompletas.
- Script ejecutable con `chmod +x`.
- Sin errores críticos reportados; warning FutureWarning de pandas no rompe ejecución.

## Próximos pasos

1. Esperar confirmación de 2-3 ejecuciones consecutivas exitosas.
2. Cambiar cron a horario definitivo (ej.: cada hora) para full-time.
3. Revisar alertas de negocio real (ventas inusuales) y ajustar umbrales si es necesario.
4. Documentar resultados de pruebas en NOTES.md.
    
Weekly Post-Mortem - 21 Diciembre 2025 (Avance Mes 3)

🚀 API DATA FETCHER – EJECUCIÓN INICIAL DOCUMENTADA
Estado actual:
Pipeline ejecutado con python3 -i api_data_fetcher.py.
Backup automático del script creado: backups/api_data_fetcher_backup_TIMESTAMP.py.
Fetch API funcionando: 10 registros obtenidos y validados.
CSV y JSON raw generados en output/.
Validación de columnas completada: ✅ todas presentes.
Alertas revisadas:
Filas incompletas: ninguna detectada.
Stock bajo: no aplica (sin columna 'stock').
Duplicados: ninguno detectado.
Procesamiento de duplicados y limpieza final correcto.
CSV limpio generado: output/users_data_TIMESTAMP_clean.csv.
Ejecución finalizada sin errores.
Checklist de verificación previa a cada corrida:
.env actualizado con credenciales correctas (EMAIL_PASSWORD, SHOPIFY_TOKEN, etc.).
Librerías instaladas: pandas, requests, python-dotenv, schedule.
Carpetas existentes:
output/
backups/
Script actualizado y versionado (backup automático activo).
Variables globales definidas (OUTPUT_DIR, LOW_STOCK_THRESHOLD, etc.).
Funciones principales listas: fetch, validate, alerts, process, save.
SMTP listo para envíos de correo (prueba manual o dummy).
Logs funcionando (logs/cron.log si se ejecuta en cron).
Python 3.14 confirmado.

Próximos pasos:
Testear flujo shopify y validar paginación completa.
Ejecutar pipeline con CSV local de prueba para debug.
Configurar schedule o cron para automatización periódica.
Revisar alertas de negocio real (stock bajo, ventas inusuales) y ajustar thresholds.
Documentar resultados de cada corrida en NOTES.md.
Preparar snippet de ejecución automática para producción.

# 🧠 NOTES – Webhook Automation System

## 📅 Fecha

22‑12‑2025

---

## 🎯 Objetivo de esta fase

Construir y validar un **servidor de webhooks funcional**, capaz de recibir datos tipo Shopify, procesarlos y generar diagnósticos automáticos con evidencia.

---

## ✅ Logros confirmados

* Flask server levantado correctamente en `:5001`
* Endpoint `/webhook/shopify` operativo
* Payload recibido y visible en terminal
* Conversión correcta a `DataFrame`
* Alertas ejecutadas:

  * Stock bajo
  * Sin ventas
  * Datos faltantes
* CSVs generados automáticamente en `/output`

---

## 🧩 Problemas resueltos (importante)

### 1. Imports rotos

* Causa: módulos no existentes o sin `__init__.py`
* Solución:

  * Crear estructura correcta
  * Ejecutar `setup_project.py`

### 2. Error `logging not defined`

* Causa: uso de `logging` sin import
* Solución:

```python
import logging
```

### 3. Confusión de puertos

* Flask corre en **5001**, no 5000
* Curl debe apuntar al puerto correcto

---

## 🏗️ Arquitectura validada

* Flask = capa de entrada
* fetchers = ingestión
* alerts = reglas de negocio
* diagnostics = limpieza / outputs
* output = evidencia (no logs ocultos)

Esto cumple estándar **MVP vendible**.

---

## 🧠 Decisiones técnicas clave

* CSV como output principal (auditable)
* Sin DB por ahora (simplicidad > complejidad)
* Código modular (escala fácil)
* Errores visibles, no silenciosos

---

## 🚀 Próximos bloques (confirmados)

### 2️⃣ Conectar Shopify real

* API REST
* Token privado
* Webhook real desde admin Shopify

### 3️⃣ Automatizar

* `cron` (producción)
* `schedule` (local / demo)

---

## 🧱 Estado mental del proyecto

> Esto **ya no es práctica**, es un sistema real.

Base sólida para:

* Portafolio
* Side income
* Cliente real

Seguimos.


---

## 3️⃣ Contenido sugerido para `NOTES.md`

```markdown
# NOTES.md - Python Automation

## Últimas pruebas
- [x] Webhook Shopify simulado correctamente con ngrok.
- [x] CSV de alertas generados (`low_stock`, `simulation_test`).
- [x] Variables de entorno cargadas desde `.env`.
- [x] Configuración segura para GitHub (secrets ignorados).

## Próximos pasos
1. Validar HMAC de Shopify en `webhook_server.py`.
2. Organizar `config.py` central para todas las variables.
3. Automatización programada con `schedule` / cron.
4. Documentar funciones clave en cada módulo.

## Observaciones
- Mantener `.env` y `security.env` fuera de GitHub.
- Archivos generados y logs solo locales.
- Subir únicamente scripts y documentación.
