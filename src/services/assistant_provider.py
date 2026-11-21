"""Provider-neutral interface and Sarvam-compatible HTTP adapter."""
import json
import logging
import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.domain.assistant import AssistantProviderStatus

LOGGER = logging.getLogger(__name__)


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
        timeout_seconds: int = 60,
    ):
        self.api_key = api_key if api_key is not None else self._load_api_key()
        self.api_url = api_url if api_url is not None else os.getenv(
            "SARVAM_API_URL",
            "https://api.sarvam.ai/v1/chat/completions",
        )
        self.model = model if model is not None else os.getenv("SARVAM_MODEL", "sarvam-105b")
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _load_api_key() -> Optional[str]:
        env_key = os.getenv("SARVAM_API_KEY")
        if env_key:
            return env_key.strip()

        secret_path = Path(__file__).resolve().parent.parent.parent / "secrets.env"
        if not secret_path.exists():
            return None
        for raw_line in secret_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() in ("SARVAM_API_KEY", "key"):
                return value.strip() or None
        return None

    def status(self) -> AssistantProviderStatus:
        if not self.api_key:
            return AssistantProviderStatus(False, "Sarvam AI", "SARVAM_API_KEY is not configured")
        if not self.api_url:
            return AssistantProviderStatus(False, "Sarvam AI", "SARVAM_API_URL is not configured")
        return AssistantProviderStatus(True, "Sarvam AI")

    @staticmethod
    def _extract_final_answer(text: str) -> str:
        markers = (
            r"(?:Let me refine[^:\n]*:\s*)(.+)$",
            r"(?:Let me draft[^:\n]*:\s*)(.+)$",
            r"(?:Final (?:answer|response):\s*)(.+)$",
        )
        for marker in markers:
            match = re.search(marker, text, flags=re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(1).strip()
        summary_match = re.search(
            r"(The (?:network|overall).{0,700})",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if summary_match:
            return summary_match.group(1).strip()
        return text.strip()

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
            "reasoning_effort": "low",
            "max_tokens": 800,
        }
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer " + str(self.api_key),
                "api-subscription-key": str(self.api_key),
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            try:
                error_body = json.loads(exc.read().decode("utf-8"))
                code = error_body.get("error", {}).get("code")
            except (json.JSONDecodeError, UnicodeDecodeError):
                code = None
            if code == "invalid_api_key_error":
                raise AssistantProviderError("Sarvam AI rejected the configured API key") from exc
            raise AssistantProviderError(f"Sarvam AI returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError) as exc:
            raise AssistantProviderError("Sarvam AI is unreachable") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise AssistantProviderError("Sarvam AI returned malformed JSON") from exc

        try:
            message = body["choices"][0]["message"]
            content = message.get("content")
            if content is None:
                reasoning = (
                    message.get("reasoning_content")
                    or message.get("reasoning")
                    or message.get("text")
                )
                content = (
                    self._extract_final_answer(reasoning)
                    if isinstance(reasoning, str)
                    else reasoning
                )
        except (KeyError, IndexError, TypeError):
            content = body.get("output_text") or body.get("text")
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    text_parts.append(str(item.get("text") or item.get("content") or ""))
            content = "".join(text_parts)
        elif isinstance(content, dict):
            content = content.get("text") or content.get("content")
        if not isinstance(content, str) or not content.strip():
            LOGGER.warning(
                "Sarvam returned malformed content: body_keys=%s content_type=%s",
                sorted(body.keys()) if isinstance(body, dict) else type(body).__name__,
                type(content).__name__,
            )
            raise AssistantProviderError("Sarvam AI returned an empty or malformed response")
        return content.strip()
