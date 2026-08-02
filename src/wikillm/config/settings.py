import json
from pathlib import Path

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class LLMProvider(BaseModel):
    """A single LLM provider tried in order."""

    provider: str = "openrouter"  # "openrouter" | "opencode" | "ollama"
    model: str = ""
    api_key: str = ""
    base_url: str = ""  # opencode: http://127.0.0.1:PORT
    username: str = "opencode"  # opencode basic auth
    password: str = ""


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""

    # OpenRouter (default provider, used if LLM_PROVIDERS is empty)
    openrouter_api_key: str = ""
    openrouter_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

    # LLM providers tried in order (list of LLMProvider, JSON in env)
    llm_providers: list[LLMProvider] = []

    # GitHub
    github_token: str = ""
    github_repo: str = ""  # e.g. "username/wikillm-vault"
    github_branch: str = "main"

    # Google Drive
    google_drive_credentials: str = ""  # path to credentials.json
    google_drive_folder_id: str = ""

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    web_secret_key: str = "change-me-in-production"
    web_password: str = "admin"

    # Wiki
    wiki_pages_dir: str = "pages"
    wiki_site_dir: str = "site"

    @property
    def project_root(self) -> Path:
        return PROJECT_ROOT

    @property
    def pages_dir(self) -> Path:
        return PROJECT_ROOT / self.wiki_pages_dir

    @property
    def site_dir(self) -> Path:
        return PROJECT_ROOT / self.wiki_site_dir

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("llm_providers", mode="before")
    @classmethod
    def parse_llm_providers(cls, v):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except json.JSONDecodeError:
                return []
        return v


settings = Settings()
