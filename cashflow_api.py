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

Autor: Claude Code
Fecha: 2026-01-18
"""

from flask import Blueprint, request, jsonify, send_file
import sqlite3
import csv
import io
import os
import json
import logging
from datetime import datetime, timedelta
from auth_middleware import require_api_key  # 🔐 Auth

# ============================================================
# LOGGING NARRATIVO + CENTINELA
# ============================================================
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Crear Blueprint
cashflow_bp = Blueprint('cashflow', __name__)

# ============================================================
# HELPER: VALIDACIÓN DE PARÁMETROS
# ============================================================
def get_validated_param(param_name, default, min_val=None, max_val=None):
    """
    Valida y sanitiza parámetros query con límites min/max.

    Previene DoS accidental (e.g., ?days=999999) y valores inválidos.
    """
    value = request.args.get(param_name, default, type=type(default))
    if min_val is not None:
        value = max(value, min_val)
    if max_val is not None:
        value = min(value, max_val)
    return value

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
@require_api_key  # 🔐 Requiere autenticación (WRITE operation)
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
@require_api_key  # 🔐 Requiere autenticación
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
@require_api_key  # 🔐 Requiere autenticación
def cashflow_summary():
    """
    Resumen completo de Cash Flow con detección de anomalías.

    Returns:
        JSON con métricas clave
    """
    shop = request.args.get('shop', 'unknown')
    logger.info(f"GET /api/cashflow/summary - shop: {shop}")

    conn = None
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

        # 🚨 CENTINELA: Detección de Anomalías
        if inventory_value < 10000:
            logger.warning(
                f"⚠️ ANOMALÍA en {shop}: Inventory bajo (${inventory_value:.2f})! "
                f"Posible stockout inminente. Con calor en Los Andes, demanda puede explotar - "
                f"chequea logística YA."
            )

        if stockouts > 5:
            logger.warning(
                f"🔴 ALERTA CRÍTICA: {stockouts} productos agotados en {shop}! "
                f"Categoría A en riesgo. Reorder urgente para no perder ventas en temporada alta."
            )

        if critical_stock > 10:
            logger.warning(
                f"🟡 ATENCIÓN: {critical_stock} productos con menos de 7 días de stock. "
                f"Revisar reorden para evitar quiebres de inventario."
            )

        logger.info(f"Summary calculado: {total_products} productos, {stockouts} stockouts, ${lost_revenue:.2f} perdidos")

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
        logger.error(f"Error en cashflow_summary: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            conn.close()

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
# REORDER CALCULATOR - OPTIMIZACIÓN DE COMPRAS CON PRESUPUESTO
# ============================================================================

@cashflow_bp.route('/api/reorder-calculator', methods=['GET'])
@require_api_key  # 🔐 Requiere autenticación
def reorder_calculator():
    """
    Calcula lista optimizada de compras dentro de presupuesto.
    Usa índices idx_products_stock_low y idx_products_category para performance.

    Query params:
        - budget: Presupuesto disponible (default: 5000)
        - lead_time: Días de reposición (default: 14)
        - shop: Filtro por tienda (opcional)

    Returns:
        {
            'budget': float,
            'used': float,
            'remaining': float,
            'shopping_list': [...],
            'items_count': int,
            'categories_breakdown': {...}
        }
    """
    # ✅ VALIDACIÓN con límites
    budget = get_validated_param('budget', 5000, min_val=0, max_val=1000000)
    lead_time = get_validated_param('lead_time', 14, min_val=1, max_val=90)
    shop_filter = request.args.get('shop', None)

    logger.info(f"GET /api/reorder-calculator - shop: {shop_filter or 'all'}, budget: ${budget}, lead_time: {lead_time}d")

    conn = None
    try:
        conn = get_db_connection()
        # Query optimizado con índices idx_products_stock_low + idx_products_category
        query = """
            SELECT
                sku, name, stock, velocity_daily, price, cost_price,
                category, shop,
                CAST(stock / NULLIF(velocity_daily, 0) AS INTEGER) as days_left,
                CAST(velocity_daily * ? AS INTEGER) - stock as units_needed
            FROM products
            WHERE velocity_daily > 0
              AND (stock / NULLIF(velocity_daily, 0)) < ?
        """
        params = [lead_time, lead_time * 1.5]

        if shop_filter:
            query += " AND shop = ?"
            params.append(shop_filter)

        # Ordenar por prioridad: A > B > C, luego por urgencia
        query += """
            ORDER BY
                CASE category
                    WHEN 'A' THEN 1
                    WHEN 'B' THEN 2
                    ELSE 3
                END,
                days_left ASC
        """

        products = conn.execute(query, params).fetchall()

        shopping_list = []
        total_cost = 0
        category_breakdown = {'A': 0, 'B': 0, 'C': 0}

        for p in products:
            if p['units_needed'] <= 0:
                continue

            # Calcular costo (usar cost_price si existe, sino estimar 60% del precio)
            unit_cost = p['cost_price'] if p['cost_price'] else (p['price'] * 0.6)
            item_cost = p['units_needed'] * unit_cost

            # Solo agregar si cabe en presupuesto
            if total_cost + item_cost <= budget:
                category = p['category'] or 'C'

                shopping_list.append({
                    'sku': p['sku'],
                    'name': p['name'],
                    'shop': p['shop'],
                    'units_needed': p['units_needed'],
                    'unit_cost': round(unit_cost, 2),
                    'total_cost': round(item_cost, 2),
                    'priority': category,
                    'urgency': f"{p['days_left']} días",
                    'current_stock': p['stock']
                })

                total_cost += item_cost
                category_breakdown[category] += item_cost

        # 🚨 CENTINELA: Detección de Demanda Explosiva
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sku, product_name,
                   AVG(quantity) as avg_recent_sales
            FROM sales_history
            WHERE sale_date >= date('now', '-3 days')
            GROUP BY sku
            HAVING AVG(quantity) > 0
        """)
        recent_sales = cursor.fetchall()

        for sale in recent_sales:
            # Buscar velocity normal del producto
            cursor.execute("""
                SELECT velocity_daily FROM products WHERE sku = ?
            """, (sale['sku'],))
            product = cursor.fetchone()

            if product and product['velocity_daily']:
                velocity_spike = (sale['avg_recent_sales'] / product['velocity_daily']) - 1
                if velocity_spike > 0.5:  # 50% más que lo normal
                    logger.warning(
                        f"🔥 DEMANDA EXPLOTANDO: {sale['product_name']} ({sale['sku']}) "
                        f"vendió {velocity_spike*100:.0f}% más en últimos 3 días! "
                        f"Posible efecto calor/estacional en Los Andes? Chequeá proveedores AHORA."
                    )

        logger.info(
            f"Reorder calculado: {len(shopping_list)} items, ${total_cost:.2f}/{budget:.2f} usado "
            f"({(total_cost/budget)*100:.1f}% utilización)"
        )

        return jsonify({
            'budget': budget,
            'used': round(total_cost, 2),
            'remaining': round(budget - total_cost, 2),
            'utilization_pct': round((total_cost / budget) * 100, 2) if budget > 0 else 0,
            'shopping_list': shopping_list,
            'items_count': len(shopping_list),
            'categories_breakdown': {
                'A': round(category_breakdown['A'], 2),
                'B': round(category_breakdown['B'], 2),
                'C': round(category_breakdown['C'], 2)
            },
            'lead_time_days': lead_time
        })

    except Exception as e:
        logger.error(f"Error en reorder_calculator: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    finally:
        if conn:
            conn.close()
