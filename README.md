# External Data Monitor - Baseline Project

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)
![Progress](https://img.shields.io/badge/progress-Mes%202%20(80%25)-yellow.svg)
![Commits](https://img.shields.io/github/commit-activity/w/CADIZza570/external-data-monitor)

Professional Python script that:
- Consumes public APIs (currently JSONPlaceholder /users)
- Validates data structure
- Saves results to timestamped CSV and JSON files
- Logs detailed execution and errors

## 📸 Demo

### Successful execution:
```
🚀 Iniciando api_data_fetcher.py – Proyecto Línea Base (Mes 1-2)
[18:08:28] Conectando a la API...
✅ Datos descargados: 10 registros
Validando estructura de datos...
✅ Validación exitosa

REPORTE DE LIMPIEZA (Mes 2)
- Registros originales: 10
- Registros limpios: 10
- Duplicados eliminados: 0
- Columnas seleccionadas: id, name, username, email, phone, website, city

✅ CSV guardado: output/users_data_20251218_180828.csv
✅ JSON guardado: output/users_data_20251218_180828.json
🎉 Script completado con éxito
```

### Data analysis with groupby():
```
📊 ANÁLISIS DE DATOS CON GROUPBY (Mes 2)
============================================================

1️⃣ Usuarios por dominio de email:
email_domain
annie.ca       1
april.biz      1
elvis.io       1
...

🏆 Dominio más común: annie.ca (1 usuarios)

2️⃣ Usuarios por ciudad:
city
Aliyaview         1
Bartholomebury    1
Gwenborough       1
...

✅ Análisis completado
```

## Data Validation Logic

### Required fields
- **id:** Unique identifier required for tracking records
- **name:** Primary human-readable identifier
- **email:** Required for contact and system integrations
- **phone:** Required for potential outreach or CRM use

### Optional fields
- **address:** Not always needed depending on use case
- **website:** Informational only

### Discarded fields
- **company:** Removed to reduce noise and because it's not required for the current automation scope

Part of the **DEFINITIVE PLAN - Python + Automations (6 months)**  
Philosophy: Living systems that don't die.

## Installation

```bash
pip install pandas requests
```

## Dependencies

See `requirements.txt` for exact versions.

Install with:
```bash
pip install -r requirements.txt
```

## Usage

```bash
python api_data_fetcher.py
```

The script will:
1. Fetch data from JSONPlaceholder API
2. Validate required columns
3. Clean duplicates and normalize emails
4. Save timestamped outputs to `output/` directory
5. Log all operations to `api_data_fetcher.log`

### Data analysis:
```bash
python analyze_users.py
```

## Features

### Resilience (Mes 1 + Mes 4)
- ✅ Exponential backoff retry logic (1s, 2s, 4s)
- ✅ Handles 500, 502, 503, 504 server errors
- ✅ Timeout protection (10s max)
- ✅ Connection error handling

### Data Processing (Mes 2)
- ✅ Pandas data cleaning pipeline
- ✅ Duplicate removal by email
- ✅ Email normalization (lowercase)
- ✅ Email validation (contains @)
- ✅ City extraction from address
- ✅ Column selection and filtering

### Analysis (Mes 2)
- ✅ groupby() aggregations
- ✅ Multi-column statistics with .agg()
- ✅ Domain frequency analysis
- ✅ Geographic distribution

## Project Structure

```
python-automation/
├── api_data_fetcher.py      # Main script with retry logic
├── analyze_users.py          # Data analysis with groupby()
├── test_manual.py            # Manual test suite
├── requirements.txt          # Dependencies
├── README.md                 # This file
├── NOTES.md                  # Project journal and post-mortems
└── output/                   # Generated files (not in Git)
    ├── users_data_*.csv
    ├── users_data_*.json
    └── users_data_*_clean.csv
```

## 🎯 Roadmap

### ✅ Completed (Mes 1-2):
- [x] Resilient API fetching with retry logic
- [x] Data validation and cleaning with Pandas
- [x] Professional logging and error handling
- [x] Automated duplicate removal
- [x] Email normalization and validation
- [x] Data analysis with groupby()
- [x] City extraction from nested JSON

### 🟡 In Progress (Mes 3):
- [ ] n8n workflow integration
- [ ] Webhook endpoints
- [ ] Email alerts on errors
- [ ] Multi-source data aggregation

### ⏳ Planned (Mes 4-6):
- [ ] Niche validation (Columbus, OH market)
- [ ] Client-ready maintenance package ($30-50/month)
- [ ] Production deployment with monitoring
- [ ] Excel file support (read_excel)
- [ ] Data merging from multiple sources

### Mes 3 - Ejecuciones automáticas (Python + schedule)
- El script ahora corre como daemon local.
- Intervalo actual: cada 10 minutos (para pruebas).
- Próximo: migración a cron en servidor real.
- Control total: sin dependencias externas.

Usage daemon:
```bash
python3 api_data_fetcher.py

## Progress Status

**Current:** Mes 2 (80% complete) - 5-6 weeks ahead of schedule  
**Next milestone:** n8n basic workflow (Mes 3)  
**Timeline:** Started Dec 17, 2025

## Contributing

This is a learning project following the "Definitive Plan - Python + Automations (6 months)".  
Philosophy: Systems that don't die. Action > Perfection.

## License

Personal learning project - Not licensed for commercial use yet.

---

**Part of:** [DEFINITIVE PLAN - Python + Automations (6 months)](PLAN.md)  
**Author:** Constanza Araya  
**Location:** Columbus, Ohio, US

# 🚀 Webhook Automation System – Shopify (MVP)

## 📌 Descripción general

Sistema de automatización en Python que recibe webhooks (simulados o reales), procesa datos de productos, genera diagnósticos automáticos y guarda evidencia en archivos CSV.

Este proyecto está diseñado bajo la filosofía de **sistemas vivos, mantenibles y vendibles**, enfocado en automatizaciones reales para e‑commerce.

---

## 🧠 Qué hace el sistema

* Recibe webhooks vía **Flask** (`POST`)
* Procesa payloads tipo Shopify
* Convierte datos a `DataFrame`
* Ejecuta diagnósticos automáticos:

  * 📉 Stock bajo
  * 💤 Productos sin ventas
  * ⚠️ Datos faltantes
* Guarda resultados en CSV auditables
* Devuelve respuesta HTTP clara

---

## 🗂️ Estructura del proyecto

```
tu_proyecto/
│
├── webhook_server.py        # Servidor Flask (entrada principal)
├── config.py                # Configuración global (thresholds, paths)
│
├── fetchers/
│   ├── __init__.py
│   └── fetchers.py          # Ingesta de datos (local / APIs)
│
├── alerts/
│   ├── __init__.py
│   └── alerts.py            # Lógica de alertas
│
├── diagnostics/
│   ├── __init__.py
│   └── diagnostics.py       # Limpieza, validación y guardado
│
├── output/                  # Evidencia generada (CSV)
│
├── logs/                    # Logs de ejecución
└── README.md
```

---

## ▶️ Cómo ejecutar el servidor

Desde la carpeta del proyecto:

```bash
python3 webhook_server.py
```

Servidor disponible en:

```
http://127.0.0.1:5001
```

---

## 🧪 Cómo probar (simulación Shopify)

```bash
curl -X POST http://127.0.0.1:5001/webhook/shopify \
-H "Content-Type: application/json" \
-d '{
  "products": [
    {
      "title": "Camiseta Roja",
      "variants": [
        {
          "id": 101,
          "title": "S",
          "inventory_quantity": 3,
          "last_sold_date": "2025-12-10"
        }
      ]
    }
  ]
}'
```

---

## 📂 Resultados esperados

Después de una llamada exitosa:

* `output/shopify_webhook_*.csv`
* `output/low_stock_*.csv`
* `output/no_sales_*.csv`

Estos archivos son **evidencia directa** del diagnóstico.

---

## 🧱 Estado del proyecto

* ✅ MVP funcional
* ✅ Arquitectura modular
* ✅ Listo para integración real con Shopify
* ✅ Automatizable con cron / schedule

---

## 🚀 Próximos pasos

1. Conectar Shopify real (API + Webhooks oficiales)
2. Automatizar ejecución con `cron` o `schedule`
3. Agregar notificaciones (email / Slack)
4. Empaquetar como servicio vendible

---
# Python Automation: Shopify Webhook & CSV Alerts

## Descripción
Proyecto de automatización en Python para:
- Recibir webhooks de Shopify (productos, stock, ventas).
- Generar alertas de bajo stock o sin ventas.
- Crear CSV de reportes y registros históricos.
- Integración segura usando `.env` para variables de configuración.

Se enfoca en **Python puro + cron/schedule** para sistemas mantenibles.

---

## Estructura del proyecto



## 👤 Autor

Gonzalo Diaz – Automatización & Sistemas Python
