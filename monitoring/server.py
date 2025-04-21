"""
HTTP Server for Health Checks and Metrics

This module provides a simple HTTP server that exposes health check and metrics
endpoints for monitoring the application. It uses aiohttp to create a lightweight
web server that can be used by monitoring systems to check the health of the
application and collect metrics.

Usage:
    from monitoring.server import start_monitoring_server
    
    # Create health check and metrics instances
    health_check = HealthCheck()
    metrics = MetricsCollector()
    
    # Register components to check
    health_check.register_check("redis", check_redis_connection(redis_client))
    
    # Start the monitoring server
    await start_monitoring_server(health_check, metrics, host="0.0.0.0", port=8080)
"""

import asyncio
import json
import logging
from typing import Dict, Optional

from aiohttp import web

from .health import HealthCheck, MetricsCollector

logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    """
    Handler for the /health endpoint.
    
    This endpoint returns the health status of the application and its components.
    
    Args:
        request: The HTTP request
        
    Returns:
        HTTP response with health check result
    """
    health_check: HealthCheck = request.app["health_check"]
    
    # Check if we should use cached result
    use_cache = request.query.get("cache", "false").lower() == "true"
    
    if use_cache:
        # Use cached result if available
        result = health_check.get_last_result()
        if result is None:
            # No cached result, perform check
            result = await health_check.check_health()
    else:
        # Perform fresh health check
        result = await health_check.check_health()
    
    # Convert result to JSON
    result_dict = result.to_dict()
    
    # Set response status based on health status
    if result.status.value == "healthy":
        status = 200
    elif result.status.value == "degraded":
        status = 200  # Still return 200 for degraded, but include status in body
    else:
        status = 503  # Service Unavailable
    
    return web.json_response(result_dict, status=status)


async def metrics_handler(request: web.Request) -> web.Response:
    """
    Handler for the /metrics endpoint.
    
    This endpoint returns the collected metrics in JSON format.
    
    Args:
        request: The HTTP request
        
    Returns:
        HTTP response with metrics
    """
    metrics: MetricsCollector = request.app["metrics"]
    
    # Get all metrics
    metrics_data = metrics.get_metrics()
    
    return web.json_response(metrics_data)


async def start_monitoring_server(
    health_check: HealthCheck,
    metrics: MetricsCollector,
    host: str = "localhost",
    port: int = 8080,
    shutdown_timeout: float = 60.0,
) -> web.AppRunner:
    """
    Start the monitoring HTTP server.
    
    This function creates and starts an HTTP server that exposes health check
    and metrics endpoints for monitoring the application.
    
    Args:
        health_check: HealthCheck instance
        metrics: MetricsCollector instance
        host: Host to bind the server to
        port: Port to bind the server to
        shutdown_timeout: Timeout for graceful shutdown in seconds
        
    Returns:
        The AppRunner instance for the server
    """
    # Create the application
    app = web.Application()
    
    # Store health check and metrics in app context
    app["health_check"] = health_check
    app["metrics"] = metrics
    
    # Add routes
    app.add_routes([
        web.get("/health", health_handler),
        web.get("/metrics", metrics_handler),
    ])
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"Monitoring server started at http://{host}:{port}")
    logger.info(f"Health check endpoint: http://{host}:{port}/health")
    logger.info(f"Metrics endpoint: http://{host}:{port}/metrics")
    
    # Add cleanup callback
    async def cleanup(app: web.Application) -> None:
        logger.info("Shutting down monitoring server...")
        await runner.cleanup()
    
    app.on_cleanup.append(cleanup)
    
    return runner


def create_monitoring_middleware(metrics: MetricsCollector) -> web.middleware:
    """
    Create a middleware for monitoring HTTP requests.
    
    This middleware collects metrics for HTTP requests, including request count,
    response status codes, and request duration.
    
    Args:
        metrics: MetricsCollector instance
        
    Returns:
        Middleware function
    """
    @web.middleware
    async def middleware(request: web.Request, handler) -> web.Response:
        # Record request start time
        start_time = asyncio.get_event_loop().time()
        
        # Increment request counter
        metrics.increment("http_requests_total")
        
        try:
            # Process the request
            response = await handler(request)
            
            # Record response status
            metrics.increment(f"http_responses_total{{status={response.status}}}")
            
            return response
        finally:
            # Record request duration
            duration = asyncio.get_event_loop().time() - start_time
            metrics.observe("http_request_duration_seconds", duration)
    
    return middleware


def setup_monitoring(app: web.Application, metrics: MetricsCollector) -> None:
    """
    Set up monitoring for an existing aiohttp application.
    
    This function adds monitoring middleware and endpoints to an existing
    aiohttp application.
    
    Args:
        app: The aiohttp application
        metrics: MetricsCollector instance
    """
    # Add metrics to app context
    app["metrics"] = metrics
    
    # Add monitoring middleware
    app.middlewares.append(create_monitoring_middleware(metrics))
    
    # Add metrics endpoint
    app.add_routes([
        web.get("/metrics", metrics_handler),
    ])
    
    logger.info("Monitoring middleware and endpoints added to application")


if __name__ == "__main__":
    # Example usage
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
    
    # Create health check and metrics instances
    health_check = HealthCheck()
    metrics = MetricsCollector()
    
    # Register a simple health check
    health_check.register_check("example", lambda: {"status": "healthy", "details": {"example": "ok"}})
    
    # Start the server
    asyncio.run(start_monitoring_server(health_check, metrics))