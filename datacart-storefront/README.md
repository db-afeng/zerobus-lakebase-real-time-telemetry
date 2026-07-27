# DataCart Storefront

## Local development with Docker

The local stack builds the React storefront from source and serves it with
Nginx, alongside the FastAPI backend and PostgreSQL 17 seeded workshop data.

```bash
make dev-local
```

`docker compose up --build` remains equivalent, so the existing local workflow
continues to use the PostgreSQL container and `postgres-data` volume.

The Compose build uses the Databricks PyPI and npm proxies by default. Override
`PIP_INDEX_URL` or `NPM_REGISTRY` when different package indexes are required.

Open:

- Storefront: http://localhost:3000
- Supplier view: http://localhost:3000/supplier
- API health: http://localhost:3000/api/health
- Backend directly: http://localhost:8000
- PostgreSQL: `localhost:5432` (`datacart` / `datacart` / `datacart`)

The backend source is bind-mounted, so Python changes trigger an automatic
reload. Frontend source changes require rebuilding the frontend image:

```bash
docker compose build frontend
docker compose up -d frontend
```

Useful commands:

```bash
docker compose logs -f backend
docker compose down
docker compose down --volumes  # Also deletes local database data.
```

Alembic migrations run automatically before the backend starts. A fresh
PostgreSQL volume creates and seeds the `ecommerce` schema.

## Local development with Lakebase

Lakebase mode omits the local PostgreSQL container and connects the backend to
an ephemeral Lakebase Autoscaling branch copied from `production`.

Prerequisites:

- Databricks CLI with `databricks postgres` support (0.287.0 or newer)
- An authenticated Databricks CLI profile, `jq`, and Python 3
- The bundle deployed at least once so the per-user project exists

The checked-in `lakebase.config` defaults to the same project as
`databricks.yml`: `zerobus-lakebase-<Databricks user id>`. Override its profile
or project settings when needed.

Start Lakebase development:

```bash
make dev-lakebase
```

This creates or reuses `dev-<sanitized git user.name>-<sanitized git branch>`,
waits for its read-write endpoint, writes a mode-0600 `.env.lakebase`, and
starts Compose with `compose.lakebase.yaml`. The generated credential expires
after about one hour. Refresh it and recreate the backend with:

```bash
make refresh-lakebase
```

Stop either development mode with `make dev-down`. Development branches expire
after six hours; stopping Compose does not delete one immediately.

### Optional post-checkout provisioning

Enable checkout-triggered provisioning once for this clone:

```bash
make hooks-install
```

The installer does not edit the managed global hook or change
`core.hooksPath`. It creates the separate user hook already supported by the
global Databricks hook and allowlists this clone's exact absolute path. Other
repositories are ignored. Branch checkouts provision Lakebase synchronously;
file checkouts are ignored, and provisioning errors are warnings rather than
checkout failures.

The managed global hook exits before user-hook dispatch when
`DBR_SKIP_COMPILE_COMMANDS=1`, so that opt-out also skips Lakebase provisioning.

The hook prepares `.env.lakebase` but does not restart running containers.
Run `make dev-lakebase` to apply a newly generated environment. Disable the
registration with:

```bash
make hooks-uninstall
```

If an unrelated `~/.databricks/user-githooks/post-checkout` already exists, the
installer refuses to overwrite it and prints the command that must be chained
manually.

Run the local checks with:

```bash
make check
```
