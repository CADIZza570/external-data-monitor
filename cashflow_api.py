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
from datetime import datetime

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
