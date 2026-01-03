"""
Event Logger v3 - Sistema de logging estructurado
VERSIÓN FINAL con estructura profesional

Características:
- Logs separados por cliente en logs/events/
- event_id único (previene duplicados)
- schema_version (migración futura)
- run_id (execution tracking)
- Event names jerárquicos
- UTC siempre
"""
import logging
import json
import time
import os
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Versión del schema
SCHEMA_VERSION = "1.0"

# Configuración de rutas
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Sube 3 niveles: utils -> src -> proyecto
EVENTS_LOG_DIR = PROJECT_ROOT / "logs" / "events"
EVENTS_LOG_DIR.mkdir(parents=True, exist_ok=True)

class EventLogger:
    """
    Logger de eventos estructurado JSON
    
    Logs se guardan en: logs/events/{client_id}.log
    Formato: JSON estructurado con schema versionado
    """
    
    def __init__(self, client_id: str):
        """
        Inicializa logger para un cliente específico
        
        Args:
            client_id: Identificador del cliente (ej: "chaparrita", "connie-dev-studio")
        """
        self.client_id = client_id
        self.run_id = self._generate_run_id()
        self.log_file = EVENTS_LOG_DIR / f"{client_id}.log"
        
        self._setup_logger()
    
    def _generate_run_id(self) -> str:
        """Genera run_id único para esta ejecución"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _generate_event_id(self) -> str:
        """
        Genera event_id único
        Formato: evt_{timestamp_ms}_{hash}
        """
        timestamp_ms = int(time.time() * 1000)
        random_bytes = os.urandom(4)
        random_hash = hashlib.sha256(random_bytes).hexdigest()[:8]
        return f"evt_{timestamp_ms}_{random_hash}"
    
    def _setup_logger(self):
        """
        Configura logger JSON
        ✅ Evita duplicar handlers
        ✅ Logs en logs/events/{client_id}.log
        """
        logger_name = f"events.{self.client_id}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # ✅ CRÍTICO: Verificar handlers existentes
        if not self.logger.handlers:
            from logging.handlers import TimedRotatingFileHandler
            
            handler = TimedRotatingFileHandler(
                filename=str(self.log_file),
                when='midnight',
                interval=1,
                backupCount=30,
                encoding='utf-8'
            )
            
            handler.setFormatter(JSONFormatter(self.client_id))
            self.logger.addHandler(handler)
            
            # Evitar propagación al root logger
            self.logger.propagate = False
    
    def log_event(
        self,
        event_name: str,
        data: Dict[str, Any],
        level: str = "INFO"
    ) -> str:
        """
        Log evento estructurado
        
        Args:
            event_name: Nombre jerárquico (alert.inventory_low.sent)
            data: Datos del evento
            level: Nivel log (INFO, WARNING, ERROR)
        
        Returns:
            event_id generado
        """
        # Generar event_id único
        event_id = self._generate_event_id()
        
        # Payload completo
        payload = {
            "event_id": event_id,
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",  # ✅ UTC
            "client_id": self.client_id,
            "run_id": self.run_id,
            "event_name": event_name,
            "data": data
        }
        
        # Log según nivel
        log_func = getattr(self.logger, level.lower())
        log_func(
            event_name,
            extra={"event_payload": payload, "client_id": self.client_id}
        )
        
        return event_id
    
    # ========================================
    # EVENTOS ESPECÍFICOS - Wrappers
    # ========================================
    # Los métodos específicos los importamos desde src/events/
    # Aquí solo dejamos el método genérico log_event


class JSONFormatter(logging.Formatter):
    """
    Formatter JSON para logs
    Convierte LogRecord a JSON estructurado
    """
    
    def __init__(self, client_id: str):
        super().__init__()
        self.client_id = client_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Convierte log a JSON"""
        
        # Payload del evento (si existe)
        if hasattr(record, 'event_payload'):
            return json.dumps(record.event_payload, ensure_ascii=False)
        
        # Fallback (logs normales)
        return json.dumps({
            "schema_version": SCHEMA_VERSION,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "client_id": self.client_id,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName
        }, ensure_ascii=False)