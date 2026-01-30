# ============================================================
# 🚀 ALERT DEDUPLICATION SYSTEM v1.0
# ============================================================
# Sistema profesional anti-duplicados para alertas de Shopify
# 
# CARACTERÍSTICAS:
# - ✅ Cache en memoria (sin Redis para MVP)
# - ✅ TTL configurable por tipo de alerta
# - ✅ Thread-safe para múltiples workers
# - ✅ Cleanup automático de cache viejo
# - ✅ Estadísticas de deduplicación
# - ✅ Listo para upgrade a Redis
# ============================================================

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("alert_dedup")

class AlertDeduplicator:
    """
    Sistema de deduplicación de alertas con TTL.
    
    Evita enviar la misma alerta múltiples veces en un periodo de tiempo.
    
    Ejemplo de uso:
    >>> dedup = AlertDeduplicator(default_ttl_hours=24)
    >>> 
    >>> # Primera vez: envía alerta
    >>> if dedup.should_send_alert("low_stock", product_id=12345):
    >>>     send_discord_alert(...)
    >>>     dedup.mark_sent("low_stock", product_id=12345)
    >>> 
    >>> # Siguiente vez (dentro de 24h): NO envía
    >>> if dedup.should_send_alert("low_stock", product_id=12345):
    >>>     # No entra aquí
    """
    
    def __init__(self, default_ttl_hours: int = 24):
        """
        Args:
            default_ttl_hours: Tiempo en horas antes de permitir re-alertar
        """
        self.default_ttl_hours = default_ttl_hours
        self.cache: Dict[str, float] = {}  # {alert_key: timestamp_expiry}
        self.lock = threading.Lock()  # Thread-safe para Gunicorn workers
        self.stats = {
            "alerts_sent": 0,
            "alerts_deduplicated": 0,
            "last_cleanup": time.time()
        }

        # Solo loguear en modo debug (silenciar spam en producción)
        logger.debug(f"AlertDeduplicator inicializado (TTL: {default_ttl_hours}h)")
    
    def _make_key(self, alert_type: str, **identifiers) -> str:
        """
        Genera clave única para la alerta.
        
        Args:
            alert_type: Tipo de alerta (low_stock, no_sales, etc)
            **identifiers: Identificadores únicos (product_id, sku, etc)
        
        Returns:
            String único que identifica la alerta
        
        Ejemplo:
            _make_key("low_stock", product_id=12345, shop="chaparrita")
            → "low_stock:product_id:12345:shop:chaparrita"
        """
        key_parts = [alert_type]
        for k, v in sorted(identifiers.items()):
            key_parts.extend([k, str(v)])
        return ":".join(key_parts)
    
    def should_send_alert(self, alert_type: str, ttl_hours: Optional[int] = None, 
                         **identifiers) -> bool:
        """
        Verifica si se debe enviar la alerta o si es duplicada.
        
        Args:
            alert_type: Tipo de alerta
            ttl_hours: TTL específico (override del default)
            **identifiers: Identificadores únicos del recurso
        
        Returns:
            True si debe enviar, False si es duplicado
        
        Ejemplo:
            # Stock bajo de producto 12345
            should_send_alert("low_stock", product_id=12345)
            
            # Nueva orden #1002 (TTL corto: 1h)
            should_send_alert("new_order", ttl_hours=1, order_id=1002)
        """
        key = self._make_key(alert_type, **identifiers)
        current_time = time.time()
        
        with self.lock:
            # Cleanup periódico (cada hora)
            self._cleanup_expired(current_time)
            
            # Verificar si existe en cache y no ha expirado
            if key in self.cache:
                expiry_time = self.cache[key]
                
                if current_time < expiry_time:
                    # Alerta duplicada - NO enviar
                    self.stats["alerts_deduplicated"] += 1
                    
                    remaining_seconds = int(expiry_time - current_time)
                    remaining_hours = remaining_seconds / 3600
                    
                    logger.info(
                        f"🔄 Alerta deduplicada: {alert_type} "
                        f"({', '.join(f'{k}={v}' for k, v in identifiers.items())}) "
                        f"- Expira en {remaining_hours:.1f}h"
                    )
                    return False
            
            # Alerta nueva o expirada - SÍ enviar
            return True
    
    def mark_sent(self, alert_type: str, ttl_hours: Optional[int] = None, 
                  **identifiers) -> None:
        """
        Marca una alerta como enviada (guarda en cache).
        
        IMPORTANTE: Llamar DESPUÉS de enviar la alerta exitosamente.
        
        Args:
            alert_type: Tipo de alerta
            ttl_hours: TTL específico (override del default)
            **identifiers: Identificadores únicos del recurso
        
        Ejemplo:
            if should_send_alert("low_stock", product_id=12345):
                send_discord_alert(...)
                mark_sent("low_stock", product_id=12345)  # ← Aquí
        """
        key = self._make_key(alert_type, **identifiers)
        ttl = ttl_hours or self.default_ttl_hours
        expiry_time = time.time() + (ttl * 3600)  # Convertir horas a segundos
        
        with self.lock:
            self.cache[key] = expiry_time
            self.stats["alerts_sent"] += 1
            
            logger.info(
                f"✅ Alerta marcada como enviada: {alert_type} "
                f"({', '.join(f'{k}={v}' for k, v in identifiers.items())}) "
                f"- TTL: {ttl}h"
            )
    
    def _cleanup_expired(self, current_time: float) -> None:
        """
        Limpia alertas expiradas del cache (ejecuta cada hora).
        
        Args:
            current_time: Timestamp actual
        """
        # Solo ejecutar cleanup cada hora
        if current_time - self.stats["last_cleanup"] < 3600:
            return
        
        expired_keys = [
            key for key, expiry in self.cache.items() 
            if current_time >= expiry
        ]
        
        if expired_keys:
            for key in expired_keys:
                del self.cache[key]
            
            logger.info(f"🧹 Cleanup: {len(expired_keys)} alertas expiradas eliminadas")
        
        self.stats["last_cleanup"] = current_time
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de deduplicación.
        
        Returns:
            Dict con stats del sistema
        """
        with self.lock:
            total_alerts = self.stats["alerts_sent"] + self.stats["alerts_deduplicated"]
            dedup_rate = (
                (self.stats["alerts_deduplicated"] / total_alerts * 100)
                if total_alerts > 0 else 0
            )
            
            return {
                "alerts_sent": self.stats["alerts_sent"],
                "alerts_deduplicated": self.stats["alerts_deduplicated"],
                "deduplication_rate_percent": round(dedup_rate, 2),
                "cache_size": len(self.cache),
                "last_cleanup": datetime.fromtimestamp(
                    self.stats["last_cleanup"]
                ).isoformat()
            }
    
    def force_cleanup(self) -> int:
        """
        Fuerza limpieza completa del cache.
        
        Returns:
            Número de alertas eliminadas
        """
        with self.lock:
            count = len(self.cache)
            self.cache.clear()
            logger.info(f"🧹 Cleanup forzado: {count} alertas eliminadas")
            return count
    
    def reset_alert(self, alert_type: str, **identifiers) -> bool:
        """
        Elimina una alerta específica del cache (permite re-enviar).
        
        Útil para testing o manualmente forzar re-envío.
        
        Args:
            alert_type: Tipo de alerta
            **identifiers: Identificadores únicos
        
        Returns:
            True si se encontró y eliminó, False si no existía
        """
        key = self._make_key(alert_type, **identifiers)
        
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                logger.info(f"🔄 Reset manual de alerta: {key}")
                return True
            return False


# ============================================================
# 🎯 CONFIGURACIÓN DE TTLs POR TIPO DE ALERTA
# ============================================================

# TTLs recomendados (horas)
ALERT_TTL_CONFIG = {
    "low_stock": 24,        # 24h - Stock bajo (no spamear)
    "no_sales": 168,        # 7 días - Sin ventas (semanal)
    "missing_data": 72,     # 3 días - Datos faltantes
    "new_order": 0.25,      # 15 min - Nueva orden (corto, puede venir edit)
    "product_created": 1,   # 1h - Producto nuevo
    "product_deleted": 24,  # 24h - Producto eliminado
    "inventory_updated": 6, # 6h - Actualización inventario
}


# ============================================================
# 🚀 INSTANCIA GLOBAL (Singleton)
# ============================================================

# Instancia compartida entre todos los workers
# IMPORTANTE: En producción multi-worker, considera Redis
_global_deduplicator = None

def get_deduplicator() -> AlertDeduplicator:
    """
    Obtiene la instancia global del deduplicator (singleton).

    Returns:
        AlertDeduplicator singleton
    """
    global _global_deduplicator

    if _global_deduplicator is None:
        _global_deduplicator = AlertDeduplicator(default_ttl_hours=24)
        # Solo loguear UNA VEZ cuando se crea el singleton
        logger.info("✅ AlertDeduplicator singleton creado (TTL: 24h)")

    return _global_deduplicator


# ============================================================
# 📝 EJEMPLOS DE USO
# ============================================================

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Crear deduplicator
    dedup = AlertDeduplicator(default_ttl_hours=24)
    
    # Ejemplo 1: Stock bajo
    print("\n=== EJEMPLO 1: Stock Bajo ===")
    
    # Primera alerta - envía
    if dedup.should_send_alert("low_stock", product_id=12345, shop="chaparrita"):
        print("📧 Enviando alerta de stock bajo...")
        dedup.mark_sent("low_stock", product_id=12345, shop="chaparrita")
    
    # Segunda alerta inmediata - NO envía (duplicado)
    if dedup.should_send_alert("low_stock", product_id=12345, shop="chaparrita"):
        print("📧 Enviando alerta de stock bajo...")
    else:
        print("⏭️  Alerta ignorada (duplicado)")
    
    # Ejemplo 2: Nueva orden (TTL corto)
    print("\n=== EJEMPLO 2: Nueva Orden ===")
    
    if dedup.should_send_alert("new_order", ttl_hours=1, order_id=1002):
        print("📧 Enviando notificación de orden...")
        dedup.mark_sent("new_order", ttl_hours=1, order_id=1002)
    
    # Ejemplo 3: Estadísticas
    print("\n=== ESTADÍSTICAS ===")
    stats = dedup.get_stats()
    print(f"Alertas enviadas: {stats['alerts_sent']}")
    print(f"Alertas deduplicadas: {stats['alerts_deduplicated']}")
    print(f"Tasa de deduplicación: {stats['deduplication_rate_percent']}%")
    print(f"Cache size: {stats['cache_size']}")
