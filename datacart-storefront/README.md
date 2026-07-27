# DataCart Storefront

## Local development with Docker

The local stack builds the React storefront from source and serves it with
Nginx, alongside the FastAPI backend and PostgreSQL 17 seeded workshop data.

```bash
docker compose up --build
```

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
