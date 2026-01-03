"""
System Events - Eventos del sistema
Eventos de health, checks, integraciones
"""
from typing import Dict, List
from src.utils.event_logger import EventLogger


class SystemEvents:
    """
    Wrapper para eventos de sistema
    Observability y health tracking
    """
    
    def __init__(self, logger: EventLogger):
        self.logger = logger
    
    def check_completed(
        self,
        checks_evaluated: List[str],
        alerts_triggered: int,
        alerts_suppressed: int,
        suppression_reasons: Dict[str, str],
        products_checked: int,
        duration_ms: int,
        errors: int = 0
    ) -> str:
        """
        Evento: system.check_completed
        
        Cuándo: Sistema completó run de checks
        
        CRÍTICO: Este evento SIEMPRE debe logearse
        
        Args:
            checks_evaluated: Lista de checks ejecutados
            alerts_triggered: Cantidad alertas enviadas
            alerts_suppressed: Cantidad alertas suprimidas
            suppression_reasons: Dict {product_id: razón}
            products_checked: Cantidad productos evaluados
            duration_ms: Duración en milisegundos
            errors: Cantidad de errores
        """
        return self.logger.log_event(
            event_name="system.check_completed",
            data={
                "checks_evaluated": checks_evaluated,
                "alerts_triggered": alerts_triggered,
                "alerts_suppressed": alerts_suppressed,
                "suppression_reasons": suppression_reasons,
                "products_checked": products_checked,
                "duration_ms": duration_ms,
                "errors": errors
            }
        )