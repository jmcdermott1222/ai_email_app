"""JSON Schemas for LLM structured outputs."""

EMAIL_TRIAGE_SCHEMA_VERSION = "v1"
EMAIL_SUMMARY_SCHEMA_VERSION = "v1"
CALENDAR_CANDIDATE_SCHEMA_VERSION = "v1"
DRAFT_PROPOSAL_SCHEMA_VERSION = "v1"

EMAIL_TRIAGE_RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "importance_label": {
            "type": "string",
            "enum": ["IGNORE", "LOW", "MEDIUM", "HIGH"],
        },
        "needs_response": {"type": "boolean"},
        "summary_bullets": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "why_important": {"type": "string"},
    },
    "required": [
        "importance_label",
        "needs_response",
        "summary_bullets",
        "why_important",
    ],
}

EMAIL_SUMMARY_RESULT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary_bullets": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 5,
        },
        "action_items": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary_bullets", "action_items"],
}

CALENDAR_CANDIDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "candidates": {"type": "array", "items": {"type": "object"}},
    },
    "required": ["candidates"],
}

DRAFT_PROPOSAL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["subject", "body"],
}
