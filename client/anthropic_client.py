import json
import logging
from typing import Any, Dict

import anthropic

from utils.configuration import Configuration
from utils.exception import AnthropicException
from utils.logger import Logger


class AnthropicClient:
    def __init__(self, configuration: Configuration) -> None:
        self.logger = Logger.get_logger("anthropic_client", logging.INFO)
        self._model = configuration.anthropic_model
        self._client = anthropic.Anthropic(
            api_key=configuration.anthropic_api_key,
            max_retries=3,
        )

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self, system: str, user_payload: str, max_tokens: int = 4096
    ) -> Dict[str, Any]:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                thinking={"type": "disabled"},
                system=system,
                messages=[{"role": "user", "content": user_payload}],
            )
        except (anthropic.APIError, anthropic.APIConnectionError) as e:
            raise AnthropicException(f"Anthropic API call failed: {e}")

        if response.stop_reason == "max_tokens":
            raise AnthropicException(
                "Anthropic response truncated (max_tokens)"
            )
        return self._parse_json(self._extract_text(response))

    def _extract_text(self, response: Any) -> str:
        for block in response.content:
            if block.type == "text":
                return block.text
        raise AnthropicException("Anthropic response has no text block")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[len("json") :]
                cleaned = cleaned.strip()
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise AnthropicException(f"Invalid JSON from Anthropic: {e}")
        if not isinstance(data, dict):
            raise AnthropicException("Anthropic JSON is not an object")
        return data
