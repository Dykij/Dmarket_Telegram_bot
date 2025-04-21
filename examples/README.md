# Example Scripts for DMarket Telegram Bot

This directory contains example scripts that demonstrate how to use various features of the DMarket Telegram Bot project. These examples are designed to help you understand how to integrate and use the different components of the system.

## Available Examples

### Monitoring Example

The `monitoring_example.py` script demonstrates how to use the monitoring and health check features of the system. It shows:

1. How to set up health checks for various components (Redis, RabbitMQ, DMarket API)
2. How to create a custom health check function
3. How to collect metrics for monitoring (counters, gauges, histograms)
4. How to start a monitoring server to expose health and metrics endpoints

#### Running the Monitoring Example

```bash
python examples/monitoring_example.py
```

After running the script, you can access:
- Health check endpoint: http://localhost:8080/health
- Metrics endpoint: http://localhost:8080/metrics

### Telegram Rich Media Example

The `telegram_rich_media_example.py` script demonstrates how to use the rich media and interactive features in the Telegram bot. It shows:

1. How to create different types of notifications (text, image, photo group, video)
2. How to add inline buttons to notifications
3. How to handle callback queries from inline buttons
4. How to implement a simple whitelist for the bot
5. How to create custom commands for the bot

#### Running the Telegram Rich Media Example

Before running the script, you need to set up your Telegram bot token and whitelist:

1. Create a `.env` file in the project root or set environment variables:
   ```
   TELEGRAM_API_TOKEN=your_telegram_bot_token
   TELEGRAM_WHITELIST=your_telegram_user_id
   ```

2. Run the script:
   ```bash
   python examples/telegram_rich_media_example.py
   ```

3. Open your Telegram app and send the `/examples` command to your bot.

## Creating Your Own Examples

Feel free to modify these examples or create your own to explore other features of the system. The examples are designed to be simple and easy to understand, focusing on specific features of the system.

When creating your own examples, consider:

1. Keeping the example focused on a specific feature or set of related features
2. Adding clear comments to explain what the code is doing
3. Handling errors gracefully
4. Cleaning up resources properly

## Contributing Examples

If you create an example that demonstrates a useful feature or pattern, consider contributing it back to the project. This helps other users learn how to use the system effectively.

To contribute an example:

1. Create a new Python file in the `examples` directory
2. Add clear comments and documentation
3. Update this README.md to include your example
4. Submit a pull request