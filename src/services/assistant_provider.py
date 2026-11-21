"""Provider-neutral interface and Sarvam-compatible HTTP adapter."""
import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.domain.assistant import AssistantProviderStatus


class IAssistantProvider(ABC):
    @abstractmethod
    def status(self) -> AssistantProviderStatus:
        """Return whether the provider is configured."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate provider text or raise a provider error."""


class AssistantProviderError(RuntimeError):
    pass


class SarvamAssistantProvider(IAssistantProvider):
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: int = 30,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("SARVAM_API_KEY")
        self.api_url = api_url if api_url is not None else os.getenv("SARVAM_API_URL")
        self.model = model if model is not None else os.getenv("SARVAM_MODEL", "sarvam-m")
        self.timeout_seconds = timeout_seconds

    def status(self) -> AssistantProviderStatus:
        if not self.api_key:
            return AssistantProviderStatus(False, "Sarvam AI", "SARVAM_API_KEY is not configured")
        if not self.api_url:
            return AssistantProviderStatus(False, "Sarvam AI", "SARVAM_API_URL is not configured")
        return AssistantProviderStatus(True, "Sarvam AI")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        status = self.status()
        if not status.configured:
            raise AssistantProviderError(status.message or "Sarvam AI is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise AssistantProviderError(f"Sarvam AI returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise AssistantProviderError("Sarvam AI is unreachable") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AssistantProviderError("Sarvam AI returned malformed JSON") from exc

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = body.get("output_text") or body.get("text")
        if not isinstance(content, str) or not content.strip():
            raise AssistantProviderError("Sarvam AI returned an empty or malformed response")
        return content.strip()
