# DataCart Storefront

## Local development with Docker

The local stack builds the React storefront from source and serves it with
Nginx, alongside the FastAPI backend and PostgreSQL 17.

```bash
make dev-local
```

Always use the Make targets rather than raw `docker compose` commands. Each
linked Git worktree gets a Compose project derived from its canonical checkout
path, which isolates its containers, network, images, and `postgres-data`
volume from other local worktrees.

The Compose build uses the Databricks PyPI and npm proxies by default. Override
`PIP_INDEX_URL` or `NPM_REGISTRY` when different package indexes are required.

Docker assigns each worktree a free loopback port for the storefront. From a
second terminal, print its URL with:

```bash
make url
```

Append `/supplier` for the supplier view or `/api/health` for backend health.
FastAPI and PostgreSQL are not published on host ports; the storefront proxies
API requests to FastAPI over the worktree's private Compose network.

The backend source is bind-mounted, so Python changes trigger an automatic
reload. Frontend source changes require rebuilding the frontend image:

```bash
make compose ARGS='build frontend'
make compose ARGS='up -d frontend'
```

Useful commands:

```bash
make compose ARGS='logs -f backend'
make compose ARGS='exec postgres psql -U datacart -d datacart'
make dev-down
make dev-destroy  # Also deletes only this worktree's local database data.
```

Alembic migrations run automatically before the backend starts. A fresh
PostgreSQL volume creates an empty `ecommerce` schema; Alembic does not load fixtures.

## Local development with Lakebase

Lakebase mode omits the local PostgreSQL container and connects the backend to
an ephemeral Lakebase Autoscaling branch copied from `production`.

Prerequisites:

- Databricks CLI with `databricks postgres` support (0.287.0 or newer)
- An authenticated Databricks CLI profile, `jq`, and Python 3
- The external `zerobus-lakebase-workshop-alex-feng` project exists
- Your Databricks identity belongs to `lakebase-app-schema-owner`

The checked-in `lakebase.config` targets `zerobus-lakebase-workshop-alex-feng`
and authenticates each branch connection as `lakebase-app-schema-owner`.
Override its profile or project settings when needed.

Start Lakebase development:

```bash
make dev-lakebase
```

This creates or reuses
`dev-<sanitized git user.name>-<sanitized git branch>-<hash>`, waits for its
read-write endpoint, writes a mode-0600 worktree-local `.env.lakebase`, and
starts Compose with `compose.lakebase.yaml`. The hash preserves distinctions
between Git refs that sanitize to the same text. Branch Alembic migrations
therefore remain owned by the same group role as production. The generated
credential expires after about one hour. Refresh it and recreate only this
worktree's backend with:

```bash
make refresh-lakebase
```

Stop either development mode with `make dev-down`. Development branches expire
after six hours; stopping Compose does not delete one immediately.

### Explicit Lakebase migration and seed commands

Run Alembic against production or a named branch as the shared group owner:

```bash
python scripts/lakebase_db.py migrate --profile infomedia-lakebase
python scripts/lakebase_db.py migrate --profile infomedia-lakebase --branch <branch-id>
```

Load the deterministic workshop fixture manually after migration:

```bash
python scripts/lakebase_db.py seed --profile infomedia-lakebase
```

The seed is idempotent by fixture ID and repairs the five table sequences.

### Optional post-checkout provisioning

Enable checkout-triggered provisioning once for this clone:

```bash
make hooks-install
```

The installer does not edit the managed global hook or change
`core.hooksPath`. It creates the separate user hook already supported by the
global Databricks hook and allowlists this clone's canonical Git common
directory. The main checkout and Cursor worktrees under
`~/.cursor/worktrees/` share that directory, so each dispatches the repository
hook from its own checkout root. Unrelated clones are ignored. Separate clones
and cloud agents do not share this local hook or Docker daemon. Branch
checkouts provision Lakebase asynchronously; file checkouts are ignored, and
provisioning errors do not fail the checkout. Each worktree replaces its own
`lakebase-branch-post-commit.log` with the run output.

The managed global hook exits before user-hook dispatch when
`DBR_SKIP_COMPILE_COMMANDS=1`, so that opt-out also skips Lakebase provisioning.

The hook prepares `.env.lakebase` but does not restart running containers.
`make dev-lakebase` waits for the matching checkout run to succeed before
starting containers, or retries provisioning synchronously if the hook did not
run or failed. Disable the registration with:

```bash
make hooks-uninstall
```

If an unrelated `~/.databricks/user-githooks/post-checkout` already exists, the
installer refuses to overwrite it and prints the command that must be chained
manually.

After upgrading from the earlier exact-root hook, rerun `make hooks-install`
once to migrate the registration to the clone's Git common directory.

Run the local checks with:

```bash
make check
```
