import re
import os

BANNED_WORDS = os.getenv('VINX_BANNED_WORDS', 'sex,violence,illegal').split(',')
BANNED_WORDS = [w.strip().lower() for w in BANNED_WORDS if w.strip()]


def check_text_allowed(text: str) -> (bool, str):
    """Return (allowed: bool, reason: str). Very small rule-based filter."""
    if not text or not text.strip():
        return False, 'empty'
    lowered = text.lower()
    for b in BANNED_WORDS:
        if b and b in lowered:
            return False, f'blocked word: {b}'
    # simple length guard
    if len(text) > 20000:
        return False, 'text too long'
    return True, ''
