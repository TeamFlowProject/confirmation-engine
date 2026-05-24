# confirmation-engine

Сервис подтверждения команд и правил (TeamFlow).

## Переменные окружения (Docker Compose)

Для **каждого** сервиса в `compose.yaml` — свой файл (в git не попадают, кроме example):

| Сервис | Файл |
|--------|------|
| KrakenD | `.env_krakend` |
| confirmation-engine | `.env_event_service` |
| PostgreSQL | `.env_postgres` |
| Redpanda | `.env_redpanda` |
| Redpanda Console | `.env_redpanda_console` |

В репозитории только **`.env_event_service.example`**.

Создать все файлы одной командой:

```bash
make init-env
```

Или вручную: `cp .env_event_service.example .env_event_service` и дописать остальные по таблице выше / из `make init-env`.

## Локальный запуск (Docker Compose)

```bash
make init-env
make compose-up
```

Остановка:

```bash
make compose-down
```

`make compose-up` передаёт все `.env_*` в `docker compose`, чтобы подставлялись порты и параметры из каждого файла.

### Точки входа

| Сервис | URL |
|--------|-----|
| API Gateway (KrakenD) | http://localhost:8000 |
| Confirmation Engine (напрямую) | http://localhost:8002 |
| Redpanda Console | http://localhost:8080 |

HTTP API через gateway: `http://localhost:8000/rules`, `http://localhost:8000/applications`, …

## Разработка без Docker

```bash
cp .env_event_service.example .env_event_service
# для локального Postgres/Kafka поправьте DATABASE_DSN и KAFKA_BOOTSTRAP

uv sync
uv run python -m src.main migrate
uv run python -m src.main run
```

## Make

```bash
make lint-fix && make lint
make unit-test
make integration-test
make compose-config   # проверка compose.yaml
```
