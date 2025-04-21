# System for monitoring prices on DMarket

## High-Level Features
* Supports proxies (HTTP, SOCKS4, SOCKS5)
* Built using asyncio + uvloop
* Resistant to failure with comprehensive error handling and circuit breaker pattern
* Enhanced security and data validation
* Efficient batch processing for handling large datasets
* Covered by unit tests (almost 100% coverage)
* Most obvious bottlenecks are optimized
* Created a simple CI pipeline
* Added tracing support for some features using Zipkin
* Advanced rate limiting with adaptive backoff strategies
* Rich media support in Telegram notifications (images, videos, animations)
* Interactive user interface with inline keyboards in Telegram
* Comprehensive monitoring and health check system

## Technologies
* Python 3.10, Asyncio, Poetry
* Docker, Docker Compose
* Redis
* RabbitMQ
* Pytest
* Pylint, mypy, black, ruff
* Aiohttp for HTTP client and server
* Zipkin for distributed tracing
* Custom monitoring and metrics collection

## Simplified Flow Chart

```mermaid
graph LR;
    dmarket_parser(DMarket Parser)-->rabbitmq;
    rabbitmq(RabbitMQ);
    rabbitmq-->worker;
    worker(Worker #N)-->Redis;
    Redis[(Redis)];
    Redis-->bot(Telegram Bot);
```

The DMarket parser sends responses to a queue. After that, a worker fetches the response from the queue and processes it. The result of processing is uploaded to a Redis instance. A Telegram bot periodically retrieves results from Redis and computes profit for each market item.

## How to Run (Last Tested in April 2024)
1. Open the `bot.dev.env` file and locate the line that starts with `TELEGRAM_API_TOKEN=`. Set the value of the `TELEGRAM_API_TOKEN` variable to your own Telegram bot's API token. To obtain the token, you can create a bot on Telegram and follow their instructions.
   Additionally, you need to specify the Telegram user IDs that will have access to this bot. To find your Telegram user ID, you can message the bot at https://t.me/myidbot, and it will provide you with your ID. If you have multiple user IDs, separate them with commas (",").
   Here's an example of how it should look:
   ```
   ...
   TELEGRAM_API_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
   TELEGRAM_WHITELIST=12345,45678
   ```
2. Create/open the `utils_mount/dmarket_proxies.txt` file. 
   Add the proxies you want to use in the following format: `<protocol>://<user>:<pass>@<host>:<port>`. 
   If the proxy requires authentication (username and password), include them in the URL.
   If no authentication is needed, simply provide the host and port. Here are some examples:
   * `http://user:pass@1.1.1.1:1234`
   * `http://1.1.1.1:1234`
   * `https://user:pass@1.1.1.1:1234`
   * `socks4://1.1.1.1:1234` - (note: the SOCKS4 protocol doesn't support authorization)
   * `socks5://user:pass@1.1.1.1:1234`
3. Open your terminal or command prompt and run the following command:
   ```
   docker-compose --env-file prod.env up -d
   ```
4. Set up initial settings for your Telegram bot:
   1. `/set_min_price 0` - This command sets the minimum price limit. Any item with a price lower than this value will not be displayed.
   2. `/set_limit -30` - This command sets the profit limit for withdrawals. For example, if you set it to -30, only items with a profit margin greater than -30% will be displayed.

Available Telegram bot commands:
* `/offers` - Displays the currently available offers.

With these adjusted instructions, you should be able to easily run the application and configure your Telegram bot for usage. All prices are in dollars.

![Bot work screenshot](images/bot.png "Bot work screenshot")

## DMarket Parser

The DMarket parser fetches items from the DMarket API. It processes items in batches and sends the results to a RabbitMQ queue. The parser uses proxies to avoid rate limiting and implements retry logic for failed requests. The throughput of the parser depends on the number of available proxies. After a successful request, the parser continues with the next batch of items. In case of errors, it will retry with exponential backoff to avoid overloading the API. The implementation can be found [here](price_monitoring/parsers/dmarket).

At this moment, only one instance of each parser can be running at a time.

## Worker

A worker fetches results from the queue, processes them, and passes results to Redis. The worker implementation includes:

* **Enhanced data validation**: All incoming data undergoes rigorous validation to ensure integrity
* **Security measures**: Input sanitization and sensitive data masking to prevent security vulnerabilities
* **Efficient batch processing**: Items are processed in batches to optimize memory usage and performance
* **Comprehensive error handling**: Graceful handling of exceptions with detailed logging for troubleshooting

The worker architecture is designed for both reliability and performance, processing large volumes of market data while maintaining stability. The applied processors can be found [here](price_monitoring/worker/processing).

For the sell history of a skin, a worker determines the stability of the item and the sell probability for each price for the last week: ![Sell history analyzer](images/sell_history.jpg "Sell history analyzer")

Several workers can be running at one time for horizontal scaling.

## Redis

Prices for items from DMarket are stored in Redis, allowing for:
* Setting TTL for each pair of a name and price
* Fetching all items in one request

Items on DMarket may have different statuses (available for immediate purchase, on hold, etc.). Each item has its own unique key formatted as `prices:dmarket:<item_name>`. Price data is stored with additional metadata about the item's availability and condition.

The implementation can be found [here](price_monitoring/storage).

## Security and Data Validation

The system incorporates multiple layers of security and data validation:

### Validation Framework
* **Data Validators**: Specialized validators ensure integrity and correctness of all incoming data
* **Type Checking**: Runtime type validation prevents processing of incorrectly formatted data
* **Schema Conformance**: Verifies that data structures conform to expected schemas

### Security Measures
* **Input Sanitization**: All user-facing inputs and external data are sanitized to prevent injection attacks
* **Sensitive Data Protection**: API keys and authentication tokens are automatically masked in logs
* **Advanced Rate Limiting**: Protection against excessive requests with adaptive backoff strategies
* **Circuit Breaker Pattern**: Prevents cascading failures by temporarily disabling failing services

### Error Handling
* **Graceful Failure**: The system is designed to continue operating even when parts of it encounter errors
* **Detailed Logging**: Comprehensive logging with appropriate detail levels helps with troubleshooting
* **Granular Error Classification**: Specific error types for different API errors enable targeted handling
* **Retry Logic**: Automatic retries with exponential backoff for transient errors

The validation framework can be found [here](price_monitoring/validation.py).

## Monitoring and Observability

The system includes comprehensive monitoring and observability features:

### Health Checks
* **Component Health Monitoring**: Individual health checks for Redis, RabbitMQ, and DMarket API
* **Health Status API**: HTTP endpoint for external monitoring systems to check application health
* **Degradation Detection**: Identifies degraded services before they fail completely

### Metrics Collection
* **Performance Metrics**: Tracks key performance indicators like request counts and durations
* **Resource Usage**: Monitors system resource utilization
* **Business Metrics**: Tracks business-relevant metrics like processed items and notifications

### Monitoring Integration
* **HTTP API**: Exposes metrics and health data via HTTP endpoints
* **Prometheus Compatible**: Can be integrated with Prometheus for metrics collection
* **Grafana Dashboards**: Supports visualization through Grafana

The monitoring system can be found [here](monitoring/).
