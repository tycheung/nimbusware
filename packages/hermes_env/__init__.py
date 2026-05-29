"""Load Nimbusware repository environment (``.env``), including Hermes agent settings."""

from hermes_env.dotenv import find_repo_root, load_dotenv, set_env_var

__all__ = ["find_repo_root", "load_dotenv", "set_env_var"]
