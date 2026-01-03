"""
Health Monitor - System Health Scoring
🔥 "SISTEMAS QUE VIVEN" - Sistemas que se MONITOREAN

FEATURES:
- ✅ Health score 0-100% (overall system)
- ✅ Component-level health (Redis, circuits, memory)
- ✅ Automatic degradation detection
- ✅ Alert triggers
- ✅ Trend analysis

SCORING:
- 90-100%: Healthy ✅
- 70-89%:  Degraded ⚠️
- 0-69%:   Critical 🔴

COMPONENTS:
- Circuit breakers (estado + uptime)
- Memory (usage + leak detection)
- Redis (connectivity + performance)
- Resource manager (leaks)
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class HealthStatus(Enum):
    """Estados de health"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health de un componente individual"""
    name: str
    status: HealthStatus
    score: float  # 0-100
    message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.utcnow)


class HealthMonitor:
    """
    Monitor de health del sistema completo
    
    Integra:
    - Circuit breakers
    - Memory monitor
    - Redis manager
    - Resource registry
    
    Usage:
        monitor = HealthMonitor()
        
        # Register components
        monitor.register_circuit_breakers(circuit_manager)
        monitor.register_memory_monitor(memory_monitor)
        monitor.register_redis(redis_manager)
        
        # Check health
        health = monitor.check_health()
        print(f"Overall: {health['overall_score']:.1f}%")
        
        if health['status'] == 'critical':
            send_alert("System health critical!")
    """
    
    def __init__(self):
        self.components: Dict[str, ComponentHealth] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100
        
        # Thresholds
        self.healthy_threshold = 90
        self.degraded_threshold = 70
    
    def check_health(self) -> Dict[str, Any]:
        """
        Check health de TODOS los componentes
        
        Returns:
            Dict con overall_score, status, components
        """
        # Check cada componente registrado
        for name in list(self.components.keys()):
            self._check_component(name)
        
        # Calculate overall score
        if not self.components:
            overall_score = 100.0
            status = HealthStatus.UNKNOWN
        else:
            scores = [c.score for c in self.components.values()]
            overall_score = sum(scores) / len(scores)
            
            # Determine status
            if overall_score >= self.healthy_threshold:
                status = HealthStatus.HEALTHY
            elif overall_score >= self.degraded_threshold:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.CRITICAL
        
        # Build result
        result = {
            "overall_score": overall_score,
            "status": status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {
                name: {
                    "score": c.score,
                    "status": c.status.value,
                    "message": c.message,
                    "metrics": c.metrics
                }
                for name, c in self.components.items()
            }
        }
        
        # Add to history
        self.history.append(result)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        
        return result
    
    def _check_component(self, name: str):
        """Check health de un componente específico"""
        component = self.components[name]
        
        # Cada tipo de componente tiene su check
        if name == "circuit_breakers":
            self._check_circuit_breakers()
        elif name == "memory":
            self._check_memory()
        elif name == "redis":
            self._check_redis()
        elif name == "resources":
            self._check_resources()
    
    def register_circuit_breakers(self, get_metrics_func):
        """
        Registra circuit breakers para monitoring
        
        Args:
            get_metrics_func: Función que retorna metrics de circuits
                              (ej: circuit_breaker.get_all_circuit_metrics)
        """
        self.components["circuit_breakers"] = ComponentHealth(
            name="circuit_breakers",
            status=HealthStatus.UNKNOWN,
            score=100.0
        )
        self._get_circuit_metrics = get_metrics_func
    
    def _check_circuit_breakers(self):
        """Check health de circuit breakers"""
        try:
            metrics = self._get_circuit_metrics()
            
            if not metrics:
                # No circuits = healthy
                self.components["circuit_breakers"].score = 100.0
                self.components["circuit_breakers"].status = HealthStatus.HEALTHY
                self.components["circuit_breakers"].message = "No circuits registered"
                return
            
            # Analizar circuits
            total = len(metrics)
            open_circuits = sum(1 for m in metrics.values() if m.state == "open")
            half_open = sum(1 for m in metrics.values() if m.state == "half_open")
            
            # Scoring
            if open_circuits == 0:
                score = 100.0
                status = HealthStatus.HEALTHY
                message = f"{total} circuits healthy"
            elif open_circuits == total:
                score = 0.0
                status = HealthStatus.CRITICAL
                message = f"All {total} circuits OPEN"
            else:
                # Partial degradation
                healthy_pct = (total - open_circuits - half_open) / total * 100
                score = healthy_pct
                status = HealthStatus.DEGRADED
                message = f"{open_circuits}/{total} circuits OPEN"
            
            self.components["circuit_breakers"].score = score
            self.components["circuit_breakers"].status = status
            self.components["circuit_breakers"].message = message
            self.components["circuit_breakers"].metrics = {
                "total": total,
                "open": open_circuits,
                "half_open": half_open,
                "closed": total - open_circuits - half_open
            }
        
        except Exception as e:
            self.components["circuit_breakers"].score = 50.0
            self.components["circuit_breakers"].status = HealthStatus.DEGRADED
            self.components["circuit_breakers"].message = f"Error checking: {e}"
    
    def register_memory_monitor(self, get_trend_func):
        """
        Registra memory monitor
        
        Args:
            get_trend_func: Función que retorna memory trend
                           (ej: resource_manager.get_memory_trend)
        """
        self.components["memory"] = ComponentHealth(
            name="memory",
            status=HealthStatus.UNKNOWN,
            score=100.0
        )
        self._get_memory_trend = get_trend_func
    
    def _check_memory(self):
        """Check health de memoria"""
        try:
            trend = self._get_memory_trend()
            
            if trend["trend"] == "unknown":
                self.components["memory"].score = 100.0
                self.components["memory"].status = HealthStatus.HEALTHY
                self.components["memory"].message = "Memory monitoring starting"
                return
            
            # Scoring basado en trend
            if trend["trend"] == "stable":
                score = 100.0
                status = HealthStatus.HEALTHY
                message = f"Memory stable at {trend['current_mb']:.1f}MB"
            elif trend["trend"] == "growing":
                score = 75.0
                status = HealthStatus.DEGRADED
                message = f"Memory growing: +{trend['growth_mb']:.1f}MB"
            else:  # leaking
                score = 30.0
                status = HealthStatus.CRITICAL
                message = f"Memory leak detected: +{trend['growth_mb']:.1f}MB"
            
            self.components["memory"].score = score
            self.components["memory"].status = status
            self.components["memory"].message = message
            self.components["memory"].metrics = trend
        
        except Exception as e:
            self.components["memory"].score = 50.0
            self.components["memory"].status = HealthStatus.DEGRADED
            self.components["memory"].message = f"Error checking: {e}"
    
    def register_redis(self, get_metrics_func):
        """
        Registra Redis manager
        
        Args:
            get_metrics_func: Función que retorna Redis metrics
                             (ej: redis_manager.get_metrics)
        """
        self.components["redis"] = ComponentHealth(
            name="redis",
            status=HealthStatus.UNKNOWN,
            score=100.0
        )
        self._get_redis_metrics = get_metrics_func
    
    def _check_redis(self):
        """Check health de Redis"""
        try:
            metrics = self._get_redis_metrics()
            
            # Check health status
            if metrics["health_status"] == "healthy":
                score = 100.0
                status = HealthStatus.HEALTHY
                message = "Redis healthy"
            elif "error" in metrics["health_status"]:
                score = 0.0
                status = HealthStatus.CRITICAL
                message = f"Redis error: {metrics['health_status']}"
            else:
                score = 50.0
                status = HealthStatus.DEGRADED
                message = f"Redis unhealthy: {metrics['health_status']}"
            
            self.components["redis"].score = score
            self.components["redis"].status = status
            self.components["redis"].message = message
            self.components["redis"].metrics = metrics
        
        except Exception as e:
            self.components["redis"].score = 0.0
            self.components["redis"].status = HealthStatus.CRITICAL
            self.components["redis"].message = f"Error checking: {e}"
    
    def register_resource_manager(self, get_stats_func):
        """
        Registra resource manager
        
        Args:
            get_stats_func: Función que retorna resource stats
                           (ej: resource_manager.get_resource_stats)
        """
        self.components["resources"] = ComponentHealth(
            name="resources",
            status=HealthStatus.UNKNOWN,
            score=100.0
        )
        self._get_resource_stats = get_stats_func
    
    def _check_resources(self):
        """Check health de recursos"""
        try:
            stats = self._get_resource_stats()
            
            # Check for leaks
            active = stats["active_resources"]
            
            if active == 0:
                score = 100.0
                status = HealthStatus.HEALTHY
                message = "No resource leaks"
            elif active < 10:
                score = 90.0
                status = HealthStatus.HEALTHY
                message = f"{active} active resources"
            elif active < 50:
                score = 70.0
                status = HealthStatus.DEGRADED
                message = f"{active} active resources (potential leak)"
            else:
                score = 30.0
                status = HealthStatus.CRITICAL
                message = f"{active} active resources (LEAK DETECTED)"
            
            self.components["resources"].score = score
            self.components["resources"].status = status
            self.components["resources"].message = message
            self.components["resources"].metrics = stats
        
        except Exception as e:
            self.components["resources"].score = 50.0
            self.components["resources"].status = HealthStatus.DEGRADED
            self.components["resources"].message = f"Error checking: {e}"
    
    def get_trend(self, window: int = 10) -> Dict[str, Any]:
        """
        Analiza tendencia de health
        
        Args:
            window: Número de checks a analizar
        
        Returns:
            Dict con trend info
        """
        if len(self.history) < 2:
            return {"trend": "unknown", "message": "Insufficient data"}
        
        # Get last N checks
        recent = self.history[-window:]
        scores = [h["overall_score"] for h in recent]
        
        # Calculate trend
        first_score = scores[0]
        last_score = scores[-1]
        delta = last_score - first_score
        
        if abs(delta) < 5:
            trend = "stable"
        elif delta > 0:
            trend = "improving"
        else:
            trend = "degrading"
        
        return {
            "trend": trend,
            "delta": delta,
            "first_score": first_score,
            "last_score": last_score,
            "avg_score": sum(scores) / len(scores),
            "window_size": len(recent)
        }
    
    def should_alert(self) -> bool:
        """
        Determina si debe enviar alerta
        
        Returns:
            True si health es crítico o degradando
        """
        if not self.history:
            return False
        
        latest = self.history[-1]
        
        # Alert si crítico
        if latest["status"] == "critical":
            return True
        
        # Alert si degradando
        trend = self.get_trend()
        if trend["trend"] == "degrading" and latest["overall_score"] < 80:
            return True
        
        return False