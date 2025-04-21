"""
Health Check and Monitoring Module

This module provides functionality for health checks and basic monitoring
of the application. It includes:

1. A health check endpoint that can be used to verify the application is running
2. Basic metrics collection for monitoring application performance
3. Utilities for integrating with monitoring systems

Usage:
    from monitoring.health import HealthCheck, MetricsCollector
    
    # Create a health check instance
    health_check = HealthCheck()
    
    # Register components to check
    health_check.register_check("database", check_database_connection)
    health_check.register_check("redis", check_redis_connection)
    
    # Get health status
    status = await health_check.check_health()
    
    # Create a metrics collector
    metrics = MetricsCollector()
    
    # Record metrics
    metrics.increment("api_requests_total")
    metrics.observe("request_duration_seconds", 0.45)
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Type aliases
HealthCheckFunc = Callable[[], Union[bool, Dict[str, Any], asyncio.Future]]
MetricValue = Union[int, float]


class HealthStatus(Enum):
    """Health status of a component or the entire application."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health information for a single component."""
    name: str
    status: HealthStatus
    details: Optional[Dict[str, Any]] = None
    last_check_time: float = field(default_factory=time.time)
    error: Optional[str] = None


@dataclass
class HealthCheckResult:
    """Result of a health check for the entire application."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the health check result to a dictionary."""
        return {
            "status": self.status.value,
            "components": [
                {
                    "name": component.name,
                    "status": component.status.value,
                    "details": component.details,
                    "last_check_time": component.last_check_time,
                    "error": component.error
                }
                for component in self.components
            ],
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        """Convert the health check result to a JSON string."""
        return json.dumps(self.to_dict())


class HealthCheck:
    """
    Health check manager for the application.
    
    This class manages health checks for various components of the application
    and provides an overall health status.
    """
    
    def __init__(self):
        """Initialize a new HealthCheck instance."""
        self._checks: Dict[str, HealthCheckFunc] = {}
        self._results: Dict[str, ComponentHealth] = {}
        self._last_check_time: float = 0
    
    def register_check(self, name: str, check_func: HealthCheckFunc) -> None:
        """
        Register a health check function for a component.
        
        Args:
            name: Name of the component
            check_func: Function that performs the health check
        """
        self._checks[name] = check_func
        logger.info(f"Registered health check for component: {name}")
    
    async def check_component(self, name: str, check_func: HealthCheckFunc) -> ComponentHealth:
        """
        Check the health of a single component.
        
        Args:
            name: Name of the component
            check_func: Function that performs the health check
            
        Returns:
            Health information for the component
        """
        try:
            # Call the check function
            result = check_func()
            
            # Handle async functions
            if asyncio.iscoroutine(result):
                result = await result
            
            # Process the result
            if isinstance(result, bool):
                # Simple boolean result
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                details = None
            elif isinstance(result, dict):
                # Detailed result with status and details
                status_value = result.get("status", "healthy").lower()
                if status_value == "degraded":
                    status = HealthStatus.DEGRADED
                elif status_value == "unhealthy":
                    status = HealthStatus.UNHEALTHY
                else:
                    status = HealthStatus.HEALTHY
                
                details = result.get("details")
            else:
                # Unexpected result type
                raise ValueError(f"Unexpected health check result type: {type(result)}")
            
            # Create and return component health
            component_health = ComponentHealth(
                name=name,
                status=status,
                details=details,
                last_check_time=time.time()
            )
            
            # Store the result
            self._results[name] = component_health
            return component_health
            
        except Exception as e:
            # Handle errors during health check
            logger.error(f"Health check failed for component {name}: {e}")
            component_health = ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                error=str(e),
                last_check_time=time.time()
            )
            self._results[name] = component_health
            return component_health
    
    async def check_health(self) -> HealthCheckResult:
        """
        Check the health of all registered components.
        
        Returns:
            Overall health check result
        """
        self._last_check_time = time.time()
        components = []
        
        # Check each component
        for name, check_func in self._checks.items():
            component_health = await self.check_component(name, check_func)
            components.append(component_health)
        
        # Determine overall status
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        # Create and return result
        return HealthCheckResult(
            status=status,
            components=components,
            timestamp=self._last_check_time
        )
    
    def get_last_result(self) -> Optional[HealthCheckResult]:
        """
        Get the result of the last health check.
        
        Returns:
            Last health check result, or None if no check has been performed
        """
        if not self._results:
            return None
        
        components = list(self._results.values())
        
        # Determine overall status
        if any(c.status == HealthStatus.UNHEALTHY for c in components):
            status = HealthStatus.UNHEALTHY
        elif any(c.status == HealthStatus.DEGRADED for c in components):
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.HEALTHY
        
        return HealthCheckResult(
            status=status,
            components=components,
            timestamp=self._last_check_time
        )


