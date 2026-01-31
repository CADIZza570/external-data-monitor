#!/usr/bin/env python3
"""
🦈 MARKET PREDATOR ENGINE - Instinto de Mercado Depredador

Estrategias comerciales dinámicas:
1. Price Surge Logic: Aumenta precios cuando contexto favorece (temperatura extrema)
2. Parasite Bundle Logic: Productos estrella absorben dead stock

Autor: Claude Code
Fecha: 2026-01-31
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from external_signals_engine import ExternalSignalsEngine

logger = logging.getLogger(__name__)

DB_FILE = os.getenv("DATA_DIR", ".") + "/webhooks.db"


# ============================================================================
# 💹 PRICE SURGE LOGIC
# ============================================================================

class PriceSurgeEngine:
    """
    Motor de precios dinámicos basado en contexto externo.

    Regla: Si temperatura < -10°C, aumentar margen 10-15% en productos invierno
    durante 48h máximo.
    """

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path
        self.signals = ExternalSignalsEngine()

    def analyze_surge_opportunities(self, shop='columbus-shop'):
        """
        Identifica productos que deberían tener price surge activo.

        Returns:
            [
                {
                    'sku': str,
                    'name': str,
                    'current_price': float,
                    'suggested_surge_price': float,
                    'surge_percentage': float,
                    'reason': str,
                    'projected_net_increase': float,
                    'expires_in_hours': int
                }
            ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Obtener clima actual
        weather = self.signals.get_weather_data(use_mock=False)
        temp_celsius = weather.get('temp_celsius', 0)

        opportunities = []

        # Si temperatura < -10°C, activar surge
        if temp_celsius < -10:
            # Productos candidatos: alta velocity + categoría A + keywords invierno
            cursor.execute("""
                SELECT
                    sku, name, price, cost_price, velocity_daily, category
                FROM products
                WHERE shop = ?
                  AND velocity_daily > 2.0
                  AND category = 'A'
                  AND (
                      LOWER(name) LIKE '%chaqueta%' OR
                      LOWER(name) LIKE '%jacket%' OR
                      LOWER(name) LIKE '%boots%' OR
                      LOWER(name) LIKE '%guantes%' OR
                      LOWER(name) LIKE '%gloves%'
                  )
                ORDER BY velocity_daily DESC
            """, (shop,))

            products = cursor.fetchall()

            for sku, name, current_price, cost_price, velocity, category in products:
                # Calcular surge óptimo
                current_margin = current_price - cost_price
                current_margin_pct = (current_margin / current_price) * 100

                # Surge: 10-15% según intensidad de frío
                surge_pct = 10.0 if temp_celsius > -15 else 12.0 if temp_celsius > -20 else 15.0

                surge_price = current_price * (1 + surge_pct / 100)
                new_margin = surge_price - cost_price

                # Projected net increase
                # Asumimos caída demanda -5% por precio alto, pero +surge_pct% ganancia
                projected_sales_48h = velocity * 2 * 0.95  # 2 días, -5% demanda
                current_net_48h = current_margin * (velocity * 2)
                surge_net_48h = new_margin * projected_sales_48h

                net_increase = surge_net_48h - current_net_48h
                net_increase_pct = (net_increase / current_net_48h) * 100 if current_net_48h > 0 else 0

                opportunities.append({
                    'sku': sku,
                    'name': name,
                    'current_price': current_price,
                    'suggested_surge_price': round(surge_price, 2),
                    'surge_percentage': surge_pct,
                    'reason': f"Temperatura {temp_celsius:.1f}°C (frío extremo) → alta demanda",
                    'projected_net_increase': round(net_increase, 2),
                    'projected_net_increase_pct': round(net_increase_pct, 1),
                    'expires_in_hours': 48
                })

        conn.close()

        return opportunities

    def activate_price_surge(self, sku, surge_price, duration_hours=48):
        """
        Activa price surge para un SKU.

        Crea registro temporal en tabla price_surge_active.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Crear tabla si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_surge_active (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                original_price REAL NOT NULL,
                surge_price REAL NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                reason TEXT,
                status TEXT DEFAULT 'active'
            )
        """)

        # Obtener precio original
        cursor.execute("SELECT price FROM products WHERE sku = ?", (sku,))
        result = cursor.fetchone()
        if not result:
            conn.close()
            raise ValueError(f"SKU {sku} no encontrado")

        original_price = result[0]
        expires_at = datetime.now() + timedelta(hours=duration_hours)

        # Insertar surge
        cursor.execute("""
            INSERT INTO price_surge_active
            (sku, original_price, surge_price, expires_at, reason)
            VALUES (?, ?, ?, ?, ?)
        """, (sku, original_price, surge_price, expires_at.isoformat(), "Temperature surge"))

        # Actualizar precio en products
        cursor.execute("""
            UPDATE products
            SET price = ?
            WHERE sku = ?
        """, (surge_price, sku))

        conn.commit()
        conn.close()

        logger.info(f"Price surge activated: {sku} ${original_price} → ${surge_price} (expires in {duration_hours}h)")

        return {
            'success': True,
            'sku': sku,
            'original_price': original_price,
            'surge_price': surge_price,
            'expires_at': expires_at.isoformat()
        }

    def deactivate_expired_surges(self):
        """
        Desactiva surges expirados (restaura precios originales).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Verificar si tabla existe
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='price_surge_active'
        """)

        if not cursor.fetchone():
            conn.close()
            return 0

        # Obtener surges expirados
        cursor.execute("""
            SELECT sku, original_price
            FROM price_surge_active
            WHERE status = 'active'
              AND expires_at <= ?
        """, (datetime.now().isoformat(),))

        expired = cursor.fetchall()

        for sku, original_price in expired:
            # Restaurar precio
            cursor.execute("""
                UPDATE products
                SET price = ?
                WHERE sku = ?
            """, (original_price, sku))

            # Marcar surge como expirado
            cursor.execute("""
                UPDATE price_surge_active
                SET status = 'expired'
                WHERE sku = ? AND status = 'active'
            """, (sku,))

            logger.info(f"Price surge expired: {sku} restored to ${original_price}")

        conn.commit()
        conn.close()

        return len(expired)


