# DataCart Storefront

## Local development with Docker

The local stack runs the compiled React storefront in Nginx, the FastAPI backend
with reload enabled, and PostgreSQL 17 with the seeded workshop data.

```bash
docker compose up --build
```

The Compose build uses the Databricks PyPI proxy by default. Override
`PIP_INDEX_URL` when a different package index is required.

Open:

- Storefront: http://localhost:3000
- Supplier view: http://localhost:3000/supplier
- API health: http://localhost:3000/api/health
- Backend directly: http://localhost:8000
- PostgreSQL: `localhost:5432` (`datacart` / `datacart` / `datacart`)

The backend source is bind-mounted, so Python changes trigger an automatic
reload. The frontend container serves the existing `frontend/dist` artifact;
after replacing that build, rebuild the frontend image:

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
