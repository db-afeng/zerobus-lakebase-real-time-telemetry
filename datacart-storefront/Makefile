SHELL := /bin/bash

LAKEBASE_COMPOSE := docker compose -f compose.yaml -f compose.lakebase.yaml --env-file .env.lakebase

.PHONY: help dev-local dev-lakebase refresh-lakebase dev-down dev-destroy hooks-install hooks-uninstall check

.DEFAULT_GOAL := help

help: ## Show available commands
	@awk -F ':.*## ' '/^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-local: ## Start the app with its local PostgreSQL container
	docker compose up --build

dev-lakebase: ## Start the app with this Git branch's Lakebase branch
	@status=0; ./scripts/lakebase-branch.sh --wait-for-hook || status=$$?; \
		if [[ $$status -eq 2 ]]; then \
			./scripts/lakebase-branch.sh; \
		elif [[ $$status -ne 0 ]]; then \
			exit $$status; \
		fi
	$(LAKEBASE_COMPOSE) up --build

refresh-lakebase: ## Refresh the hourly credential and recreate the backend
	@./scripts/lakebase-branch.sh --refresh-only
	$(LAKEBASE_COMPOSE) up -d --force-recreate backend

dev-down: ## Stop local or Lakebase development containers
	docker compose down

dev-destroy: ## Stop local or Lakebase development containers
	docker compose down --volumes

hooks-install: ## Enable Lakebase provisioning after branch checkouts
	@./scripts/manage-post-checkout-hook.sh install

hooks-uninstall: ## Remove this clone's post-checkout registration
	@./scripts/manage-post-checkout-hook.sh uninstall

check: ## Validate branch naming and both Compose modes
	@./scripts/lakebase-branch.sh --self-test
	@python3 -c 'from server.runtime import get_runtime_info; local = get_runtime_info({"APP_RUNTIME": "docker"}); assert local == {"backend": "docker", "database": {"location": "local-docker", "project": None, "branch": None}}; lakebase = get_runtime_info({"DATABRICKS_APP_NAME": "storefront", "ENDPOINT_NAME": "projects/demo-project/branches/dev-alex/endpoints/primary"}); assert lakebase == {"backend": "production", "database": {"location": "lakebase", "project": "demo-project", "branch": "dev-alex"}}'
	@docker compose config --quiet
	@PGHOST=lakebase.example PGUSER=developer@example.com PGPASSWORD=test \
		ENDPOINT_NAME=projects/test/branches/test/endpoints/primary \
		docker compose -f compose.yaml -f compose.lakebase.yaml config --format json | \
		jq -e '.services.postgres == null and .services.backend.depends_on.postgres.required == false and .services.backend.environment.PGHOST == "lakebase.example"' >/dev/null
