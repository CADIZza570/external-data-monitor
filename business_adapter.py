"""
Business Context Adapter - Shopify App (VERSIÓN SIMPLE)
Interpreta alertas según rubro del cliente

✅ MEJORAS sobre versión original:
- kwargs extraídos al inicio de evaluate_stock()
- Mejor manejo de errores
- Validación de tipos de negocio
- Documentación mejorada
"""

BUSINESS_CONTEXTS = {
    'ecommerce': {
        'name': 'E-commerce / Retail',
        'icon': '🛍️',
        'stock_critical': 3,    
        'stock_warning': 7,
        'stock_low': 10,
        'urgency_high': True,
        'alert_frequency': 'immediate',
        'message_template': '🔴 {product} - Stock crítico: {stock} unidades\n💡 Acción: Reabastecer HOY',
        'kpis': [
            'inventory_turnover',
            'sell_through_rate',
            'days_of_inventory',
            'stockout_rate'
        ],
        'description': 'Alertas inmediatas. Stock bajo = pérdida directa de ventas.'
    },
    
    'restaurant': {
        'name': 'Restaurant / Food Service',
        'icon': '🍽️',
        'stock_critical': 1,
        'stock_warning': 3,
        'stock_low': 5,
        'urgency_high': False,
        'alert_frequency': 'weekly',
        'message_template': '🟡 {product} - Incluir en pedido semanal\n💡 Ingrediente para menú',
        'kpis': [
            'food_cost_percentage',
            'waste_percentage',
            'menu_item_profitability',
            'supplier_reliability'
        ],
        'description': 'Alertas semanales. Stock bajo = orden a proveedor.'
    },
    
    'construction': {
        'name': 'Construction / Materials',
        'icon': '🏗️',
        'stock_critical': 10,
        'stock_warning': 30,
        'stock_low': 50,
        'urgency_high': False,
        'alert_frequency': 'biweekly',
        'message_template': '🟠 {product} - Solicitar cotización\n💡 Lead time: 30-60 días',
        'kpis': [
            'days_inventory',
            'project_margin',
            'material_waste',
            'lead_time_compliance'
        ],
        'description': 'Alertas anticipadas. Stock bajo = planificar con 30-60 días.'
    },
    
    'retail': {
        'name': 'Retail Store',
        'icon': '🏪',
        'stock_critical': 5,
        'stock_warning': 15,
        'stock_low': 25,
        'urgency_high': True,
        'alert_frequency': 'immediate',
        'message_template': '🟠 {product} - Reposición necesaria\n💡 Safety stock: {safety_stock} unidades',
        'kpis': [
            'sell_through_rate',
            'shrinkage',
            'footfall_conversion',
            'seasonal_index'
        ],
        'description': 'Considera estacionalidad y rotación.'
    },
    
    'manufacturing': {
        'name': 'Manufacturing',
        'icon': '🏭',
        'stock_critical': 20,
        'stock_warning': 50,
        'stock_low': 100,
        'urgency_high': False,
        'alert_frequency': 'weekly',
        'message_template': '🟣 {product} - Materia prima para orden #{order_id}\n💡 Producción JIT',
        'kpis': [
            'oee',
            'cycle_time',
            'material_yield',
            'downtime_hours'
        ],
        'description': 'Just-in-time. Stock bajo = riesgo de parada producción.'
    }
}


class BusinessAdapter:
    """
    Adaptador de contexto de negocio
    Core diferenciador de la Shopify App
    """
    
    def __init__(self, business_type: str = 'ecommerce'):
        """
        Args:
            business_type: ecommerce | restaurant | construction | retail | manufacturing
        
        Raises:
            ValueError: Si business_type no es válido
        """
        if business_type not in BUSINESS_CONTEXTS:
            raise ValueError(
                f"business_type '{business_type}' inválido. "
                f"Opciones: {', '.join(BUSINESS_CONTEXTS.keys())}"
            )
        
        self.business_type = business_type
        self.context = BUSINESS_CONTEXTS[business_type]
    
    def evaluate_stock(self, product_name: str, stock: int, **kwargs) -> dict:
        """
        Evalúa nivel de stock según contexto de negocio
        
        Args:
            product_name: Nombre del producto
            stock: Cantidad actual
            **kwargs: Opcionales
                - price (float): Precio unitario
                - sku (str): SKU del producto
                - variant_id (str): ID de variante
                - order_id (str): ID de orden (para manufacturing)
                - lead_time_days (int): Días de lead time
        
        Returns:
            dict con evaluación completa:
                - urgency: str ('ok', 'info', 'warning', 'critical', 'outofstock')
                - severity: str ('info', 'warning', 'critical')
                - color: str (emoji de color)
                - action: str (acción recomendada)
                - message: str (mensaje formateado)
                - business_type: str
                - business_name: str
                - business_icon: str
                - alert_frequency: str
                - value_at_risk: float
                - thresholds: dict
        """
        # ✅ CORRECCIÓN: Extraer kwargs AL INICIO con valores seguros
        order_id = kwargs.get('order_id', 'N/A')
        safety_stock = kwargs.get('safety_stock', self.context['stock_low'])
        price = kwargs.get('price', 0)
        sku = kwargs.get('sku', 'N/A')
        
        # Determinar urgencia
        if stock == 0:
            urgency = 'outofstock'
            color = '❌'
            severity = 'critical'
            action = 'AGOTADO - Reabastecer URGENTE'
        elif stock <= self.context['stock_critical']:
            urgency = 'critical'
            color = '🔴'
            severity = 'critical'
            action = f"Reabastecer {self.context['alert_frequency']}"
        elif stock <= self.context['stock_warning']:
            urgency = 'warning'
            color = '🟠'
            severity = 'warning'
            action = 'Planificar orden'
        elif stock <= self.context['stock_low']:
            urgency = 'info'
            color = '🟡'
            severity = 'info'
            action = 'Monitorear'
        else:
            urgency = 'ok'
            color = '🟢'
            severity = 'info'
            action = 'Stock OK'
        
        # Calcular valor en riesgo
        value_at_risk = 0.0
        try:
            value_at_risk = float(price) * stock
        except (ValueError, TypeError):
            pass  # price inválido, mantener 0.0
        
        # ✅ CORRECCIÓN: Mensaje con kwargs ya extraídos
        try:
            message = self.context['message_template'].format(
                product=product_name,
                stock=stock,
                safety_stock=safety_stock,
                order_id=order_id
            )
        except KeyError as e:
            # Fallback si faltan placeholders
            message = f"{color} {product_name} - Stock: {stock} unidades\n💡 {action}"
        
        return {
            'urgency': urgency,
            'severity': severity,
            'color': color,
            'action': action,
            'message': message,
            'business_type': self.business_type,
            'business_name': self.context['name'],
            'business_icon': self.context['icon'],
            'alert_frequency': self.context['alert_frequency'],
            'value_at_risk': value_at_risk,
            'thresholds': {
                'critical': self.context['stock_critical'],
                'warning': self.context['stock_warning'],
                'low': self.context['stock_low']
            },
            # Extras útiles
            'sku': sku,
            'order_id': order_id
        }
    
    def get_kpis(self) -> list:
        """Retorna KPIs relevantes para el negocio"""
        return self.context['kpis']
    
    def get_description(self) -> str:
        """Descripción del comportamiento para este rubro"""
        return self.context['description']
    
    @staticmethod
    def get_available_types() -> list:
        """Lista de rubros soportados"""
        return [
            {
                'id': key,
                'name': ctx['name'],
                'icon': ctx['icon'],
                'description': ctx['description']
            }
            for key, ctx in BUSINESS_CONTEXTS.items()
        ]


