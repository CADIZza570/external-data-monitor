#!/bin/bash
# =============================================================
# 🚀 RAILWAY STARTUP SCRIPT - La Chaparrita
# =============================================================
# Este script se ejecuta cada vez que Railway inicia el servidor.
#
# Orden de ejecución:
# 1. Migrar base de datos (si es necesario)
# 2. Levantar servidor Flask
# =============================================================

set -e  # Exit on error

echo "============================================================"
echo "🚀 INICIANDO SERVIDOR - La Chaparrita"
echo "============================================================"

# =============================================================
# PASO 1: MIGRACIÓN DE BASE DE DATOS
# =============================================================

echo ""
echo "📊 PASO 1: Verificando migración de base de datos..."
echo "============================================================"

if python3 migrate_db_cashflow.py; then
    echo "✅ Migración completada exitosamente"
else
    echo "⚠️  Migración falló o ya estaba ejecutada (continuando...)"
fi

echo ""
echo "============================================================"

# =============================================================
# PASO 2: LEVANTAR SERVIDOR FLASK
# =============================================================

echo ""
echo "🌐 PASO 2: Levantando servidor Flask..."
echo "============================================================"

# Railway usa PORT variable de entorno
# Gunicorn es mejor que Flask directamente para producción
if command -v gunicorn &> /dev/null; then
    echo "✅ Usando Gunicorn (producción)"
    exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 2 --timeout 120 webhook_server:app
else
    echo "⚠️  Gunicorn no disponible, usando Flask directamente"
    exec python3 webhook_server.py
fi
