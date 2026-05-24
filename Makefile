DB_DSN ?= postgresql://user:password@localhost:5432/event_db
MIGRATIONS_DIR = migrations
COMPOSE_FILE = compose.yaml
COMPOSE_ENV_FILES = \
	--env-file .env_krakend \
	--env-file .env_event_service \
	--env-file .env_postgres \
	--env-file .env_redpanda \
	--env-file .env_redpanda_console

.PHONY: run
run:
	python -m src.main run

.PHONY: unit-test
unit-test:
	uv run pytest --cov=src -m unit

.PHONY: integration-test
integration-test:
	uv run pytest --cov=src -m integration

.PHONY: test
test: unit-test integration-test

.PHONY: migrate-up
migrate-up:
	python -m src.main migrate

.PHONY: migrate-down
migrate-down:
	python -m src.main migrate-down

.PHONY: migrate-drop
migrate-drop:
	python -m src.main migrate-drop

.PHONY: install-tools
install-tools:
	uv tool install pyright
	uv tool install ruff

.PHONY: lint
lint:
	uv tool run pyright .
	uv tool run ruff check .
	uv tool run ruff format --check .

.PHONY: lint-fix
lint-fix:
	uv tool run ruff check --fix .
	uv tool run ruff format .

.PHONY: compose-config compose-up compose-down init-env
compose-config:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) config

compose-up:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) up --build

compose-down:
	docker compose $(COMPOSE_ENV_FILES) -f $(COMPOSE_FILE) down

init-env:
	@test -f .env_event_service || cp .env_event_service.example .env_event_service
	@test -f .env_krakend || printf '%s\n' 'KRAKEND_PORT=8000' > .env_krakend
	@test -f .env_postgres || printf '%s\n' \
		'POSTGRES_PORT=5432' 'POSTGRES_DB=event_db' 'POSTGRES_USER=user' 'POSTGRES_PASSWORD=password' > .env_postgres
	@test -f .env_redpanda || printf '%s\n' \
		'REDPANDA_EXTERNAL_PORT=19092' \
		'REDPANDA_KAFKA_ADDR=internal://0.0.0.0:9092,external://0.0.0.0:19092' \
		'REDPANDA_ADVERTISE_KAFKA_ADDR=internal://redpanda:9092,external://localhost:19092' \
		'REDPANDA_SMP=1' 'REDPANDA_MEMORY=512M' 'REDPANDA_LOG_LEVEL=warn' > .env_redpanda
	@test -f .env_redpanda_console || printf '%s\n' \
		'REDPANDA_CONSOLE_PORT=8080' 'KAFKA_BROKERS=redpanda:9092' > .env_redpanda_console
	@echo "Env files are ready."