# ============================================================================
# EJEMPLO DE USO
# ============================================================================
if __name__ == '__main__':
    print("🧪 Testing BusinessAdapter (Versión Simple)\n")
    
    # Test 1: E-commerce
    print("=" * 60)
    print("TEST 1: E-commerce - Stock crítico")
    print("=" * 60)
    adapter = BusinessAdapter('ecommerce')
    result = adapter.evaluate_stock(
        product_name='iPhone 15 Pro',
        stock=2,
        price=999.99,
        sku='IP15P-BLK-256'
    )
    print(f"Urgencia: {result['urgency']}")
    print(f"Mensaje:\n{result['message']}")
    print(f"Valor en riesgo: ${result['value_at_risk']:.2f}")
    print(f"KPIs: {', '.join(result['thresholds'].keys())}\n")
    
    # Test 2: Restaurant
    print("=" * 60)
    print("TEST 2: Restaurant - Stock bajo")
    print("=" * 60)
    adapter = BusinessAdapter('restaurant')
    result = adapter.evaluate_stock(
        product_name='Harina 25kg',
        stock=2,
        price=15000
    )
    print(f"Urgencia: {result['urgency']}")
    print(f"Mensaje:\n{result['message']}")
    print(f"Frecuencia alertas: {result['alert_frequency']}\n")
    
    # Test 3: Construction
    print("=" * 60)
    print("TEST 3: Construction - Stock warning")
    print("=" * 60)
    adapter = BusinessAdapter('construction')
    result = adapter.evaluate_stock(
        product_name='Cemento Portland 50kg',
        stock=25,
        price=8500,
        sku='CEM-PORT-50'
    )
    print(f"Urgencia: {result['urgency']}")
    print(f"Mensaje:\n{result['message']}")
    print(f"Thresholds: critical={result['thresholds']['critical']}, "
          f"warning={result['thresholds']['warning']}, "
          f"low={result['thresholds']['low']}\n")
    
    # Test 4: Manufacturing
    print("=" * 60)
    print("TEST 4: Manufacturing - Con order_id")
    print("=" * 60)
    adapter = BusinessAdapter('manufacturing')
    result = adapter.evaluate_stock(
        product_name='Acero inoxidable 304',
        stock=15,
        price=25000,
        order_id='ORD-2025-0104'
    )
    print(f"Urgencia: {result['urgency']}")
    print(f"Mensaje:\n{result['message']}")
    print(f"KPIs relevantes: {adapter.get_kpis()}\n")
    
    # Test 5: Stock agotado
    print("=" * 60)
    print("TEST 5: Stock AGOTADO (cualquier rubro)")
    print("=" * 60)
    adapter = BusinessAdapter('retail')
    result = adapter.evaluate_stock(
        product_name='Zapatillas Nike Air',
        stock=0,
        price=89990
    )
    print(f"Urgencia: {result['urgency']}")
    print(f"Severidad: {result['severity']}")
    print(f"Mensaje:\n{result['message']}\n")
    
    # Test 6: Tipos disponibles
    print("=" * 60)
    print("TIPOS DE NEGOCIO DISPONIBLES")
    print("=" * 60)
    for btype in BusinessAdapter.get_available_types():
        print(f"{btype['icon']} {btype['name']} ({btype['id']})")
        print(f"   {btype['description']}")
    
    print("\n✅ Todos los tests completados")