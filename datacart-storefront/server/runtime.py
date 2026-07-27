import os
from collections.abc import Mapping


def get_runtime_info(environ: Mapping[str, str] = os.environ) -> dict:
    """Return safe deployment metadata for the storefront runtime indicator."""
    if environ.get("DATABRICKS_APP_NAME"):
        backend = "production"
    else:
        configured_backend = environ.get("APP_RUNTIME", "local")
        backend = configured_backend if configured_backend in {"local", "docker"} else "local"

    endpoint_parts = environ.get("ENDPOINT_NAME", "").split("/")
    if (
        len(endpoint_parts) >= 4
        and endpoint_parts[0] == "projects"
        and endpoint_parts[2] == "branches"
        and endpoint_parts[1]
        and endpoint_parts[3]
    ):
        database = {
            "location": "lakebase",
            "project": endpoint_parts[1],
            "branch": endpoint_parts[3],
        }
    else:
        database = {"location": "local-docker", "project": None, "branch": None}

    return {"backend": backend, "database": database}
