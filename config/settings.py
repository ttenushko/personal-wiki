from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str = ""

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct:free"

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
    wiki_raw_dir: str = "raw"
    wiki_pages_dir: str = "wiki"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
