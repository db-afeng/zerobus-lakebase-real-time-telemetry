# Workshop Setup — Data-Centric Edition

## Overview

This setup guide is for the **data-centric** workshop variant. The Lakebase Autoscaling project and
its shared OAuth group role are created first; the Declarative Automation Bundle (DAB) then deploys
the DataCart Storefront app against those existing resources.

## Prerequisites

- **Databricks Workspace**: any workspace with Lakebase Autoscaling and Databricks Apps support
- **Databricks CLI**: v0.229.0+ (only required if deploying via terminal — workspace-UI deploy needs no local CLI)
- **Unity Catalog**: enabled in your workspace (required for Bonus Lab 1.1 and Lab 4.1)
- **A SQL warehouse**: needed for the federated queries in Bonus Lab 1.1 (any size)
- **Workspace files** and **serverless compute** must be enabled in the workspace (admin settings) for the workspace-UI deploy flow to work

> **Note:** the React frontend is pre-built and included in `frontend/dist/`. No Node.js or npm
> is required for setup — the bundle deploys the static assets directly.

## What the Bundle Deploys

```
datacart-storefront/                  ← bundle root (databricks.yml)
├── databricks.yml                    →  bundle target + workspace path
└── resources/
    └── datacart_storefront.app.yml   →  Databricks App: storefront-<your-user-id>
                                          (existing Lakebase binding + group-role env)
```

The bundle references these externally managed resources:

- Project: `projects/zerobus-lakebase-workshop-alex-feng`
- Production endpoint: `projects/zerobus-lakebase-workshop-alex-feng/branches/production/endpoints/primary`
- Database: `projects/zerobus-lakebase-workshop-alex-feng/branches/production/databases/databricks-postgres`
- Workspace and Lakebase OAuth group role: `lakebase-app-schema-owner`

The app name remains per-user (`storefront-${workspace.current_user.id}`). The database project is
shared and is not deleted by `bundle destroy`.

## One-time Lakebase and group setup

Before deploying the app:

1. Create the project and its `production` branch.
2. Create the workspace group `lakebase-app-schema-owner` and add
   `alex.feng@databricks.com`.
3. In the production branch, create an OAuth Postgres role for that workspace group.
4. Connect as the project owner and grant only the database privileges needed to create the app
   schema:

```sql
GRANT CONNECT, CREATE ON DATABASE databricks_postgres
TO "lakebase-app-schema-owner";
```

Creating the app service principal is necessarily a second phase: it does not exist until the
first bundle deploy.

## Path A: Deploy from the workspace UI (no CLI required)

1. **Add the repo as a Databricks Git folder.** In the workspace, open your home folder → Add → Git folder → paste the repo URL → Create.
2. Navigate into the Git folder → `lakebase-in-a-box-workshop-data-centric` → `datacart-storefront`.
3. Click `databricks.yml` to open it in the editor.
4. Click the **deployments icon** in the editor toolbar.
5. In the **Deployments** pane choose target **`dev`** → click **Deploy**.
6. Confirm in the **Deploy to dev** dialog → click **Deploy** again.

This creates the stopped app shell and uploads the source files to:

```
/Workspace/Users/<your-email>/.bundle/datacart-storefront-data-centric/dev/files/
```

Before starting it, open Settings → Identity and access → Groups →
`lakebase-app-schema-owner`, then add the new `storefront-<your-user-id>` app service principal.

**Push the source and start the app** — do one of:

- **From a local terminal (recommended)**: `cd datacart-storefront && databricks bundle run datacart_storefront --profile <your-profile>`
- **Or in the workspace**: Compute → Apps → `storefront-<your-user-id>` → **Deploy** button → set source path to `/Workspace/Users/<your-email>/.bundle/datacart-storefront-data-centric/dev/files` → click Deploy.

After source is deployed, Alembic initializes empty tables as `lakebase-app-schema-owner`, then the
app status moves to `RUNNING`.

## Path B: Deploy from a local terminal

Make sure you have the Databricks CLI installed and authenticated:

```bash
databricks auth login --host <workspace-url> --profile <your-profile>
```

Then:

```bash
cd datacart-storefront

# Validate
databricks bundle validate --profile <your-profile>

# Create the stopped app shell and upload source
databricks bundle deploy --profile <your-profile>

# Add the new app service principal to the lakebase-app-schema-owner workspace group.

# Push source onto the app and start it
databricks bundle run datacart_storefront --profile <your-profile>

# Load the workshop fixture explicitly after Alembic succeeds
python scripts/lakebase_db.py seed --profile <your-profile>
```

If your default CLI profile already targets the right workspace, the `--profile` flag is optional.

## Run the Labs

After deployment, Alembic creates the five empty core tables. The explicit seed command above loads
the sample data:

1. **Lab 1.1** (`1.1 Lab - Setup Lakebase and Connect the Storefront`) — verifies the storefront, creates the Unity Catalog `clickstream_bronze` table needed by Zerobus, and grants the app service principal permission to ingest.
2. **Remaining labs** in order: 3.1 → 4.1 → 5.1, plus the bonus labs.

Branches created from production inherit its OAuth role, grants, Alembic state, and object
ownership. Apply future Alembic revisions to a branch with:

```bash
cd datacart-storefront
python scripts/lakebase_db.py migrate --profile <your-profile> --branch <branch-id>
```

## Re-deploying After Edits

```bash
databricks bundle deploy --profile <your-profile>
databricks bundle run datacart_storefront --profile <your-profile>    # pushes new source onto running app
```

`bundle deploy` is incremental — only changed files are uploaded.

## Tearing Down

```bash
databricks bundle destroy --profile <your-profile>
```

This removes the app only. The externally managed Lakebase project, group role, and database data
remain in place.

## Troubleshooting

### Storefront deployment reports a missing project

Verify the project deployed successfully:

```bash
databricks postgres list-projects --profile <your-profile>
```

You should see `projects/zerobus-lakebase-workshop-alex-feng`. If absent, create or restore the
external project before deploying the app.

### Storefront stays on "Loading…" after deployment

Look at the app logs:

```bash
databricks apps logs storefront-<your-user-id> --profile <your-profile>
```

Common causes:
- If logs show `password authentication failed`, verify the app service principal belongs to the
  `lakebase-app-schema-owner` workspace group and that a matching production-branch OAuth role
  exists with exact case.
- If logs show `permission denied to create database`, grant the group `CONNECT, CREATE` on
  `databricks_postgres`.
- If logs report legacy tables without Alembic state, recreate the workshop Lakebase project. The
  automatic migration intentionally supports fresh deployments rather than taking ownership of
  tables created previously by a notebook user.
- If the endpoint was scaled to zero, wait for the bounded startup retries; persistent failures
  indicate an endpoint or credential problem in the preceding log entries.

### `bundle validate` errors about `root_path`

The bundle pins `root_path` to `${workspace.current_user.userName}`, so it auto-derives. If you see this error, your workspace might not have user-derived paths enabled — open `databricks.yml` and hardcode `root_path` to your `/Workspace/Users/<your-email>/.bundle/...` path.

### The federated query in Bonus Lab 1.1 errors with "connection refused"

Foreign catalog connections require Lakehouse Federation to be enabled on your SQL warehouse. Use a serverless SQL warehouse if you don't have classic warehouses configured for federation.

### The Lakehouse Sync option doesn't appear in the UI (Lab 4.1)

Lakehouse Sync is gated by region and feature flag — confirm the **Sync to Unity Catalog** option is visible on your project's page. If not, ask your Databricks contact to enable the feature on this workspace.
