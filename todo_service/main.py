from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from enum import Enum
import sqlite3
import json
import os

app = FastAPI(
    title="TODO Service",
    description="CRUD operations for TODO tasks",
    version="1.0.0"
)

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/app/data/todo.db")


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


def get_db_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            tags TEXT DEFAULT '[]'
        )
    """)
    conn.commit()
    conn.close()


def parse_tags(tags_json: str) -> list[str]:
    try:
        return json.loads(tags_json) if tags_json else []
    except json.JSONDecodeError:
        return []


@app.on_event("startup")
def startup_event():
    init_db()


class ItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: Priority = Priority.medium
    tags: list[str] = []


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[Priority] = None
    tags: Optional[list[str]] = None


class Item(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool = False
    priority: Priority = Priority.medium
    tags: list[str] = []


@app.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (title, description, completed, priority, tags) VALUES (?, ?, ?, ?, ?)",
        (item.title, item.description, item.completed, item.priority.value, json.dumps(item.tags))
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()

    return Item(
        id=item_id,
        title=item.title,
        description=item.description,
        completed=item.completed,
        priority=item.priority,
        tags=item.tags
    )


@app.get("/items", response_model=list[Item])
def get_items():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    rows = cursor.fetchall()
    conn.close()

    return [
        Item(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            completed=bool(row["completed"]),
            priority=row["priority"] or "medium",
            tags=parse_tags(row["tags"])
        )
        for row in rows
    ]


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )

    return Item(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
        priority=row["priority"] or "medium",
        tags=parse_tags(row["tags"])
    )


@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    existing = cursor.fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )

    updates = []
    values = []

    if item.title is not None:
        updates.append("title = ?")
        values.append(item.title)
    if item.description is not None:
        updates.append("description = ?")
        values.append(item.description)
    if item.completed is not None:
        updates.append("completed = ?")
        values.append(item.completed)
    if item.priority is not None:
        updates.append("priority = ?")
        values.append(item.priority.value)
    if item.tags is not None:
        updates.append("tags = ?")
        values.append(json.dumps(item.tags))

    if updates:
        values.append(item_id)
        query = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()

    return Item(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
        priority=row["priority"] or "medium",
        tags=parse_tags(row["tags"])
    )


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    existing = cursor.fetchone()

    if existing is None:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item with id {item_id} not found"
        )

    cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()

    return None
