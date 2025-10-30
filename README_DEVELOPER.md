# 👨‍💻 Руководство для разработчика

## 🔧 Поддержка и развитие системы мониторинга

### 📋 Обзор архитектуры

```
telegram_bot/
├── core/
│   ├── monitoring.py      # 📊 Метрики + Sentry + Логи
│   ├── alerts.py         # 🚨 Система алертов
│   └── application.py    # 🎯 Главное приложение (обновлено)
├── handlers/             # 🎮 Обработчики (обновлены)
├── tests/               # 🧪 Тесты мониторинга
└── docs/               # 📚 Документация
```

### 🚀 Добавление новых метрик

#### В MetricsCollector (core/monitoring.py):

```python
# Добавьте новую метрику в __init__
self.new_metric = Counter('telegram_bot_new_feature_total', 'Description')

# Используйте в коде
metrics.new_metric.labels(type='example').inc()
```

#### В handlers:

```python
# Автоматически через декораторы
@measure_time(metrics, 'api_name')
async def some_api_call(self):
    pass

@error_handler(metrics, 'handler_name')
async def risky_operation(self):
    pass
```

### 🚨 Добавление новых алертов

#### В AlertManager (core/alerts.py):

```python
# Добавьте правило в __init__
self.alert_rules['new_alert'] = {
    'enabled': True,
    'threshold': 100,
    'cooldown': 300,
    'last_alert': None
}

# Добавьте метод проверки
async def _check_new_alert(self):
    if some_condition:
        await self._trigger_alert('new_alert', 'Message', {'data': value})
```

#### Настройка уведомлений:

```python
# Добавьте обработчик в __init__
self.alert_handlers.append(self._send_slack_alert)

# Реализуйте метод
async def _send_slack_alert(self, alert_type, message, extra_data):
    # Отправка в Slack
    pass
```

### 📊 Добавление новых обработчиков

#### Создание нового handler:

```python
from handlers.base_handler import BaseHandler

class NewHandler(BaseHandler):
    def __init__(self, config, metrics, service):
        super().__init__(config, metrics)  # Передача metrics обязательна!
        self.service = service

    def get_command_handlers(self):
        return {
            'new_command': self.handle_new_command
        }
```

#### Регистрация в Application:

```python
# В core/application.py
from handlers.new_handler import NewHandler

# В _initialize_handlers
handlers['new'] = NewHandler(self.config, self.metrics, NewService())
```

### 🧪 Тестирование

#### Запуск тестов:
```bash
# Все тесты мониторинга
pytest tests/test_monitoring.py -v

# Интеграционные тесты
python test_monitoring_integration.py

# Финальное тестирование
python final_test.py

# Автонастройка
python setup_monitoring.py
```

#### Добавление новых тестов:

```python
# В tests/test_monitoring.py
def test_new_metric(metrics):
    """Тест новой метрики"""
    # Тестовая логика
    assert True
```

### 📚 Обновление документации

#### При добавлении функций:
1. Обновите `MONITORING.md`
2. Добавьте примеры в `README_MONITORING.md`
3. Обновите `README_SYSTEM.md` с новыми файлами

#### Структура документации:
- `MONITORING.md` - технические детали
- `README_MONITORING.md` - для пользователей
- `GLITCHTIP_SETUP.md` - настройка
- `START_MONITORING.md` - пошаговое руководство

### 🔧 Конфигурация

#### Добавление новых настроек:

```python
# В core/config.py
@dataclass
class BotConfig:
    # ... существующие поля
    new_feature_enabled: bool = False

# В _load_from_environment
self._config['new_feature_enabled'] = self._str_to_bool(
    os.getenv('NEW_FEATURE_ENABLED', 'false')
)
```

### 🚀 Развертывание

#### Продакшен рекомендации:

1. **GlitchTip:**
   ```bash
   docker-compose up -d
   # Настройка HTTPS, backup, scaling
   ```

2. **Prometheus:**
   ```bash
   # Отдельный сервер Prometheus
   # Конфигурация scraping
   ```

3. **Grafana:**
   ```bash
   docker run -d -p 3000:3000 grafana/grafana
   # Дашборды для телеграм-бота
   ```

4. **Мониторинг мониторинга:**
   - Health checks для GlitchTip
   - Алерты на недоступность метрик
   - Backup конфигурации

### 🐛 Отладка

#### Распространенные проблемы:

1. **Метрики не собираются:**
   ```bash
   curl http://localhost:8000/metrics
   # Проверьте порт и firewall
   ```

2. **GlitchTip не работает:**
   ```bash
   docker-compose logs glitchtip
   # Проверьте логи и конфигурацию
   ```

3. **Алерты не приходят:**
   - Проверьте DEVELOPER_CHAT_ID
   - Убедитесь в правах бота
   - Проверьте webhook URL

4. **Логи не записываются:**
   ```bash
   tail -f bot.log
   # Проверьте права на файл
   ```

### 📈 Мониторинг производительности

#### Оптимизация:
- Используйте sampling для высоконагруженных endpoint'ов
- Настройте retention для метрик
- Мониторьте использование памяти декораторами

#### Профилирование:
```python
import cProfile

# В коде
pr = cProfile.Profile()
pr.enable()
# Ваш код
pr.disable()
pr.print_stats()
```

### 🤝 Лучшие практики

1. **Атомарные изменения:**
   - Тестируйте каждый новый компонент
   - Документируйте изменения
   - Обновляйте тесты

2. **Безопасность:**
   - Не логируйте чувствительную информацию
   - Валидируйте все входные данные
   - Используйте HTTPS для webhook

3. **Производительность:**
   - Асинхронные операции для алертов
   - Кеширование частых метрик
   - Оптимизация запросов к БД

4. **Поддерживаемость:**
   - Следуйте существующей архитектуре
   - Добавляйте тесты для новых функций
   - Документируйте все изменения

### 📞 Поддержка команды

#### Для новых разработчиков:
1. Изучите `MONITORING.md`
2. Запустите `setup_monitoring.py`
3. Пройдите `final_test.py`
4. Ознакомьтесь с примерами в коде

#### Структура кода:
- Каждый модуль имеет четкую ответственность
- Используйте type hints
- Добавляйте docstrings
- Следуйте PEP 8

## 🎯 Будущие улучшения

- [ ] Интеграция с Grafana
- [ ] Machine learning для анализа ошибок
- [ ] Автоматическое создание дашбордов
- [ ] A/B тестирование алертов
- [ ] Интеграция с системами CI/CD

## 📋 Контрольные списки

### Перед коммитом:
- [ ] Тесты проходят
- [ ] Документация обновлена
- [ ] Код reviewed
- [ ] Никаких TODO в коде

### Перед развертыванием:
- [ ] Все зависимости установлены
- [ ] Конфигурация проверена
- [ ] Тесты в staging пройдены
- [ ] Backup создан

---

**Система мониторинга готова для развития и поддержки!** 🚀

*Для разработчиков: следуйте этим рекомендациям для поддержания качества системы*