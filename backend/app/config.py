from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Liquidity Logic Engine API"
    secret_key: str = "hackathon-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "sqlite:///./lle.db"
    demo_user_email: str = "sarah@lle.demo"
    demo_user_password: str = "Demo123!"
    frontend_origin: str = "http://localhost:3000"
    tesseract_cmd: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
