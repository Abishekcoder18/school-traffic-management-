"""
GateFlow AI Backend Configuration
----------------------------------
All settings are loaded from environment variables or the .env file.
Never hard-code secrets here.
"""
from sqlalchemy import URL
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
    map_state_path: Path = Path("./data/map_state.json")

    # Simulation
    random_seed: int = 42
    simulation_interval_min: int = 15  # time-step size for queue model
    vehicle_capacity_threshold: int = 35  # campus perimeter queue limit

    # AI (not used in deterministic mode — key kept server-side)
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "moonshotai/kimi-k2:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

        # ── PostgreSQL Database ───────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "schooltraffic"
    db_user: str = "postgres"
    db_password: str = ""

    @property
    def database_url(self):
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 8  # 8 hours


settings = Settings()
