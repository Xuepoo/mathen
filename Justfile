set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

# Python card validation, tests, and formatting checks.
python-check: python-validate python-test python-format python-lint

python-validate:
    uv run mathen validate

python-test:
    uv run python -m unittest discover -s tests -v

python-format:
    uv run ruff format --check .

python-lint:
    uv run ruff check .

# TypeScript checks for the Worker, browser, and MCP packages.
typescript-check:
    bun run check

api-test:
    bun run test:api

web-test:
    bun run test:web

mcp-test:
    bun test apps/mcp/src/*.test.ts

test: python-test api-test web-test mcp-test

build:
    bun run build

# Run the local D1 migrations and deterministic seed from a clean database.
db-reset:
    bun run db:reset:local

db-migrate:
    bun run db:migrate:local

db-seed:
    bun run db:seed:local

db-seed-remote:
    bun run db:seed:remote

deploy:
    bun run deploy

db-query:
    bun run db:query:local

# Run the complete local quality gate.
check: python-check typescript-check test build

# Run the local API and Vite development servers together.
dev:
    bun run dev

api:
    bun run dev:api

web:
    bun run dev:web

mcp:
    bun run mcp
