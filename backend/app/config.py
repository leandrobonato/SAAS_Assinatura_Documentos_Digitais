from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # env_prefix avoids collisions with generic ambient env vars some dev
    # machines/tools already set (e.g. a stray DATABASE_URL from an unrelated
    # Postgres setup silently shadowing this app's own default).
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="DOCUFLOW_"
    )

    app_name: str = "DocuFlow"
    secret_key: str = "docuflow-dev-secret-change-in-production"
    access_token_expire_minutes: int = 60 * 24
    algorithm: str = "HS256"

    database_url: str = f"sqlite:///{BASE_DIR / 'storage' / 'docuflow.db'}"
    storage_dir: Path = BASE_DIR / "storage"

    free_plan_monthly_limit: int = 5
    free_plan_max_signers: int = 1
    reminder_after_days: float = 2.0
    reminder_min_interval_days: float = 2.0

    frontend_base_url: str = "http://localhost:5173"

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "no-reply@docuflow.local"


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
(settings.storage_dir / "documents").mkdir(parents=True, exist_ok=True)
(settings.storage_dir / "emails").mkdir(parents=True, exist_ok=True)
