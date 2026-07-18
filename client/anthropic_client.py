import json
import logging
from typing import Any, Dict, Optional, Tuple

import anthropic

from utils.configuration import Configuration
from utils.exception import AnthropicException
from utils.logger import Logger

# Standard (non-introductory) USD price per million tokens: (input, output).
_MODEL_PRICING_PER_MILLION: Dict[str, Tuple[float, float]] = {
    "claude-fable-5": (10.00, 50.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
}


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

        self._log_cost(response)

        if response.stop_reason == "max_tokens":
            raise AnthropicException(
                "Anthropic response truncated (max_tokens)"
            )
        return self._parse_json(self._extract_text(response))

    def _log_cost(self, response: Any) -> None:
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = self._estimate_cost(input_tokens, output_tokens)
        cost_text = f"${cost:.4f}" if cost is not None else "unknown"
        self.logger.info(
            f"Anthropic call model={self._model} "
            f"input_tokens={input_tokens} output_tokens={output_tokens} "
            f"estimated_cost={cost_text}"
        )

    def _estimate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> Optional[float]:
        pricing = _MODEL_PRICING_PER_MILLION.get(self._model)
        if pricing is None:
            return None
        input_price, output_price = pricing
        return (
            input_tokens * input_price + output_tokens * output_price
        ) / 1_000_000

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
            self.logger.warning(
                f"Anthropic response is not valid JSON: {text!r}"
            )
            raise AnthropicException(f"Invalid JSON from Anthropic: {e}")
        if not isinstance(data, dict):
            self.logger.warning(
                f"Anthropic response is not a JSON object: {text!r}"
            )
            raise AnthropicException("Anthropic JSON is not an object")
        return data
