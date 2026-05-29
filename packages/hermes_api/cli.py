"""`poetry run hermes-api` → uvicorn."""

from __future__ import annotations


def main() -> None:
    from hermes_env import load_dotenv

    load_dotenv()
    import uvicorn

    host = __import__("os").environ.get("HERMES_API_HOST", "0.0.0.0")
    uvicorn.run(
        "hermes_api.app:app",
        host=host,
        port=int(__import__("os").environ.get("PORT", "8000")),
        factory=False,
    )


if __name__ == "__main__":
    main()
