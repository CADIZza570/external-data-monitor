"""
Grafana Exporter - Metrics Export para Dashboards
🔥 "SISTEMAS QUE VIVEN" - Métricas que se VEN

FEATURES:
- ✅ Prometheus metrics export
- ✅ HTTP endpoint (/metrics)
- ✅ Custom metrics de TODO el sistema
- ✅ Grafana dashboard ready
- ✅ Real-time monitoring

METRICS EXPORTED:
- System health score
- Circuit breaker states
- Memory usage & trends
- Redis performance
- Webhook throughput
- Alert counts

USAGE:
    from src.observability.grafana_exporter import MetricsExporter
    
    exporter = MetricsExporter(port=9090)
    
    # Register components
    exporter.register_health_monitor(health_monitor)
    exporter.register_async_processor(async_processor)
    
    # Start HTTP server
    exporter.start()
    
    # Metrics available at: http://localhost:9090/metrics
"""
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    start_http_server,
    REGISTRY
)
from typing import Dict, Any, Optional, Callable
import time
from datetime import datetime


class MetricsExporter:
    """
    Exportador de métricas para Grafana/Prometheus
    
    🚀 FEATURES:
    - HTTP endpoint (/metrics)
    - Auto-update de métricas
    - Custom metrics
    - Dashboard ready
    
    Usage:
        exporter = MetricsExporter(port=9090)
        exporter.register_health_monitor(health_monitor)
        exporter.start()
        
        # Metrics en: http://localhost:9090/metrics
        # Importar en Grafana como Prometheus datasource
    """
    
    def __init__(self, port: int = 9090, update_interval: int = 10):
        """
        Args:
            port: Puerto HTTP para /metrics endpoint
            update_interval: Intervalo de actualización (seconds)
        """
        self.port = port
        self.update_interval = update_interval
        self.running = False
        
        # Component references
        self._health_monitor = None
        self._async_processor = None
        self._get_circuit_metrics = None
        self._get_memory_stats = None
        self._get_redis_metrics = None
        
        # Prometheus metrics
        self._setup_metrics()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        
        # System Health
        self.health_score = Gauge(
            'system_health_score',
            'Overall system health score (0-100)',
            ['status']
        )
        
        # Circuit Breakers
        self.circuit_state = Gauge(
            'circuit_breaker_state',
            'Circuit breaker state (0=closed, 1=half_open, 2=open)',
            ['circuit_name']
        )
        
        self.circuit_failures = Counter(
            'circuit_breaker_failures_total',
            'Total circuit breaker failures',
            ['circuit_name']
        )
        
        # Memory
        self.memory_usage_mb = Gauge(
            'memory_usage_mb',
            'Memory usage in MB',
            ['type']  # rss, vms
        )
        
        self.memory_trend = Gauge(
            'memory_trend_score',
            'Memory trend score (0=leaking, 1=growing, 2=stable)',
            []
        )
        
        # Redis
        self.redis_hit_rate = Gauge(
            'redis_hit_rate',
            'Redis cache hit rate (0-1)',
            []
        )
        
        self.redis_operations = Counter(
            'redis_operations_total',
            'Total Redis operations',
            ['operation']  # hits, misses, errors
        )
        
        # Async Processor
        self.webhook_throughput = Gauge(
            'webhook_throughput_per_min',
            'Webhook processing throughput (per minute)',
            []
        )
        
        self.webhook_queue_size = Gauge(
            'webhook_queue_size',
            'Current webhook queue size',
            []
        )
        
        self.webhook_processing_time = Histogram(
            'webhook_processing_time_ms',
            'Webhook processing time in milliseconds',
            buckets=(10, 50, 100, 250, 500, 1000, 2500, 5000)
        )
        
        # Alerts
        self.alerts_sent = Counter(
            'alerts_sent_total',
            'Total alerts sent',
            ['channel']  # discord, email, sheets
        )
        
        self.alert_failures = Counter(
            'alert_failures_total',
            'Total alert failures',
            ['channel']
        )
    
    def register_health_monitor(self, health_monitor):
        """Registra health monitor para export"""
        self._health_monitor = health_monitor
    
    def register_async_processor(self, async_processor):
        """Registra async processor para export"""
        self._async_processor = async_processor
    
    def register_circuit_metrics(self, get_metrics_func: Callable):
        """Registra función para obtener circuit metrics"""
        self._get_circuit_metrics = get_metrics_func
    
    def register_memory_stats(self, get_stats_func: Callable):
        """Registra función para obtener memory stats"""
        self._get_memory_stats = get_stats_func
    
    def register_redis_metrics(self, get_metrics_func: Callable):
        """Registra función para obtener Redis metrics"""
        self._get_redis_metrics = get_metrics_func
    
    def update_metrics(self):
        """
        Actualiza TODAS las métricas
        
        🔥 Llamado automáticamente cada update_interval
        """
        # Health Monitor
        if self._health_monitor:
            self._update_health_metrics()
        
        # Circuit Breakers
        if self._get_circuit_metrics:
            self._update_circuit_metrics()
        
        # Memory
        if self._get_memory_stats:
            self._update_memory_metrics()
        
        # Redis
        if self._get_redis_metrics:
            self._update_redis_metrics()
        
        # Async Processor
        if self._async_processor:
            self._update_async_metrics()
    
    def _update_health_metrics(self):
        """Update health metrics"""
        health = self._health_monitor.check_health()
        
        # Overall score
        self.health_score.labels(status=health['status']).set(
            health['overall_score']
        )
    
    def _update_circuit_metrics(self):
        """Update circuit breaker metrics"""
        metrics = self._get_circuit_metrics()
        
        for name, circuit in metrics.items():
            # State (0=closed, 1=half_open, 2=open)
            state_map = {"closed": 0, "half_open": 1, "open": 2}
            self.circuit_state.labels(circuit_name=name).set(
                state_map.get(circuit.state, 0)
            )
            
            # Failures
            self.circuit_failures.labels(circuit_name=name)._value.set(
                circuit.total_failures
            )
    
    def _update_memory_metrics(self):
        """Update memory metrics"""
        stats = self._get_memory_stats()
        
        # Usage
        self.memory_usage_mb.labels(type="rss").set(stats['rss_mb'])
        self.memory_usage_mb.labels(type="vms").set(stats['vms_mb'])
        
        # Trend (si hay get_memory_trend)
        if hasattr(self._get_memory_stats, '__self__'):
            monitor = self._get_memory_stats.__self__
            if hasattr(monitor, 'get_trend'):
                trend = monitor.get_trend()
                trend_map = {"stable": 2, "growing": 1, "leaking": 0}
                self.memory_trend.set(
                    trend_map.get(trend.get('trend', 'stable'), 2)
                )
    
    def _update_redis_metrics(self):
        """Update Redis metrics"""
        metrics = self._get_redis_metrics()
        
        # Hit rate
        self.redis_hit_rate.set(metrics.get('hit_rate', 0))
        
        # Operations
        self.redis_operations.labels(operation="hits")._value.set(
            metrics.get('hits', 0)
        )
        self.redis_operations.labels(operation="misses")._value.set(
            metrics.get('misses', 0)
        )
        self.redis_operations.labels(operation="errors")._value.set(
            metrics.get('errors', 0)
        )
    
    def _update_async_metrics(self):
        """Update async processor metrics"""
        metrics = self._async_processor.get_metrics()
        
        # Throughput
        self.webhook_throughput.set(metrics['throughput_per_min'])
        
        # Queue size
        self.webhook_queue_size.set(metrics['pending_tasks'])
        
        # Processing time (usar avg como observe)
        if metrics['avg_processing_time_ms'] > 0:
            self.webhook_processing_time.observe(
                metrics['avg_processing_time_ms']
            )
    
    def record_alert_sent(self, channel: str):
        """
        Registra alerta enviada
        
        Usage:
            exporter.record_alert_sent("discord")
        """
        self.alerts_sent.labels(channel=channel).inc()
    
    def record_alert_failure(self, channel: str):
        """
        Registra falla de alerta
        
        Usage:
            exporter.record_alert_failure("discord")
        """
        self.alert_failures.labels(channel=channel).inc()
    
    def start(self):
        """
        Inicia HTTP server y auto-update loop
        
        🔥 Metrics disponibles en http://localhost:{port}/metrics
        """
        # Start Prometheus HTTP server
        start_http_server(self.port)
        print(f"[MetricsExporter] HTTP server started on port {self.port}")
        print(f"[MetricsExporter] Metrics endpoint: http://localhost:{self.port}/metrics")
        
        self.running = True
        
        # Auto-update loop (en background)
        import threading
        def update_loop():
            while self.running:
                try:
                    self.update_metrics()
                except Exception as e:
                    print(f"[MetricsExporter] Error updating metrics: {e}")
                
                time.sleep(self.update_interval)
        
        thread = threading.Thread(target=update_loop, daemon=True)
        thread.start()
    
    def stop(self):
        """Stop auto-update loop"""
        self.running = False


