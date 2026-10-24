"""
GateFlow AI Backend Configuration
----------------------------------
All settings are loaded from environment variables or the .env file.
Never hard-code secrets here.
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "GateFlow AI Backend"
    app_version: str = "1.0.0"
    debug: bool = False

    # CORS — frontend dev server
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Data
    scenario_data_path: Path = Path("./data/scenario.json")

    # Simulation
    random_seed: int = 42
    simulation_interval_min: int = 15  # time-step size for queue model
    vehicle_capacity_threshold: int = 35  # campus perimeter queue limit

    # AI (not used in deterministic mode — key kept server-side)
    gemini_api_key: str = ""

    # ── MySQL Database ────────────────────────────────────────────────────────
    db_host: str = "10.0.23.73"
    db_port: int = 3306
    db_name: str = "schooltraffic"
    db_user: str = "root"
    db_password: str = "venkat@2007VKK"

    @property
    def database_url(self) -> str:
        """SQLAlchemy-compatible MySQL connection URL (PyMySQL driver)."""
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
            f"?charset=utf8mb4"
        )

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    jwt_secret: str = "gateflow-super-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8  # 8 hours


settings = Settings()

