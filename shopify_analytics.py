"""
Shopify Inventory Analytics Engine
Calcula velocity, predice stockouts, genera recomendaciones
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # ← AGREGAR ESTA LÍNEA


class ShopifyAnalytics:
    """
    Analytics engine para inventario Shopify
    
    Capabilities:
    - Calcular inventory velocity (units/day)
    - Predecir stockouts con confidence
    - Generar recomendaciones de reorder
    """
    
    def __init__(self, shop_name: str, access_token: str, api_version: str = "2025-01"):
        """
        Args:
            shop_name: Nombre de la tienda (ej: chaparrita-boots)
            access_token: Admin API access token
            api_version: Versión de API (default: 2025-01)
        """
        self.shop_name = shop_name
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"https://{shop_name}.myshopify.com/admin/api/{api_version}"
        
        self.headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
    
    def get_product_sales_history(self, product_id: int, days: int = 30) -> List[Dict]:
        """
        Obtiene historial de ventas de un producto
        
        Args:
            product_id: ID del producto
            days: Días hacia atrás (default: 30)
        
        Returns:
            Lista de órdenes con ese producto
        """
        date_min = (datetime.now() - timedelta(days=days)).isoformat()
        
        url = f"{self.base_url}/orders.json"
        params = {
            "status": "any",
            "created_at_min": date_min,
            "limit": 250  # Máximo por página
        }
        
        # ============= NUEVO: LOGS DETALLADOS =============
        logger.info(f"🔍 Consultando Shopify API para product_id={product_id}")
        logger.info(f"   URL: {url}")
        logger.info(f"   Params: {params}")
        # ==================================================
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            # ============= NUEVO: LOG RESPONSE =============
            logger.info(f"   Response status: {response.status_code}")
            # ===============================================
            
            if response.status_code != 200:
                logger.error(f"❌ Error fetching orders: {response.status_code} - {response.text[:200]}")
                return []
            
            orders = response.json()['orders']
            
            # ============= NUEVO: LOG ORDERS COUNT =============
            logger.info(f"   Total orders fetched: {len(orders)}")
            # ===================================================
            
            # Filtrar órdenes que contienen este producto
            product_orders = []
            for order in orders:
                for item in order['line_items']:
                    if item['product_id'] == product_id:
                        product_orders.append({
                            'order_id': order['id'],
                            'date': order['created_at'],
                            'quantity': item['quantity'],
                            'price': item['price']
                        })
            
            # ============= NUEVO: LOG FILTERED ORDERS =============
            logger.info(f"   Orders with product_id={product_id}: {len(product_orders)}")
            if product_orders:
                total_qty = sum(o['quantity'] for o in product_orders)
                logger.info(f"   Total units sold: {total_qty}")
            # ======================================================
            
            return product_orders
            
        except Exception as e:
            logger.error(f"❌ Error getting sales history: {e}")
            return []
    
    def calculate_velocity(self, product_id: int, days: int = 30) -> Dict:
        """
        Calcula velocity de ventas (units/day)
        
        Args:
            product_id: ID del producto
            days: Período de análisis (default: 30)
        
        Returns:
            dict con velocity data y confidence
        """
        sales = self.get_product_sales_history(product_id, days)
        
        if not sales:
            return {
                'velocity': 0.0,
                'units_sold': 0,
                'days_analyzed': days,
                'confidence': 'low',
                'has_data': False
            }
        
        # Calcular total vendido
        total_units = sum(sale['quantity'] for sale in sales)
        
        # Velocity = units / days
        velocity = total_units / days
        
        # Determinar confidence según cantidad de datos
        if len(sales) >= 10:
            confidence = 'high'
        elif len(sales) >= 5:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        return {
            'velocity': round(velocity, 2),
            'units_sold': total_units,
            'days_analyzed': days,
            'orders_count': len(sales),
            'confidence': confidence,
            'has_data': True
        }
    
    def predict_stockout(self, product_id: int, current_stock: int, 
                        safety_stock: int = 0) -> Dict:
        """
        Predice cuándo se agotará el stock
        
        Args:
            product_id: ID del producto
            current_stock: Stock actual
            safety_stock: Stock de seguridad (default: 0)
        
        Returns:
            dict con predicción de stockout
        """
        # Calcular velocity
        velocity_data = self.calculate_velocity(product_id, days=30)
        velocity = velocity_data['velocity']
        
        if velocity == 0 or not velocity_data['has_data']:
            return {
                'days_until_stockout': None,
                'stockout_date': None,
                'urgency': 'unknown',
                'velocity': 0.0,
                'confidence': 'low',
                'message': 'Sin datos de ventas para predecir'
            }
        
        # Calcular días hasta stockout
        available_stock = current_stock - safety_stock
        days_until_stockout = available_stock / velocity
        
        # Fecha estimada de stockout
        stockout_date = datetime.now() + timedelta(days=days_until_stockout)
        
        # Determinar urgencia
        if days_until_stockout < 0:
            urgency = 'critical'
            message = 'Stock por debajo de safety stock'
        elif days_until_stockout <= 7:
            urgency = 'critical'
            message = f'Se agota en {days_until_stockout:.1f} días'
        elif days_until_stockout <= 14:
            urgency = 'warning'
            message = f'Se agota en {days_until_stockout:.1f} días'
        elif days_until_stockout <= 28:
            urgency = 'watch'
            message = f'Se agota en {days_until_stockout:.1f} días'
        else:
            urgency = 'ok'
            message = f'Stock suficiente ({days_until_stockout:.0f} días)'
        
        return {
            'days_until_stockout': round(days_until_stockout, 1),
            'stockout_date': stockout_date.strftime('%Y-%m-%d'),
            'urgency': urgency,
            'velocity': velocity,
            'confidence': velocity_data['confidence'],
            'message': message,
            'units_sold_30d': velocity_data['units_sold'],
            'orders_count': velocity_data['orders_count']
        }
    
    def generate_reorder_recommendation(self, product_id: int, current_stock: int,
                                       lead_time_days: int = 7) -> Dict:
        """
        Genera recomendación de reabastecimiento
        
        Args:
            product_id: ID del producto
            current_stock: Stock actual
            lead_time_days: Tiempo de entrega del proveedor (default: 7)
        
        Returns:
            dict con recomendación de reorder
        """
        # Predecir stockout
        prediction = self.predict_stockout(product_id, current_stock)
        
        if not prediction['days_until_stockout']:
            return {
                'should_reorder': False,
                'recommended_quantity': 0,
                'reason': 'Sin datos suficientes para recomendar'
            }
        
        velocity = prediction['velocity']
        days_until_stockout = prediction['days_until_stockout']
        
        # Determinar si necesita reorder
        should_reorder = days_until_stockout <= lead_time_days * 1.5
        
        if should_reorder:
            # Calcular cantidad recomendada
            # Fórmula: (30 días de demanda) + (lead time * velocity) + 20% buffer
            demand_30d = velocity * 30
            lead_time_buffer = velocity * lead_time_days
            safety_buffer = demand_30d * 0.2
            
            recommended_quantity = int(demand_30d + lead_time_buffer + safety_buffer)
            
            # Ajustar a múltiplos de 5 (más profesional)
            recommended_quantity = ((recommended_quantity + 4) // 5) * 5
            
            return {
                'should_reorder': True,
                'recommended_quantity': recommended_quantity,
                'reason': f'Stock se agota en {days_until_stockout:.1f} días',
                'urgency': prediction['urgency'],
                'breakdown': {
                    'demand_30d': int(demand_30d),
                    'lead_time_buffer': int(lead_time_buffer),
                    'safety_buffer': int(safety_buffer)
                }
            }
        else:
            return {
                'should_reorder': False,
                'recommended_quantity': 0,
                'reason': f'Stock suficiente ({days_until_stockout:.0f} días)',
                'urgency': 'ok'
            }
    
    def analyze_product(self, product_id: int, current_stock: int,
                       product_name: str = None) -> Dict:
        """
        Análisis completo de un producto
        
        Args:
            product_id: ID del producto
            current_stock: Stock actual
            product_name: Nombre del producto (opcional)
        
        Returns:
            dict con análisis completo
        """
        # Velocity
        velocity_data = self.calculate_velocity(product_id, days=30)
        
        # Stockout prediction
        stockout = self.predict_stockout(product_id, current_stock)
        
        # Reorder recommendation
        reorder = self.generate_reorder_recommendation(product_id, current_stock)
        
        return {
            'product_id': product_id,
            'product_name': product_name or f'Product {product_id}',
            'current_stock': current_stock,
            'velocity': velocity_data,
            'stockout_prediction': stockout,
            'reorder_recommendation': reorder,
            'analyzed_at': datetime.now().isoformat()
        }


# ============================================================================
# EJEMPLO DE USO
# ============================================================================
if __name__ == '__main__':
    # Configuración
    SHOP_NAME = "chaparrita-boots"
    ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN_CHAPARRITA', 'TOKEN_AQUI')
    
    # Crear analytics engine
    analytics = ShopifyAnalytics(SHOP_NAME, ACCESS_TOKEN)
    
    # Productos de test (de tu tienda)
    products = [
        {'id': 9183074943215, 'name': 'Producto A', 'stock': 4},
        {'id': 9183075008751, 'name': 'Producto B Especial', 'stock': 8},
        {'id': 9183075041519, 'name': 'Producto C', 'stock': 3}
    ]
    
    print("")
    print("🔍 SHOPIFY INVENTORY ANALYTICS")
    print("=" * 80)
    print("")
    
    for product in products:
        print(f"📦 {product['name']}")
        print("-" * 80)
        
        # Análisis completo
        analysis = analytics.analyze_product(
            product_id=product['id'],
            current_stock=product['stock'],
            product_name=product['name']
        )
        
        # Mostrar resultados
        velocity = analysis['velocity']
        stockout = analysis['stockout_prediction']
        reorder = analysis['reorder_recommendation']
        
        print(f"Stock actual: {product['stock']} unidades")
        print("")
        
        print(f"📊 Velocity:")
        print(f"   {velocity['velocity']} units/día (últimos 30 días)")
        print(f"   Vendidos: {velocity['units_sold']} unidades en {velocity['orders_count']} órdenes")
        print(f"   Confianza: {velocity['confidence'].upper()}")
        print("")
        
        print(f"⏰ Predicción Stockout:")
        if stockout['days_until_stockout']:
            print(f"   {stockout['message']}")
            print(f"   Fecha estimada: {stockout['stockout_date']}")
            print(f"   Urgencia: {stockout['urgency'].upper()}")
        else:
            print(f"   {stockout['message']}")
        print("")
        
        print(f"💡 Recomendación:")
        if reorder['should_reorder']:
            print(f"   ✅ REABASTECER: {reorder['recommended_quantity']} unidades")
            print(f"   Razón: {reorder['reason']}")
            print(f"   Breakdown:")
            print(f"      - Demanda 30d: {reorder['breakdown']['demand_30d']} units")
            print(f"      - Buffer lead time: {reorder['breakdown']['lead_time_buffer']} units")
            print(f"      - Safety buffer: {reorder['breakdown']['safety_buffer']} units")
        else:
            print(f"   ⏸️  No requiere reabastecimiento")
            print(f"   Razón: {reorder['reason']}")
        
        print("")
        print("=" * 80)
        print("")