# ========================================
# GRAFANA DASHBOARD CONFIG (JSON)
# ========================================
GRAFANA_DASHBOARD_JSON = """
{
  "dashboard": {
    "title": "Sistema Chaparrita - Monitoring",
    "panels": [
      {
        "title": "System Health Score",
        "targets": [
          {
            "expr": "system_health_score"
          }
        ],
        "type": "gauge"
      },
      {
        "title": "Circuit Breaker States",
        "targets": [
          {
            "expr": "circuit_breaker_state"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Memory Usage",
        "targets": [
          {
            "expr": "memory_usage_mb"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Webhook Throughput",
        "targets": [
          {
            "expr": "webhook_throughput_per_min"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Redis Hit Rate",
        "targets": [
          {
            "expr": "redis_hit_rate"
          }
        ],
        "type": "gauge"
      },
      {
        "title": "Alerts Sent",
        "targets": [
          {
            "expr": "rate(alerts_sent_total[5m])"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
"""


def export_grafana_dashboard(filepath: str = "grafana_dashboard.json"):
    """
    Exporta dashboard JSON para Grafana
    
    Usage:
        export_grafana_dashboard("dashboard.json")
        # Importar en Grafana: Dashboards → Import → Upload JSON
    """
    with open(filepath, 'w') as f:
        f.write(GRAFANA_DASHBOARD_JSON)
    
    print(f"✅ Dashboard exported to: {filepath}")
    print("ℹ️  Import in Grafana: Dashboards → Import → Upload JSON")