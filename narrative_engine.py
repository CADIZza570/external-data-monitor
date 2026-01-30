"""
🗣️ NARRATIVE ENGINE - El Cerebro que Habla de La Chaparrita
Transforma datos fríos en mensajes humanos, cómplices, con personalidad.

El sistema ya no solo alerta - ACONSEJA como un socio que entiende el negocio.

Tono: Chileno/callejero, directo, con humor cuando corresponde.
Ejemplo: "Con 30°C en Los Andes, Sombrero Arcoíris pide pista o se acaba antes del finde"
"""

from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)

# ============================================================
# FRASES Y PERSONALIDAD
# ============================================================

# Saludos dinámicos (hora del día)
SALUDOS = {
    'madrugada': [
        "🌙 Oye loco, te pillé despierto...",
        "🌙 Buena madrugá, Fer...",
        "🌙 Insomnio o estrategia? 🤔"
    ],
    'mañana': [
        "☀️ Buenos días, socio!",
        "☀️ Qué hay, loco! Acá está el pulso...",
        "☀️ Arriba nomás! Te traigo el reporte..."
    ],
    'tarde': [
        "🌤️ Buenas tardes, Fer!",
        "🌤️ Tarde calurosa? Acá el update...",
        "🌤️ Qué tal? Te paso el estado..."
    ],
    'noche': [
        "🌆 Buena noche, compa!",
        "🌆 Ya oscureció pero el sistema sigue...",
        "🌆 Turno noche activado..."
    ]
}

# Context climático/estacional
CLIMA_CONTEXT = [
    "Con el calor en Los Andes",
    "A 30°C en Ohio",
    "En plena temporada alta",
    "Con este sol que pela"
]

# Urgencia narrativa
URGENCIA_FRASES = {
    'critico': [
        "🔴 URGENTE wn, esto no puede esperar!",
        "🔴 ROJO TOTAL - necesitas actuar YA!",
        "🔴 Código rojo, socio..."
    ],
    'alto': [
        "🟡 Ojo con esto, está al límite...",
        "🟡 Atención: se viene el quiebre...",
        "🟡 Esto pide acción pronto..."
    ],
    'normal': [
        "🟢 Todo tranqui por ahora",
        "🟢 Bajo control, pero ojo...",
        "🟢 Sin drama, pero revisá igual"
    ]
}

# Recomendaciones accionables
RECOMENDACIONES = {
    'reorder_urgente': [
        "Dale 30 unidades o lloramos después? 😅",
        "Reordená ya o te quedás sin stock antes del finde",
        "Proveedores al teléfono, loco - esto vuela",
        "Si no comprás hoy, el lunes lloran las ventas"
    ],
    'todo_ok': [
        "Sigue así nomás, va bien 👍",
        "Inventario sano, nada que reportar",
        "Todo en orden, podés dormir tranquilo",
        "Sin dramas hoy, seguí con lo tuyo"
    ],
    'revisar': [
        "Echale un ojo a esto cuando puedas",
        "No es urgente pero dale una mirada",
        "Para la tarde revisá esto",
        "Agregalo a la lista de pendientes"
    ]
}

# ============================================================
# HELPERS
# ============================================================

def get_saludo() -> str:
    """Retorna saludo dinámico según hora del día."""
    hora = datetime.now().hour

    if 0 <= hora < 6:
        momento = 'madrugada'
    elif 6 <= hora < 12:
        momento = 'mañana'
    elif 12 <= hora < 19:
        momento = 'tarde'
    else:
        momento = 'noche'

    return random.choice(SALUDOS[momento])


def get_urgencia_nivel(stockouts: int, critical_stock: int, inventory_value: float) -> str:
    """
    Calcula nivel de urgencia del negocio.

    Returns:
        'critico', 'alto', 'normal'
    """
    if stockouts > 5 or critical_stock > 15 or inventory_value < 5000:
        return 'critico'
    elif stockouts > 2 or critical_stock > 8 or inventory_value < 10000:
        return 'alto'
    else:
        return 'normal'


def format_number(num: float) -> str:
    """Formatea números grandes con K/M."""
    if num >= 1_000_000:
        return f"${num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"${num/1_000:.1f}K"
    else:
        return f"${num:.0f}"


# ============================================================
# PULSO NARRATIVO PRINCIPAL
# ============================================================

