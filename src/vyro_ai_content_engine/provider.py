from __future__ import annotations

import os
import random
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv


class ProviderError(RuntimeError):
    """Raised when the configured model provider fails or returns invalid data."""


@dataclass(frozen=True)
class ProviderResponse:
    content: str
    request_id: str
    model: str
    usage: dict[str, Any] | None = None


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 75,
                 connect_timeout: float = 15, max_retries: int = 3, temperature: float = 0.55,
                 max_output_tokens: int = 3500, json_mode: bool = True):
        if not api_key.strip():
            raise ValueError("AI_API_KEY belum diatur")
        if not base_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("AI_BASE_URL harus HTTPS; HTTP hanya diizinkan untuk localhost")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)
        self.max_retries = max(0, min(max_retries, 5))
        self.temperature = max(0.0, min(temperature, 1.2))
        self.max_output_tokens = max(500, min(max_output_tokens, 8000))
        self.json_mode = json_mode

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider":
        load_dotenv()
        return cls(
            os.getenv("AI_BASE_URL", "https://api.openai.com/v1"),
            os.getenv("AI_API_KEY", ""),
            os.getenv("AI_MODEL", "gpt-4.1-mini"),
            float(os.getenv("AI_TIMEOUT_SECONDS", "75")),
            float(os.getenv("AI_CONNECT_TIMEOUT_SECONDS", "15")),
            int(os.getenv("AI_MAX_RETRIES", "3")),
            float(os.getenv("AI_TEMPERATURE", "0.55")),
            int(os.getenv("AI_MAX_OUTPUT_TOKENS", "3500")),
            os.getenv("AI_JSON_MODE", "true").lower() in {"1", "true", "yes", "on"},
        )

    def complete(self, system_prompt: str, user_prompt: str) -> ProviderResponse:
        request_id = uuid.uuid4().hex
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_output_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.json_mode:
            payload["response_format"] = {"type": "json_object"}
        last_error: Exception | None = None
        with httpx.Client(timeout=self.timeout) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                            "X-Client-Request-Id": request_id,
                        },
                        json=payload,
                    )
                    if response.status_code in {408, 409, 429, 500, 502, 503, 504} and attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After", "")
                        try:
                            delay = min(max(float(retry_after), 0), 45) if retry_after else min(2 ** attempt + random.random(), 20)
                        except ValueError:
                            delay = min(2 ** attempt + random.random(), 20)
                        time.sleep(delay)
                        continue
                    response.raise_for_status()
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    if not isinstance(text, str) or not text.strip():
                        raise ProviderError("Provider mengembalikan content kosong")
                    return ProviderResponse(text, request_id, data.get("model", self.model), data.get("usage"))
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    last_error = exc
                    if attempt >= self.max_retries:
                        break
                    time.sleep(min(2 ** attempt + random.random(), 20))
                except (httpx.HTTPStatusError, KeyError, IndexError, ValueError) as exc:
                    raise ProviderError(f"Respons provider tidak valid: {type(exc).__name__}; request_id={request_id}") from exc
        raise ProviderError(f"Provider gagal setelah retry terbatas; request_id={request_id}; cause={type(last_error).__name__ if last_error else 'unknown'}")
