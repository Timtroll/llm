# backend/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    redis_url: str = "redis://redis:6379/0"
    #  Секретный ключ и алгоритм для JWT (держи в секрете!)
    secret_key: str = "c8f3e0e7f2c49aa647d944fa19b7a81e5fbd49e6c534a3a8c22ef13ccf7bd189"
    # SECRET_KEY = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
    algorithm: str = "HS256"
    # время жизни в секундах
    access_token_expire: int = 60 * 60

    class Config:
        env_file = ".env"

settings = Settings()
