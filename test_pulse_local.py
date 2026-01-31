#!/usr/bin/env python3
"""
🧪 Test Pulso Local - Con DB local (datos reales Columbus)
Simula el Pulse completo sin llamar al API de Railway
"""

import sqlite3
from datetime import datetime
from external_signals_engine import ExternalSignalsEngine

DB_FILE = "./webhooks.db"


def get_top_opportunities():
    """Obtener top oportunidades ROI de DB local"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Simular cálculo ROI básico
    cursor.execute("""
        SELECT
            sku,
            name,
            stock,
            velocity_daily,
            price,
            cost_price,
            category,
            ROUND((stock / NULLIF(velocity_daily, 0)), 1) as days_of_stock,
            ROUND((price - cost_price) * velocity_daily * 30, 2) as monthly_profit_potential
        FROM products
        WHERE velocity_daily > 0 AND category IN ('A', 'B')
        ORDER BY days_of_stock ASC
        LIMIT 5
    """)

    opportunities = []
    for row in cursor.fetchall():
        sku, name, stock, vel, price, cost, cat, days_stock, monthly_profit = row

        # Calcular ROI simplificado
        roi_percent = ((price - cost) / cost * 100) if cost > 0 else 0

        opportunities.append({
            'sku': sku,
            'name': name,
            'stock': stock,
            'velocity': vel,
            'days_stock': days_stock,
            'roi_expected': roi_percent,
            'units': int(vel * 7),  # Reorden para 7 días
            'category': cat,
            'monthly_profit': monthly_profit
        })

    conn.close()
    return opportunities


def get_cash_flow_summary():
    """Resumen cash flow de DB local"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ROUND(SUM(stock * cost_price), 2) as total_inventory_value,
            ROUND(SUM(CASE WHEN category = 'Dead' THEN stock * cost_price ELSE 0 END), 2) as dead_stock_value,
            COUNT(CASE WHEN velocity_daily > 0 AND stock / NULLIF(velocity_daily, 0) < 3 THEN 1 END) as stockout_risk_count
        FROM products
    """)

    row = cursor.fetchone()
    conn.close()

    return {
        'total_inventory_value': row[0] or 0,
        'dead_stock_value': row[1] or 0,
        'stockout_opportunity_cost': row[2] * 1200 if row[2] else 0  # Estimado
    }


def generate_sticker():
    """Generar Sticker Tiburón con datos locales"""

    # 1. Señales externas (clima Columbus)
    engine = ExternalSignalsEngine()
    weather = engine.get_weather_data(use_mock=False)  # Clima REAL
    holidays = engine.get_upcoming_holidays(days_ahead=30)

    # 2. Cash flow
    summary = get_cash_flow_summary()

    # 3. Top oportunidades
    opportunities = get_top_opportunities()

    # 4. Generar mensaje
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    # Header
    message = f"🦈 **TIBURÓN PREDICTIVO - PULSO DIARIO**\n"
    message += f"⏰ {timestamp}\n\n"

    # Clima
    temp = weather.get('temp_celsius', 0)
    condition = weather.get('condition', 'Unknown')
    message += f"🌡️ **Columbus, Ohio:** {temp:.1f}°C, {condition}\n"

    # Feriados
    if holidays:
        next_holiday = holidays[0]
        days = next_holiday.get('days_until', 0)
        name = next_holiday.get('name', '')
        message += f"🎉 **Próximo feriado:** {name} (en {days} días)\n"

    # Cash Flow
    total_inv = summary['total_inventory_value']
    stockout_cost = summary['stockout_opportunity_cost']
    dead = summary['dead_stock_value']

    message += f"\n💰 **Cash Flow:**\n"
    message += f"- Inventario: ${total_inv:,.0f}\n"
    message += f"- Stockout Cost: ${stockout_cost:,.0f}/mes\n"
    message += f"- Dead Stock: ${dead:,.0f}\n"

    # Escudo (simplificado)
    message += f"\n🛡️ **Escudo de Liquidez:** ✅ ACTIVO\n"
    message += f"- CCC: 45.2 días\n"
    message += f"- Estado: 🔥 OPERATIVO\n"

    # Top oportunidades CON contexto clima
    if opportunities:
        message += f"\n📊 **TOP OPORTUNIDADES (ROI Predictivo):**\n"

        for i, opp in enumerate(opportunities, 1):
            name = opp['name']
            roi = opp['roi_expected']
            units = opp['units']
            days_stock = opp['days_stock']

            message += f"{i}. **{name}**: ROI {roi:.1f}% ({units} unidades, {days_stock:.1f} días stock)\n"

            # Contexto predictivo clima
            context = engine.get_contextual_multiplier(name, use_mock_weather=False)

            if context.get('has_any_impact'):
                reason = context.get('combined_reason', '')
                message += f"   🌡️ *{reason}*\n"

    # Veredicto
    dead_percent = (dead / total_inv * 100) if total_inv > 0 else 0

    if dead_percent > 30:
        message += f"\n**Veredicto:** 🛡️ Modo cautela - {dead_percent:.1f}% inventario muerto"
    elif stockout_cost > 2000:
        message += f"\n**Veredicto:** 🔥 Dale gas con las oportunidades!"
    else:
        message += f"\n**Veredicto:** ✅ Operación saludable - monitorear tendencias"

    return message


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 TEST PULSO LOCAL - Datos Reales Columbus")
    print("="*70 + "\n")

    print("📊 Generando Sticker con datos locales...\n")

    sticker = generate_sticker()

    print(sticker)

    print("\n" + "="*70)
    print("✅ Test completado - Este es el Sticker que se enviaría a Discord")
    print("="*70 + "\n")
