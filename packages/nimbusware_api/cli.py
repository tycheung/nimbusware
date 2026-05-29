"""Nimbusware Hermes agent API — ``poetry run nimbusware-api`` (uvicorn)."""

from __future__ import annotations


def main() -> None:
    from nimbusware_env import load_dotenv

    load_dotenv()
    import uvicorn

    host = __import__("os").environ.get("HERMES_API_HOST", "0.0.0.0")
    uvicorn.run(
        "nimbusware_api.app:app",
        host=host,
        port=int(__import__("os").environ.get("PORT", "8000")),
        factory=False,
    )


if __name__ == "__main__":
    main()
