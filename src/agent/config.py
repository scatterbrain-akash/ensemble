import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field, PrivateAttr
from ruamel.yaml import YAML


yaml = YAML(typ="safe")


class Settings(BaseModel):
    env: str = Field("personal", description="Environment profile")
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    ai_studio_api_key: str | None = None
    model_config_path: Path = Field(Path("config/models.yaml"))
    settings_path: Path = Field(Path("config/settings.yaml"))
    timeouts: dict[str, int] = Field(default_factory=dict)
    retries: dict[str, int] = Field(default_factory=dict)
    cost: dict[str, float] = Field(default_factory=dict)
    cache: dict[str, int] = Field(default_factory=dict)
    cms: dict[str, Any] = Field(default_factory=dict)

    _config_data: dict[str, Any] = PrivateAttr(default_factory=dict)

    def __init__(self, **data: Any):
        if os.environ.get("DISABLE_DOTENV") != "1":
            load_dotenv()
        env_override = data.pop("env", None) or "personal"
        super().__init__(env=env_override, **data)
        self._load_yaml()
        self._load_env()

    def _load_yaml(self) -> None:
        if self.model_config_path.exists():
            with self.model_config_path.open("r", encoding="utf-8") as fd:
                self._config_data = yaml.load(fd) or {}
        if self.settings_path.exists():
            with self.settings_path.open("r", encoding="utf-8") as fd:
                settings_data = yaml.load(fd) or {}
                self.timeouts = settings_data.get("timeouts", {})
                self.retries = settings_data.get("retries", {})
                self.cost = settings_data.get("cost", {})
                self.cache = settings_data.get("cache", {})
                self.cms = settings_data.get("cms", {})

    def _load_env(self) -> None:
        self.openai_api_key = self.openai_api_key or self._get_env("OPENAI_API_KEY")
        self.groq_api_key = self.groq_api_key or self._get_env("GROQ_API_KEY")
        self.ai_studio_api_key = self.ai_studio_api_key or self._get_env("AI_STUDIO_API_KEY")

    def _get_env(self, name: str) -> str | None:
        value = __import__("os").environ.get(name)
        return value if value not in (None, "") else None

    def model_role_config(self, role: str) -> dict[str, Any]:
        roles = self._config_data.get("roles", {})
        return roles.get(role, {})
