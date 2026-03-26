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
    setu_base_url: str = "https://aa-sandbox.setu.co"
    setu_client_id: str | None = None
    setu_client_secret: str | None = None
    setu_product_instance_id: str | None = None
    setu_redirect_url: str = "http://localhost:3000/setu/consent/callback"
    setu_mock_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
