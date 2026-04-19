DB_DSN ?= postgresql://user:password@localhost:5432/confirmations
MIGRATIONS_DIR = migrations

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
