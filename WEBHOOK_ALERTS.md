# 🚨 Webhook сервер для алертов

## 📋 Описание

Простой Flask сервер для получения алертов из GlitchTip и отправки их в Telegram.

## 🛠 Настройка

### 1. Создайте webhook_server.py

```python
from flask import Flask, request
import requests

app = Flask(__name__)

# Настройки бота
TELEGRAM_TOKEN = "your-bot-token"
CHAT_ID = "your-chat-id"

@app.route('/glitchtip-webhook', methods=['POST'])
def webhook():
    data = request.json

    # Формируем сообщение для Telegram
    message = f"🚨 GlitchTip Alert\n\n{data['message']}"

    # Добавляем детали ошибки если есть
    if 'data' in data and 'issue' in data['data']:
        issue = data['data']['issue']
        message += f"\n\n🔍 Детали:"
        message += f"\n• Проект: {issue.get('project', {}).get('name', 'N/A')}"
        message += f"\n• Уровень: {issue.get('level', 'N/A')}"
        message += f"\n• URL: {issue.get('url', 'N/A')}"

    # Отправляем в Telegram
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    })

    return 'OK'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
```

### 2. Настройте в GlitchTip

1. В проекте перейдите в Settings → Alerts
2. Создайте правило:
   - Condition: "An issue is first seen"
   - Action: "Send a webhook"
   - URL: `http://your-server:5000/glitchtip-webhook`

### 3. Запуск

```bash
pip install flask requests
python webhook_server.py
```

## ✅ Результат

Теперь все ошибки из GlitchTip будут автоматически отправляться в ваш Telegram! 📱