#!/usr/bin/env python3
"""
Отдельный сервер для метрик Prometheus.
Запускается как отдельный процесс для сбора метрик.
"""

import logging
from prometheus_client import start_http_server, REGISTRY
from .monitoring import MetricsCollector
from core.config import Config


def main():
    """Запуск сервера метрик"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        # Загружаем конфигурацию
        config = Config()

        # Создаем сборщик метрик
        metrics = MetricsCollector(config)

        # Запускаем HTTP сервер для Prometheus
        port = config.bot_config.prometheus_port
        logger.info(f"Starting Prometheus metrics server on port {port}")

        start_http_server(port)
        logger.info(f"Prometheus server started successfully on port {port}")

        # Держим сервер запущенным
        import time
        while True:
            time.sleep(60)  # Проверяем каждые 60 секунд

    except KeyboardInterrupt:
        logger.info("Shutting down Prometheus server")
    except Exception as e:
        logger.error(f"Error starting Prometheus server: {e}")
        raise


if __name__ == "__main__":
    main()