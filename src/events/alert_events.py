"""
Alert Events - Eventos de alertas
Todos los eventos relacionados con alertas de inventario
"""
from typing import Optional
from src.utils.event_logger import EventLogger


class AlertEvents:
    """
    Wrapper para eventos de alertas
    Separa lógica de eventos del logger base
    """
    
    def __init__(self, logger: EventLogger):
        self.logger = logger
    
    def inventory_low_sent(
        self,
        alert_id: str,
        severity: str,
        channel: str,
        product_id: int,
        product_sku: str,
        product_name: str,
        current_qty: int,
        threshold: int,
        **kwargs
    ) -> str:
        """
        Evento: alert.inventory_low.sent
        
        Cuándo: Se envió alerta de stock bajo
        
        Args:
            alert_id: ID único de la alerta
            severity: info | warning | critical
            channel: discord | email | slack
            product_id: ID del producto Shopify
            product_sku: SKU del producto
            product_name: Nombre del producto
            current_qty: Cantidad actual stock
            threshold: Threshold configurado
            **kwargs: Campos opcionales (variant_id, price, etc)
        
        Returns:
            event_id generado
        """
        return self.logger.log_event(
            event_name="alert.inventory_low.sent",
            data={
                "alert_id": alert_id,
                "severity": severity,
                "channel": channel,
                "product_id": product_id,
                "product_sku": product_sku,
                "product_name": product_name,
                "current_qty": current_qty,
                "threshold": threshold,
                **kwargs
            }
        )
    
    def inventory_stagnation_sent(
        self,
        alert_id: str,
        severity: str,
        channel: str,
        product_id: int,
        product_sku: str,
        product_name: str,
        days_no_sale: int,
        threshold_days: int,
        **kwargs
    ) -> str:
        """
        Evento: alert.inventory_stagnation.sent
        
        Cuándo: Producto no vendió en X días
        """
        return self.logger.log_event(
            event_name="alert.inventory_stagnation.sent",
            data={
                "alert_id": alert_id,
                "severity": severity,
                "channel": channel,
                "product_id": product_id,
                "product_sku": product_sku,
                "product_name": product_name,
                "days_no_sale": days_no_sale,
                "threshold_days": threshold_days,
                **kwargs
            }
        )
    
    def inventory_low_viewed(
        self,
        alert_id: str,
        channel: str,
        time_since_sent: int,
        user_id: Optional[str] = None,
        reaction_emoji: Optional[str] = None
    ) -> str:
        """
        Evento: alert.inventory_low.viewed
        
        Cuándo: Cliente marcó alerta como vista
        
        Args:
            alert_id: ID de la alerta vista
            channel: discord | email | slack
            time_since_sent: Segundos desde envío
            user_id: ID usuario (Discord/Slack)
            reaction_emoji: Emoji usado (Discord)
        """
        return self.logger.log_event(
            event_name="alert.inventory_low.viewed",
            data={
                "alert_id": alert_id,
                "channel": channel,
                "time_since_sent_seconds": time_since_sent,
                "user_id": user_id,
                "reaction_emoji": reaction_emoji
            }
        )