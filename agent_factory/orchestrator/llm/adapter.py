from __future__ import annotations

import json
import os
import urllib.request
from typing import Any, Dict, Optional


class LLMError(Exception):
    pass


class OpenAICompatibleAdapter:
    def __init__(self, api_key: Optional[str], base_url: str, model: str):
        if not api_key:
            raise LLMError("Missing API key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # pragma: no cover - network errors handled in runtime
            raise LLMError(str(e))

        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception:
            raise LLMError("Model did not return valid JSON")

    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }

        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:  # pragma: no cover - network errors handled in runtime
            raise LLMError(str(e))

        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            raise LLMError("Model did not return text content")
