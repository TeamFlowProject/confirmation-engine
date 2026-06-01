# confirmation-engine

Сервис **подтверждения команд** платформы **TeamFlow**. Слушает доменные события от
[`event-service`](../event-service), поддерживает собственную проекцию команд-заявок
(`team_application`) и треков с правилами, проверяет заявки по настраиваемым правилам и решает,
**подтвердить** (`CONFIRMED`), **отклонить** (`REJECTED`) или пометить **невалидной** (`INVALID`)
команду. Результаты публикуются обратно в Kafka, и `event-service` обновляет статус команды.

В отличие от `event-service`, здесь применён более строгий **Domain-Driven Design**: выделены
агрегаты, сущности, value-объекты, доменные события и репозитории-порты. Исходящие сообщения
отправляются через **transactional outbox** — гарантия «состояние и событие фиксируются атомарно».

- **Язык / рантайм:** Python 3.13
- **HTTP-фреймворк:** FastAPI + Uvicorn (вспомогательное read/-admin API)
- **Хранилище:** PostgreSQL (`psycopg`)
- **Шина событий:** Kafka (`aiokafka`; локально — Redpanda)
- **Паттерн доставки:** transactional outbox + outbox-worker
- **Миграции:** yoyo-migrations
- **Порт по умолчанию:** `8002` (в `.env.example`)

---

## Содержание

