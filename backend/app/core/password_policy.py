"""Password policy rules — must stay in sync with frontend Yup schema."""
import re
from typing import Callable

_RULES: list[tuple[Callable[[str], bool], str]] = [
    (lambda p: len(p) >= 8,                  "At least 8 characters"),
    (lambda p: bool(re.search(r'[A-Z]', p)), "At least one uppercase letter"),
    (lambda p: bool(re.search(r'[a-z]', p)), "At least one lowercase letter"),
    (lambda p: bool(re.search(r'\d', p)),    "At least one digit (0–9)"),
]


def validate_password(password: str) -> list[str]:
    """Returns list of failed rule messages. Empty list means password is valid."""
    return [msg for check, msg in _RULES if not check(password)]
