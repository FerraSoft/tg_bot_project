"""
Репозиторий для работы с платежами и транзакциями.
"""

import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from database.repository import BaseRepository
from core.payment_models import Payment, Transaction, PaymentStatus, TransactionType
from core.exceptions import DatabaseError


class PaymentRepository(BaseRepository):
    """Репозиторий платежей"""

    def create_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание нового платежа"""
        try:
            # Подготовка данных
            metadata = payment_data.get('metadata', {})
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata)

            query = """
                INSERT INTO payments (
                    user_id, amount, currency, provider, external_id,
                    status, metadata, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                payment_data['user_id'],
                payment_data['amount'],
                payment_data.get('currency', 'RUB'),
                payment_data['provider'],
                payment_data['external_id'],
                payment_data.get('status', 'pending'),
                metadata,
                payment_data.get('created_at', datetime.now()),
                payment_data.get('updated_at', datetime.now())
            )

            cursor = self._execute_query(query, params)
            payment_id = cursor.lastrowid

            # Возвращаем созданный платеж
            return self.get_payment_by_id(payment_id)

        except Exception as e:
            raise DatabaseError(f"Ошибка создания платежа: {e}")

    def get_payment_by_id(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Получение платежа по ID"""
        query = """
            SELECT p.*, u.first_name, u.username
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        """
        result = self._fetch_one(query, (payment_id,))
        if result:
            # Парсим JSON metadata
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except (json.JSONDecodeError, TypeError):
                    result['metadata'] = {}
            else:
                result['metadata'] = {}
        return result

    def get_payment_by_external_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        """Получение платежа по external ID"""
        query = """
            SELECT p.*, u.first_name, u.username
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.external_id = ?
        """
        result = self._fetch_one(query, (external_id,))
        if result:
            # Парсим JSON metadata
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except (json.JSONDecodeError, TypeError):
                    result['metadata'] = {}
            else:
                result['metadata'] = {}
        return result

    def update_payment_status(self, payment_id: int, status: str,
                            processed_at: Optional[datetime] = None,
                            error_message: Optional[str] = None) -> bool:
        """Обновление статуса платежа"""
        try:
            if processed_at is None and status in ['succeeded', 'failed', 'cancelled']:
                processed_at = datetime.now()

            if processed_at:
                query = """
                    UPDATE payments
                    SET status = ?, processed_at = ?, updated_at = ?, error_message = ?
                    WHERE id = ?
                """
                params = (status, processed_at, datetime.now(), error_message, payment_id)
            else:
                query = """
                    UPDATE payments
                    SET status = ?, updated_at = ?, error_message = ?
                    WHERE id = ?
                """
                params = (status, datetime.now(), error_message, payment_id)

            cursor = self._execute_query(query, params)
            return cursor.rowcount > 0

        except Exception as e:
            raise DatabaseError(f"Ошибка обновления статуса платежа: {e}")

    def update_payment_status_by_external_id(self, external_id: str, status: str,
                                           processed_at: Optional[datetime] = None,
                                           error_message: Optional[str] = None) -> bool:
        """Обновление статуса платежа по external ID"""
        try:
            if processed_at is None and status in ['succeeded', 'failed', 'cancelled']:
                processed_at = datetime.now()

            if processed_at:
                query = """
                    UPDATE payments
                    SET status = ?, processed_at = ?, updated_at = ?, error_message = ?
                    WHERE external_id = ?
                """
                params = (status, processed_at, datetime.now(), error_message, external_id)
            else:
                query = """
                    UPDATE payments
                    SET status = ?, updated_at = ?, error_message = ?
                    WHERE external_id = ?
                """
                params = (status, datetime.now(), error_message, external_id)

            cursor = self._execute_query(query, params)
            return cursor.rowcount > 0

        except Exception as e:
            raise DatabaseError(f"Ошибка обновления статуса платежа по external_id: {e}")

    def get_payments_by_user(self, user_id: int, limit: int = 50,
                           offset: int = 0) -> List[Dict[str, Any]]:
        """Получение платежей пользователя"""
        query = """
            SELECT p.*, u.first_name, u.username
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            ORDER BY p.created_at DESC
            LIMIT ? OFFSET ?
        """
        results = self._fetch_all(query, (user_id, limit, offset))

        # Парсим JSON metadata для каждого платежа
        for result in results:
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except (json.JSONDecodeError, TypeError):
                    result['metadata'] = {}
            else:
                result['metadata'] = {}

        return results

    def get_payments_by_status(self, status: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение платежей по статусу"""
        query = """
            SELECT p.*, u.first_name, u.username
            FROM payments p
            LEFT JOIN users u ON p.user_id = u.id
            WHERE p.status = ?
            ORDER BY p.created_at DESC
            LIMIT ?
        """
        results = self._fetch_all(query, (status, limit))

        # Парсим JSON metadata
        for result in results:
            if result.get('metadata'):
                try:
                    result['metadata'] = json.loads(result['metadata'])
                except (json.JSONDecodeError, TypeError):
                    result['metadata'] = {}
            else:
                result['metadata'] = {}

        return results

    def get_payment_statistics(self, date_from: Optional[datetime] = None,
                             date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """Получение статистики платежей"""
        try:
            base_conditions = []
            params = []

            if date_from:
                base_conditions.append("p.created_at >= ?")
                params.append(date_from)

            if date_to:
                base_conditions.append("p.created_at <= ?")
                params.append(date_to)

            where_clause = " AND ".join(base_conditions) if base_conditions else "1=1"

            # Общая статистика
            total_query = f"""
                SELECT
                    COUNT(*) as total_payments,
                    SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) as total_amount,
                    AVG(CASE WHEN status = 'succeeded' THEN amount ELSE NULL END) as avg_amount,
                    COUNT(CASE WHEN status = 'succeeded' THEN 1 END) as successful_payments,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments
                FROM payments p
                WHERE {where_clause}
            """

            total_stats = self._fetch_one(total_query, tuple(params))

            # Статистика по провайдерам
            provider_query = f"""
                SELECT
                    provider,
                    COUNT(*) as count,
                    SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) as amount
                FROM payments p
                WHERE {where_clause}
                GROUP BY provider
            """

            provider_stats = self._fetch_all(provider_query, tuple(params))

            return {
                'total_stats': total_stats or {},
                'provider_stats': provider_stats or [],
                'date_from': date_from,
                'date_to': date_to
            }

        except Exception as e:
            raise DatabaseError(f"Ошибка получения статистики платежей: {e}")

    def check_duplicate_payment(self, external_id: str, amount: float,
                              user_id: int, time_window_minutes: int = 30) -> bool:
        """Проверка на дубликат платежа"""
        query = """
            SELECT COUNT(*) as count
            FROM payments
            WHERE external_id = ?
               OR (user_id = (SELECT id FROM users WHERE telegram_id = ?)
                   AND amount = ?
                   AND created_at >= datetime('now', '-{} minutes'))
        """.format(time_window_minutes)

        result = self._fetch_one(query, (external_id, user_id, amount))
        return result['count'] > 0 if result else False


class TransactionRepository(BaseRepository):
    """Репозиторий транзакций"""

    def create_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Создание новой транзакции"""
        try:
            # Подготовка данных
            details = transaction_data.get('details', {})
            if isinstance(details, dict):
                details = json.dumps(details)

            query = """
                INSERT INTO transactions (
                    payment_id, type, amount, status,
                    external_transaction_id, details, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                transaction_data['payment_id'],
                transaction_data['type'],
                transaction_data['amount'],
                transaction_data['status'],
                transaction_data.get('external_transaction_id'),
                details,
                transaction_data.get('created_at', datetime.now())
            )

            cursor = self._execute_query(query, params)
            transaction_id = cursor.lastrowid

            # Возвращаем созданную транзакцию
            return self.get_transaction_by_id(transaction_id)

        except Exception as e:
            raise DatabaseError(f"Ошибка создания транзакции: {e}")

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """Получение транзакции по ID"""
        query = """
            SELECT t.*, p.external_id as payment_external_id, u.first_name, u.username
            FROM transactions t
            LEFT JOIN payments p ON t.payment_id = p.id
            LEFT JOIN users u ON p.user_id = u.id
            WHERE t.id = ?
        """
        result = self._fetch_one(query, (transaction_id,))
        if result:
            # Парсим JSON details
            if result.get('details'):
                try:
                    result['details'] = json.loads(result['details'])
                except (json.JSONDecodeError, TypeError):
                    result['details'] = {}
            else:
                result['details'] = {}
        return result

    def get_transactions_by_payment(self, payment_id: int) -> List[Dict[str, Any]]:
        """Получение транзакций платежа"""
        query = """
            SELECT t.*, p.external_id as payment_external_id
            FROM transactions t
            LEFT JOIN payments p ON t.payment_id = p.id
            WHERE t.payment_id = ?
            ORDER BY t.created_at DESC
        """
        results = self._fetch_all(query, (payment_id,))

        # Парсим JSON details
        for result in results:
            if result.get('details'):
                try:
                    result['details'] = json.loads(result['details'])
                except (json.JSONDecodeError, TypeError):
                    result['details'] = {}
            else:
                result['details'] = {}

        return results

    def update_transaction_status(self, transaction_id: int, status: str,
                                details: Optional[Dict] = None) -> bool:
        """Обновление статуса транзакции"""
        try:
            if details:
                details_json = json.dumps(details)
                query = """
                    UPDATE transactions
                    SET status = ?, details = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                params = (status, details_json, transaction_id)
            else:
                query = """
                    UPDATE transactions
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """
                params = (status, transaction_id)

            cursor = self._execute_query(query, params)
            return cursor.rowcount > 0

        except Exception as e:
            raise DatabaseError(f"Ошибка обновления статуса транзакции: {e}")