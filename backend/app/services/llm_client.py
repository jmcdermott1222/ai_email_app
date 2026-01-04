"""OpenAI LLM client wrapper with structured outputs."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import jsonschema
from openai import OpenAI

from app.config import Settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when LLM call fails."""


class LLMClient:
    """Wrapper for OpenAI structured output calls."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMError("OPENAI_API_KEY is not configured")
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._default_model = settings.openai_model

    def call_structured(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Call OpenAI with strict JSON schema output and one repair retry."""
        target_model = model or self._default_model
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        logger.info(
            "LLM call start",
            extra={
                "prompt_hash": prompt_hash,
                "prompt_len": len(prompt),
                "model": target_model,
            },
        )
        content = self._call_model(
            prompt=prompt,
            json_schema=json_schema,
            model=target_model,
            temperature=temperature,
            include_schema=True,
        )
        parsed = self._parse_and_validate(content, json_schema)
        if parsed is not None:
            return parsed

        repair_prompt = (
            "You returned JSON that did not match the schema. "
            "Return ONLY valid JSON that matches the schema. "
            "Do not include any extra keys or text.\n\n"
            f"Schema:\n{json.dumps(json_schema)}\n\n"
            f"Invalid JSON:\n{content}"
        )
        repair_hash = hashlib.sha256(repair_prompt.encode("utf-8")).hexdigest()
        logger.warning(
            "LLM repair retry",
            extra={
                "prompt_hash": repair_hash,
                "prompt_len": len(repair_prompt),
                "model": target_model,
            },
        )
        repair_content = self._call_model(
            prompt=repair_prompt,
            json_schema=json_schema,
            model=target_model,
            temperature=0,
            include_schema=False,
        )
        parsed = self._parse_and_validate(repair_content, json_schema)
        if parsed is None:
            raise LLMError("LLM output failed schema validation after repair")
        return parsed

    def _call_model(
        self,
        prompt: str,
        json_schema: dict[str, Any],
        model: str,
        temperature: float,
        include_schema: bool,
    ) -> str:
        if hasattr(self._client, "responses"):
            response = self._client.responses.create(
                model=model,
                input=prompt,
                temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_output",
                        "schema": json_schema,
                        "strict": True,
                    },
                },
            )
            return response.output_text

        schema_block = (
            f"\n\nJSON Schema:\n{json.dumps(json_schema)}" if include_schema else ""
        )
        response = self._client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON that matches the provided schema. "
                        "No extra keys or commentary."
                    ),
                },
                {"role": "user", "content": f"{prompt}{schema_block}"},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise LLMError("LLM returned empty content")
        return content

    @staticmethod
    def _parse_and_validate(
        content: str, json_schema: dict[str, Any]
    ) -> dict[str, Any] | None:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return None
        try:
            jsonschema.validate(parsed, json_schema)
        except jsonschema.ValidationError:
            return None
        return parsed
