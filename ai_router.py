from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key_env: str
    model_env: str
    default_model: str


PROVIDERS = {
    "openrouter": Provider("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "openrouter/auto"),
    "deepseek": Provider("deepseek", "https://api.deepseek.com", "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "deepseek-chat"),
    "groq": Provider("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile"),
    "openai": Provider("openai", "https://api.openai.com/v1", "OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4.1-mini"),
    "ollama": Provider("ollama", "http://127.0.0.1:11434/v1", "OLLAMA_API_KEY", "OLLAMA_MODEL", "llama3.2"),
}


class AIProviderError(RuntimeError):
    pass


def _configured(provider: Provider) -> bool:
    if provider.name == "ollama":
        return True
    return bool(os.getenv(provider.api_key_env, "").strip())


def configured_provider_names() -> list[str]:
    return [name for name, provider in PROVIDERS.items() if _configured(provider)]


def _headers(provider: Provider) -> dict[str, str]:
    token = os.getenv(provider.api_key_env, "").strip()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if provider.name == "openrouter":
        headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "https://github.com/wjrm2/qahtan-telegram-server")
        headers["X-OpenRouter-Title"] = "Az Telegram assistant"
    return headers


def _request(provider: Provider, messages: list[dict[str, Any]], *, temperature: float = 0.4, timeout: int = 45) -> str:
    model = os.getenv(provider.model_env, provider.default_model).strip()
    response = requests.post(
        f"{provider.base_url.rstrip('/')}/chat/completions",
        headers=_headers(provider),
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=timeout,
    )
    if not response.ok:
        raise AIProviderError(f"{provider.name}: HTTP {response.status_code}")
    data = response.json()
    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise AIProviderError(f"{provider.name}: invalid response") from exc


def chat(messages: list[dict[str, Any]], *, preferred: str | None = None) -> tuple[str, str]:
    requested = (preferred or os.getenv("AI_PROVIDER", "openrouter")).strip().lower()
    order = [requested] + [name for name in ("openrouter", "ollama", "deepseek", "groq", "openai") if name != requested]
    errors: list[str] = []
    for name in order:
        provider = PROVIDERS.get(name)
        if not provider or not _configured(provider):
            continue
        try:
            return _request(provider, messages), provider.name
        except (requests.RequestException, AIProviderError) as exc:
            errors.append(str(exc))
    raise AIProviderError("لا يوجد مزود ذكاء متاح حاليًا: " + "; ".join(errors[-3:]))
