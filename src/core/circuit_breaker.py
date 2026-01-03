"""
Circuit Breaker - Protección contra Cascading Failures
🔥 "SISTEMAS QUE VIVEN" - Sistemas que SE RECUPERAN

PROBLEMA RESUELTO:
- ❌ ANTES: Si Discord falla → Retry infinito → Sistema muerto
- ✅ AHORA: Circuit abre → Fail fast → Auto-recovery

STATES:
┌─────────┐  failures   ┌──────┐  timeout  ┌───────────┐
│ CLOSED  │ ──────────> │ OPEN │ ────────> │ HALF_OPEN │
│ (normal)│             │(fail)│           │ (testing) │
└─────────┘             └──────┘           └───────────┘
     ^                                            │
     │                  success                   │
     └────────────────────────────────────────────┘

FEATURES:
- ✅ Auto-recovery (test después de timeout)
- ✅ Fail fast (no retry en OPEN)
- ✅ Métricas por servicio (Discord, Email, Sheets)
- ✅ Graceful degradation
- ✅ Decorator simple (@circuit)

MIGRATION:
# ANTES (sin protección):
def send_discord_alert(...):
    response = requests.post(webhook_url, ...)
    # Si falla, retry infinito ❌

# DESPUÉS (con circuit breaker):
@circuit(failure_threshold=5, name="discord")
def send_discord_alert(...):
    response = requests.post(webhook_url, ...)
    # Si falla 5 veces, abre circuit ✅
"""
from pybreaker import CircuitBreaker, CircuitBreakerError
from functools import wraps
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time
import threading

# ========================================
# SIMPLE CIRCUIT BREAKER (con fallback support)
# ========================================
class SimpleCircuitBreaker:
    """
    Circuit breaker simple que SÍ soporta fallbacks correctamente
    
    States: CLOSED → OPEN → HALF_OPEN
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
        
        self._lock = threading.Lock()
    
    @property
    def current_state(self) -> str:
        """Get estado actual (con auto-recovery check)"""
        with self._lock:
            if self.state == "open":
                # Check si debe pasar a HALF_OPEN
                if self.last_failure_time:
                    elapsed = time.time() - self.last_failure_time
                    if elapsed >= self.recovery_timeout:
                        self.state = "half_open"
                        return "half_open"
            
            return self.state
    
    def call(self, func: Callable, *args, **kwargs):
        """Ejecuta función con circuit protection"""
        state = self.current_state
        
        with self._lock:
            if state == "open":
                raise CircuitBreakerError(self)
            
            # CLOSED o HALF_OPEN → try
            try:
                result = func(*args, **kwargs)
                
                # Success
                if state == "half_open":
                    # Recovery exitoso
                    self.failure_count = 0
                    self.state = "closed"
                
                return result
            
            except Exception as e:
                # Failure
                self.failure_count += 1
                self.last_failure_time = time.time()
                
                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                
                raise  # Re-raise original exception
    
    def reset(self):
        """Reset circuit (force CLOSED)"""
        with self._lock:
            self.failure_count = 0
            self.state = "closed"
            self.last_failure_time = None

# ========================================
# CIRCUIT BREAKER CONFIGS
# ========================================
@dataclass
class CircuitConfig:
    """Configuración de circuit breaker"""
    failure_threshold: int = 5  # Failures antes de abrir
    recovery_timeout: int = 60  # Seconds antes de HALF_OPEN
    expected_exception: type = Exception  # Qué exceptions contar
    name: str = "default"


# ========================================
# REGISTRY DE CIRCUIT BREAKERS
# ========================================
_circuit_breakers: Dict[str, CircuitBreaker] = {}

def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception
) -> SimpleCircuitBreaker:  # ← Cambiado a SimpleCircuitBreaker
    """
    Get o crea circuit breaker (usando SimpleCircuitBreaker)
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = SimpleCircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    return _circuit_breakers[name]

