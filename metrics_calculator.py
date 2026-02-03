"""
🧮 METRICS CALCULATOR - Módulo de Cálculo de Métricas
================================================================

Módulo centralizado para cálculos de métricas de negocio.
Diseñado para facilitar migración a PostgreSQL - solo cambiar
la capa de acceso a datos.

Funciones principales:
- calculate_roi: ROI de producto
- calculate_velocity: Velocidad de ventas
- calculate_stock_coverage: Cobertura de stock (días)
- calculate_days_to_stockout: Días hasta agotamiento

Author: Claude (Cirujano Maestro)
Version: 1.0.0 - Optimizado pre-migración PostgreSQL
"""

from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculadora de métricas de negocio.

    Diseño modular para facilitar migración:
    - Recibe datos como dict (compatible con SQLite row y Postgres dict)
    - Sin dependencias de database.py
    - Validaciones de entrada robustas
    """

    # Constantes de negocio
    DEFAULT_MARGIN = 0.5  # 50% margen si no hay cost_price
    CRITICAL_STOCK_THRESHOLD = 10
    CRITICAL_DAYS_THRESHOLD = 3.0
    VELOCITY_PERIOD_DAYS = 30
    HIGH_ROI_THRESHOLD = 100.0  # 100% ROI es alto

    @staticmethod
    def calculate_roi(price: float, cost_price: Optional[float] = None) -> float:
        """
        Calcula Return on Investment (ROI).

        Args:
            price: Precio de venta
            cost_price: Costo del producto (opcional)

        Returns:
            float: ROI en porcentaje (0-infinito)

        Formula: ((precio - costo) / costo) * 100

        Examples:
            >>> calculate_roi(100, 50)
            100.0  # 100% ROI
            >>> calculate_roi(150, 50)
            200.0  # 200% ROI
        """
        try:
            # Validaciones
            if price < 0:
                logger.warning(f"Precio negativo: {price}, usando 0")
                price = 0

            # Si no hay cost_price, usar margen por defecto
            if cost_price is None or cost_price <= 0:
                cost_price = price * MetricsCalculator.DEFAULT_MARGIN

            # Evitar división por cero
            if cost_price == 0:
                return 0.0

            roi = ((price - cost_price) / cost_price) * 100

            # ROI no puede ser menor que -100% (pérdida total)
            return max(-100.0, roi)

        except (TypeError, ValueError) as e:
            logger.error(f"Error calculando ROI: {e}")
            return 0.0

    @staticmethod
    def calculate_velocity(
        total_sales_period: float,
        period_days: int = VELOCITY_PERIOD_DAYS
    ) -> float:
        """
        Calcula velocidad de ventas diaria.

        Args:
            total_sales_period: Ventas totales en el período
            period_days: Días del período (default 30)

        Returns:
            float: Unidades vendidas por día

        Examples:
            >>> calculate_velocity(30, 30)
            1.0  # 1 unidad/día
            >>> calculate_velocity(60, 30)
            2.0  # 2 unidades/día
        """
        try:
            if period_days <= 0:
                logger.warning(f"Período inválido: {period_days}, usando 30")
                period_days = 30

            if total_sales_period < 0:
                logger.warning(f"Ventas negativas: {total_sales_period}, usando 0")
                total_sales_period = 0

            return round(total_sales_period / period_days, 4)

        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculando velocity: {e}")
            return 0.0

    @staticmethod
    def calculate_days_to_stockout(
        current_stock: int,
        velocity_daily: float
    ) -> Optional[float]:
        """
        Calcula días hasta agotamiento de stock.

        Args:
            current_stock: Stock actual
            velocity_daily: Velocidad de ventas diaria

        Returns:
            float: Días hasta stockout, o None si velocity es 0

        Examples:
            >>> calculate_days_to_stockout(10, 2.0)
            5.0  # Se agota en 5 días
            >>> calculate_days_to_stockout(10, 0)
            None  # Sin ventas, no se calcula
        """
        try:
            if current_stock < 0:
                logger.warning(f"Stock negativo: {current_stock}, usando 0")
                current_stock = 0

            if velocity_daily <= 0:
                return None  # Sin ventas, no hay predicción

            days = current_stock / velocity_daily
            return round(days, 1)

        except (TypeError, ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculando days to stockout: {e}")
            return None

    @staticmethod
    def calculate_stock_coverage(
        current_stock: int,
        velocity_daily: float,
        safety_margin_days: float = 3.0
    ) -> Dict[str, any]:
        """
        Calcula cobertura de stock (Escudo).

        Args:
            current_stock: Stock actual
            velocity_daily: Velocidad de ventas diaria
            safety_margin_days: Margen de seguridad en días

        Returns:
            dict: {
                'days_coverage': float,
                'status': str ('OK', 'WARNING', 'CRITICAL'),
                'needs_reorder': bool,
                'recommended_reorder': int
            }
        """
        try:
            days_to_stockout = MetricsCalculator.calculate_days_to_stockout(
                current_stock, velocity_daily
            )

            if days_to_stockout is None:
                # Sin ventas recientes
                return {
                    'days_coverage': None,
                    'status': 'OK',
                    'needs_reorder': False,
                    'recommended_reorder': 0
                }

            # Determinar status
            if days_to_stockout >= safety_margin_days * 2:
                status = 'OK'
                needs_reorder = False
            elif days_to_stockout >= safety_margin_days:
                status = 'WARNING'
                needs_reorder = True
            else:
                status = 'CRITICAL'
                needs_reorder = True

            # Calcular reorden recomendado (velocity * safety_margin + current_stock)
            recommended_reorder = 0
            if needs_reorder and velocity_daily > 0:
                target_stock = velocity_daily * (safety_margin_days * 2)  # 2x margen
                recommended_reorder = max(0, int(target_stock - current_stock))

            return {
                'days_coverage': days_to_stockout,
                'status': status,
                'needs_reorder': needs_reorder,
                'recommended_reorder': recommended_reorder
            }

        except Exception as e:
            logger.error(f"Error calculando stock coverage: {e}")
            return {
                'days_coverage': None,
                'status': 'ERROR',
                'needs_reorder': False,
                'recommended_reorder': 0
            }

    @staticmethod
    def update_product_metrics(
        product_data: Dict,
        quantity_sold: int,
        sale_price: float
    ) -> Dict:
        """
        Actualiza métricas de producto después de una venta.

        Esta función es el PUNTO CRÍTICO de migración a PostgreSQL.
        Recibe un dict (compatible con row SQLite y dict Postgres).

        Args:
            product_data: Dict con datos del producto
            quantity_sold: Cantidad vendida
            sale_price: Precio de venta

        Returns:
            dict: Métricas actualizadas {
                'old_stock': int,
                'new_stock': int,
                'old_sales_30d': int,
                'new_sales_30d': int,
                'new_velocity': float,
                'roi': float,
                'stock_coverage': dict
            }
        """
        try:
            # Extraer datos actuales (compatible SQLite row y dict)
            old_stock = product_data.get('stock', 0) if isinstance(product_data, dict) else product_data['stock']
            old_sales_30d = product_data.get('total_sales_30d', 0) if isinstance(product_data, dict) else product_data['total_sales_30d']
            cost_price = product_data.get('cost_price') if isinstance(product_data, dict) else product_data['cost_price']

            # Calcular nuevos valores
            new_stock = max(0, old_stock - quantity_sold)
            new_sales_30d = old_sales_30d + quantity_sold
            new_velocity = MetricsCalculator.calculate_velocity(new_sales_30d)
            roi = MetricsCalculator.calculate_roi(sale_price, cost_price)
            stock_coverage = MetricsCalculator.calculate_stock_coverage(
                new_stock, new_velocity
            )

            return {
                'old_stock': old_stock,
                'new_stock': new_stock,
                'old_sales_30d': old_sales_30d,
                'new_sales_30d': new_sales_30d,
                'new_velocity': new_velocity,
                'roi': roi,
                'stock_coverage': stock_coverage
            }

        except Exception as e:
            logger.error(f"Error actualizando métricas producto: {e}")
            # Retornar valores seguros
            return {
                'old_stock': 0,
                'new_stock': 0,
                'old_sales_30d': 0,
                'new_sales_30d': 0,
                'new_velocity': 0.0,
                'roi': 0.0,
                'stock_coverage': {
                    'days_coverage': None,
                    'status': 'ERROR',
                    'needs_reorder': False,
                    'recommended_reorder': 0
                }
            }

    @staticmethod
    def is_high_roi_sale(roi: float) -> bool:
        """Determina si una venta es de alto ROI."""
        return roi >= MetricsCalculator.HIGH_ROI_THRESHOLD

    @staticmethod
    def is_critical_stock(
        stock: int,
        velocity: float,
        threshold_days: float = CRITICAL_DAYS_THRESHOLD
    ) -> bool:
        """Determina si el stock está en nivel crítico."""
        if stock <= 0:
            return True

        if stock > MetricsCalculator.CRITICAL_STOCK_THRESHOLD:
            return False

        days_to_stockout = MetricsCalculator.calculate_days_to_stockout(stock, velocity)

        if days_to_stockout is None:
            return False

        return days_to_stockout < threshold_days


# ============================================================
# COMPATIBILIDAD: Funciones helper standalone
# ============================================================

def calculate_roi(price: float, cost_price: Optional[float] = None) -> float:
    """Wrapper standalone para compatibilidad."""
    return MetricsCalculator.calculate_roi(price, cost_price)


def calculate_velocity(total_sales_period: float, period_days: int = 30) -> float:
    """Wrapper standalone para compatibilidad."""
    return MetricsCalculator.calculate_velocity(total_sales_period, period_days)


def calculate_days_to_stockout(current_stock: int, velocity_daily: float) -> Optional[float]:
    """Wrapper standalone para compatibilidad."""
    return MetricsCalculator.calculate_days_to_stockout(current_stock, velocity_daily)
