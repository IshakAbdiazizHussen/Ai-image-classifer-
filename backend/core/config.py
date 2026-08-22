"""Environment-based settings — the only place secrets/config values are
read from (constraints.md rule 18). Nothing in the backend reads
`os.environ` directly outside this module."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root's .env, resolved from this file's location rather than the
# process's cwd — so `.env` is found the same way whether the app is run
# from the repo root, from backend/ (e.g. `alembic` invoked in-place), or
# in a container where this file's relative position is unchanged.
_REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # protected_namespaces=() — pydantic reserves the "model_" prefix for
    # its own methods; `model_version` is our field name, not a conflict.
    model_config = SettingsConfigDict(
        env_file=str(_REPO_ROOT / ".env"), extra="ignore", protected_namespaces=()
    )

    database_url: str
    redis_url: str

    model_version: str
    artifacts_dir: str = "ml/artifacts"

    log_level: str = "INFO"
    rate_limit_per_minute: int = 30
    max_upload_bytes: int = 5 * 1024 * 1024  # 5 MB

    # Comma-separated allowed browser origins for the frontend to call
    # this API from (CORS). Never "*" with credentials, and never
    # hardcoded in main.py — configured here like everything else.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
