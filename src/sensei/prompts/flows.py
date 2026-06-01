"""Deterministic openers for scheduled check-ins.

Sent instantly (no LLM call) so the user sees a message the moment the check-in fires.
The LLM takes over from the user's first reply onward.
"""

MORNING_OPENER = "Morning. What are we working on today?"

EVENING_OPENER = "Evening. How did today actually go?"

INTRO_OPENER = (
    "Hey — before we start the daily routine, I want to properly get to know you. "
    "Tell me a bit about yourself: who you are, what you do, what's going on in your life right now."
)


def session_context(slot: str, local_time: str) -> str:
    return (
        f"[System: This is the user's {slot} check-in, started at {local_time} local time. "
        "The user was just greeted. Their next message is incoming. "
        "Begin by reading get_user_info() and the relevant day log before responding.]"
    )


def intro_context() -> str:
    return (
        "[System: This is the first-time onboarding conversation. "
        "The user has just been greeted with the intro opener. "
        "Your job is to learn who they are and what they're working toward, "
        "then call save_user_info() with a structured summary.]"
    )
