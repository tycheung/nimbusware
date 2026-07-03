from urllib.parse import quote


def ollama_models_path(*, query: str = "") -> str:
    path = "/platform/ollama/models"
    q = query.strip()
    if q:
        path = f"{path}?q={quote(q)}"
    return path


def ollama_model_delete_path(model_name: str) -> str:
    return f"/platform/ollama/models/{quote(model_name.strip(), safe='')}"


def admin_ollama_model_delete_path(model_name: str) -> str:
    return f"/admin/ollama/models/{quote(model_name.strip(), safe='')}"
