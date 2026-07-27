SHELL := /bin/bash

LAKEBASE_COMPOSE := docker compose -f compose.yaml -f compose.lakebase.yaml --env-file .env.lakebase

.PHONY: help dev-local dev-lakebase refresh-lakebase dev-down hooks-install hooks-uninstall check

.DEFAULT_GOAL := help

help: ## Show available commands
	@awk -F ':.*## ' '/^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-local: ## Start the app with its local PostgreSQL container
	docker compose up --build

dev-lakebase: ## Start the app with this Git branch's Lakebase branch
	@./scripts/lakebase-branch.sh
	$(LAKEBASE_COMPOSE) up --build

refresh-lakebase: ## Refresh the hourly credential and recreate the backend
	@./scripts/lakebase-branch.sh --refresh-only
	$(LAKEBASE_COMPOSE) up -d --force-recreate backend

dev-down: ## Stop local or Lakebase development containers
	docker compose down

hooks-install: ## Enable Lakebase provisioning after branch checkouts
	@./scripts/manage-post-checkout-hook.sh install

hooks-uninstall: ## Remove this clone's post-checkout registration
	@./scripts/manage-post-checkout-hook.sh uninstall

check: ## Validate branch naming and both Compose modes
	@./scripts/lakebase-branch.sh --self-test
	@docker compose config --quiet
	@PGHOST=lakebase.example PGUSER=developer@example.com PGPASSWORD=test \
		ENDPOINT_NAME=projects/test/branches/test/endpoints/primary \
		docker compose -f compose.yaml -f compose.lakebase.yaml config --format json | \
		jq -e '.services.postgres == null and .services.backend.depends_on.postgres.required == false and .services.backend.environment.PGHOST == "lakebase.example"' >/dev/null