# ========================================
# DECORATOR PATTERN
# ========================================
def circuit(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    name: str = None,
    fallback: Optional[Callable] = None
):
    """
    Decorator para proteger funciones con circuit breaker
    
    🔥 AHORA SÍ FUNCIONA con fallbacks
    """
    def decorator(func):
        circuit_name = name or f"{func.__module__}.{func.__name__}"
        breaker = get_circuit_breaker(
            name=circuit_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return breaker.call(func, *args, **kwargs)
            except (CircuitBreakerError, Exception) as e:
                # CUALQUIER error → fallback si existe
                if fallback:
                    return fallback(*args, **kwargs)
                else:
                    raise
        
        wrapper._circuit_breaker = breaker
        return wrapper
    
    return decorator

# ========================================
# METRICS
# ========================================
@dataclass
class CircuitMetrics:
    """Métricas de un circuit breaker"""
    name: str
    state: str  # CLOSED, OPEN, HALF_OPEN
    fail_counter: int
    failure_threshold: int
    last_failure_time: Optional[datetime] = None
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    uptime_percentage: float = 0.0

def get_circuit_metrics(name: str) -> Optional[CircuitMetrics]:
    """
    Retorna métricas de un circuit
    
    Returns:
        CircuitMetrics o None si no existe
    """
    breaker = _circuit_breakers.get(name)
    if not breaker:
        return None
    
    # SimpleCircuitBreaker usa failure_count, no fail_counter
    total_failures = breaker.failure_count
    total_successes = 0  # SimpleCircuitBreaker no trackea esto
    total_calls = total_failures  # Aproximación
    
    # Uptime percentage (aproximado)
    uptime = 0.0 if total_calls == 0 else ((total_calls - total_failures) / total_calls * 100)
    
    # Last failure time
    last_failure = None
    if hasattr(breaker, 'last_failure_time') and breaker.last_failure_time:
        last_failure = datetime.fromtimestamp(breaker.last_failure_time)
    
    return CircuitMetrics(
        name=breaker.name,
        state=breaker.state,  # SimpleCircuitBreaker usa 'state', no 'current_state'
        fail_counter=total_failures,
        failure_threshold=breaker.failure_threshold,
        last_failure_time=last_failure,
        total_calls=total_calls,
        total_failures=total_failures,
        total_successes=total_successes,
        uptime_percentage=uptime
    )
def get_all_circuit_metrics() -> Dict[str, CircuitMetrics]:
    """
    Retorna métricas de TODOS los circuits
    
    Returns:
        Dict[name, CircuitMetrics]
    """
    return {
        name: get_circuit_metrics(name)
        for name in _circuit_breakers.keys()
    }


def reset_circuit(name: str) -> bool:
    """
    Reset circuit breaker (force CLOSED)
    
    ⚠️ USE WITH CAUTION - Solo para testing/debugging
    
    Returns:
        True si reseteó exitosamente
    """
    breaker = _circuit_breakers.get(name)
    if breaker:
        breaker.close()
        return True
    return False


def reset_all_circuits():
    """Reset ALL circuits (testing/debugging)"""
    for breaker in _circuit_breakers.values():
        breaker.close()


# ========================================
# HEALTH CHECK
# ========================================
def get_system_health() -> Dict[str, Any]:
    """
    Health check de TODOS los circuits
    
    Returns:
        Dict con:
        - overall_health: healthy/degraded/down
        - circuits: Lista de métricas
        - degraded_services: Servicios con problemas
    """
    metrics = get_all_circuit_metrics()
    
    if not metrics:
        return {
            "overall_health": "unknown",
            "circuits": [],
            "degraded_services": []
        }
    
    # Analizar states
    open_circuits = [m for m in metrics.values() if m.state == "open"]
    half_open_circuits = [m for m in metrics.values() if m.state == "half_open"]
    
    # Overall health
    if len(open_circuits) == len(metrics):
        overall = "down"
    elif open_circuits or half_open_circuits:
        overall = "degraded"
    else:
        overall = "healthy"
    
    # Degraded services
    degraded = [m.name for m in open_circuits + half_open_circuits]
    
    return {
        "overall_health": overall,
        "total_circuits": len(metrics),
        "healthy_circuits": len(metrics) - len(open_circuits) - len(half_open_circuits),
        "degraded_circuits": len(half_open_circuits),
        "failed_circuits": len(open_circuits),
        "circuits": {name: {
            "state": m.state,
            "uptime": f"{m.uptime_percentage:.1f}%",
            "failures": m.total_failures,
            "successes": m.total_successes
        } for name, m in metrics.items()},
        "degraded_services": degraded
    }


# ========================================
# GRACEFUL DEGRADATION HELPERS
# ========================================
class ServiceUnavailable(Exception):
    """Exception cuando servicio no está disponible (circuit OPEN)"""
    pass


def try_with_fallback(
    primary_func: Callable,
    fallback_func: Callable,
    *args,
    **kwargs
):
    """
    Try primary, si falla (circuit open), usa fallback
    
    Usage:
        def send_discord(msg):
            ...
        
        def send_email(msg):
            ...
        
        # Try Discord, fallback to Email
        try_with_fallback(send_discord, send_email, message="Alert!")
    """
    try:
        return primary_func(*args, **kwargs)
    except (CircuitBreakerError, ServiceUnavailable):
        return fallback_func(*args, **kwargs)


# ========================================
# EJEMPLO DE USO
# ========================================
"""
EJEMPLO 1: Decorator básico
----------------------------
from src.core.circuit_breaker import circuit
import requests

@circuit(failure_threshold=5, name="discord")
def send_discord_alert(message):
    response = requests.post(
        "https://discord.com/api/webhooks/...",
        json={"content": message}
    )
    response.raise_for_status()
    return response

# Si falla 5 veces, circuit abre
# Próximas llamadas fallan fast (no retry)


EJEMPLO 2: Con fallback
------------------------
def email_fallback(message):
    send_email_alert(message)

@circuit(name="discord", fallback=email_fallback)
def send_discord_alert(message):
    ...

# Si Discord está down, automáticamente usa Email


EJEMPLO 3: Métricas
--------------------
from src.core.circuit_breaker import get_system_health

health = get_system_health()
print(f"System health: {health['overall_health']}")
print(f"Degraded services: {health['degraded_services']}")


EJEMPLO 4: Manual circuit check
--------------------------------
from src.core.circuit_breaker import get_circuit_breaker

breaker = get_circuit_breaker("discord")

if breaker.current_state == "open":
    print("Discord circuit is OPEN, using fallback")
    send_email_alert(message)
else:
    send_discord_alert(message)


EJEMPLO 5: Try con fallback chain
----------------------------------
from src.core.circuit_breaker import try_with_fallback

def send_alert(message):
    # Try Discord → Email → Sheets (cascade)
    try_with_fallback(
        lambda: send_discord_alert(message),
        lambda: try_with_fallback(
            lambda: send_email_alert(message),
            lambda: send_to_google_sheets(message)
        )
    )
"""


# ========================================
# TESTING HELPERS
# ========================================
def simulate_failures(circuit_name: str, count: int):
    """
    Simula failures para testing
    
    ⚠️ SOLO PARA TESTING
    
    Usage:
        simulate_failures("discord", 5)
        # Circuit should be OPEN now
    """
    breaker = get_circuit_breaker(circuit_name)
    
    for _ in range(count):
        try:
            breaker.call(lambda: (_ for _ in ()).throw(Exception("Simulated failure")))
        except Exception:
            pass


def get_circuit_state(name: str) -> str:
    """
    Get estado actual del circuit
    
    Returns:
        "closed", "open", "half_open", o "unknown"
    """
    breaker = _circuit_breakers.get(name)
    return breaker.current_state if breaker else "unknown"