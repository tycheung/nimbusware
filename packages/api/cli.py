from __future__ import annotations


def main() -> None:
    from env import load_dotenv

    load_dotenv()
    import uvicorn

    from env.env_flags import api_host, api_port

    host = api_host()
    from env.admin_token import require_non_default_admin_token_for_host

    require_non_default_admin_token_for_host(host)
    uvicorn.run(
        "api.app:app",
        host=host,
        port=api_port(),
        factory=False,
    )


if __name__ == "__main__":
    main()
