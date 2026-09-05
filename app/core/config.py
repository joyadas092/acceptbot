import functools
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    bot_token: str = Field(alias='BOT_TOKEN')
    
    mongodb_uri: str = Field(alias='MONGODB_URI')
    mongodb_database: str = Field(alias='MONGODB_DATABASE')
    
    redis_url: str = Field(alias='REDIS_URL')
    
    webhook_url: str | None = Field(default=None, alias='WEBHOOK_URL')
    webhook_secret: str | None = Field(default=None, alias='WEBHOOK_SECRET')
    webhook_path: str = Field(default='/webhook', alias='WEBHOOK_PATH')
    
    super_admin_ids: list[int] = Field(default_factory=list, alias='SUPER_ADMIN_IDS')
    
    log_level: str = Field(default='INFO', alias='LOG_LEVEL')
    environment: str = Field(default='development', alias='ENVIRONMENT')
    
    app_host: str = Field(default='0.0.0.0', alias='APP_HOST')
    app_port: int = Field(default=8000, alias='APP_PORT')
    
    approval_poll_interval: int = Field(default=10, alias='APPROVAL_POLL_INTERVAL')
    broadcast_batch_size: int = Field(default=30, alias='BROADCAST_BATCH_SIZE')
    broadcast_rate_limit: int = Field(default=30, alias='BROADCAST_RATE_LIMIT')
    
    max_connected_chats_free: int = Field(default=3, alias='MAX_CONNECTED_CHATS_FREE')
    max_broadcast_recipients_free: int = Field(default=1000, alias='MAX_BROADCAST_RECIPIENTS_FREE')

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    @field_validator('super_admin_ids', mode='before')
    @classmethod
    def parse_super_admin_ids(cls, v: str | list | None) -> list[int]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(',') if x.strip().isdigit()]
        if isinstance(v, list):
            return [int(x) for x in v]
        return []

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == 'production'

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == 'development'

@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()
