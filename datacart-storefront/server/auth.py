import os
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response

SESSION_COOKIE = "datacart_customer_email"
SESSION_MAX_AGE = 60 * 60 * 24 * 30


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if (
        not email
        or len(email) > 255
        or email.count("@") != 1
        or any(char.isspace() for char in email)
    ):
        raise ValueError("Enter a valid email address")
    local, domain = email.split("@")
    if not local or not domain:
        raise ValueError("Enter a valid email address")
    return email


def normalize_address(value: str | None) -> str | None:
    if value is None:
        return None
    address = value.strip()
    return address or None


def set_customer_session(response: Response, email: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        normalize_email(email),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        secure=bool(os.environ.get("DATABRICKS_APP_NAME")),
        samesite="lax",
    )


def clear_customer_session(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        httponly=True,
        secure=bool(os.environ.get("DATABRICKS_APP_NAME")),
        samesite="lax",
    )


def get_current_customer_id(request: Request) -> int:
    from server.db import DB_SCHEMA, pool

    email = request.cookies.get(SESSION_COOKIE)
    if not email:
        raise HTTPException(status_code=401, detail="Log in to continue")

    try:
        normalized_email = normalize_email(email)
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Session is invalid") from error

    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id
                FROM {DB_SCHEMA}.customers
                WHERE lower(trim(email)) = %s
                """,
                (normalized_email,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="Session is invalid")
    return row[0]


CurrentCustomerId = Annotated[int, Depends(get_current_customer_id)]
