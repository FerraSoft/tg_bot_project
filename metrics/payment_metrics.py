"""
Метрики и мониторинг платежных операций.
"""

import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque


class PaymentMetrics:
    """
    Класс для сбора и анализа метрик платежных операций.

    Отвечает за:
    - Сбор статистики платежей
    - Мониторинг производительности
    - Обнаружение аномалий
    - Генерацию отчетов
    """

    def __init__(self, max_history_size: int = 1000):
        """
        Инициализация метрик.

        Args:
            max_history_size: Максимальный размер истории для каждой метрики
        """
        self.logger = logging.getLogger(__name__)
        self.max_history_size = max_history_size

        # Метрики счетчиков
        self.counters = defaultdict(int)

        # Метрики временных рядов
        self.time_series = defaultdict(lambda: deque(maxlen=max_history_size))

        # Метрики гистограмм (для длительности операций)
        self.histograms = defaultdict(list)

        # Статистика по провайдерам
        self.provider_stats = defaultdict(lambda: {
            'total_payments': 0,
            'successful_payments': 0,
            'failed_payments': 0,
            'total_amount': 0.0,
            'average_amount': 0.0,
            'last_payment_time': None
        })

        # Статистика ошибок
        self.error_stats = defaultdict(lambda: {
            'count': 0,
            'last_occurrence': None,
            'error_messages': deque(maxlen=50)
        })

        # Время запуска мониторинга
        self.start_time = datetime.now()

    def record_payment_created(self, amount: float, provider: str, user_id: int):
        """
        Запись метрики создания платежа.

        Args:
            amount: Сумма платежа
            provider: Провайдер платежа
            user_id: ID пользователя
        """
        timestamp = datetime.now()

        # Обновление счетчиков
        self.counters['payments_created'] += 1
        self.counters[f'payments_created_{provider}'] += 1

        # Запись в временной ряд
        self.time_series['payments_created'].append({
            'timestamp': timestamp,
            'amount': amount,
            'provider': provider,
            'user_id': user_id
        })

        # Обновление статистики провайдера
        self.provider_stats[provider]['total_payments'] += 1
        self.provider_stats[provider]['last_payment_time'] = timestamp

        self.logger.debug(f"Recorded payment creation: amount={amount}, provider={provider}")

    def record_payment_completed(self, payment_id: str, amount: float, provider: str,
                               duration_seconds: float):
        """
        Запись метрики завершенного платежа.

        Args:
            payment_id: ID платежа
            amount: Сумма платежа
            provider: Провайдер
            duration_seconds: Длительность обработки
        """
        timestamp = datetime.now()

        # Обновление счетчиков
        self.counters['payments_completed'] += 1
        self.counters[f'payments_completed_{provider}'] += 1

        # Запись длительности
        self.histograms['payment_duration'].append(duration_seconds)

        # Запись в временной ряд
        self.time_series['payments_completed'].append({
            'timestamp': timestamp,
            'payment_id': payment_id,
            'amount': amount,
            'provider': provider,
            'duration': duration_seconds
        })

        # Обновление статистики провайдера
        self.provider_stats[provider]['successful_payments'] += 1
        self.provider_stats[provider]['total_amount'] += amount

        # Пересчет средней суммы
        total_payments = self.provider_stats[provider]['successful_payments']
        self.provider_stats[provider]['average_amount'] = (
            self.provider_stats[provider]['total_amount'] / total_payments
        )

        self.logger.debug(f"Recorded payment completion: id={payment_id}, duration={duration_seconds:.2f}s")

    def record_payment_failed(self, payment_id: str, provider: str, error_type: str,
                            error_message: str = ""):
        """
        Запись метрики неудачного платежа.

        Args:
            payment_id: ID платежа
            provider: Провайдер
            error_type: Тип ошибки
            error_message: Сообщение об ошибке
        """
        timestamp = datetime.now()

        # Обновление счетчиков
        self.counters['payments_failed'] += 1
        self.counters[f'payments_failed_{provider}'] += 1
        self.counters[f'payments_failed_{error_type}'] += 1

        # Запись в статистику ошибок
        self.error_stats[error_type]['count'] += 1
        self.error_stats[error_type]['last_occurrence'] = timestamp
        self.error_stats[error_type]['error_messages'].append(error_message)

        # Запись в временной ряд
        self.time_series['payments_failed'].append({
            'timestamp': timestamp,
            'payment_id': payment_id,
            'provider': provider,
            'error_type': error_type,
            'error_message': error_message
        })

        # Обновление статистики провайдера
        self.provider_stats[provider]['failed_payments'] += 1

        self.logger.warning(f"Recorded payment failure: id={payment_id}, error={error_type}")

    def record_webhook_received(self, provider: str, processing_time: float):
        """
        Запись метрики полученного webhook.

        Args:
            provider: Провайдер
            processing_time: Время обработки
        """
        timestamp = datetime.now()

        self.counters['webhooks_received'] += 1
        self.counters[f'webhooks_received_{provider}'] += 1

        # Запись длительности обработки
        self.histograms['webhook_processing_time'].append(processing_time)

        self.time_series['webhooks_received'].append({
            'timestamp': timestamp,
            'provider': provider,
            'processing_time': processing_time
        })

    def record_webhook_validation_failed(self, provider: str, reason: str):
        """
        Запись метрики неудачной валидации webhook.

        Args:
            provider: Провайдер
            reason: Причина неудачи
        """
        timestamp = datetime.now()

        self.counters['webhook_validation_failed'] += 1
        self.counters[f'webhook_validation_failed_{provider}'] += 1

        self.time_series['webhook_validation_failed'].append({
            'timestamp': timestamp,
            'provider': provider,
            'reason': reason
        })

        self.logger.warning(f"Webhook validation failed: provider={provider}, reason={reason}")

    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Получение сводной статистики.

        Returns:
            Dict[str, Any]: Сводная статистика
        """
        total_payments = self.counters['payments_created']
        completed_payments = self.counters['payments_completed']
        failed_payments = self.counters['payments_failed']

        # Расчет конверсии
        conversion_rate = (completed_payments / total_payments * 100) if total_payments > 0 else 0

        # Расчет средней длительности платежей
        payment_durations = self.histograms.get('payment_duration', [])
        avg_payment_duration = sum(payment_durations) / len(payment_durations) if payment_durations else 0

        return {
            'total_payments': total_payments,
            'completed_payments': completed_payments,
            'failed_payments': failed_payments,
            'conversion_rate_percent': round(conversion_rate, 2),
            'avg_payment_duration_seconds': round(avg_payment_duration, 2),
            'webhooks_received': self.counters['webhooks_received'],
            'webhook_validation_failures': self.counters['webhook_validation_failed'],
            'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
            'provider_stats': dict(self.provider_stats),
            'top_errors': self._get_top_errors()
        }

    def get_recent_activity(self, minutes: int = 60) -> Dict[str, Any]:
        """
        Получение недавней активности.

        Args:
            minutes: Период в минутах

        Returns:
            Dict[str, Any]: Недавняя активность
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        recent_payments = [
            item for item in self.time_series['payments_created']
            if item['timestamp'] > cutoff_time
        ]

        recent_completions = [
            item for item in self.time_series['payments_completed']
            if item['timestamp'] > cutoff_time
        ]

        recent_failures = [
            item for item in self.time_series['payments_failed']
            if item['timestamp'] > cutoff_time
        ]

        return {
            'period_minutes': minutes,
            'payments_created': len(recent_payments),
            'payments_completed': len(recent_completions),
            'payments_failed': len(recent_failures),
            'total_amount_recent': sum(p['amount'] for p in recent_completions)
        }

    def detect_anomalies(self) -> Dict[str, Any]:
        """
        Обнаружение аномалий в метриках.

        Returns:
            Dict[str, Any]: Найденные аномалии
        """
        anomalies = {
            'high_failure_rate': False,
            'unusual_traffic': False,
            'slow_processing': False,
            'webhook_spike': False,
            'details': []
        }

        # Проверка высокой доли неудачных платежей
        total = self.counters['payments_created']
        failed = self.counters['payments_failed']
        if total > 10 and (failed / total) > 0.3:  # > 30% неудач
            anomalies['high_failure_rate'] = True
            anomalies['details'].append(f"High failure rate: {failed}/{total} ({failed/total*100:.1f}%)")

        # Проверка необычного трафика (вдруг вырос на 5x по сравнению со средним)
        recent_activity = self.get_recent_activity(10)  # последние 10 минут
        if recent_activity['payments_created'] > 50:  # порог для обнаружения
            anomalies['unusual_traffic'] = True
            anomalies['details'].append(f"Unusual traffic: {recent_activity['payments_created']} payments in 10 min")

        # Проверка медленной обработки
        durations = self.histograms.get('payment_duration', [])
        if durations and len(durations) > 5:
            avg_duration = sum(durations[-10:]) / len(durations[-10:])  # среднее за последние 10
            if avg_duration > 30:  # > 30 секунд
                anomalies['slow_processing'] = True
                anomalies['details'].append(f"Slow processing: avg {avg_duration:.1f}s")

        # Проверка спайка webhook
        recent_webhooks = len([
            w for w in self.time_series['webhooks_received']
            if (datetime.now() - w['timestamp']).seconds < 300  # последние 5 минут
        ])
        if recent_webhooks > 100:  # порог
            anomalies['webhook_spike'] = True
            anomalies['details'].append(f"Webhook spike: {recent_webhooks} in 5 min")

        return anomalies

    def _get_top_errors(self, limit: int = 5) -> list:
        """
        Получение топа самых частых ошибок.

        Args:
            limit: Количество ошибок для возврата

        Returns:
            list: Топ ошибок
        """
        sorted_errors = sorted(
            self.error_stats.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )

        return [
            {
                'error_type': error_type,
                'count': stats['count'],
                'last_occurrence': stats['last_occurrence'].isoformat() if stats['last_occurrence'] else None,
                'recent_messages': list(stats['error_messages'])[-3:]  # последние 3 сообщения
            }
            for error_type, stats in sorted_errors[:limit]
        ]

    def reset_counters(self):
        """Сброс всех счетчиков (для тестирования)"""
        self.counters.clear()
        self.time_series.clear()
        self.histograms.clear()
        self.provider_stats.clear()
        self.error_stats.clear()
        self.start_time = datetime.now()

    def export_metrics(self) -> Dict[str, Any]:
        """
        Экспорт всех метрик для внешнего использования.

        Returns:
            Dict[str, Any]: Все метрики
        """
        return {
            'counters': dict(self.counters),
            'time_series_lengths': {k: len(v) for k, v in self.time_series.items()},
            'histogram_stats': {
                k: {
                    'count': len(v),
                    'avg': sum(v) / len(v) if v else 0,
                    'min': min(v) if v else 0,
                    'max': max(v) if v else 0
                }
                for k, v in self.histograms.items()
            },
            'provider_stats': dict(self.provider_stats),
            'summary': self.get_summary_stats(),
            'anomalies': self.detect_anomalies(),
            'export_time': datetime.now().isoformat()
        }


# Глобальный экземпляр метрик
payment_metrics = PaymentMetrics()


def get_payment_metrics() -> PaymentMetrics:
    """Получение глобального экземпляра метрик"""
    return payment_metrics