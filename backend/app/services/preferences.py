"""Preference defaults and helpers."""

from __future__ import annotations

from copy import deepcopy

DEFAULT_PREFERENCES = {
    "digest_time_local": "08:00",
    "vip_alerts_enabled": True,
    "working_hours": {
        "days": ["mon", "tue", "wed", "thu", "fri"],
        "start_time": "09:00",
        "end_time": "17:00",
        "lunch_start": "12:00",
        "lunch_end": "13:00",
    },
    "meeting_default_duration_min": 30,
    "automation_level": "SUGGEST_ONLY",
}


def default_preferences() -> dict:
    """Return a copy of default preferences."""
    return deepcopy(DEFAULT_PREFERENCES)
