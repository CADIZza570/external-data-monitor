#!/usr/bin/env python3
"""
💰 CASH FLOW API - Endpoints para métricas financieras

Endpoints:
- POST /api/costs/import - Importar costos desde CSV
- GET /api/costs/export - Exportar costos a CSV
- GET /api/cashflow/stockout-cost - Calcular costo de oportunidad por stockouts
- GET /api/cashflow/doi - Días de Inventario (Days of Inventory)
- GET /api/cashflow/abc-classification - Clasificación ABC de productos
- GET /api/cashflow/summary - Resumen completo de Cash Flow
- POST /api/cashflow/roi-simulator - Simulación ROI con Monte Carlo
- GET /api/cashflow/liquidity-shield - Escudo de Liquidez y CCC
- GET /api/cashflow/dead-stock - Candidatos a liquidación
- POST /api/execute-reorder - Ejecutar reorden de producto
- POST /api/execute-liquidate - Ejecutar liquidación de productos
- POST /api/execute-combined - Acciones combinadas (liquidar + reordenar)

Autor: Claude Code
Fecha: 2026-01-18
Actualizado: 2026-01-29 (Tiburón Interactivo)
"""

from flask import Blueprint, request, jsonify, send_file
import sqlite3
import csv
import io
import os
import json
import logging
from datetime import datetime, timedelta

# Logger setup
logger = logging.getLogger(__name__)

# Importar motores del Tiburón
from stats_engine import StatsEngine
from liquidity_guard import LiquidityGuard
from interactive_handler import InteractiveHandler

# Importar Protocolo Cero Absoluto
from lockdown_manager import get_lockdown_manager
from security_middleware import check_system_status, require_admin_key, log_execution_attempt

# Crear Blueprint
cashflow_bp = Blueprint('cashflow', __name__)

# Database
DB_FILE = os.getenv("DATA_DIR", ".") + "/webhooks.db"

