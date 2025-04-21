# Monitoring and Health Check Module

This module provides functionality for monitoring the health and performance of the DMarket Telegram Bot application. It includes:

1. Health checks for various components of the application
2. Metrics collection for monitoring application performance
3. A simple HTTP server that exposes health check and metrics endpoints

## Features

### Health Checks

The health check system allows you to:

- Register health check functions for different components
- Get the health status of individual components and the entire application
- Expose health status through an HTTP endpoint

Health statuses can be:
- **HEALTHY**: The component is functioning normally
- **DEGRADED**: The component is functioning but with reduced performance or capabilities
- **UNHEALTHY**: The component is not functioning properly

### Metrics Collection

The metrics collection system allows you to:

- Collect counter metrics (e.g., number of API requests)
- Collect gauge metrics (e.g., current number of active connections)
- Collect histogram metrics (e.g., request duration)
- Get basic statistics for histogram metrics (count, sum, average, percentiles)
- Expose metrics through an HTTP endpoint

### Monitoring Server

The monitoring server provides:

- A `/health` endpoint that returns the health status of the application
- A `/metrics` endpoint that returns the collected metrics
- Middleware for monitoring HTTP requests in existing aiohttp applications

## Usage

### Basic Health Check

```python
from monitoring.health import HealthCheck

# Create a health check instance
health_check = HealthCheck()

# Register health check functions
health_check.register_check("redis", check_redis_connection(redis_client))
health_check.register_check("rabbitmq", check_rabbitmq_connection(rabbitmq_connector))
health_check.register_check("dmarket_api", check_dmarket_api(dmarket_client))

# Check health
result = await health_check.check_health()
print(f"Overall status: {result.status.value}")
for component in result.components:
    print(f"  {component.name}: {component.status.value}")
```

### Basic Metrics Collection

```python
from monitoring.health import MetricsCollector

# Create a metrics collector
metrics = MetricsCollector()

# Record metrics
metrics.increment("api_requests_total")
metrics.set_gauge("active_connections", 42)
metrics.observe("request_duration_seconds", 0.45)

# Get metrics
all_metrics = metrics.get_metrics()
print(all_metrics)
```

### Starting the Monitoring Server

```python
from monitoring.server import start_monitoring_server
from monitoring.health import HealthCheck, MetricsCollector

# Create health check and metrics instances
health_check = HealthCheck()
metrics = MetricsCollector()

# Register health check functions
health_check.register_check("redis", check_redis_connection(redis_client))

# Start the monitoring server
await start_monitoring_server(health_check, metrics, host="0.0.0.0", port=8080)
```

### Adding Monitoring to an Existing aiohttp Application

```python
from aiohttp import web
from monitoring.server import setup_monitoring
from monitoring.health import MetricsCollector

# Create your aiohttp application
app = web.Application()

# Create a metrics collector
metrics = MetricsCollector()

# Set up monitoring
setup_monitoring(app, metrics)

# Add your routes
app.add_routes([
    web.get("/", handler),
])

# Run the application
web.run_app(app)
```

## Common Health Check Functions

The module provides common health check functions for:

- Redis: `check_redis_connection(redis_client)`
- RabbitMQ: `check_rabbitmq_connection(rabbitmq_connector)`
- DMarket API: `check_dmarket_api(dmarket_client)`

You can also create your own health check functions. A health check function should:

- Return a boolean (`True` for healthy, `False` for unhealthy), or
- Return a dictionary with a `status` key (values: "healthy", "degraded", "unhealthy") and optional `details` key

## Integrating with Monitoring Systems

The monitoring server exposes endpoints that can be integrated with various monitoring systems:

### Prometheus

You can use the [prometheus-client](https://github.com/prometheus/client_python) library to expose metrics in Prometheus format:

```python
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.exposition import start_http_server

# Create Prometheus metrics
request_counter = Counter('http_requests_total', 'Total HTTP requests')
active_connections = Gauge('active_connections', 'Active connections')
request_duration = Histogram('request_duration_seconds', 'Request duration in seconds')

# Start Prometheus HTTP server
start_http_server(8000)
```

### Grafana

You can use Grafana to visualize metrics from Prometheus or directly from the `/metrics` endpoint using the JSON API data source.

### Custom Monitoring

You can create a custom monitoring solution by periodically querying the `/health` and `/metrics` endpoints:

```python
import aiohttp
import asyncio

async def monitor():
    async with aiohttp.ClientSession() as session:
        # Check health
        async with session.get("http://localhost:8080/health") as response:
            health = await response.json()
            print(f"Health status: {health['status']}")
        
        # Get metrics
        async with session.get("http://localhost:8080/metrics") as response:
            metrics = await response.json()
            print(f"API requests: {metrics.get('api_requests_total', {}).get('value', 0)}")

# Run monitoring every 60 seconds
while True:
    asyncio.run(monitor())
    await asyncio.sleep(60)
```