def generar_pulso_diario(
    summary: dict,
    top_reorder: list = None,
    abc_breakdown: dict = None
) -> str:
    """
    Genera mensaje narrativo diario completo (El Pulso).

    Args:
        summary: Dict con total_products, inventory_value, stockouts_count, etc
        top_reorder: Lista de top productos para reordenar
        abc_breakdown: Breakdown por categoría ABC

    Returns:
        String formateado para Discord (con emojis, saltos de línea)

    Ejemplo output:
        ☀️ Buenos días, socio!

        📊 **PULSO DE LA CHAPARRITA** (29 Ene 2026)

        💰 **Inventario:** $45.2K en 150 productos
        🔴 **Stockouts:** 3 productos agotados (-$1,250 perdidos)
        🟡 **Stock crítico:** 12 productos con menos de 7 días

        🔥 **LO QUE PIDE ACCIÓN:**
        • Sombrero Arcoíris (SOMB-ARCO-09): 25 unidades
          Con 30°C en Los Andes, esto vuela - dale ya!
        • Bota Texana (BOT-TEX-07): 15 unidades
          Quedan 3 días de stock, apurá el reorder

        💡 **Recomendación:**
        🔴 URGENTE wn, 3 stockouts no pueden esperar!
        Dale 40 unidades totales o lloramos después? 😅

        ---
        🤖 Pulso automático del Centinela
    """
    mensaje_partes = []

    # 1. Saludo dinámico
    mensaje_partes.append(get_saludo())
    mensaje_partes.append("")  # Línea vacía

    # 2. Header con fecha
    hoy = datetime.now().strftime("%d %b %Y")
    mensaje_partes.append(f"📊 **PULSO DE LA CHAPARRITA** ({hoy})")
    mensaje_partes.append("")

    # 3. Métricas clave
    total_products = summary.get('total_products', 0)
    inventory_value = summary.get('inventory_value', 0)
    stockouts = summary.get('stockouts_count', 0)
    lost_revenue = summary.get('lost_revenue', 0)
    critical_stock = summary.get('critical_stock_count', 0)

    mensaje_partes.append(f"💰 **Inventario:** {format_number(inventory_value)} en {total_products} productos")

    if stockouts > 0:
        mensaje_partes.append(f"🔴 **Stockouts:** {stockouts} productos agotados (-{format_number(lost_revenue)} perdidos)")
    else:
        mensaje_partes.append(f"✅ **Stockouts:** Cero! Todo con stock 🎉")

    if critical_stock > 0:
        mensaje_partes.append(f"🟡 **Stock crítico:** {critical_stock} productos con menos de 7 días")

    mensaje_partes.append("")

    # 4. Top productos para reordenar (narrativa)
    if top_reorder and len(top_reorder) > 0:
        mensaje_partes.append(f"🔥 **LO QUE PIDE ACCIÓN:**")

        for idx, item in enumerate(top_reorder[:3], 1):  # Top 3
            sku = item.get('sku', 'N/A')
            name = item.get('name', 'Producto')
            units = item.get('units_needed', 0)
            urgency = item.get('urgency', '0 días')
            priority = item.get('priority', 'C')

            # Emoji según prioridad
            emoji_priority = "🔴" if priority == 'A' else "🟡" if priority == 'B' else "🟢"

            # Frase narrativa con context
            clima = random.choice(CLIMA_CONTEXT)
            mensaje_partes.append(f"{emoji_priority} **{name}** ({sku}): {units} unidades")
            mensaje_partes.append(f"   {clima}, esto vuela - dale ya! (quedan {urgency})")

        mensaje_partes.append("")

    # 5. Recomendación final (call to action)
    nivel_urgencia = get_urgencia_nivel(stockouts, critical_stock, inventory_value)
    frase_urgencia = random.choice(URGENCIA_FRASES[nivel_urgencia])

    mensaje_partes.append(f"💡 **Recomendación:**")
    mensaje_partes.append(frase_urgencia)

    if nivel_urgencia in ['critico', 'alto'] and top_reorder:
        total_units = sum(item.get('units_needed', 0) for item in top_reorder[:3])
        recomendacion = random.choice(RECOMENDACIONES['reorder_urgente'])
        mensaje_partes.append(f"Dale {total_units} unidades totales o {recomendacion.split('o')[1] if 'o' in recomendacion else 'revisá mañana'}")
    elif nivel_urgencia == 'normal':
        mensaje_partes.append(random.choice(RECOMENDACIONES['todo_ok']))

    mensaje_partes.append("")

    # 6. Footer
    mensaje_partes.append("---")
    mensaje_partes.append("🤖 Pulso automático del Centinela")

    return "\n".join(mensaje_partes)


# ============================================================
# VARIANTES NARRATIVAS
# ============================================================

def generar_alerta_spike(producto: dict, spike_pct: float) -> str:
    """
    Genera alerta narrativa para spike de demanda.

    Args:
        producto: Dict con name, sku, velocity
        spike_pct: Porcentaje de aumento (0.75 = 75%)

    Returns:
        Mensaje narrativo

    Ejemplo:
        "🔥 OYE LOCO! Sombrero Arcoíris (SOMB-09) explotó +75% en 3 días!
        Con este calor, la gente compra como loca. Reordeá YA o te quedás sin nada."
    """
    name = producto.get('name', 'Producto')
    sku = producto.get('sku', 'N/A')
    spike_percent = int(spike_pct * 100)

    clima = random.choice(CLIMA_CONTEXT)

    mensaje = f"🔥 **OYE LOCO!** {name} ({sku}) explotó +{spike_percent}% en 3 días!\n"
    mensaje += f"{clima}, la gente compra como loca. Reordeá YA o te quedás sin nada."

    return mensaje


def generar_resumen_semanal(metricas_semana: dict) -> str:
    """
    Genera resumen semanal narrativo (futuro).

    Args:
        metricas_semana: Dict con métricas de la semana

    Returns:
        Mensaje narrativo semanal
    """
    # TODO: Implementar cuando tengamos data histórica
    return "📅 **Resumen Semanal** - Próximamente..."


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test pulso diario
    print("=== TEST: PULSO DIARIO ===\n")

    summary_test = {
        'total_products': 150,
        'inventory_value': 45200.50,
        'stockouts_count': 3,
        'lost_revenue': 1250.00,
        'critical_stock_count': 12
    }

    top_reorder_test = [
        {
            'sku': 'SOMB-ARCO-09',
            'name': 'Sombrero Arcoiris',
            'units_needed': 25,
            'urgency': '3 días',
            'priority': 'A'
        },
        {
            'sku': 'BOT-TEX-07',
            'name': 'Bota Texana',
            'units_needed': 15,
            'urgency': '5 días',
            'priority': 'B'
        }
    ]

    pulso = generar_pulso_diario(summary_test, top_reorder_test)
    print(pulso)

    print("\n\n=== TEST: ALERTA SPIKE ===\n")

    producto_test = {
        'name': 'Sombrero Arcoiris',
        'sku': 'SOMB-09',
        'velocity': 3.2
    }

    spike_msg = generar_alerta_spike(producto_test, 0.75)
    print(spike_msg)