class MetricsCollector:
    """
    Collector for application metrics.
    
    This class collects and manages metrics for monitoring application performance.
    It supports counters, gauges, and histograms.
    """
    
    def __init__(self):
        """Initialize a new MetricsCollector instance."""
        self._counters: Dict[str, int] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
    
    def increment(self, name: str, value: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Name of the metric
            value: Value to increment by (default: 1)
        """
        if name not in self._counters:
            self._counters[name] = 0
        self._counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """
        Set a gauge metric.
        
        Args:
            name: Name of the metric
            value: Value to set
        """
        self._gauges[name] = value
    
    def observe(self, name: str, value: float) -> None:
        """
        Observe a value for a histogram metric.
        
        Args:
            name: Name of the metric
            value: Value to observe
        """
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)
    
    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary of all metrics
        """
        metrics = {}
        
        # Add counters
        for name, value in self._counters.items():
            metrics[name] = {
                "type": "counter",
                "value": value
            }
        
        # Add gauges
        for name, value in self._gauges.items():
            metrics[name] = {
                "type": "gauge",
                "value": value
            }
        
        # Add histograms
        for name, values in self._histograms.items():
            if not values:
                continue
                
            # Calculate basic statistics
            count = len(values)
            sum_values = sum(values)
            avg = sum_values / count
            
            # Sort values for percentiles
            sorted_values = sorted(values)
            p50 = sorted_values[int(count * 0.5)] if count > 0 else 0
            p90 = sorted_values[int(count * 0.9)] if count > 0 else 0
            p99 = sorted_values[int(count * 0.99)] if count > 0 else 0
            
            metrics[name] = {
                "type": "histogram",
                "count": count,
                "sum": sum_values,
                "avg": avg,
                "p50": p50,
                "p90": p90,
                "p99": p99
            }
        
        return metrics
    
    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()


# Common health check functions

async def check_redis_connection(redis_client) -> Dict[str, Any]:
    """
    Check if Redis is available and responding.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        Health check result
    """
    try:
        # Ping Redis
        await redis_client.ping()
        return {
            "status": "healthy",
            "details": {
                "connection": "ok"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {
                "error": str(e)
            }
        }

async def check_rabbitmq_connection(rabbitmq_connector) -> Dict[str, Any]:
    """
    Check if RabbitMQ is available and responding.
    
    Args:
        rabbitmq_connector: RabbitMQ connector instance
        
    Returns:
        Health check result
    """
    try:
        # Check if connection is open
        if not rabbitmq_connector.is_connected():
            return {
                "status": "unhealthy",
                "details": {
                    "connection": "closed"
                }
            }
        
        return {
            "status": "healthy",
            "details": {
                "connection": "open"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {
                "error": str(e)
            }
        }

async def check_dmarket_api(dmarket_client) -> Dict[str, Any]:
    """
    Check if DMarket API is available and responding.
    
    Args:
        dmarket_client: DMarket client instance
        
    Returns:
        Health check result
    """
    try:
        # Try to get account balance as a simple API test
        result = await dmarket_client.get_account_balance()
        
        if result is None:
            return {
                "status": "unhealthy",
                "details": {
                    "api": "not responding"
                }
            }
        
        return {
            "status": "healthy",
            "details": {
                "api": "responding"
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "details": {
                "error": str(e)
            }
        }