- [Назначение и роль в системе](#назначение-и-роль-в-системе)
- [Архитектура (DDD)](#архитектура-ddd)
- [Структура каталогов](#структура-каталогов)
- [Доменная логика](#доменная-логика)
- [Событийная модель (Kafka)](#событийная-модель-kafka)
- [Outbox-паттерн](#outbox-паттерн)
- [HTTP API](#http-api)
- [Конфигурация](#конфигурация)
- [Быстрый старт](#быстрый-старт)
- [Миграции, тесты, линт](#миграции-тесты-линт)
- [CI/CD](#cicd)

---

## Назначение и роль в системе

```
 event-service ──(team.*, track.*, member.*, invitation/join_request.accepted)──▶ confirmation-engine
       ▲                                                                                   │
       └──────────(team.validated / confirmed / rejected / became_invalid)─────────────────┘
```

`event-service` управляет составом команд, а `confirmation-engine` отвечает на вопрос «соответствует
ли команда правилам трека и есть ли для неё свободный слот». Он держит собственную модель данных
(проекцию), чтобы принимать решения автономно, не дёргая `event-service` синхронно.

## Архитектура (DDD)

```
controller/        ── входящий слой: Kafka-консьюмер + REST-роутер
   ├── kafka/       consumer, dto, protocols, topics
   └── rest/v1/     confirmation_router, schemas, protocols
service/           ── прикладной слой: ConfirmationService (оркестрация сценариев)
domain/            ── ядро (не зависит от инфраструктуры)
   ├── aggregates/      team_application, track
   ├── entities/        member, role
   ├── value_objects/   confirmation_rule, team_status
   ├── events/          доменные события (DomainEvent + наследники)
   └── repositories/    порты репозиториев (интерфейсы)
adapters/          ── исходящий слой: реализации портов
   ├── repositories/    postgres-реализации team_application / track
   ├── kafka/           producer
   ├── serializers/     сериализация правил и событий
   └── workers/         outbox_worker (релей событий в Kafka)
```

Поток управления: **Kafka-консьюмер** десериализует входящее событие в DTO → вызывает
**`ConfirmationService`** → сервис загружает агрегаты из **репозиториев**, выполняет доменную логику
(проверку правил, смену статуса) и сохраняет результат. Доменные события складываются в таблицу
outbox, откуда их асинхронно разбирает **`OutboxWorker`** и публикует в Kafka.

## Структура каталогов

```
src/
├── main.py                    # Typer-CLI: run / migrate / migrate-down / migrate-drop
├── application.py             # сборка: пул БД, producer, consumer, outbox-worker, REST
├── config.py                  # Pydantic Settings
├── domain/
│   ├── aggregates/team_application.py   # агрегат «заявка команды» (validate/confirm/reject/...)
│   ├── aggregates/track.py              # агрегат «трек» с набором правил подтверждения
│   ├── entities/{member,role}.py
│   ├── value_objects/confirmation_rule.py   # RoleConfirmationRule, TeamSizeConfirmationRule
│   ├── value_objects/team_status.py         # NONE/SUBMITTED/VALIDATED/CONFIRMED/REJECTED/INVALID
│   ├── events/events.py                 # TeamValidated / TeamConfirmed / TeamRejected / ...
│   └── repositories/                    # порты
├── service/confirmation.py    # ConfirmationService
└── adapters/
    ├── repositories/{team_application,track}/postgres/
    ├── kafka/producer.py
    ├── serializers/
    └── workers/outbox_worker.py
migrations/                    # SQL-миграции yoyo (outbox, roles, members, tracks, applications, связи)
tests/
```

## Доменная логика

### Правила подтверждения (`confirmation_rule.py`)

Правила — value-объекты с методом `check(team, track) -> str | None` (вернул строку = причина
отклонения; вернул `None` = правило пройдено):

- **`RoleConfirmationRule`** — проверяет состав ролей. Без учёта количества: каждая обязательная роль
  трека должна быть представлена хотя бы одним участником. С учётом (`take_into_account_role_count`):
  число участников каждой роли должно точно совпадать с `role.count`.
- **`TeamSizeConfirmationRule`** — размер команды должен попадать в `[min_team_size, max_team_size]`.

### Сценарии `ConfirmationService`

- **Регистрация/изменение состава** (`create_team`, `update_team`, `add_member`, `delete_member`,
  `change_member_role`) — обновляют проекцию заявки и при необходимости перепроверяют её.
- **`submit_team`** — валидирует заявку относительно трека и наличия свободных слотов
  (`max_team_count`). Уже `CONFIRMED` заявки игнорируются.
- **`confirm_team` / `reject_team`** — явное подтверждение/отклонение.
- **`confirm_next_from_waitlist`** — при освобождении слота подтверждает следующую ожидающую заявку
  (логика листа ожидания).
- **`expire_grace_periods`** — отклоняет заявки, у которых истёк grace-период после того, как команда
  стала невалидной (вызывается инфраструктурой/воркером).

Статусы заявки (`TeamStatus`): `NONE → SUBMITTED → VALIDATED → CONFIRMED` либо `REJECTED` / `INVALID`.

## Событийная модель (Kafka)

### Потребляет (от `event-service`)

Маппинг «топик → DTO» задан в [`src/controller/kafka/topics.py`](src/controller/kafka/topics.py):

| Топик | Обрабатывается как |
|-------|--------------------|
| `event_service.team.created` | создание заявки |
| `event_service.team.submitted` | отправка на проверку |
| `event_service.team.updated` | изменение заявки |
| `event_service.team.member.kicked` / `.left` | исключение / выход участника |
| `event_service.team.member.role_changed` | смена роли участника |
| `event_service.invitation.accepted` / `event_service.join_request.accepted` | вступление участника |
| `event_service.track.created` / `.updated` | создание/обновление правил трека |

Консьюмер работает с ручным коммитом оффсетов (`enable_auto_commit=False`).

### Публикует (доменные события → outbox → Kafka)

| Событие | Топик |
|---------|-------|
| `TeamValidated` | `confirmation_engine.team.validated` |
| `TeamConfirmed` | `confirmation_engine.team.confirmed` |
| `TeamRejected` | `confirmation_engine.team.rejected` (с полем `reason`) |
| `TeamBecameInvalid` | `confirmation_engine.team.became_invalid` (с `grace_deadline`) |
| `SlotReleased` | `confirmation_engine.team.slot_released` |

Эти топики `event-service` потребляет, чтобы обновлять статусы команд.

## Outbox-паттерн

Доменные события не публикуются напрямую: они пишутся в таблицу `outbox_events` (статус `PENDING`) в
той же транзакции, что и изменение состояния. Фоновый
[`OutboxWorker`](src/adapters/workers/outbox_worker.py) с интервалом ~200 мс выбирает `PENDING`-записи
и публикует их в Kafka, после чего помечает обработанными. Это гарантирует **at-least-once** доставку
и согласованность «состояние ⇄ событие» даже при сбоях продюсера.

## HTTP API

Вспомогательное REST API (префикс `/api/v1/confirmation`, см.
[`confirmation_router.py`](src/controller/rest/v1/confirmation_router.py)) — в основном для чтения и
ручного администрирования:

| Метод | Путь | Описание |
|-------|------|----------|
| `POST` | `/rule/{track_id}` | Создать/задать правило подтверждения для трека → `201` |
| `POST` | `/applications` | Подтвердить команду вручную (`ConfirmTeamRequest`) |
| `GET` | `/track/{track_id}/applications` | Все заявки трека |
| `GET` | `/rule/{track_id}` | Правило трека |
| `GET` | `/track/{track_id}/teams` | Подтверждённые команды трека |

## Конфигурация

Читается из `.env` (см. [`.env.example`](.env.example)) через `pydantic-settings`.

| Переменная | По умолчанию | Назначение |
|------------|--------------|------------|
| `HTTP_HOST` / `HTTP_PORT` | `0.0.0.0` / `8002` | адрес HTTP-сервера |
| `DATABASE_DSN` | `postgresql://user:password@localhost:5432/confirmation_db` | DSN PostgreSQL |
| `DATABASE_MIN_CONNECTIONS` / `DATABASE_MAX_CONNECTIONS` | `1` / `10` | размер пула |
| `KAFKA_BOOTSTRAP` | `localhost:9092` | брокеры Kafka |
| `KAFKA_TOPIC_COMMANDS` / `KAFKA_TOPIC_EVENTS` | `confirmation-commands` / `event-events` | имена топиков |
| `KAFKA_GROUP_ID` | `confirmation-engine` | группа консьюмера |
| `LOG_LEVEL` | `INFO` | уровень логирования |

## Быстрый старт

```bash
uv sync
cp .env.example .env

# инфраструктура (Postgres + Redpanda)
docker compose up -d postgres redpanda

make migrate-up     # python -m src.main migrate
make run            # python -m src.main run
```

Или целиком в Docker: `docker compose up --build`. Полный запуск платформы — в репозитории
[`compose`](../compose).

## Миграции, тесты, линт

```bash
make migrate-up / migrate-down / migrate-drop   # управление миграциями
make unit-test        # -m unit, с покрытием
make integration-test # -m integration (testcontainers, нужен Docker)
make test             # всё вместе
make lint             # pyright + ruff check + ruff format --check
make lint-fix         # ruff check --fix + ruff format
```

Схема БД: `outbox_events`, `roles`, `members`, `tracks`, `team_applications` и таблицы связей
ролей↔треков и участников↔заявок.

## CI/CD

GitHub Actions (`.github/workflows`) переиспользует общие шаблоны из
[`cicd-templates`](../cicd-templates): ruff + pyright, юнит- и интеграционные тесты — на push/PR в
`main` и `develop`.
