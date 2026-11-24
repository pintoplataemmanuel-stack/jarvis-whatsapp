from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    webhook_path: str = Field(default="/webhook/evolution", alias="WEBHOOK_PATH")
    webhook_secret: str = Field(default="", alias="WEBHOOK_SECRET")
    max_webhook_bytes: int = Field(default=1_000_000, alias="MAX_WEBHOOK_BYTES")
    timezone: str = Field(default="America/Bogota", alias="TIMEZONE")

    evolution_base_url: str = Field(default="http://evolution:8080", alias="EVOLUTION_BASE_URL")
    evolution_api_key: str = Field(default="", alias="EVOLUTION_API_KEY")
    evolution_instance: str = Field(default="jarvis", alias="EVOLUTION_INSTANCE")

    llm_base_url: str = Field(default="http://localhost:11434/v1", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="qwen2.5:7b-instruct", alias="LLM_MODEL")
    max_tool_iterations: int = Field(default=6, alias="MAX_TOOL_ITERATIONS")

    allowed_numbers_raw: str = Field(default="", alias="ALLOWED_NUMBERS")
    max_messages_per_minute: int = Field(default=10, alias="MAX_MESSAGES_PER_MINUTE")
    max_message_chars: int = Field(default=4000, alias="MAX_MESSAGE_CHARS")

    db_path: str = Field(default="data/jarvis.db", alias="DB_PATH")
    summary_message_threshold: int = Field(default=30, alias="SUMMARY_MESSAGE_THRESHOLD")
    summary_token_threshold: int = Field(default=4000, alias="SUMMARY_TOKEN_THRESHOLD")
    keep_recent_messages: int = Field(default=10, alias="KEEP_RECENT_MESSAGES")

    voice_enabled: bool = Field(default=True, alias="VOICE_ENABLED")
    whisper_model: str = Field(default="small", alias="WHISPER_MODEL")
    whisper_device: str = Field(default="cpu", alias="WHISPER_DEVICE")
    whisper_compute_type: str = Field(default="int8", alias="WHISPER_COMPUTE_TYPE")
    reply_with_audio: bool = Field(default=False, alias="REPLY_WITH_AUDIO")


@lru_cache
def get_settings() -> Settings:
    return Settings()
