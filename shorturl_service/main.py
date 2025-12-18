from fastapi import FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime
import sqlite3
import os
import string
import random

app = FastAPI(
    title="Short URL Service",
    description="URL shortening service",
    version="1.0.0"
)

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/shorturl.db")
CHARS = string.ascii_letters + string.digits


def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_id TEXT UNIQUE NOT NULL,
            full_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def get_unique_short_id(conn) -> str:
    cursor = conn.cursor()
    while True:
        short_id = ''.join(random.choices(CHARS, k=6))
        cursor.execute("SELECT id FROM urls WHERE short_id = ?", (short_id,))
        if cursor.fetchone() is None:
            return short_id


def is_expired(expires_at: Optional[str]) -> bool:
    if expires_at is None:
        return False

    try:
        expiry_time = datetime.fromisoformat(expires_at)
        return datetime.now() > expiry_time
    except ValueError:
        return False


@app.on_event("startup")
def startup_event():
    init_db()


class URLCreate(BaseModel):
    url: HttpUrl
    expires_at: Optional[datetime] = None


class URLResponse(BaseModel):
    short_id: str
    short_url: str
    full_url: str
    expires_at: Optional[datetime] = None


class URLStats(BaseModel):
    short_id: str
    full_url: str
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False


class DeleteResponse(BaseModel):
    message: str
    short_id: str


@app.post("/shorten", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
def shorten_url(url_data: URLCreate):
    conn = get_db_connection()
    cursor = conn.cursor()

    full_url = str(url_data.url)
    expires_at = url_data.expires_at.isoformat() if url_data.expires_at else None

    cursor.execute("SELECT short_id, expires_at FROM urls WHERE full_url = ?", (full_url,))
    existing = cursor.fetchone()

    if existing and not is_expired(existing["expires_at"]):
        short_id = existing["short_id"]
        expires_at = existing["expires_at"]
    else:
        if existing:
            cursor.execute("DELETE FROM urls WHERE full_url = ?", (full_url,))

        short_id = get_unique_short_id(conn)
        cursor.execute(
            "INSERT INTO urls (short_id, full_url, expires_at) VALUES (?, ?, ?)",
            (short_id, full_url, expires_at)
        )
        conn.commit()

    conn.close()

    return URLResponse(
        short_id=short_id,
        short_url=f"/{short_id}",
        full_url=full_url,
        expires_at=datetime.fromisoformat(expires_at) if expires_at else None
    )


@app.get("/{short_id}")
def redirect_to_url(short_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT full_url, expires_at FROM urls WHERE short_id = ?", (short_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_id}' not found"
        )

    if is_expired(row["expires_at"]):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Short URL '{short_id}' has expired"
        )

    return RedirectResponse(url=row["full_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@app.get("/stats/{short_id}", response_model=URLStats)
def get_url_stats(short_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT short_id, full_url, created_at, expires_at FROM urls WHERE short_id = ?",
        (short_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_id}' not found"
        )

    return URLStats(
        short_id=row["short_id"],
        full_url=row["full_url"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        is_expired=is_expired(row["expires_at"])
    )


@app.delete("/{short_id}", response_model=DeleteResponse)
def delete_url(short_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM urls WHERE short_id = ?", (short_id,))
    existing = cursor.fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_id}' not found"
        )

    cursor.execute("DELETE FROM urls WHERE short_id = ?", (short_id,))
    conn.commit()
    conn.close()

    return DeleteResponse(
        message="URL deleted successfully",
        short_id=short_id
    )
