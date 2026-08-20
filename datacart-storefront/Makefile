SHELL := /bin/bash

DEV_CONTEXT_ID := $(shell bash ./scripts/dev-context-id.sh)
ifeq ($(strip $(DEV_CONTEXT_ID)),)
$(error Unable to determine development context ID)
endif
COMPOSE_PROJECT_NAME := datacart-$(DEV_CONTEXT_ID)
export COMPOSE_PROJECT_NAME

COMPOSE := docker compose -p $(COMPOSE_PROJECT_NAME)
LAKEBASE_COMPOSE := $(COMPOSE) -f compose.yaml -f compose.lakebase.yaml --env-file .env.lakebase

.PHONY: help dev-local dev-lakebase refresh-lakebase url compose dev-down dev-destroy hooks-install hooks-uninstall check

.DEFAULT_GOAL := help

help: ## Show available commands
	@awk -F ':.*## ' '/^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev-local: ## Start the app with its local PostgreSQL container
	$(COMPOSE) up --build

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

url: ## Print this worktree's storefront URL
	@address="$$($(COMPOSE) port frontend 80 2>/dev/null)" && [[ -n "$$address" ]] || { \
		echo "Frontend is not running; start it with make dev-local or make dev-lakebase." >&2; \
		exit 1; \
	}; \
	printf 'http://%s\n' "$$address"

compose: ## Run a scoped Compose command with ARGS='...'
	$(if $(strip $(ARGS)),,$(error Usage: make compose ARGS='logs -f backend'))
	$(COMPOSE) $(ARGS)

dev-down: ## Stop local or Lakebase development containers
	$(COMPOSE) down

dev-destroy: ## Stop local or Lakebase development containers
	$(COMPOSE) down --volumes

hooks-install: ## Enable Lakebase provisioning after branch checkouts
	@./scripts/manage-post-checkout-hook.sh install

hooks-uninstall: ## Remove this clone's post-checkout registration
	@./scripts/manage-post-checkout-hook.sh uninstall

check: ## Validate branch naming and both Compose modes
	@bash ./scripts/dev-context-id.sh --self-test
	@./scripts/lakebase-branch.sh --self-test
	@python3 -c 'from server.runtime import get_runtime_info; local = get_runtime_info({"APP_RUNTIME": "docker"}); assert local == {"backend": "docker", "database": {"location": "local-docker", "project": None, "branch": None}}; lakebase = get_runtime_info({"DATABRICKS_APP_NAME": "storefront", "ENDPOINT_NAME": "projects/demo-project/branches/dev-alex/endpoints/primary"}); assert lakebase == {"backend": "production", "database": {"location": "lakebase", "project": "demo-project", "branch": "dev-alex"}}'
	@$(COMPOSE) config --format json | jq -e --arg name "$(COMPOSE_PROJECT_NAME)" \
		'.name == $$name and (.services.postgres.ports == null) and (.services.backend.ports == null) and (.services.frontend.ports == [{host_ip: "127.0.0.1", mode: "ingress", protocol: "tcp", published: "0", target: 80}])' >/dev/null
	@PGHOST=lakebase.example PGUSER=developer@example.com PGPASSWORD=test \
		ENDPOINT_NAME=projects/test/branches/test/endpoints/primary \
		$(COMPOSE) -f compose.yaml -f compose.lakebase.yaml config --format json | \
		jq -e '.services.postgres == null and .services.backend.depends_on.postgres.required == false and .services.backend.environment.PGHOST == "lakebase.example"' >/dev/null
