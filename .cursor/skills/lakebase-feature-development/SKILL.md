---
name: lakebase-feature-development
description: Develop and test DataCart Storefront features against an isolated Lakebase copy-on-write branch containing a production data snapshot. Use for feature work, database changes, Alembic migrations, backend changes, and end-to-end testing in datacart-storefront.
---

# Lakebase feature development

Use the repository's Lakebase branch workflow for all database-dependent feature work.

## Mental model

- A Git branch checkout creates or reuses a Lakebase branch named
  `dev-<git-user>-<git-branch>-<hash>`.
- The Lakebase branch is an instant copy-on-write snapshot of `production`. It
  contains production data as of branch creation, while schema and data writes
  remain isolated from `production`.
- It is a snapshot, not a live mirror. Later production changes do not appear
  automatically. A reused branch can also contain earlier development changes.
- The branch is disposable and expires after six hours by default.
- Isolation covers Lakebase only. Do not trigger writes to shared external
  systems. Local Compose disables Zerobus with `ZEROBUS_ENABLED=false`.
- Each linked worktree has a path-derived Compose project and a dynamically
  published frontend port. Always use the Make targets so containers, networks,
  images, and local PostgreSQL volumes remain worktree-scoped.

## Safety rules

1. Never develop or test against the Lakebase `production` branch.
2. Do not print, export, copy, or commit production-derived records or
   `.env.lakebase`. Treat branch data as production-sensitive.
3. Before a destructive database operation, verify that
   `LAKEBASE_BRANCH_PATH` in `.env.lakebase` contains `/branches/dev-` and is
   the branch prepared for the current Git checkout.
4. Do not reset or delete a branch unless it is the current disposable
   development branch. Never reset or delete `production`.

## Required workflow

Work from `datacart-storefront/`.

1. Check out or create the Git feature branch. Do not work from detached HEAD.
2. Let the post-checkout hook provision Lakebase asynchronously.
3. Use `make dev-lakebase` as the authoritative readiness barrier. It waits for
   the matching hook run, retries provisioning when needed, refreshes
   `.env.lakebase`, starts the full stack, and runs `alembic upgrade head`
   before FastAPI starts.
4. If the credential expires, run `make refresh-lakebase`.
5. Make the smallest application and migration changes needed.
6. Run `make check`, then run `make url` in another terminal and test the
   changed behavior end to end against the returned worktree URL.
7. Keep the stack running when finished. Run `make dev-down` only when the user
   explicitly asks to stop the stack.

The hook alone is not proof that the database is ready: it is asynchronous,
does not fail checkout, and does not restart running containers. Check
`lakebase-branch-post-commit.log` only when provisioning fails.

## Migration development

Every schema change must be an Alembic migration under `migrations/versions/`.
Exercise it against the feature branch's production snapshot, not an empty
local database alone.

1. Capture only non-sensitive baseline facts needed by the test, such as the
   Alembic revision, row counts, null counts, or constraint violations.
2. Start with `make dev-lakebase`; startup applies the migration to the branch.
3. Verify the migration reached `head`, preserved existing rows, backfilled
   values correctly, and enforced new constraints or indexes.
4. Exercise the application path that reads and writes the changed schema.
5. Run `alembic downgrade -1`, verify the previous revision is restored, then
   run `alembic upgrade head` and repeat the invariants. Every new migration
   must have a working `downgrade()`.
6. Leave one runnable regression check for non-trivial migration logic.

When a migration must be rerun from a pristine, current production snapshot,
reset only the verified current `dev-*` Lakebase branch or use a new Git branch,
then rerun `make dev-lakebase`. A reset destroys all changes on that development
branch.

## End-to-end completion criteria

Database-dependent work is not complete after unit tests or a successful
migration. Verify all applicable layers:

- `make check` passes.
- The backend starts after Alembic completes.
- `/api/health` and `/api/dbtest` succeed.
- Changed API endpoints work with production-shaped data.
- The affected browser journey works at the URL returned by `make url`.
- Database writes are visible through a subsequent application read.
- Existing production-derived rows remain valid after migrations.
- `alembic downgrade -1` and the subsequent `alembic upgrade head` both work.
- No command or connection targeted `production`.

Prefer exercising the real UI and API over inserting synthetic fixtures. Add
minimal branch-local test rows only when existing production-shaped data cannot
cover the case, and use unmistakable test identifiers.
