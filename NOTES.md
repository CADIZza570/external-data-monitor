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