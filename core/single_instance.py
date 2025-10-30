"""
Защита от множественных экземпляров бота.
Использует файл-блокировку для предотвращения запуска нескольких копий.
"""

import os
import logging
from typing import Optional

# fcntl доступен только на Unix-подобных системах
try:
    import fcntl
except ImportError:
    fcntl = None


class SingleInstance:
    """
    Класс для обеспечения запуска только одного экземпляра приложения.
    Использует файловую блокировку для синхронизации.
    """

    def __init__(self, lock_file_path: str = None):
        """
        Инициализация защиты от множественных экземпляров.

        Args:
            lock_file_path: Путь к файлу блокировки (по умолчанию в директории проекта)
        """
        if lock_file_path is None:
            # Создаем файл блокировки в директории проекта
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            lock_file_path = os.path.join(project_root, '.bot.lock')

        self.lock_file_path = lock_file_path
        self.lock_file = None
        self.logger = logging.getLogger(__name__)

    def acquire_lock(self) -> bool:
        """
        Попытка получить блокировку.
        Если блокировка уже установлена другим процессом, возвращает False.

        Returns:
            True если блокировка получена успешно, False в противном случае
        """
        try:
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.lock_file_path), exist_ok=True)

            # Открываем файл блокировки
            self.lock_file = open(self.lock_file_path, 'w')

            # Пытаемся получить эксклюзивную блокировку
            # На Windows fcntl не работает, используем альтернативный подход
            if os.name == 'nt':  # Windows
                try:
                    # На Windows используем простую проверку существования процесса
                    # путем создания PID файла
                    import psutil

                    # Читаем PID из файла блокировки если он существует
                    if os.path.exists(self.lock_file_path):
                        try:
                            with open(self.lock_file_path, 'r') as f:
                                old_pid = int(f.read().strip())
                                if psutil.pid_exists(old_pid):
                                    self.logger.warning(f"Найден запущенный процесс с PID {old_pid}")
                                    return False
                                else:
                                    self.logger.info(f"Процесс с PID {old_pid} больше не существует, очищаем блокировку")
                        except (ValueError, FileNotFoundError):
                            pass

                    # Записываем текущий PID
                    self.lock_file.write(str(os.getpid()))
                    self.lock_file.flush()
                    return True

                except Exception as e:
                    self.logger.error(f"Ошибка при проверке процесса на Windows: {e}")
                    return False
            else:  # Unix-like системы
                # Используем fcntl для блокировки файла
                if fcntl is not None:
                    fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Записываем PID для информации
                self.lock_file.write(str(os.getpid()))
                self.lock_file.flush()
                return True

        except BlockingIOError:
            # Блокировка уже установлена другим процессом
            self.logger.warning("Блокировка уже установлена другим экземпляром бота")
            self._cleanup()
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при получении блокировки: {e}")
            self._cleanup()
            return False

    def release_lock(self):
        """Освобождает блокировку и закрывает файл"""
        try:
            if self.lock_file:
                if os.name != 'nt' and fcntl is not None:  # Только для Unix-like систем с fcntl
                    try:
                        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                    except Exception as e:
                        self.logger.warning(f"Ошибка снятия блокировки: {e}")

                self.lock_file.close()
                self.lock_file = None

            # Удаляем файл блокировки
            try:
                if os.path.exists(self.lock_file_path):
                    os.remove(self.lock_file_path)
            except Exception as e:
                self.logger.warning(f"Ошибка удаления файла блокировки: {e}")

        except Exception as e:
            self.logger.error(f"Ошибка при освобождении блокировки: {e}")

    def _cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
        except Exception as e:
            self.logger.warning(f"Ошибка при очистке ресурсов: {e}")

    def __enter__(self):
        """Контекстный менеджер - вход"""
        if not self.acquire_lock():
            raise RuntimeError("Не удалось получить блокировку. Возможно, другой экземпляр бота уже запущен.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Контекстный менеджер - выход"""
        self.release_lock()


def check_single_instance(lock_file_path: str = None) -> bool:
    """
    Проверяет и устанавливает блокировку для единственного экземпляра.

    Args:
        lock_file_path: Путь к файлу блокировки

    Returns:
        True если блокировка установлена успешно, False в противном случае

    Raises:
        RuntimeError: Если не удалось установить блокировку
    """
    instance = SingleInstance(lock_file_path)
    if instance.acquire_lock():
        # Сохраняем ссылку на объект блокировки чтобы GC не удалил его
        import atexit
        atexit.register(instance.release_lock)
        return True
    else:
        return False