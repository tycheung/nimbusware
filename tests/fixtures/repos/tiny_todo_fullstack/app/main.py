from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
_todos: list[dict[str, object]] = []
_next_id = 1


class TodoIn(BaseModel):
    title: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/todos")
def list_todos() -> list[dict[str, object]]:
    return _todos


@app.post("/todos", status_code=201)
def create_todo(body: TodoIn) -> dict[str, object]:
    global _next_id
    item = {"id": _next_id, "title": body.title}
    _next_id += 1
    _todos.append(item)
    return item


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int) -> dict[str, str]:
    global _todos
    _todos = [t for t in _todos if t["id"] != todo_id]
    return {"deleted": str(todo_id)}
