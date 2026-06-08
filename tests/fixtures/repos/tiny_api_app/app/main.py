from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="tiny-api-app")
_CONTACTS: list[dict[str, str]] = []
_TODOS: list[dict[str, str]] = []


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "tiny-api-app"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/contacts")
def list_contacts() -> list[dict[str, str]]:
    return list(_CONTACTS)


@app.post("/contacts", status_code=201)
def create_contact(body: dict[str, str]) -> dict[str, str]:
    _CONTACTS.append(body)
    return body


@app.get("/todos")
def list_todos() -> list[dict[str, str]]:
    return list(_TODOS)


@app.post("/todos", status_code=201)
def create_todo(body: dict[str, str]) -> dict[str, str]:
    _TODOS.append(body)
    return body
