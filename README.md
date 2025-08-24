# LeonidBot
- Пет-проект для изучения возможностей Telegram-ботов. [LeonidBot.t.me](https://LeonidBot.t.me)
- Бот должен включать в себя различные полезные утилиты (таск-система, тайм-менеджер, интеграции с календарями, напоминалки, управление TG-группами)
- Для усложнения задачи поставил себе цель прикрутить веб-морду с авторизацией через Telegram.
- В качестве веб морды буду использовать Flask/FastApi/Django.

## Структура проекта

- `bot/` – Telegram-бот и его обработчики
- `web/` – веб-приложение и связанные утилиты
- `core/` – общие модули (`db.py`, `models.py`, `services/`)

## Правила разработки

- `/core` содержит общие модели, сервисы, утилиты и логирование;
- `/bot` хранит только код Telegram-бота (хендлеры, FSM-состояния, роутинг aiogram);
- `/web` содержит только FastAPI-роуты, шаблоны и зависимости;
- новую общую бизнес-логику нужно выносить в `/core`, чтобы переиспользовать её в боте и веб-интерфейсе.

## Backlog внедрения нового функционала:
- [x] Асинхронный бэкенд на aiogram и SQLAlchemy с подключением к PostgreSQL.
- [x] Определены модели пользователей, групп, каналов и настроек логирования.
- [x] Сервис `UserService` для работы с пользователями, группами и логированием.
- [x] Команды `/start`, `/cancel`, `/birthday`, `/contact` для взаимодействия с пользователем.
- [x] Команда `/group` для управления группами и декоратор проверки членства.
- [x] Логирование событий: middleware, пересылка неизвестных сообщений в группу логов, ответы админа, команды `/setloglevel` и `/getloglevel`.
- [x] Декоратор `role_required` для проверки ролей пользователей.
- [x] Заготовка FSM для обновления контактных данных и описания групп.
- [x] Каркас веб-приложения на FastAPI для работы через webhook.
- [ ] Каркас таск-системы.
- [ ] Каркас тайм-менеджера.
- [ ] Каркас системы напоминаний.
- [ ] Напоминания по таскам.
- [ ] Каркас работы с календарём.
- [ ] Интеграция с Google-календарём.
- [ ] Напоминания по Google-календарю.
- [ ] Реализовать команды `/setfullname`, `/setemail`, `/setphone`, `/setbirthday` и редактирование описаний групп.
- [ ] Веб-интерфейс с авторизацией через Telegram и админ-панелью.
- [ ] Рефакторинг сервисов и логирования, устранение дублирования кода, покрытие тестами.
- [ ] Разделение кода на модули и добавление миграций БД.
- [ ] Тесты и CI/CD для бота и веб-сервера
- [ ] Дополнительные модули: заметки, трекер привычек, учёт финансов, интеграция с внешними задачниками и календарями.

## Веб-морда

Веб-приложение на FastAPI предоставляет админ-панель с авторизацией через Telegram.

### Настройка `.env`

Создайте файл `.env` в корне репозитория со следующими переменными:

```dotenv
BOT_TOKEN=123456789:AA...your...token
TELEGRAM_BOT_USERNAME=YourBotName   # БЕЗ @; можно оставить BOT_USERNAME — тоже подхватится
PUBLIC_BASE_URL=http://109.196.99.158:5800  # можно указать домен или IP с портом
SESSION_MAX_AGE=86400
ADMIN_TELEGRAM_IDS=123,456  # список Telegram-ID администраторов через запятую
```

### Telegram Login Widget

1. В @BotFather сделайте `/setdomain` и укажите домен или IP, где открывается `/auth/login` (без схемы).
2. `TELEGRAM_BOT_USERNAME` — без `@`.
3. Если видите «Bot domain invalid», домен страницы не совпадает с заданным у бота или указан username с `@`.

### Запуск

Установите зависимости и запустите сервер:

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 5800
# или
uvicorn web:app --host 0.0.0.0 --port 5800
```

### Навигация

- `/` → редирект на `/auth/login`
- `/auth/login` — кнопка входа Telegram
- `/auth/callback` — проверка подписи, апсерт пользователя → редирект на `/admin`
- `/admin` → редирект на `/admin/users`
- `/admin/users`, `/admin/groups`, `/profile/{telegram_id}` — админские страницы

### Траблшутинг

- «ValidationError / Extra inputs…» → теперь игнорируются (`extra='ignore'`).
- «Field required: TELEGRAM_BOT_USERNAME» → используйте `TELEGRAM_BOT_USERNAME` или `BOT_USERNAME`.
- «Bot domain invalid» → проверьте `/setdomain` и username без `@`.

## Панель администратора на основе ролей

Роли, определённые в файле `models.py`, определяют доступ к функциям панели администратора:

- `ban` – у меня нет доступа к боту.
- `single` – управляйте только личными данными.
- `multiplayer` – просмотр участников группы.
- `moderator` – отредактируйте информацию об участнике.
- `admin` – полный доступ ко всем функциям.

## Сервисы systemd (Debian 12)

Этот документ описывает, как запускать **бота** (`python -m bot.main`) и **веб-приложение** (`uvicorn web:app`) как два независимых сервиса `systemd`.

### Требования

- Проект расположен в **`/sd/tg/LeonidBot`**
- Виртуальное окружение Python: **`/sd/tg/LeonidBot/venv`**
- Debian 12, `systemd`, права sudo

Проверьте наличие интерпретатора:
```bash
ls -l /sd/tg/LeonidBot/venv/bin/python
```

### Структура сервисов

Будут созданы два сервиса:

- `leonidbot-bot.service` — Telegram-бот
- `leonidbot-web.service` — FastAPI/uvicorn (порт 5800)

Сервисы независимы: их можно запускать/останавливать и журналировать отдельно.

#### 1) Unit для бота

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

#### 2) Unit для веб-приложения

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

#### 3) Применение и автозапуск

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

#### 4) Управление сервисами

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

#### 5) Логи

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

#### 6) Обновление кода и зависимостей

```bash
cd /sd/tg/LeonidBot
# обновление зависимостей
./venv/bin/pip install -U -r requirements.txt
# перезапуск сервисов
sudo systemctl restart leonidbot-bot.service leonidbot-web.service
```

#### 7) (Опционально) Запуск от отдельного пользователя

```bash
sudo adduser --system --group --home /sd/tg/LeonidBot leonidbot
sudo chown -R leonidbot:leonidbot /sd/tg/LeonidBot
# затем раскомментируйте User/Group в обоих unit-файлах, daemon-reload и restart
```

#### 8) Типичные проблемы

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

#### 9) Проверка, что всё работает

```bash
# Бот отвечает? (смотрите свои логи бота)
journalctl -u leonidbot-bot.service -n 100

# Веб на месте?
curl -I http://127.0.0.1:5800/
```

Готово: бот и веб-часть запускаются автоматически вместе с системой и управляются через `systemctl`.
