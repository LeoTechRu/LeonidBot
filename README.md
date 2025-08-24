# LeonidBot — сервисы systemd (Debian 12)

Этот документ описывает, как запускать **бота** (`python -m bot.main`) и **веб-приложение** (`uvicorn web:app`) как два независимых сервиса `systemd`.

## Требования

- Проект расположен в **`/sd/tg/LeonidBot`**
- Виртуальное окружение Python: **`/sd/tg/LeonidBot/venv`**
- Debian 12, `systemd`, права sudo

Проверьте наличие интерпретатора:
```bash
ls -l /sd/tg/LeonidBot/venv/bin/python
```

## Структура сервисов

Будут созданы два сервиса:

- `leonidbot-bot.service` — Telegram-бот
- `leonidbot-web.service` — FastAPI/uvicorn (порт 5800)

Сервисы независимы: их можно запускать/останавливать и журналировать отдельно.

### 1) Unit для бота

Создайте файл `/etc/systemd/system/leonidbot-bot.service`:

```ini
[Unit]
Description=LeonidBot Telegram Bot Service
After=network.target

[Service]
WorkingDirectory=/sd/tg/LeonidBot
Environment="PATH=/sd/tg/LeonidBot/venv/bin"
# Если используете переменные окружения — раскомментируйте следующую строку и создайте .env:
# EnvironmentFile=/sd/tg/LeonidBot/.env
ExecStart=/sd/tg/LeonidBot/venv/bin/python -m bot.main
Restart=always
# (опционально) запуск не от root:
# User=leonidbot
# Group=leonidbot

[Install]
WantedBy=multi-user.target
```

### 2) Unit для веб-приложения

Создайте файл `/etc/systemd/system/leonidbot-web.service`:

```ini
[Unit]
Description=LeonidBot Web Service (FastAPI/Uvicorn)
After=network.target

[Service]
WorkingDirectory=/sd/tg/LeonidBot
Environment="PATH=/sd/tg/LeonidBot/venv/bin"
# EnvironmentFile=/sd/tg/LeonidBot/.env
ExecStart=/sd/tg/LeonidBot/venv/bin/uvicorn web:app --host 0.0.0.0 --port 5800
Restart=always
# User=leonidbot
# Group=leonidbot

[Install]
WantedBy=multi-user.target
```

> Если порт 5800 занят — измените его здесь и в реверс-прокси (Apache/Nginx).

### 3) Применение и автозапуск

```bash
# Подхватить новые unit-файлы
sudo systemctl daemon-reload

# Включить автозапуск при загрузке ОС
sudo systemctl enable leonidbot-bot.service
sudo systemctl enable leonidbot-web.service

# Запустить сейчас
sudo systemctl start leonidbot-bot.service
sudo systemctl start leonidbot-web.service

# Проверить статус
sudo systemctl status leonidbot-bot.service
sudo systemctl status leonidbot-web.service
```

### 4) Управление сервисами

```bash
# Остановка
sudo systemctl stop leonidbot-bot.service
sudo systemctl stop leonidbot-web.service

# Перезапуск (после обновления кода/конфига)
sudo systemctl restart leonidbot-bot.service
sudo systemctl restart leonidbot-web.service

# Перезагрузка unit-файлов после правок .service
sudo systemctl daemon-reload
```

### 5) Логи

Последние 100 строк:

```bash
journalctl -u leonidbot-bot.service -n 100
journalctl -u leonidbot-web.service -n 100
```

Онлайн-хвост (реальное время):

```bash
journalctl -fu leonidbot-bot.service
journalctl -fu leonidbot-web.service
```

Полезные варианты:

```bash
# Логи за сегодня
journalctl -u leonidbot-bot.service --since today

# Только ошибки и выше
journalctl -p err -u leonidbot-web.service -n 100
```

### 6) Обновление кода и зависимостей

```bash
cd /sd/tg/LeonidBot
# обновление зависимостей
./venv/bin/pip install -U -r requirements.txt
# перезапуск сервисов
sudo systemctl restart leonidbot-bot.service leonidbot-web.service
```

### 7) (Опционально) Запуск от отдельного пользователя

```bash
sudo adduser --system --group --home /sd/tg/LeonidBot leonidbot
sudo chown -R leonidbot:leonidbot /sd/tg/LeonidBot
# затем раскомментируйте User/Group в обоих unit-файлах, daemon-reload и restart
```

### 8) Типичные проблемы

```
status=203/EXEC / No such file or directory
```

Неверный путь в ExecStart или PATH. Проверьте, что существуют:

- `/sd/tg/LeonidBot/venv/bin/python`
- `/sd/tg/LeonidBot/venv/bin/uvicorn`

и что WorkingDirectory указывает на корень проекта.

```
Address already in use
```

Порт занят. Поменяйте `--port` в `leonidbot-web.service` и настройку реверс-прокси.

```
Не видны переменные окружения
```

Вынесите их в `/sd/tg/LeonidBot/.env` и подключите `EnvironmentFile=...`, затем:

```bash
sudo systemctl daemon-reload && sudo systemctl restart <service>
```

### 9) Проверка, что всё работает

```bash
# Бот отвечает? (смотрите свои логи бота)
journalctl -u leonidbot-bot.service -n 100

# Веб на месте?
curl -I http://127.0.0.1:5800/
```

Готово: бот и веб-часть запускаются автоматически вместе с системой и управляются через `systemctl`.
