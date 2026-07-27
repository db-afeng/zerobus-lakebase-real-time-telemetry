from fastapi import APIRouter, HTTPException, Response
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field

from server.auth import (
    CurrentCustomerId,
    clear_customer_session,
    normalize_address,
    normalize_email,
    set_customer_session,
)
from server.db import pool, DB_SCHEMA
from server.schema_detector import column_exists, table_exists

router = APIRouter(prefix="/account")


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class SignupRequest(LoginRequest):
    name: str = Field(min_length=1, max_length=100)
    address: str | None = Field(default=None, max_length=1000)


def _normalized_email(value: str) -> str:
    try:
        return normalize_email(value)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _load_account(customer_id: int) -> dict:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cols = ["c.id", "c.name", "c.email", "c.address"]
            if column_exists("customers", "loyalty_points"):
                cols.append("c.loyalty_points")
            if column_exists("customers", "email_verified"):
                cols.append("c.email_verified")

            cur.execute(
                f"SELECT {', '.join(cols)} FROM {DB_SCHEMA}.customers c WHERE c.id = %s",
                (customer_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Account not found")
            col_names = [d.name for d in cur.description]
            result = dict(zip(col_names, row))

            if table_exists("loyalty_members"):
                cur.execute(
                    f"""
                    SELECT lm.tier, lm.total_earned, lm.enrolled_at
                    FROM {DB_SCHEMA}.loyalty_members lm
                    JOIN {DB_SCHEMA}.customers c ON c.email = lm.email
                    WHERE c.id = %s
                    """,
                    (customer_id,),
                )
                loyalty_row = cur.fetchone()
                if loyalty_row:
                    result["loyalty_tier"] = loyalty_row[0]
                    result["loyalty_total_earned"] = loyalty_row[1]
                    result["loyalty_enrolled_at"] = str(loyalty_row[2])

    return result


@router.get("")
def get_account(customer_id: CurrentCustomerId):
    """Return the signed-in customer's profile."""
    return _load_account(customer_id)


@router.post("/signup", status_code=201)
def signup(payload: SignupRequest, response: Response):
    email = _normalized_email(payload.email)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Enter your name")

    try:
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    INSERT INTO {DB_SCHEMA}.customers (name, email, address)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, normalize_address(payload.address)),
                )
                customer_id = cur.fetchone()[0]
            conn.commit()
    except UniqueViolation as error:
        raise HTTPException(
            status_code=409, detail="An account with that email already exists"
        ) from error

    set_customer_session(response, email)
    return _load_account(customer_id)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    email = _normalized_email(payload.email)
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT id
                FROM {DB_SCHEMA}.customers
                WHERE lower(trim(email)) = %s
                """,
                (email,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=401, detail="No account found for that email")

    set_customer_session(response, email)
    return _load_account(row[0])


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_customer_session(response)
