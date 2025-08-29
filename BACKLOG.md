# Backlog (Single Source of Truth)

## Оглавление
- [Решения по архитектуре (ПРОЧНО)](#решения-по-архитектуре-прочно)
- [Эпики](#эпики)
  - [E1: PARA-first доменная модель](#e1-para-first-доменная-модель)
  - [E2: Миграции БД и индексы](#e2-миграции-бд-и-индексы)
  - [E3: API](#e3-api)
  - [E4: Синхронизация с Google Calendar](#e4-синхронизация-с-google-calendar)
  - [E5: Telegram-уведомления](#e5-telegram-уведомления)
  - [E6: ICS-фиды](#e6-ics-фиды)
  - [E7: Роли и режимы](#e7-роли-и-режимы)
  - [E8: Совместимость с напоминаниями](#e8-совместимость-с-напоминаниями)
  - [E9: Тесты и документация](#e9-тесты-и-документация)
- [Что делаем в первом релизе](#что-делаем-в-первом-релизе)

## Решения по архитектуре (ПРОЧНО)
- **Alarm** хранится внутри `CalendarItem` (эквивалент `VALARM`).
- **Время**: UTC + `tzid`, поддержка `RRULE` без материализации бесконечного ряда.
- **Google**: сохраняем `syncToken`, `resource_id`/`channel_id`/`expiration`, `extendedProperties.private {app_item_id, app_kind, app_project_id, app_area_id, checksum}`.
- **Telegram**: `project → channels` (`chat_id < 0`), правила уведомлений `on_create`, `on_change_time`, `pre_due`, `digest_weekly`.
- **PARA-инвариант**: `(project_id NOT NULL) OR (area_id NOT NULL)` для каждого `CalendarItem`/`Alarm`.

## Эпики

### E1: PARA-first доменная модель (Areas, Projects, CalendarItem, Alarm)
**User Stories**
1. Как пользователь, я создаю **Area** «Маркетинг» и привязываю к ней **Projects**, чтобы группировать работу по PARA.
2. Как пользователь, я добавляю `CalendarItem` «Release v2» со временем начала/окончания и `Alarm`.
3. Как пользователь, я связываю каждый `CalendarItem` с Project или Area, чтобы не терять контекст.

**Acceptance Criteria**
- Пример: создание Project с `area_id=1` и именем «Landing» успешно и отображается в Area «Маркетинг».
- Пример: создание элемента «Release v2» со стартом `2025-05-01T09:00Z` и `alarm=15m` планирует уведомление за 15 минут.
- Попытка сохранить элемент без `project_id` и `area_id` отклоняется ошибкой инварианта PARA.

### E2: Миграции БД и индексы (PostgreSQL)
**User Stories**
1. Как разработчик, я запускаю Alembic-модели для таблиц: `areas`, `projects`, `calendar_items`, `alarms`.
2. Как разработчик, я реализую CHECK-инвариант PARA и необходимые индексы.

**Acceptance Criteria**
- `alembic upgrade head` создаёт таблицы с внешними ключами и индексами по `(project_id, area_id, start_ts)`.
- Вставка `calendar_item` с обоими NULL (`project_id` и `area_id`) завершается ошибкой CHECK.

### E3: API (FastAPI): `/calendar/items`, `/calendar/agenda`, `/calendar/feed.ics`, `/projects/{id}/notifications`
**User Stories**
1. Как пользователь, я получаю список и создаю элементы через `/calendar/items`.
2. Как пользователь, я просматриваю повестку по диапазону через `/calendar/agenda`.
3. Как пользователь, я подписываюсь на ICS через `/calendar/feed.ics`.
4. Как участник проекта, я вижу настройки уведомлений на `/projects/{id}/notifications`.

**Acceptance Criteria**
- `POST /calendar/items` с валидным JSON возвращает созданный объект с `id`.
- `GET /calendar/agenda?from=2025-05-01&to=2025-05-07` отдаёт элементы в диапазоне.
- Открытие `/calendar/feed.ics` в внешнем календаре показывает VEVENT с VALARM.
- `GET /projects/42/notifications` отдаёт список каналов.

### E4: Синхронизация с Google Calendar
**User Stories**
1. Как пользователь, я подключаю Google через OAuth и импортирую события при начальной синхронизации.
2. Как пользователь, я делаю инкрементальную синхронизацию по `syncToken`.
3. Как разработчик, я обрабатываю push-уведомления через `channels.watch`.
4. Как разработчик, я храню `extendedProperties.private`.

**Acceptance Criteria**
- OAuth сохраняет `refresh_token`, первая синхронизация подтягивает события.
- Использование сохранённого `syncToken` возвращает только изменённые события.
- Push `POST` с известным `resource_id` инициирует повторную синхронизацию.
- `extendedProperties.private` содержит `{app_item_id:123, app_kind:'calendar', app_project_id:7, checksum:'abc'}`.

### E5: Telegram-уведомления для проектных групп
**User Stories**
1. Как админ проекта, я регистрирую групповой чат (`chat_id < 0`) для уведомлений.
2. Как участник, я получаю сообщение при создании элемента (`on_create`).
3. Как участник, я получаю напоминание до дедлайна (`pre_due`) и еженедельный дайджест.

**Acceptance Criteria**
- `POST /projects/42/notifications` с `chat_id=-1001` привязывает канал.
- Создание элемента отправляет в Telegram `sendMessage` в канал.
- Элемент со стартом `2025-05-01T09:00Z` и `pre_due=30m` шлёт сообщение в `08:30Z`.
- Документация: [как добавить бота и получить chat_id](./docs/notifications/telegram.md).

### E6: ICS-фиды с VEVENT/VTODO+VALARM
**User Stories**
1. Как пользователь, я экспортирую элементы и задачи в стандартный ICS.
2. Как пользователь, я вижу `VALARM` для элементов с напоминанием.

**Acceptance Criteria**
- Скачанный фид содержит VEVENT для событий и VTODO для задач.
- Каждое событие с напоминанием включает компонент VALARM.

### E7: Роли и режимы
**User Stories**
1. Как индивидуальный пользователь, я работаю в режиме **single**.
2. Как команда, мы переключаемся в режим **multiplayer** для общих Projects.

**Acceptance Criteria**
- Пользователь без команды видит только личные данные в single-режиме.
- В multiplayer-режиме участники проекта могут видеть и редактировать общие элементы.

### E8: Совместимость: `/reminders` → календарь, миграция «сиротских» напоминаний
**User Stories**
1. Как пользователь, я вижу старые напоминания в новом календаре.
2. Как разработчик, я мигрирую «сиротские» напоминания в `CalendarItem+Alarm`.

**Acceptance Criteria**
- Переход на `/reminders` отображает новый календарный UI.
- Скрипт миграции преобразует напоминание с `due=2024-12-31` в `calendar_item` с `alarm`.

### E9: Тесты и документация, фичефлаг `CALENDAR_V2_ENABLED`
**User Stories**
1. Как разработчик, я включаю модуль через фичефлаг.
2. Как разработчик, я имею тесты и документацию для поддержки качества.

**Acceptance Criteria**
- `.env.example` содержит `CALENDAR_V2_ENABLED=true`.
- CI запускает тесты на синхронизацию, API и уведомления.

## Что делаем в первом релизе
- [ ] E1–E2: доменная модель и миграции
- [ ] E3: базовые API `/calendar/items`, `/calendar/agenda`
- [ ] E4: OAuth и первичная синхронизация Google
- [ ] E5: Telegram `on_create` и `pre_due`
- [ ] E6: экспорт ICS-фида
- [ ] E9: фичефлаг, документация, `.env.example`
