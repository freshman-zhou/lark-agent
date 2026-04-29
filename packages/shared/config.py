from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "IMAgent-Pilot"
    app_env: str = "dev"
    debug: bool = True

    database_url: str = "sqlite:///./agent_pilot.db"

    feishu_app_id: str = "cli_a960eec755385cef"
    feishu_app_secret: str = "62Ui1XwklISacAPM0YZ1ldWVQwr21qEm"
    feishu_verification_token: str = ""
    feishu_encrypt_key: str = ""
    feishu_base_url: str = "https://open.feishu.cn/open-apis"

    # long_connection / webhook 。当前选择使用 long_connection。
    feishu_event_mode: str = "long_connection"

     # 群聊上下文拉取配置
    chat_context_limit: int = 50
    chat_context_max_chars: int = 12000

    # LLM 配置
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_api_key: str = "  "
    llm_model: str = " "
    llm_timeout: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
