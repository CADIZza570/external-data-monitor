"""
Shopify Analytics Integration
Wrapper para integrar analytics con webhook_server.py
"""
from dotenv import load_dotenv  # ← AGREGAR

# ✅ CARGAR .env
load_dotenv()  # ← AGREGAR

import os
from shopify_analytics import ShopifyAnalytics
import logging

logger = logging.getLogger(__name__)


class AnalyticsIntegrator:
    """
    Integra Shopify Analytics con el sistema de alertas
    """
    
    def __init__(self):
        """Inicializa analytics engines por cliente"""
        self.engines = {}
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Crea analytics engine para cada cliente configurado"""

        # Chaparrita
        chaparrita_token = os.getenv('SHOPIFY_ACCESS_TOKEN_CHAPARRITA')
        if chaparrita_token:
            self.engines['chaparrita-boots'] = ShopifyAnalytics(
                shop_name='chaparrita-boots',
                access_token=chaparrita_token
            )
            logger.info("✅ Analytics engine creado: Chaparrita")
        
        # DEV
        dev_token = os.getenv('SHOPIFY_ACCESS_TOKEN_DEV')
        if dev_token:
            self.engines['connie-dev-studio'] = ShopifyAnalytics(
                shop_name='connie-dev-studio',
                access_token=dev_token
            )
            logger.info("✅ Analytics engine creado: DEV")
    
    def get_engine(self, shop_name: str) -> ShopifyAnalytics:
        """
        Obtiene analytics engine para una tienda
        
        Args:
            shop_name: Nombre de la tienda (puede ser domain o nombre amigable)
        
        Returns:
            ShopifyAnalytics instance o None
        """
        # Mapeo de nombres amigables a shop domains
        name_map = {
            'La Chaparrita': 'chaparrita-boots',
            'la chaparrita': 'chaparrita-boots',
            'chaparrita': 'chaparrita-boots',
            'Development Store': 'connie-dev-studio',
            'connie': 'connie-dev-studio'
        }
        
        # Intentar con el nombre directo primero
        engine = self.engines.get(shop_name)
        if engine:
            return engine
        
        # Si no encuentra, intentar con el mapeo
        mapped_name = name_map.get(shop_name)
        if mapped_name:
            return self.engines.get(mapped_name)
        
        # Log de debug
        print(f"No analytics engine for {shop_name}")
        return None
        
    def enrich_alert(self, product_data: dict, shop_name: str) -> dict:
        """
        Enriquece datos de alerta con analytics
        
        Args:
            product_data: Dict con product_id, name, stock, etc.
            shop_name: Nombre de la tienda
        
        Returns:
            product_data enriquecido con analytics
        """
        engine = self.get_engine(shop_name)
        
        if not engine:
            logger.warning(f"No analytics engine for {shop_name}")
            return product_data
        
        try:
            # Análisis completo
            analysis = engine.analyze_product(
                product_id=int(product_data.get('product_id', 0)),
                current_stock=int(product_data.get('stock', 0)),
                product_name=product_data.get('name')
            )
            
            # Agregar analytics al product_data
            product_data['analytics'] = {
                'velocity': analysis['velocity']['velocity'],
                'velocity_confidence': analysis['velocity']['confidence'],
                'days_until_stockout': analysis['stockout_prediction']['days_until_stockout'],
                'stockout_date': analysis['stockout_prediction'].get('stockout_date'),
                'stockout_urgency': analysis['stockout_prediction']['urgency'],
                'should_reorder': analysis['reorder_recommendation']['should_reorder'],
                'reorder_quantity': analysis['reorder_recommendation']['recommended_quantity'],
                'units_sold_30d': analysis['velocity']['units_sold']
            }
            
            logger.info(f"📊 Analytics agregado: {product_data['name']} - "
                       f"Velocity: {product_data['analytics']['velocity']}/día")
            
        except Exception as e:
            logger.error(f"Error enriching alert with analytics: {e}")
            product_data['analytics'] = None
        
        return product_data
  
    def format_analytics_message(self, product_data: dict) -> str:
        """
        Formatea mensaje con analytics para alertas
        
        Args:
            product_data: Dict con analytics
        
        Returns:
            Mensaje formateado con analytics
        """
        if not product_data.get('analytics'):
            return ""
        
        analytics = product_data['analytics']
        
        # Construir mensaje
        parts = []
        
        # Velocity
        if analytics.get('velocity'):
            parts.append(f"📊 Velocity: {analytics['velocity']:.2f} units/día")
        
        # Stockout prediction
        if analytics.get('days_until_stockout'):
            days = analytics['days_until_stockout']
            parts.append(f"⏰ Se agota en: {days:.1f} días ({analytics.get('stockout_date', 'N/A')})")
        
        # Reorder recommendation
        if analytics.get('should_reorder'):
            qty = analytics['reorder_quantity']
            parts.append(f"💡 Recomendación: Reabastecer {qty} unidades")
        
        # Ventas
        if analytics.get('units_sold_30d'):
            parts.append(f"📈 Vendidos últimos 30d: {analytics['units_sold_30d']} units")
        
        return "\n".join(parts)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================
_integrator = None

def get_analytics_integrator() -> AnalyticsIntegrator:
    """
    Singleton para obtener integrator
    
    Returns:
        AnalyticsIntegrator instance
    """
    global _integrator
    if _integrator is None:
        _integrator = AnalyticsIntegrator()
    return _integrator


# ============================================================================
# EJEMPLO DE USO
# ============================================================================
if __name__ == '__main__':
    import os
    
    # Simular env vars (para test)
    os.environ['SHOPIFY_ACCESS_TOKEN_CHAPARRITA'] = os.getenv('SHOPIFY_ACCESS_TOKEN_CHAPARRITA', 'TOKEN_AQUI')
    
    # Crear integrator
    integrator = get_analytics_integrator()
    
    # Simular product data del webhook
    product = {
        'product_id': 9183074943215,
        'name': 'Producto A',
        'stock': 4,
        'sku': 'PROD-A-001',
        'price': 100.00
    }
    
    print("📦 PRODUCTO ANTES DE ENRICHMENT:")
    print(product)
    print("")
    
    # Enriquecer con analytics
    enriched = integrator.enrich_alert(product, 'chaparrita-boots')
    
    print("=" * 80)
    print("📦 PRODUCTO DESPUÉS DE ENRICHMENT:")
    print("")
    for key, value in enriched.items():
        if key == 'analytics' and value:
            print(f"{key}:")
            for k, v in value.items():
                print(f"  {k}: {v}")
        else:
            print(f"{key}: {value}")
    
    print("")
    print("=" * 80)
    print("💬 MENSAJE FORMATEADO:")
    print("")
    print(integrator.format_analytics_message(enriched))
    print("")