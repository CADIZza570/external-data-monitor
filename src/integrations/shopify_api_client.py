"""
Shopify API Client - Historical Data + Forecasting
🔥 "SISTEMAS QUE VIVEN" - Datos que PREDICEN el futuro

FEATURES:
- ✅ Historical sales data (orders, products)
- ✅ Inventory velocity (units/day)
- ✅ Stockout prediction
- ✅ Product performance analytics
- ✅ Better than GA4 for inventory tracking

SETUP:
1. Get API credentials:
   - Shopify Admin → Apps → Develop apps
   - Create private app
   - Get: API key, API secret, Access token

2. Set environment variables:
   export SHOPIFY_SHOP_NAME="tu-tienda"
   export SHOPIFY_ACCESS_TOKEN="shpat_xxx"
   export SHOPIFY_API_VERSION="2024-01"

USAGE:
    client = ShopifyClient(
        shop_name="tu-tienda",
        access_token="shpat_xxx"
    )
    
    # Get historical orders
    orders = client.get_orders(limit=250)
    
    # Inventory analytics
    analytics = client.analyze_product_velocity(product_id=123)
    print(f"Stockout in: {analytics['days_until_stockout']} days")
"""
import os
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import statistics


@dataclass
class ProductVelocity:
    """Análisis de velocidad de venta de un producto"""
    product_id: int
    product_name: str
    current_inventory: int
    units_per_day: float
    days_until_stockout: Optional[int]
    recommended_restock: int
    last_30_days_sales: int
    trend: str  # "increasing", "stable", "decreasing"


