from functools import lru_cache
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Union
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "M.A.R.K.E.T AI Dashboard"
    app_version: str = "2.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: Union[List[str], str] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if not v:
            return ["*"]
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    return ["*"]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Facebook Messenger & Graph API
    fb_page_token: str = ""
    fb_verify_token: str = "change_me_in_production"
    fb_app_secret: str = ""
    fb_api_version: str = "v19.0"
    fb_api_timeout: int = 15
    fb_max_retries: int = 3

    # Facebook Auto Reply on Comments
    auto_reply_comments: bool = True
    comment_reply_mode: str = "both"  # "public", "private", "both"

    # Ollama Local
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout: int = 45
    ollama_max_retries: int = 2

    # Cloud AI APIs
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    # Excel Database
    excel_path: str = "products.xlsx"
    excel_reload_interval: int = 300

    # Ngrok Tunnel
    ngrok_authtoken: str = ""
    ngrok_domain: str = ""
    ngrok_timeout: int = 10

    # QR Code Detection
    qr_max_image_size: int = 10 * 1024 * 1024
    qr_timeout: int = 15

    # WhatsApp OpenWA Integration
    whatsapp_openwa_url: str = "http://localhost:2785"
    whatsapp_openwa_api_key: str = ""
    whatsapp_session_id: str = "market-bot"
    whatsapp_auto_reply: bool = True
    whatsapp_send_purchase_confirmation: bool = True

    # Conversation History
    history_max_messages: int = 10
    history_ttl_seconds: int = 3600

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    @property
    def is_production(self) -> bool:
        return not self.debug

    @property
    def fb_api_url(self) -> str:
        return f"https://graph.facebook.com/{self.fb_api_version}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