# ============================================================================
# 📦 PARASITE BUNDLE LOGIC
# ============================================================================

class ParasiteBundleEngine:
    """
    Motor de bundles parásitos: Producto estrella absorbe dead stock.

    Regla: Si producto tiene velocity > 80th percentile y otro es dead stock,
    genera bundle "Compra estrella + llévate dead stock 60% off".
    """

    def __init__(self, db_path=DB_FILE):
        self.db_path = db_path

    def analyze_bundle_opportunities(self, shop='columbus-shop'):
        """
        Identifica bundles parásitos viables.

        Returns:
            [
                {
                    'star_sku': str,
                    'star_name': str,
                    'dead_sku': str,
                    'dead_name': str,
                    'bundle_price': float,
                    'dead_stock_value': float,
                    'projected_margin': float,
                    'reason': str
                }
            ]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Identificar estrellas (velocity > p80)
        cursor.execute("""
            SELECT
                sku, name, price, cost_price, velocity_daily, stock
            FROM products
            WHERE shop = ?
              AND velocity_daily > 0
            ORDER BY velocity_daily DESC
        """, (shop,))

        all_products = cursor.fetchall()
        if not all_products:
            conn.close()
            return []

        velocities = [p[4] for p in all_products]
        p80_velocity = sorted(velocities)[int(len(velocities) * 0.8)] if len(velocities) > 5 else 0

        stars = [p for p in all_products if p[4] >= p80_velocity]

        # 2. Identificar dead stock (velocity < 0.5)
        dead_products = [p for p in all_products if p[4] < 0.5]

        if not stars or not dead_products:
            conn.close()
            return []

        # 3. Generar bundles
        opportunities = []

        for star_sku, star_name, star_price, star_cost, star_vel, star_stock in stars[:3]:  # Top 3 estrellas
            for dead_sku, dead_name, dead_price, dead_cost, dead_vel, dead_stock_qty in dead_products:
                # Bundle: Estrella a precio full + Dead stock a 60% off
                dead_discounted = dead_price * 0.4  # 60% off
                bundle_price = star_price + dead_discounted

                # Margen bundle
                bundle_cost = star_cost + dead_cost
                bundle_margin = bundle_price - bundle_cost

                # Margen si solo vendiéramos estrella
                star_only_margin = star_price - star_cost

                # El bundle DEBE generar más margen que vender solo estrella
                # (absorbemos pérdida de dead stock con margen extra de estrella)
                if bundle_margin > star_only_margin * 0.9:  # Al menos 90% del margen estrella
                    dead_stock_value = dead_stock_qty * dead_cost

                    opportunities.append({
                        'star_sku': star_sku,
                        'star_name': star_name,
                        'dead_sku': dead_sku,
                        'dead_name': dead_name,
                        'bundle_price': round(bundle_price, 2),
                        'dead_stock_value': round(dead_stock_value, 2),
                        'projected_margin': round(bundle_margin, 2),
                        'star_velocity': star_vel,
                        'dead_stock_units': dead_stock_qty,
                        'reason': f"Estrella ({star_vel:.1f}/día) absorbe dead stock ({dead_stock_qty} units)"
                    })

        conn.close()

        # Ordenar por projected_margin descendente
        opportunities.sort(key=lambda x: x['projected_margin'], reverse=True)

        return opportunities[:5]  # Top 5 bundles

    def activate_bundle(self, star_sku, dead_sku, bundle_price, duration_days=7):
        """
        Activa bundle parásito.

        Crea registro en tabla parasite_bundles_active.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Crear tabla si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parasite_bundles_active (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                star_sku TEXT NOT NULL,
                dead_sku TEXT NOT NULL,
                bundle_price REAL NOT NULL,
                activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                sales_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            )
        """)

        expires_at = datetime.now() + timedelta(days=duration_days)

        # Insertar bundle
        cursor.execute("""
            INSERT INTO parasite_bundles_active
            (star_sku, dead_sku, bundle_price, expires_at)
            VALUES (?, ?, ?, ?)
        """, (star_sku, dead_sku, bundle_price, expires_at.isoformat()))

        conn.commit()
        conn.close()

        logger.info(f"Parasite bundle activated: {star_sku} + {dead_sku} @ ${bundle_price} (expires in {duration_days}d)")

        return {
            'success': True,
            'star_sku': star_sku,
            'dead_sku': dead_sku,
            'bundle_price': bundle_price,
            'expires_at': expires_at.isoformat()
        }


# ============================================================================
# 🦈 FUNCIÓN HELPER: Generar sugerencias comerciales para Sticker
# ============================================================================

def get_predator_suggestions(shop='columbus-shop'):
    """
    Genera sugerencias comerciales depredadoras para incluir en Sticker.

    Returns:
        {
            'price_surges': [...],
            'bundles': [...],
            'has_opportunities': bool
        }
    """
    surge_engine = PriceSurgeEngine()
    bundle_engine = ParasiteBundleEngine()

    # Desactivar surges expirados primero
    surge_engine.deactivate_expired_surges()

    # Obtener oportunidades
    price_surges = surge_engine.analyze_surge_opportunities(shop)
    bundles = bundle_engine.analyze_bundle_opportunities(shop)

    return {
        'price_surges': price_surges[:3],  # Top 3
        'bundles': bundles[:3],  # Top 3
        'has_opportunities': len(price_surges) > 0 or len(bundles) > 0
    }