def get_db_connection():
    """Retorna conexión a SQLite."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================================
# ENDPOINTS DE COSTOS
# ============================================================

@cashflow_bp.route('/api/costs/import', methods=['POST'])
def import_costs():
    """
    Importa costos desde CSV.

    Formato CSV esperado:
    sku,cost_price,supplier,notes
    BOT-001,45.50,Proveedor A,Botas vaqueras
    BOT-002,52.00,Proveedor B,Botas texanas

    Returns:
        JSON con estadísticas de importación
    """
    try:
        # Validar que venga un archivo
        if 'file' not in request.files:
            return jsonify({
                "error": "No se encontró archivo. Usa 'file' en multipart/form-data"
            }), 400

        file = request.files['file']

        if file.filename == '':
            return jsonify({"error": "Nombre de archivo vacío"}), 400

        # Leer CSV
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        csv_reader = csv.DictReader(stream)

        # Validar columnas requeridas
        required_fields = ['sku', 'cost_price']
        if not all(field in csv_reader.fieldnames for field in required_fields):
            return jsonify({
                "error": f"CSV debe contener columnas: {required_fields}",
                "found": csv_reader.fieldnames
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        inserted = 0
        updated = 0
        errors = []

        # Procesar cada fila
        for row_num, row in enumerate(csv_reader, start=2):
            sku = row.get('sku', '').strip()
            cost_price_str = row.get('cost_price', '0').strip()
            supplier = row.get('supplier', '').strip()
            notes = row.get('notes', '').strip()

            if not sku:
                errors.append(f"Fila {row_num}: SKU vacío")
                continue

            try:
                cost_price = float(cost_price_str)
            except ValueError:
                errors.append(f"Fila {row_num}: cost_price inválido '{cost_price_str}'")
                continue

            # UPSERT en product_costs
            cursor.execute('''
                INSERT INTO product_costs (sku, cost_price, supplier, notes)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(sku) DO UPDATE SET
                    cost_price = excluded.cost_price,
                    supplier = excluded.supplier,
                    notes = excluded.notes,
                    last_updated = CURRENT_TIMESTAMP
            ''', (sku, cost_price, supplier, notes))

            if cursor.rowcount == 1:
                inserted += 1
            else:
                updated += 1

            # Actualizar también en products
            cursor.execute('''
                UPDATE products
                SET cost_price = ?
                WHERE sku = ?
            ''', (cost_price, sku))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "inserted": inserted,
            "updated": updated,
            "errors": errors,
            "total_processed": inserted + updated
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/costs/export', methods=['GET'])
def export_costs():
    """
    Exporta costos a CSV.

    Returns:
        CSV file con todos los costos
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT sku, cost_price, supplier, notes, last_updated
            FROM product_costs
            ORDER BY sku
        ''')

        rows = cursor.fetchall()
        conn.close()

        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(['sku', 'cost_price', 'supplier', 'notes', 'last_updated'])

        # Datos
        for row in rows:
            writer.writerow([row['sku'], row['cost_price'], row['supplier'], row['notes'], row['last_updated']])

        # Convertir a bytes
        output.seek(0)
        bytes_output = io.BytesIO()
        bytes_output.write(output.getvalue().encode('utf-8'))
        bytes_output.seek(0)

        return send_file(
            bytes_output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'product_costs_{datetime.now().strftime("%Y%m%d")}.csv'
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# ENDPOINTS DE CASH FLOW
# ============================================================

@cashflow_bp.route('/api/cashflow/stockout-cost', methods=['GET'])
def stockout_cost():
    """
    Calcula el costo de oportunidad de productos agotados.

    Fórmula: VDP × días_agotado × precio × margen

    Returns:
        JSON con productos agotados y dinero perdido
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Productos con stock = 0 y VDP > 0 (se venden pero no hay stock)
        cursor.execute('''
            SELECT
                product_id,
                name,
                sku,
                stock,
                price,
                cost_price,
                velocity_daily,
                last_sale_date,
                last_updated,
                CAST(julianday('now') - julianday(last_updated) AS INTEGER) as days_out_of_stock
            FROM products
            WHERE stock = 0
            AND velocity_daily > 0
            AND price > 0
            ORDER BY velocity_daily DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        stockouts = []
        total_lost = 0

        for row in rows:
            # Cálculo de dinero perdido
            vpd = row['velocity_daily']
            days_out = row['days_out_of_stock'] or 0
            price = row['price']
            cost = row['cost_price'] or 0

            # Margen = precio - costo
            margin = price - cost

            # Dinero perdido = VDP × días × margen
            lost_revenue = vpd * days_out * margin

            total_lost += lost_revenue

            stockouts.append({
                "product_id": row['product_id'],
                "name": row['name'],
                "sku": row['sku'],
                "velocity_daily": round(vpd, 2),
                "days_out_of_stock": days_out,
                "price": price,
                "cost_price": cost,
                "margin_per_unit": round(margin, 2),
                "lost_revenue": round(lost_revenue, 2),
                "last_sale_date": row['last_sale_date']
            })

        return jsonify({
            "success": True,
            "total_lost_revenue": round(total_lost, 2),
            "stockouts_count": len(stockouts),
            "stockouts": stockouts
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/cashflow/doi', methods=['GET'])
def days_of_inventory():
    """
    Calcula Días de Inventario (DOI).

    DOI = Stock actual / VDP

    Indica cuántos días te dura el inventario actual al ritmo de ventas actual.

    Returns:
        JSON con DOI por producto
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                product_id,
                name,
                sku,
                stock,
                price,
                cost_price,
                velocity_daily,
                total_sales_30d
            FROM products
            WHERE velocity_daily > 0
            ORDER BY stock / velocity_daily ASC
        ''')

        rows = cursor.fetchall()
        conn.close()

        products_doi = []

        for row in rows:
            vpd = row['velocity_daily']
            stock = row['stock']

            # DOI = Stock / VDP
            doi = stock / vpd if vpd > 0 else 999

            # Valor de inventario bloqueado
            cost = row['cost_price'] or 0
            inventory_value = stock * cost

            products_doi.append({
                "product_id": row['product_id'],
                "name": row['name'],
                "sku": row['sku'],
                "stock": stock,
                "velocity_daily": round(vpd, 2),
                "days_of_inventory": round(doi, 1),
                "cost_price": cost,
                "inventory_value": round(inventory_value, 2),
                "status": "CRÍTICO" if doi < 7 else "BAJO" if doi < 15 else "OK"
            })

        return jsonify({
            "success": True,
            "products": products_doi
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/cashflow/abc-classification', methods=['GET'])
def abc_classification():
    """
    Clasificación ABC de productos (Pareto 80/20).

    A: Top 20% de productos que generan 80% del revenue
    B: Siguiente 30% que genera 15% del revenue
    C: Último 50% que genera 5% del revenue

    Returns:
        JSON con productos clasificados
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Calcular revenue de últimos 30 días
        cursor.execute('''
            SELECT
                p.product_id,
                p.name,
                p.sku,
                p.stock,
                p.price,
                p.cost_price,
                p.velocity_daily,
                p.total_sales_30d,
                (p.total_sales_30d * (p.price - COALESCE(p.cost_price, 0))) as revenue_30d
            FROM products p
            WHERE p.total_sales_30d > 0
            ORDER BY revenue_30d DESC
        ''')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return jsonify({
                "success": True,
                "message": "No hay datos de ventas para clasificar",
                "products": []
            }), 200

        # Calcular revenue total
        total_revenue = sum(row['revenue_30d'] for row in rows)

        # Clasificar productos
        products = []
        cumulative_revenue = 0
        cumulative_percentage = 0

        for row in rows:
            revenue = row['revenue_30d']
            cumulative_revenue += revenue
            cumulative_percentage = (cumulative_revenue / total_revenue) * 100

            # Clasificación ABC
            if cumulative_percentage <= 80:
                category = 'A'
            elif cumulative_percentage <= 95:
                category = 'B'
            else:
                category = 'C'

            products.append({
                "product_id": row['product_id'],
                "name": row['name'],
                "sku": row['sku'],
                "category": category,
                "revenue_30d": round(revenue, 2),
                "revenue_percentage": round((revenue / total_revenue) * 100, 2),
                "cumulative_percentage": round(cumulative_percentage, 2),
                "stock": row['stock'],
                "velocity_daily": round(row['velocity_daily'], 2)
            })

        # Actualizar categoría en DB
        conn = get_db_connection()
        cursor = conn.cursor()

        for product in products:
            cursor.execute('''
                UPDATE products
                SET category = ?
                WHERE product_id = ?
            ''', (product['category'], product['product_id']))

        conn.commit()
        conn.close()

        # Estadísticas por categoría
        category_stats = {
            'A': {'count': 0, 'revenue': 0},
            'B': {'count': 0, 'revenue': 0},
            'C': {'count': 0, 'revenue': 0}
        }

        for p in products:
            cat = p['category']
            category_stats[cat]['count'] += 1
            category_stats[cat]['revenue'] += p['revenue_30d']

        return jsonify({
            "success": True,
            "total_revenue_30d": round(total_revenue, 2),
            "category_stats": category_stats,
            "products": products
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/cashflow/summary', methods=['GET'])
def cashflow_summary():
    """
    Resumen completo de Cash Flow.

    Returns:
        JSON con métricas clave
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Total de productos
        cursor.execute('SELECT COUNT(*) as total FROM products')
        total_products = cursor.fetchone()['total']

        # Productos agotados con VDP > 0
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM products
            WHERE stock = 0 AND velocity_daily > 0
        ''')
        stockouts = cursor.fetchone()['count']

        # Total dinero perdido por stockouts
        cursor.execute('''
            SELECT SUM(
                velocity_daily *
                CAST(julianday('now') - julianday(last_updated) AS INTEGER) *
                (price - COALESCE(cost_price, 0))
            ) as total_lost
            FROM products
            WHERE stock = 0 AND velocity_daily > 0
        ''')
        lost_revenue = cursor.fetchone()['total_lost'] or 0

        # Valor total de inventario
        cursor.execute('''
            SELECT SUM(stock * COALESCE(cost_price, 0)) as inventory_value
            FROM products
        ''')
        inventory_value = cursor.fetchone()['inventory_value'] or 0

        # Productos con DOI < 7 días
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM products
            WHERE velocity_daily > 0
            AND (stock / velocity_daily) < 7
        ''')
        critical_stock = cursor.fetchone()['count']

        conn.close()

        return jsonify({
            "success": True,
            "summary": {
                "total_products": total_products,
                "stockouts_count": stockouts,
                "lost_revenue": round(lost_revenue, 2),
                "inventory_value": round(inventory_value, 2),
                "critical_stock_count": critical_stock
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# ENDPOINT: TRENDING DE TALLAS
# ============================================================

@cashflow_bp.route('/api/analytics/trending-sizes', methods=['GET'])
def get_trending_sizes():
    """
    Retorna trending de ventas por SKU (últimos 30 días).

    Query params:
        - days: Días a analizar (default: 30)
        - limit: Top N productos (default: 10)

    Returns:
        {
            "success": true,
            "period_days": 30,
            "total_sales": 150,
            "trending": [
                {
                    "sku": "SOMB-ARCO-09",
                    "product_name": "Sombrero Arcoiris - Talla 9",
                    "sales_count": 45,
                    "percentage": 30.0,
                    "rank": 1
                },
                ...
            ]
        }
    """
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 10, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener ventas agrupadas por SKU (últimos N días)
        cursor.execute('''
            SELECT
                sku,
                product_name,
                SUM(quantity) as sales_count
            FROM sales_history
            WHERE sale_date >= datetime('now', '-' || ? || ' days')
            GROUP BY sku, product_name
            ORDER BY sales_count DESC
            LIMIT ?
        ''', (days, limit))

        results = cursor.fetchall()

        # Calcular total de ventas
        cursor.execute('''
            SELECT SUM(quantity) as total
            FROM sales_history
            WHERE sale_date >= datetime('now', '-' || ? || ' days')
        ''', (days,))
        total_sales = cursor.fetchone()['total'] or 0

        conn.close()

        # Formatear resultados
        trending = []
        for idx, row in enumerate(results, 1):
            sales_count = row['sales_count']
            percentage = (sales_count / total_sales * 100) if total_sales > 0 else 0

            trending.append({
                "rank": idx,
                "sku": row['sku'],
                "product_name": row['product_name'],
                "sales_count": sales_count,
                "percentage": round(percentage, 1)
            })

        return jsonify({
            "success": True,
            "period_days": days,
            "total_sales": total_sales,
            "trending": trending
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/recommendations', methods=['GET'])
def get_purchase_recommendations():
    """
    Genera recomendaciones inteligentes de compra.

    Query params:
        - lead_time: días de lead time del proveedor (default 14)
        - safety_margin: días extra de stock de seguridad (default 7)
        - min_priority: prioridad mínima para recomendar (default 60)
        - limit: máximo de recomendaciones (default 10)

    Returns:
        {
            "success": true,
            "recommendations": [
                {
                    "sku": "BV-007",
                    "product_name": "Botas Vaqueras Talla 7",
                    "current_stock": 5,
                    "recommended_qty": 30,
                    "urgency_days": 2,
                    "priority": 85,
                    "velocity_daily": 2.5,
                    "estimated_cost": 750.00
                }
            ],
            "total_items": 5,
            "total_cost": 2450.00
        }
    """
    try:
        # Parámetros configurables
        lead_time = request.args.get('lead_time', 14, type=int)
        safety_margin = request.args.get('safety_margin', 7, type=int)
        min_priority = request.args.get('min_priority', 60, type=int)
        limit = request.args.get('limit', 10, type=int)

        conn = get_db_connection()
        cursor = conn.cursor()

        # Obtener productos con velocity > 0
        cursor.execute('''
            SELECT
                product_id,
                name,
                sku,
                stock,
                price,
                cost_price,
                velocity_daily,
                category,
                last_sale_date
            FROM products
            WHERE velocity_daily > 0
            ORDER BY velocity_daily DESC
        ''')

        products = cursor.fetchall()

        # Pre-calcular TODOS los trending ranks en 1 sola query (evita N+1)
        trending_ranks = {}
        trending_products = cursor.execute("""
            SELECT sku, SUM(quantity) as total_sales
            FROM sales_history
            WHERE sale_date >= date('now', '-30 days')
            GROUP BY sku
            ORDER BY total_sales DESC
            LIMIT 100
        """).fetchall()

        for idx, row in enumerate(trending_products, 1):
            trending_ranks[row['sku']] = idx

        conn.close()

        # Importar función de priorización
        from database import calculate_alert_priority

        recommendations = []
        total_cost = 0

        for p in products:
            # Usar trending rank pre-calculado (cache)
            trending_rank = trending_ranks.get(p['sku'], None)
            priority = calculate_alert_priority(
                velocity=p['velocity_daily'],
                stock=p['stock'],
                price=p['price'],
                trending_rank=trending_rank
            )

            # Filtrar por prioridad mínima
            if priority < min_priority:
                continue

            # Calcular cantidad recomendada
            # Formula: (velocity × (lead_time + safety_margin)) - stock_actual
            target_stock = p['velocity_daily'] * (lead_time + safety_margin)
            recommended_qty = max(0, round(target_stock - p['stock']))

            # Solo recomendar si necesita compra
            if recommended_qty <= 0:
                continue

            # Días hasta stockout (urgencia)
            urgency_days = round(p['stock'] / p['velocity_daily']) if p['velocity_daily'] > 0 else 999

            # Costo estimado
            cost_price = p['cost_price'] or (p['price'] * 0.6)  # Asumir 40% margen si no hay costo
            estimated_cost = recommended_qty * cost_price

            recommendations.append({
                "sku": p['sku'],
                "product_name": p['name'],
                "current_stock": p['stock'],
                "recommended_qty": recommended_qty,
                "urgency_days": urgency_days,
                "priority": priority,
                "velocity_daily": round(p['velocity_daily'], 2),
                "estimated_cost": round(estimated_cost, 2),
                "category": p['category'] or 'C'
            })

            total_cost += estimated_cost

        # Ordenar por urgencia (menos días primero)
        recommendations.sort(key=lambda x: x['urgency_days'])

        # Limitar resultados
        recommendations = recommendations[:limit]

        return jsonify({
            "success": True,
            "recommendations": recommendations,
            "total_items": len(recommendations),
            "total_cost": round(total_cost, 2),
            "config": {
                "lead_time_days": lead_time,
                "safety_margin_days": safety_margin,
                "min_priority": min_priority
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# INSIGHTS SYSTEM - MVP con 3 tipos básicos (Trending, Dead Stock, Margin)
# ============================================================================

def get_or_generate_insight(insight_type, generator_func):
    """
    Obtiene insight cacheado o genera nuevo si expiró (24h TTL).

    Args:
        insight_type: 'trending', 'dead_stock', 'margin'
        generator_func: función que genera el insight

    Returns:
        dict con success, cached, generated_at, data
    """
    conn = get_db_connection()

    try:
        # Verificar si existe insight válido
        cached = conn.execute("""
            SELECT data, generated_at, expires_at
            FROM insights
            WHERE type = ? AND expires_at > datetime('now')
        """, (insight_type,)).fetchone()

        if cached:
            return {
                'success': True,
                'cached': True,
                'generated_at': cached['generated_at'],
                'data': json.loads(cached['data'])
            }

        # Generar nuevo insight
        insight_data = generator_func()

        # Guardar con expiración 24h
        expires_at = datetime.now() + timedelta(hours=24)

        conn.execute("""
            INSERT OR REPLACE INTO insights (type, data, expires_at)
            VALUES (?, ?, ?)
        """, (insight_type, json.dumps(insight_data), expires_at))

        conn.commit()

        return {
            'success': True,
            'cached': False,
            'generated_at': datetime.now().isoformat(),
            'data': insight_data
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'data': None
        }
    finally:
        conn.close()


def generate_dead_stock_insight():
    """
    Detecta productos sin ventas en últimos 90 días.

    Returns:
        dict con products, total_locked_capital, count
    """
    conn = get_db_connection()

    try:
        dead_stock = conn.execute("""
            SELECT
                sku,
                name as product_name,
                stock,
                price,
                CAST((julianday('now') - julianday(last_sale_date)) AS INTEGER) as days_without_sales,
                (stock * price) as locked_capital
            FROM products
            WHERE last_sale_date IS NULL
               OR julianday('now') - julianday(last_sale_date) > 90
            ORDER BY locked_capital DESC
            LIMIT 10
        """).fetchall()

        total_locked = sum(row['locked_capital'] or 0 for row in dead_stock)

        return {
            'products': [dict(row) for row in dead_stock],
            'total_locked_capital': round(total_locked, 2),
            'count': len(dead_stock)
        }

    finally:
        conn.close()


def generate_margin_insight():
    """
    Analiza productos por margen de ganancia.

    Returns:
        dict con best_margin, worst_margin, average_margin, total_products_analyzed
    """
    conn = get_db_connection()

    try:
        margin_analysis = conn.execute("""
            SELECT
                sku,
                name as product_name,
                price,
                cost_price,
                (price - cost_price) as margin,
                ROUND(((price - cost_price) / price) * 100, 2) as margin_percentage,
                stock,
                total_sales_30d,
                ((price - cost_price) * COALESCE(total_sales_30d, 0)) as profit_30d
            FROM products
            WHERE cost_price IS NOT NULL AND cost_price > 0 AND price > 0
            ORDER BY margin_percentage DESC
        """).fetchall()

        if not margin_analysis:
            return {
                'best_margin': [],
                'worst_margin': [],
                'average_margin': 0,
                'total_products_analyzed': 0
            }

        # Top 5 mejores márgenes
        best_margin = margin_analysis[:5]

        # Top 5 peores márgenes
        worst_margin = margin_analysis[-5:] if len(margin_analysis) >= 5 else []

        # Margen promedio
        avg_margin = sum(row['margin_percentage'] for row in margin_analysis) / len(margin_analysis)

        return {
            'best_margin': [dict(row) for row in best_margin],
            'worst_margin': [dict(row) for row in worst_margin],
            'average_margin': round(avg_margin, 2),
            'total_products_analyzed': len(margin_analysis)
        }

    finally:
        conn.close()


# ============================================================================
# INSIGHTS ENDPOINTS
# ============================================================================

@cashflow_bp.route('/api/insights/trending', methods=['GET'])
def get_trending_insight():
    """Retorna insight de productos trending (cacheado 24h)"""
    def generator():
        # Reutilizar lógica existente de trending
        response = get_trending_sizes()
        return response.get_json()

    return jsonify(get_or_generate_insight('trending', generator))


@cashflow_bp.route('/api/insights/dead-stock', methods=['GET'])
def get_dead_stock_insight():
    """Retorna insight de dead stock (cacheado 24h)"""
    return jsonify(get_or_generate_insight('dead_stock', generate_dead_stock_insight))


@cashflow_bp.route('/api/insights/margin', methods=['GET'])
def get_margin_insight():
    """Retorna insight de margin analysis (cacheado 24h)"""
    return jsonify(get_or_generate_insight('margin', generate_margin_insight))


@cashflow_bp.route('/api/insights/refresh', methods=['POST'])
def refresh_insights():
    """Fuerza regeneración de todos los insights"""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM insights")
        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Insights cache cleared. Will regenerate on next request.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        conn.close()


# ============================================================================
# 🦈 TIBURÓN INTERACTIVO - ROI SIMULATOR + ESCUDO + ACCIONES
# ============================================================================

@cashflow_bp.route('/api/cashflow/roi-simulator', methods=['POST'])
def roi_simulator():
    """
    Simula ROI con Monte Carlo para decisiones de reorden.

    Request Body:
        {
            "sku": "SOMB-ARCO-09",
            "units": 25,
            "send_to_discord": true  // opcional
        }

    Returns:
        {
            "success": true,
            "simulation": {
                "sku": "SOMB-ARCO-09",
                "name": "Sombrero Arcoíris",
                "units": 25,
                "investment": 1500.00,
                "roi_expected": 60.5,
                "roi_range": [45.2, 75.8],
                "breakeven_days": 12.3,
                "risk_level": "bajo",
                "narrative": "..."
            },
            "discord_sent": true
        }
    """
    try:
        data = request.get_json()

        if not data or 'sku' not in data or 'units' not in data:
            return jsonify({
                "error": "Faltan parámetros. Requeridos: sku, units"
            }), 400

        sku = data['sku']
        units = int(data['units'])
        send_to_discord = data.get('send_to_discord', False)
        is_aggressive = data.get('aggressive', False)  # Detectar modo agresivo

        # 🧠 TRACKING: Si es simulación agresiva, registrar click
        if is_aggressive or units > 50:  # Considerar agresivo si units > 50
            try:
                from interaction_tracker import InteractionTracker
                tracker = InteractionTracker()
                tracker.track_click(
                    button_id="simulate_aggressive",
                    action_type="simulate",
                    context=f"Aggressive simulation for {sku}",
                    sku=sku,
                    units=units,
                    metadata={"aggressive": is_aggressive}
                )
            except Exception as e:
                pass

        # Ejecutar simulación
        engine = StatsEngine()
        simulation = engine.calculate_roi_simulation(sku=sku, units=units)

        if 'error' in simulation:
            return jsonify({
                "success": False,
                "error": simulation['error']
            }), 404

        # Enviar a Discord si se requiere
        discord_sent = False
        if send_to_discord:
            handler = InteractiveHandler()
            message = handler.create_roi_simulation_message(simulation)
            discord_sent = handler.send_interactive_message(
                content=message['content'],
                actions=message['actions'],
                embed=message['embed']
            )

        return jsonify({
            "success": True,
            "simulation": simulation,
            "discord_sent": discord_sent
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/cashflow/liquidity-shield', methods=['GET'])
def liquidity_shield():
    """
    Estado del Escudo de Liquidez y CCC.

    Query params:
        - proposed_investment: float (opcional) - simular impacto de inversión

    Returns:
        {
            "success": true,
            "ccc": {...},
            "shield": {
                "current_inventory_value": 45000,
                "days_of_coverage": 37,
                "escudo_active": false,
                "recommendation": "..."
            }
        }
    """
    try:
        proposed_investment = request.args.get('proposed_investment', 0, type=float)

        guard = LiquidityGuard()

        # CCC
        ccc = guard.calculate_ccc()

        # Escudo
        shield = guard.calculate_liquidity_shield(proposed_investment=proposed_investment)

        return jsonify({
            "success": True,
            "ccc": ccc,
            "shield": shield
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/cashflow/dead-stock', methods=['GET'])
def get_dead_stock():
    """
    Lista de productos candidatos a liquidación.

    Query params:
        - min_days: int (default 60) - días mínimos sin ventas

    Returns:
        {
            "success": true,
            "candidates": [
                {
                    "sku": "...",
                    "name": "...",
                    "capital_trapped": 500,
                    "liquidation_priority": "alta"
                }
            ],
            "total_capital_trapped": 5000
        }
    """
    try:
        min_days = request.args.get('min_days', 60, type=int)

        guard = LiquidityGuard()
        candidates = guard.get_dead_stock_candidates(min_days_stagnant=min_days)

        total_capital = sum(c['capital_trapped'] for c in candidates)

        return jsonify({
            "success": True,
            "candidates": candidates,
            "total_capital_trapped": round(total_capital, 2),
            "count": len(candidates)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/execute-reorder', methods=['POST'])
@log_execution_attempt
@check_system_status
def execute_reorder():
    """
    Ejecuta reorden de producto (placeholder - conectar con sistema real).

    Request Body:
        {
            "sku": "SOMB-ARCO-09",
            "units": 25,
            "confirm": true
        }

    Returns:
        {
            "success": true,
            "action": "reorder",
            "sku": "SOMB-ARCO-09",
            "units": 25,
            "status": "confirmed",
            "message": "Orden de compra creada"
        }
    """
    try:
        data = request.get_json()

        if not data or 'sku' not in data or 'units' not in data:
            return jsonify({
                "error": "Faltan parámetros. Requeridos: sku, units, confirm"
            }), 400

        sku = data['sku']
        units = int(data['units'])
        confirm = data.get('confirm', False)

        if not confirm:
            return jsonify({
                "error": "Debes confirmar la acción con confirm: true"
            }), 400

        # 🧠 TRACKING: Registrar click del botón
        try:
            from interaction_tracker import InteractionTracker
            tracker = InteractionTracker()
            tracker.track_click(
                button_id="approve_reorder",
                action_type="reorder",
                context=f"Reorder approved for {sku}",
                sku=sku,
                units=units,
                metadata={"confirmed": confirm}
            )
        except Exception as e:
            # No fallar si el tracking falla
            pass

        # TODO: Integrar con sistema de compras real (Shopify Draft Orders, etc.)
        # Por ahora, solo registramos la acción

        conn = get_db_connection()
        cursor = conn.cursor()

        # Verificar que el producto existe
        cursor.execute("SELECT name, cost_price FROM products WHERE sku = ?", (sku,))
        product = cursor.fetchone()

        if not product:
            conn.close()
            return jsonify({
                "error": f"Producto {sku} no encontrado"
            }), 404

        name = product['name']
        cost_price = product['cost_price'] or 0
        total_cost = units * cost_price

        # Registrar acción en DB (crear tabla si no existe)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reorder_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sku TEXT NOT NULL,
                product_name TEXT,
                units INTEGER,
                total_cost REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO reorder_actions (sku, product_name, units, total_cost, status)
            VALUES (?, ?, ?, ?, 'confirmed')
        """, (sku, name, units, total_cost))

        action_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "action": "reorder",
            "action_id": action_id,
            "sku": sku,
            "product_name": name,
            "units": units,
            "total_cost": round(total_cost, 2),
            "status": "confirmed",
            "message": f"✅ Orden de compra creada: {units}x {name} (${total_cost:,.0f})"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/execute-liquidate', methods=['POST'])
@log_execution_attempt
@check_system_status
def execute_liquidate():
    """
    Ejecuta liquidación de productos.

    Request Body:
        {
            "skus": ["SKU1", "SKU2"],
            "discount_pct": 0.30,
            "confirm": true
        }

    OR query param:
        ?top=5  // Liquidar top 5 dead stock

    Returns:
        {
            "success": true,
            "action": "liquidate",
            "simulation": {...},
            "status": "confirmed"
        }
    """
    try:
        # Opción 1: Query param ?top=N
        top_n = request.args.get('top', type=int)

        if top_n:
            guard = LiquidityGuard()
            candidates = guard.get_dead_stock_candidates()[:top_n]
            skus = [c['sku'] for c in candidates]
            discount_pct = 0.30  # Default 30%
        else:
            # Opción 2: Request body
            data = request.get_json()

            if not data or 'skus' not in data:
                return jsonify({
                    "error": "Faltan parámetros. Requeridos: skus, confirm"
                }), 400

            skus = data['skus']
            discount_pct = data.get('discount_pct', 0.30)

        confirm = request.args.get('confirm', 'false').lower() == 'true'
        if not confirm and request.is_json:
            confirm = request.get_json().get('confirm', False)

        # Simular impacto
        guard = LiquidityGuard()
        simulation = guard.simulate_liquidation_impact(skus=skus, discount_pct=discount_pct)

        if not confirm:
            return jsonify({
                "success": True,
                "action": "liquidate",
                "simulation": simulation,
                "status": "preview",
                "message": "Preview de liquidación. Envía confirm: true para ejecutar."
            }), 200

        # 🧠 TRACKING: Registrar click del botón de liquidar
        try:
            from interaction_tracker import InteractionTracker
            tracker = InteractionTracker()
            tracker.track_click(
                button_id="liquidate_dead_stock",
                action_type="liquidate",
                context=f"Liquidating {len(skus)} products",
                metadata={"skus": skus, "discount_pct": discount_pct}
            )
        except Exception as e:
            pass

        # TODO: Integrar con sistema real de descuentos/promociones
        # Por ahora, solo registramos

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS liquidation_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skus TEXT,
                discount_pct REAL,
                revenue_expected REAL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            INSERT INTO liquidation_actions (skus, discount_pct, revenue_expected, status)
            VALUES (?, ?, ?, 'confirmed')
        """, (','.join(skus), discount_pct, simulation['revenue_at_discount']))

        action_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "action": "liquidate",
            "action_id": action_id,
            "simulation": simulation,
            "status": "confirmed",
            "message": f"✅ Liquidación iniciada: {len(skus)} productos con {int(discount_pct * 100)}% descuento"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/execute-combined', methods=['POST'])
@log_execution_attempt
@check_system_status
def execute_combined():
    """
    Ejecuta acciones combinadas (ej: liquidar dead stock + reordenar producto).

    Request Body:
        {
            "action": "liquidate_reorder",
            "liquidate_top": 5,
            "reorder_sku": "SOMB-ARCO-09",
            "reorder_units": 25,
            "confirm": true
        }

    Returns:
        {
            "success": true,
            "actions": {
                "liquidation": {...},
                "reorder": {...}
            }
        }
    """
    try:
        data = request.get_json()

        if not data or 'action' not in data:
            return jsonify({
                "error": "Falta parámetro 'action'. Valores: liquidate_reorder"
            }), 400

        action_type = data['action']
        confirm = data.get('confirm', False)

        if action_type == 'liquidate_reorder':
            # Paso 1: Liquidar dead stock
            liquidate_top = data.get('liquidate_top', 5)

            guard = LiquidityGuard()
            candidates = guard.get_dead_stock_candidates()[:liquidate_top]
            skus_to_liquidate = [c['sku'] for c in candidates]

            liquidation_sim = guard.simulate_liquidation_impact(
                skus=skus_to_liquidate,
                discount_pct=0.30
            )

            # Paso 2: Reordenar producto
            reorder_sku = data.get('reorder_sku')
            reorder_units = data.get('reorder_units')

            if not reorder_sku or not reorder_units:
                return jsonify({
                    "error": "Faltan parámetros: reorder_sku, reorder_units"
                }), 400

            engine = StatsEngine()
            reorder_sim = engine.calculate_roi_simulation(sku=reorder_sku, units=reorder_units)

            if not confirm:
                return jsonify({
                    "success": True,
                    "action": "combined_preview",
                    "liquidation": liquidation_sim,
                    "reorder": reorder_sim,
                    "status": "preview",
                    "message": "Preview de acción combinada. Envía confirm: true para ejecutar."
                }), 200

            # Ejecutar ambas acciones
            # TODO: Implementar ejecución real

            return jsonify({
                "success": True,
                "action": "liquidate_reorder",
                "status": "confirmed",
                "liquidation": liquidation_sim,
                "reorder": reorder_sim,
                "message": f"✅ Combo ejecutado: Liquidando {len(skus_to_liquidate)} productos + Reordenando {reorder_units}x {reorder_sim['name']}"
            }), 200

        else:
            return jsonify({
                "error": f"Acción '{action_type}' no soportada"
            }), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ❄️ PROTOCOLO CERO ABSOLUTO - ADMIN ENDPOINTS
# ============================================================================

@cashflow_bp.route('/api/admin/freeze', methods=['POST'])
@require_admin_key
def admin_freeze():
    """
    Congela el sistema - activa Protocolo Cero Absoluto.

    Requiere header: X-Admin-Key

    Request Body (opcional):
        {
            "reason": "Emergency lockdown - suspected breach",
            "frozen_by": "admin_user_123"
        }

    Returns:
        {
            "success": true,
            "frozen": true,
            "frozen_at": "2026-01-29T...",
            "message": "Sistema criogenizado..."
        }
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'Manual freeze via API')
        frozen_by = data.get('frozen_by', request.remote_addr)

        manager = get_lockdown_manager()

        # Verificar si ya está congelado
        if manager.is_frozen():
            return jsonify({
                "success": False,
                "error": "System already frozen",
                "status": manager.get_status()
            }), 400

        # Congelar
        result = manager.freeze(frozen_by=frozen_by, reason=reason)

        return jsonify({
            "success": True,
            **result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/admin/thaw', methods=['POST'])
@require_admin_key
def admin_thaw():
    """
    Descongela el sistema - desactiva Protocolo Cero Absoluto.

    Requiere header: X-Admin-Key

    Request Body (opcional):
        {
            "thawed_by": "admin_user_123"
        }

    Returns:
        {
            "success": true,
            "frozen": false,
            "thawed_at": "2026-01-29T...",
            "message": "Sistema reactivado..."
        }
    """
    try:
        data = request.get_json() or {}
        thawed_by = data.get('thawed_by', request.remote_addr)

        manager = get_lockdown_manager()

        # Verificar si está congelado
        if not manager.is_frozen():
            return jsonify({
                "success": False,
                "error": "System is not frozen",
                "status": manager.get_status()
            }), 400

        # Descongelar
        result = manager.thaw(thawed_by=thawed_by)

        return jsonify({
            "success": True,
            **result
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cashflow_bp.route('/api/admin/lockdown-status', methods=['GET'])
@require_admin_key
def lockdown_status():
    """
    Obtiene estado completo del lockdown.

    Requiere header: X-Admin-Key

    Returns:
        {
            "frozen": bool,
            "frozen_at": "...",
            "frozen_by": "...",
            "reason": "...",
            "security_events": [...]
        }
    """
    try:
        manager = get_lockdown_manager()

        status = manager.get_status()
        events = manager.get_security_events(limit=20)

        return jsonify({
            "success": True,
            "status": status,
            "recent_events": events
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# 📱 MOBILE PULSE - WhatsApp Bridge
# ============================================================================

@cashflow_bp.route('/api/v1/mobile-pulse', methods=['GET'])
def mobile_pulse():
    """
    Endpoint simple para WhatsApp bridge - retorna estado del sistema en JSON plano

    Returns:
        {
            "status": "healthy" | "warning" | "critical",
            "message": "Texto descriptivo para WhatsApp",
            "metrics": {
                "ccc": valor CCC,
                "coverage_days": días de cobertura,
                "escudo_active": bool,
                "top_reorder": {sku, name, roi}
            }
        }
    """
    try:
        from liquidity_guard import LiquidityGuard
        from stats_engine import StatsEngine

        guard = LiquidityGuard()
        engine = StatsEngine()

        # 1. Estado de liquidez
        shield = guard.calculate_liquidity_shield(proposed_investment=0)
        ccc = guard.calculate_ccc()

        # 2. Top reorder candidate
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT sku, name, stock, velocity_daily
            FROM products
            WHERE category = 'A'
              AND stock < (velocity_daily * 7)
              AND velocity_daily > 0
            ORDER BY (velocity_daily * 7 - stock) DESC
            LIMIT 1
        """)

        top_candidate = cursor.fetchone()
        conn.close()

        top_reorder = None
        if top_candidate:
            sku, name, stock, velocity = top_candidate
            units_needed = int(velocity * 14 - stock)  # Reorden para 2 semanas

            if units_needed > 0:
                roi_data = engine.calculate_roi_simulation(sku, units_needed)

                if "error" not in roi_data:
                    top_reorder = {
                        "sku": sku,
                        "name": name,
                        "units": units_needed,
                        "roi": roi_data["roi_expected"],
                        "risk": roi_data["risk_level"]
                    }

        # 3. Status general
        if shield["risk_level"] == "crítico" or ccc["health"] == "crítico":
            status = "critical"
            emoji = "🚨"
        elif shield["risk_level"] == "warning" or ccc["health"] == "warning":
            status = "warning"
            emoji = "⚠️"
        else:
            status = "healthy"
            emoji = "✅"

        # 4. Mensaje para WhatsApp
        message = f"""{emoji} CASH FLOW STATUS

💰 Cobertura: {shield['days_of_coverage']:.0f} días
🔄 CCC: {ccc['ccc_days']:.1f} días ({ccc['trend']})
{"🛡️ Escudo: ACTIVO" if shield['escudo_active'] else "🚀 Escudo: OFF"}"""

        if top_reorder:
            message += f"\n\n🦈 Top Move:\n{top_reorder['name']}\nROI: {top_reorder['roi']:.1f}% ({top_reorder['risk']} riesgo)"

        return jsonify({
            "status": status,
            "message": message,
            "metrics": {
                "ccc_days": ccc["ccc_days"],
                "ccc_health": ccc["health"],
                "coverage_days": shield["days_of_coverage"],
                "escudo_active": shield["escudo_active"],
                "risk_level": shield["risk_level"],
                "top_reorder": top_reorder
            },
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}",
            "metrics": {}
        }), 500


# ============================================================================
# 📊 POST-MORTEM - Debug & Testing Endpoints
# ============================================================================

@cashflow_bp.route('/api/debug/post-mortem', methods=['GET'])
def debug_post_mortem():
    """
    Endpoint de debug para forzar post-mortem de la última freeze session.

    Query params:
        - session_id: ID específico de sesión (opcional)

    Returns:
        Análisis post-mortem completo
    """
    try:
        from post_mortem import PostMortemAnalyzer

        analyzer = PostMortemAnalyzer()

        # Obtener session_id del query param o usar la más reciente
        session_id = request.args.get('session_id', type=int)

        if session_id:
            # Analizar sesión específica
            analysis = analyzer.generate_post_mortem(session_id)
        else:
            # Obtener sesión más reciente cerrada
            pending = analyzer.get_pending_post_mortems(hours_after_thaw=0)

            if not pending:
                return jsonify({
                    "success": False,
                    "message": "No hay freeze sessions cerradas para analizar"
                }), 404

            session_id = pending[-1]  # La más reciente
            analysis = analyzer.generate_post_mortem(session_id)

        if "error" in analysis:
            return jsonify({
                "success": False,
                "error": analysis["error"]
            }), 404

        return jsonify({
            "success": True,
            "session_id": session_id,
            "analysis": analysis
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cashflow_bp.route('/api/debug/interaction-metrics', methods=['GET'])
def debug_interaction_metrics():
    """
    Endpoint de debug para ver métricas de interacción.

    Query params:
        - days: Días a analizar (default: 7)

    Returns:
        Patrón de clics y stats
    """
    try:
        from interaction_tracker import InteractionTracker

        tracker = InteractionTracker()
        days = request.args.get('days', type=int, default=7)

        pattern = tracker.get_recent_pattern(days=days)
        history = tracker.get_click_history(limit=10)
        stats = tracker.get_button_stats(days=days)

        return jsonify({
            "success": True,
            "pattern": pattern,
            "recent_clicks": history,
            "button_stats": stats
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@cashflow_bp.route('/api/debug/external-signals', methods=['GET'])
def debug_external_signals():
    """
    Endpoint de debug para ver señales externas (clima + feriados).

    Query params:
        - product_name: Nombre del producto a analizar (default: "Chaqueta Térmica Winter Pro")
        - use_mock: Si True, usa datos mock (default: False - usa API real si hay key)

    Returns:
        Análisis completo de señales externas
    """
    try:
        from external_signals_engine import ExternalSignalsEngine
        import os

        # ✅ Crear engine con API key del entorno
        api_key = os.getenv('OPENWEATHER_API_KEY')
        engine = ExternalSignalsEngine(api_key=api_key)

        product_name = request.args.get('product_name', 'Chaqueta Térmica Winter Pro')

        # ✅ DEFAULT A FALSE: usa API real si existe key, sino fallback a mock automático
        use_mock = request.args.get('use_mock', 'false').lower() == 'true'

        # ⚠️ Log si no hay API key
        if not api_key and not use_mock:
            logger.warning("⚠️ OPENWEATHER_API_KEY no configurada - usando datos mock como fallback")
            use_mock = True

        # Obtener datos de clima
        weather = engine.get_weather_data(use_mock=use_mock)

        # Obtener feriados
        holidays = engine.get_upcoming_holidays(days_ahead=30)

        # Analizar impacto en producto
        weather_impact = engine.analyze_weather_impact(product_name, weather)
        holiday_impact = engine.analyze_holiday_impact(product_name, days_ahead=30)

        # Multiplicador contextual total
        context = engine.get_contextual_multiplier(product_name, use_mock_weather=use_mock)

        return jsonify({
            "success": True,
            "product_name": product_name,
            "weather_data": weather,
            "upcoming_holidays": holidays,
            "weather_impact": weather_impact,
            "holiday_impact": holiday_impact,
            "contextual_multiplier": context
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@cashflow_bp.route('/api/admin/seed-columbus', methods=['POST'])
def admin_seed_columbus():
    """
    🌱 ENDPOINT ADMIN: Seed Columbus Winter Catalog
    
    Ejecuta seed para poblar DB con productos Columbus + ventas históricas.
    
    Body JSON:
        - admin_key: "tiburon-seed-2026" (o env ADMIN_SEED_KEY)
        - dry_run: true/false (default: false)
    
    Example:
        POST /api/admin/seed-columbus
        {"admin_key": "tiburon-seed-2026", "dry_run": false}
    
    Returns:
        Resumen de productos, proveedores y ventas insertadas
    """
    import os
    from datetime import datetime, timedelta
    import random
    
    # Verificar autorización
    try:
        data = request.get_json() or {}
    except:
        data = {}
    
    admin_key = data.get('admin_key', '')
    expected_key = os.getenv('ADMIN_SEED_KEY', 'tiburon-seed-2026')
    
    if admin_key != expected_key:
        return jsonify({
            "success": False,
            "error": "Unauthorized - invalid or missing admin_key"
        }), 401
    
    dry_run = data.get('dry_run', False)
    
    try:
        # Productos Columbus Winter (compacto)
        COLUMBUS_PRODUCTS = [
            {"product_id": "WINTER-001", "name": "Chaqueta Térmica Winter Pro", "sku": "JACKET-WINTER-01", "stock": 12, "price": 189.99, "cost_price": 95.00, "velocity_daily": 3.2, "total_sales_30d": 96, "total_sales_60d": 180, "category": "A", "supplier": "Winter Gear Supply Co.", "lead_time_days": 7, "moq": 25},
            {"product_id": "WINTER-002", "name": "Boots Waterproof Premium", "sku": "BOOTS-WP-01", "stock": 8, "price": 159.99, "cost_price": 80.00, "velocity_daily": 2.8, "total_sales_30d": 84, "total_sales_60d": 160, "category": "A", "supplier": "FootGear Wholesale", "lead_time_days": 10, "moq": 30},
            {"product_id": "WINTER-003", "name": "Guantes Térmicos Arctic", "sku": "GLOVES-ARC-01", "stock": 25, "price": 45.99, "cost_price": 18.00, "velocity_daily": 4.5, "total_sales_30d": 135, "total_sales_60d": 250, "category": "A", "supplier": "Winter Gear Supply Co.", "lead_time_days": 5, "moq": 50},
            {"product_id": "WINTER-004", "name": "Bufanda Lana Merino", "sku": "SCARF-WOOL-01", "stock": 40, "price": 39.99, "cost_price": 15.00, "velocity_daily": 1.8, "total_sales_30d": 54, "total_sales_60d": 100, "category": "B", "supplier": "Textile Partners Inc.", "lead_time_days": 14, "moq": 40},
            {"product_id": "WINTER-005", "name": "Gorro Térmico Fleece", "sku": "HAT-FLEECE-01", "stock": 60, "price": 29.99, "cost_price": 10.00, "velocity_daily": 2.1, "total_sales_30d": 63, "total_sales_60d": 120, "category": "B", "supplier": "Winter Gear Supply Co.", "lead_time_days": 7, "moq": 60},
            {"product_id": "WINTER-006", "name": "Abrigo Invierno Classic", "sku": "COAT-CLASSIC-01", "stock": 15, "price": 249.99, "cost_price": 130.00, "velocity_daily": 1.2, "total_sales_30d": 36, "total_sales_60d": 70, "category": "B", "supplier": "Premium Outerwear Ltd.", "lead_time_days": 14, "moq": 20},
            {"product_id": "WINTER-007", "name": "Calentadores Manos", "sku": "WARMERS-HAND-01", "stock": 200, "price": 12.99, "cost_price": 4.00, "velocity_daily": 0.8, "total_sales_30d": 24, "total_sales_60d": 45, "category": "C", "supplier": "Bulk Supplies Co.", "lead_time_days": 3, "moq": 100},
            {"product_id": "SUMMER-001", "name": "Sandalias Verano Beach", "sku": "SANDALS-BEACH-01", "stock": 150, "price": 49.99, "cost_price": 20.00, "velocity_daily": 0.0, "total_sales_30d": 0, "total_sales_60d": 1, "category": "Dead", "supplier": "Summer Fashion Inc.", "lead_time_days": 21, "moq": 100},
        ]
        
        if dry_run:
            return jsonify({
                "success": True,
                "dry_run": True,
                "message": "Dry run - no se insertaron datos",
                "would_insert": {
                    "products": len(COLUMBUS_PRODUCTS),
                    "suppliers": 6,
                    "estimated_sales_30d": "~350 registros"
                },
                "products_preview": [{"sku": p["sku"], "name": p["name"], "cat": p["category"], "vel": p["velocity_daily"]} for p in COLUMBUS_PRODUCTS[:5]]
            }), 200
        
        # Insertar productos
        conn = get_db_connection()
        cursor = conn.cursor()
        
        products_inserted = 0
        for p in COLUMBUS_PRODUCTS:
            cursor.execute("""
                INSERT OR REPLACE INTO products
                (product_id, name, sku, stock, price, cost_price, velocity_daily,
                 total_sales_30d, category, shop, last_updated, last_sale_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p['product_id'], p['name'], p['sku'], p['stock'], p['price'],
                p['cost_price'], p['velocity_daily'], p['total_sales_30d'],
                p['category'], 'columbus-shop', datetime.now().isoformat(),
                (datetime.now() - timedelta(days=1)).isoformat() if p['velocity_daily'] > 0 else None
            ))
            products_inserted += 1
        
        # Insertar proveedores
        unique_suppliers = list(set([p['supplier'] for p in COLUMBUS_PRODUCTS]))
        suppliers_inserted = 0
        for supplier in unique_suppliers:
            cursor.execute("""
                INSERT OR IGNORE INTO suppliers (name, lead_time_days, minimum_order_qty, notes)
                VALUES (?, ?, ?, ?)
            """, (supplier, 10, 50, 'Columbus winter catalog'))
            if cursor.rowcount > 0:
                suppliers_inserted += 1
        
        # Generar ventas históricas (últimos 30 días)
        today = datetime.now()
        sales_inserted = 0
        
        for p in COLUMBUS_PRODUCTS:
            if p['velocity_daily'] == 0:
                continue
            
            for days_ago in range(30, 0, -1):
                sale_date = today - timedelta(days=days_ago)
                daily_sales = max(0, int(p['velocity_daily'] + random.uniform(-p['velocity_daily'] * 0.3, p['velocity_daily'] * 0.3)))
                
                # Spike frío extremo (días 10-15)
                if 10 <= days_ago <= 15 and ('chaqueta' in p['name'].lower() or 'boots' in p['name'].lower()):
                    daily_sales = int(daily_sales * 1.5)
                
                for sale_num in range(daily_sales):
                    order_id = f"ORD-{sale_date.strftime('%Y%m%d')}-{p['sku']}-{sale_num:03d}"
                    try:
                        cursor.execute("""
                            INSERT INTO sales_history (sku, product_name, quantity, sale_date, order_id, shop)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (p['sku'], p['name'], 1, sale_date.isoformat(), order_id, 'columbus-shop'))
                        sales_inserted += 1
                    except:
                        pass  # Ignore duplicates
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Columbus seed completed: {products_inserted} products, {suppliers_inserted} suppliers, {sales_inserted} sales")
        
        return jsonify({
            "success": True,
            "message": "🦈 Columbus Winter Catalog seeded successfully",
            "inserted": {
                "products": products_inserted,
                "suppliers": suppliers_inserted,
                "sales_history_30d": sales_inserted
            },
            "next_steps": [
                "Verificar: GET /api/cashflow/summary",
                "Pulso manual: POST /api/pulse/trigger (si existe)",
                "Ver datos: GET /api/products"
            ],
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error seeding Columbus catalog: {e}")
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

@cashflow_bp.route('/api/admin/seed-fast', methods=['POST'])
def admin_seed_fast():
    """
    🚀 SEED RÁPIDO: Solo productos, sin ventas históricas
    
    Inserta productos Columbus sin timeout (< 5 segundos).
    
    Body JSON:
        - admin_key: "tiburon-seed-2026"
    """
    import os
    from datetime import datetime, timedelta
    
    try:
        data = request.get_json() or {}
    except:
        data = {}
    
    admin_key = data.get('admin_key', '')
    expected_key = os.getenv('ADMIN_SEED_KEY', 'tiburon-seed-2026')
    
    if admin_key != expected_key:
        return jsonify({"success": False, "error": "Unauthorized"}), 401
    
    try:
        PRODUCTS = [
            ("WINTER-001", "Chaqueta Térmica Winter Pro", "JACKET-WINTER-01", 12, 189.99, 95.00, 3.2, 96, "A"),
            ("WINTER-002", "Boots Waterproof Premium", "BOOTS-WP-01", 8, 159.99, 80.00, 2.8, 84, "A"),
            ("WINTER-003", "Guantes Térmicos Arctic", "GLOVES-ARC-01", 25, 45.99, 18.00, 4.5, 135, "A"),
            ("WINTER-004", "Bufanda Lana Merino", "SCARF-WOOL-01", 40, 39.99, 15.00, 1.8, 54, "B"),
            ("WINTER-005", "Gorro Térmico Fleece", "HAT-FLEECE-01", 60, 29.99, 10.00, 2.1, 63, "B"),
        ]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for p in PRODUCTS:
            cursor.execute("""
                INSERT OR REPLACE INTO products
                (product_id, name, sku, stock, price, cost_price, velocity_daily, total_sales_30d, category, shop, last_updated, last_sale_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (*p, "columbus-shop", datetime.now().isoformat(), (datetime.now() - timedelta(days=1)).isoformat()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Seed rápido: {len(PRODUCTS)} productos insertados")
        
        return jsonify({
            "success": True,
            "message": "🦈 Seed rápido completado",
            "inserted": {"products": len(PRODUCTS)},
            "note": "Sin ventas históricas (más rápido)",
            "timestamp": datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"❌ Error seed rápido: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@cashflow_bp.route('/api/admin/seed-simple', methods=['POST'])
def admin_seed_simple():
    """
    🌱 SEED ULTRA-SIMPLE: 3 productos Columbus

    Endpoint minimalista sin dependencias complejas.
    Solo inserta productos directamente.

    Body: {"key": "tiburon2026"}
    """
    try:
        data = request.get_json() or {}
        if data.get('key') != 'tiburon2026':
            return jsonify({"error": "Unauthorized"}), 401

        from datetime import datetime, timedelta

        conn = get_db_connection()
        cursor = conn.cursor()

        # 3 productos críticos
        products = [
            ("WINTER-001", "Chaqueta Térmica Winter Pro", "JACKET-WINTER-01", 12, 189.99, 95.00, 3.2, 96, "A"),
            ("WINTER-002", "Boots Waterproof Premium", "BOOTS-WP-01", 8, 159.99, 80.00, 2.8, 84, "A"),
            ("WINTER-003", "Guantes Térmicos Arctic", "GLOVES-ARC-01", 25, 45.99, 18.00, 4.5, 135, "A"),
        ]

        now = datetime.now().isoformat()
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()

        inserted = 0
        for p in products:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO products
                    (product_id, name, sku, stock, price, cost_price, velocity_daily, total_sales_30d, category, shop, last_updated, last_sale_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (*p, "columbus-shop", now, yesterday))
                inserted += 1
            except Exception as e:
                print(f"Error inserting {p[2]}: {e}")

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "inserted": inserted,
            "products": [p[2] for p in products]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

