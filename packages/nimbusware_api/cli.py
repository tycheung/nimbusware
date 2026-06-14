"""Nimbusware API CLI entrypoint."""

from __future__ import annotations


def main() -> None:
    from nimbusware_env import load_dotenv

    load_dotenv()
    import uvicorn

    from nimbusware_env.env_flags import nimbusware_api_host

    host = nimbusware_api_host()
    from nimbusware_env.admin_token import require_non_default_admin_token_for_host

    require_non_default_admin_token_for_host(host)
    uvicorn.run(
        "nimbusware_api.app:app",
        host=host,
        port=int(__import__("os").environ.get("PORT", "8000")),
        factory=False,
    )


if __name__ == "__main__":
    main()
