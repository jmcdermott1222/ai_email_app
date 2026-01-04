from types import SimpleNamespace

from app.config import Settings
from app.services import llm_client as llm_module


def test_llm_client_fallback_chat(monkeypatch):
    captured = {}

    class DummyChatCompletions:
        def create(self, **kwargs):
            captured["kwargs"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))
                ]
            )

    class DummyOpenAI:
        def __init__(self, api_key: str):
            self.chat = SimpleNamespace(completions=DummyChatCompletions())

    monkeypatch.setattr(llm_module, "OpenAI", DummyOpenAI)
    settings = Settings(openai_api_key="test-key")
    client = llm_module.LLMClient(settings)
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    result = client.call_structured("Hello", schema, model="gpt-4o-mini")

    assert result == {"ok": True}
    assert captured["kwargs"]["response_format"] == {"type": "json_object"}
