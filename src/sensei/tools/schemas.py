"""Gemini function declarations for the tools the model is allowed to call."""

from typing import Any

READ_TOOL_NAMES = {"get_user_profile", "get_user_info", "get_pending_tasks", "get_day"}
WRITE_TOOL_NAMES = {
    "save_morning_plan",
    "save_evening_review",
    "save_user_info",
    "log_checkin",
    "finalize_conversation",
}


def declarations() -> list[dict[str, Any]]:
    return [
        {
            "name": "get_user_profile",
            "description": "Read the user's technical profile (name, timezone, check-in times).",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_user_info",
            "description": (
                "Read the user's personal background — who they are, what they're working "
                "toward, their challenges. Read this at the start of every session."
            ),
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_pending_tasks",
            "description": "List incomplete tasks carried over from previous days.",
            "parameters": {"type": "OBJECT", "properties": {}},
        },
        {
            "name": "get_day",
            "description": (
                "Read the full log for a specific day — tasks planned, completed, "
                "skipped, mood, energy, and reflection. Pass 'today', 'yesterday', "
                "or an ISO date like '2026-05-28'."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "date": {
                        "type": "STRING",
                        "description": "ISO date string, or 'today' / 'yesterday'.",
                    }
                },
                "required": ["date"],
            },
        },
        {
            "name": "save_morning_plan",
            "description": (
                "Persist the user's planned tasks for today. Shown to user for "
                "confirmation before writing. Only call once the user has agreed "
                "on their plan in chat."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "tasks": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Concrete tasks the user committed to today.",
                    }
                },
                "required": ["tasks"],
            },
        },
        {
            "name": "save_evening_review",
            "description": (
                "Persist the evening review for today. completed/skipped use the "
                "exact task text from the morning plan."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "completed": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Tasks the user actually completed.",
                    },
                    "skipped": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                        "description": "Tasks the user did not do.",
                    },
                    "reflection": {
                        "type": "STRING",
                        "description": "Short reflection: what went well, what didn't, key insight.",
                    },
                },
                "required": ["completed", "skipped", "reflection"],
            },
        },
        {
            "name": "save_user_info",
            "description": (
                "Write (or update) the user's personal background file. Use during "
                "onboarding after learning who they are and what they're working toward. "
                "The user can also ask to update this at any time."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "content": {
                        "type": "STRING",
                        "description": (
                            "Full markdown body for _user_info.md. Use clear sections: "
                            "## Who I Am, ## What I'm Working Toward, ## My Challenges. "
                            "Write in first person from the user's perspective."
                        ),
                    }
                },
                "required": ["content"],
            },
        },
        {
            "name": "log_checkin",
            "description": "Record mood and energy for this check-in (1=low, 2=med, 3=high).",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "slot": {"type": "STRING", "enum": ["morning", "evening"]},
                    "mood": {"type": "INTEGER", "description": "1, 2, or 3."},
                    "energy": {"type": "INTEGER", "description": "1, 2, or 3."},
                },
                "required": ["slot", "mood", "energy"],
            },
        },
        {
            "name": "finalize_conversation",
            "description": (
                "Signal that this conversation is complete. Call after all saves are "
                "confirmed and you've said goodbye."
            ),
            "parameters": {"type": "OBJECT", "properties": {}},
        },
    ]


def onboarding_declarations() -> list[dict[str, Any]]:
    """Narrow tool set for the intro/onboarding session — only what's needed."""
    return [d for d in declarations() if d["name"] in {"save_user_info", "finalize_conversation"}]