class ShopifyClient:
    """
    Cliente para Shopify Admin API
    
    🚀 MEJOR QUE GA4 PARA:
    - Inventory tracking
    - Historical sales data
    - Stockout prediction
    - Product-level analytics
    
    Usage:
        client = ShopifyClient(
            shop_name="tu-tienda",
            access_token="shpat_xxx"
        )
        
        # Orders
        orders = client.get_orders(limit=100)
        
        # Product analytics
        velocity = client.analyze_product_velocity(product_id=123)
        
        if velocity.days_until_stockout and velocity.days_until_stockout < 7:
            send_alert(f"Product {velocity.product_name} stockout in {velocity.days_until_stockout} days!")
    """
    
    def __init__(
        self,
        shop_name: Optional[str] = None,
        access_token: Optional[str] = None,
        api_version: str = "2024-01"
    ):
        """
        Args:
            shop_name: Nombre de la tienda (ej: "mi-tienda", no URL completa)
            access_token: Access token (shpat_xxx)
            api_version: Versión API de Shopify
        """
        self.shop_name = shop_name or os.getenv("SHOPIFY_SHOP_NAME")
        self.access_token = access_token or os.getenv("SHOPIFY_ACCESS_TOKEN")
        self.api_version = api_version
        
        if not self.shop_name or not self.access_token:
            raise ValueError(
                "Missing credentials. Set SHOPIFY_SHOP_NAME and SHOPIFY_ACCESS_TOKEN "
                "or pass them to constructor."
            )
        
        self.base_url = f"https://{self.shop_name}.myshopify.com/admin/api/{api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Hace request a Shopify API
        
        Args:
            method: GET, POST, PUT, DELETE
            endpoint: Endpoint (ej: "/products.json")
            params: Query params
            json_data: JSON body
        
        Returns:
            Response JSON
        """
        url = f"{self.base_url}{endpoint}"
        
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            params=params,
            json=json_data,
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_orders(
        self,
        limit: int = 250,
        status: str = "any",
        created_at_min: Optional[datetime] = None,
        created_at_max: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get orders (historical sales data)
        
        Args:
            limit: Max orders (250 max por request)
            status: "open", "closed", "cancelled", "any"
            created_at_min: Filter desde fecha
            created_at_max: Filter hasta fecha
        
        Returns:
            Lista de orders
        """
        params = {
            "limit": min(limit, 250),
            "status": status
        }
        
        if created_at_min:
            params["created_at_min"] = created_at_min.isoformat()
        if created_at_max:
            params["created_at_max"] = created_at_max.isoformat()
        
        response = self._request("GET", "/orders.json", params=params)
        return response.get("orders", [])
    
    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Get producto por ID"""
        response = self._request("GET", f"/products/{product_id}.json")
        return response.get("product", {})
    
    def get_inventory_level(
        self,
        inventory_item_id: int,
        location_id: Optional[int] = None
    ) -> int:
        """
        Get inventory level de un producto
        
        Args:
            inventory_item_id: ID del inventory item
            location_id: ID de location (None = todas)
        
        Returns:
            Total inventory quantity
        """
        params = {"inventory_item_ids": str(inventory_item_id)}
        if location_id:
            params["location_ids"] = str(location_id)
        
        response = self._request("GET", "/inventory_levels.json", params=params)
        levels = response.get("inventory_levels", [])
        
        # Sum across all locations
        return sum(level.get("available", 0) for level in levels)
    
    def analyze_product_velocity(
        self,
        product_id: int,
        days_lookback: int = 30
    ) -> ProductVelocity:
        """
        Analiza velocidad de venta de un producto
        
        🔥 CORE FEATURE - Predice stockouts
        
        Args:
            product_id: ID del producto
            days_lookback: Días hacia atrás para calcular velocity
        
        Returns:
            ProductVelocity con análisis completo
        """
        # Get product info
        product = self.get_product(product_id)
        product_name = product.get("title", "Unknown")
        
        # Get current inventory
        variant = product.get("variants", [{}])[0]
        inventory_item_id = variant.get("inventory_item_id")
        current_inventory = self.get_inventory_level(inventory_item_id) if inventory_item_id else 0
        
        # Get historical orders
        created_at_min = datetime.utcnow() - timedelta(days=days_lookback)
        orders = self.get_orders(
            limit=250,
            status="any",
            created_at_min=created_at_min
        )
        
        # Calculate sales for this product
        daily_sales = self._calculate_daily_sales(orders, product_id, days_lookback)
        
        # Calculate velocity
        if daily_sales:
            units_per_day = statistics.mean(daily_sales)
            total_sales = sum(daily_sales)
            
            # Predict stockout
            if units_per_day > 0:
                days_until_stockout = int(current_inventory / units_per_day)
            else:
                days_until_stockout = None
            
            # Recommended restock (30 days supply)
            recommended_restock = max(0, int(units_per_day * 30 - current_inventory))
            
            # Trend analysis
            if len(daily_sales) >= 7:
                recent_avg = statistics.mean(daily_sales[-7:])
                older_avg = statistics.mean(daily_sales[:7])
                
                if recent_avg > older_avg * 1.2:
                    trend = "increasing"
                elif recent_avg < older_avg * 0.8:
                    trend = "decreasing"
                else:
                    trend = "stable"
            else:
                trend = "unknown"
        
        else:
            units_per_day = 0.0
            total_sales = 0
            days_until_stockout = None
            recommended_restock = 0
            trend = "no_sales"
        
        return ProductVelocity(
            product_id=product_id,
            product_name=product_name,
            current_inventory=current_inventory,
            units_per_day=units_per_day,
            days_until_stockout=days_until_stockout,
            recommended_restock=recommended_restock,
            last_30_days_sales=total_sales,
            trend=trend
        )
    
    def _calculate_daily_sales(
        self,
        orders: List[Dict],
        product_id: int,
        days: int
    ) -> List[float]:
        """
        Calcula ventas diarias de un producto
        
        Returns:
            Lista de ventas por día (length = days)
        """
        # Group sales by day
        sales_by_day: Dict[str, int] = {}
        
        for order in orders:
            # Check if order has this product
            line_items = order.get("line_items", [])
            for item in line_items:
                if item.get("product_id") == product_id:
                    # Extract date
                    created_at = order.get("created_at", "")
                    date_str = created_at.split("T")[0] if created_at else ""
                    
                    if date_str:
                        quantity = item.get("quantity", 0)
                        sales_by_day[date_str] = sales_by_day.get(date_str, 0) + quantity
        
        # Fill missing days with 0
        daily_sales = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days - i)).strftime("%Y-%m-%d")
            daily_sales.append(sales_by_day.get(date, 0))
        
        return daily_sales
    
    def get_top_products(
        self,
        limit: int = 10,
        days_lookback: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get top selling products
        
        Returns:
            Lista de productos ordenados por ventas
        """
        # Get orders
        created_at_min = datetime.utcnow() - timedelta(days=days_lookback)
        orders = self.get_orders(limit=250, created_at_min=created_at_min)
        
        # Count sales by product
        product_sales: Dict[int, Dict[str, Any]] = {}
        
        for order in orders:
            for item in order.get("line_items", []):
                product_id = item.get("product_id")
                if product_id:
                    if product_id not in product_sales:
                        product_sales[product_id] = {
                            "product_id": product_id,
                            "product_name": item.get("name", "Unknown"),
                            "quantity_sold": 0,
                            "revenue": 0.0
                        }
                    
                    product_sales[product_id]["quantity_sold"] += item.get("quantity", 0)
                    product_sales[product_id]["revenue"] += float(item.get("price", 0)) * item.get("quantity", 0)
        
        # Sort by quantity sold
        top_products = sorted(
            product_sales.values(),
            key=lambda x: x["quantity_sold"],
            reverse=True
        )
        
        return top_products[:limit]
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check de la API
        
        Returns:
            Dict con status
        """
        try:
            # Simple request para verificar auth
            self._request("GET", "/shop.json")
            return {
                "status": "healthy",
                "shop_name": self.shop_name,
                "api_version": self.api_version
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# ========================================
# HELPER: Batch analytics
# ========================================
def analyze_all_products(
    client: ShopifyClient,
    product_ids: List[int],
    alert_threshold_days: int = 7
) -> Dict[str, Any]:
    """
    Analiza múltiples productos y detecta stockouts
    
    Usage:
        results = analyze_all_products(
            client,
            product_ids=[123, 456, 789],
            alert_threshold_days=7
        )
        
        for alert in results["alerts"]:
            send_discord_alert(alert["message"])
    """
    results = {
        "total_products": len(product_ids),
        "alerts": [],
        "products": []
    }
    
    for product_id in product_ids:
        try:
            velocity = client.analyze_product_velocity(product_id)
            results["products"].append(velocity)
            
            # Check if alert needed
            if velocity.days_until_stockout and velocity.days_until_stockout <= alert_threshold_days:
                results["alerts"].append({
                    "product_id": product_id,
                    "product_name": velocity.product_name,
                    "days_until_stockout": velocity.days_until_stockout,
                    "current_inventory": velocity.current_inventory,
                    "message": f"⚠️ {velocity.product_name} stockout in {velocity.days_until_stockout} days! "
                               f"Current inventory: {velocity.current_inventory}, "
                               f"Recommended restock: {velocity.recommended_restock}"
                })
        
        except Exception as e:
            results["alerts"].append({
                "product_id": product_id,
                "error": str(e)
            })
    
    return results