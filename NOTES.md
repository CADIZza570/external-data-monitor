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

¡Sistemas vivos en acción! 🔥