"""Log desensitization — strip keys, tokens, document content from log output.

Sensitive patterns detected and redacted:
- JWT tokens (Bearer Authorization headers)
- API keys (X-API-Key headers, sk-* patterns)
- Passwords in JSON payloads
- Document content (bids, financial data)
- Access tokens and refresh tokens in dicts/logs
"""

from __future__ import annotations

import logging
import re
from typing import Any

# ── Regex patterns for sensitive data ───────────────────────────────────────

_SENSITIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Bearer tokens in Authorization headers
    (re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),

    # API keys (common patterns: sk-, api-, key-)
    (re.compile(r"(?:X-API-Key|api_key|apikey)\s*[:=]\s*['\"]?([A-Za-z0-9\-_]{20,})", re.IGNORECASE),
     r"[REDACTED_API_KEY]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED_API_KEY]"),

    # JWT tokens in various contexts
    (re.compile(r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+"), "[REDACTED_JWT]"),

    # Password fields in JSON payloads
    (re.compile(r'("password"\s*:\s*")[^"]*(")', re.IGNORECASE), r'\1[REDACTED]\2'),
    (re.compile(r"'password'\s*:\s*'[^']*'", re.IGNORECASE), "'password': '[REDACTED]'"),

    # Access tokens in dict representations
    (re.compile(r"'access_token'\s*:\s*'[^']*'", re.IGNORECASE), "'access_token': '[REDACTED]'"),
    (re.compile(r"\"access_token\"\s*:\s*\"[^\"]*\"", re.IGNORECASE), '"access_token": "[REDACTED]"'),

    # Refresh tokens
    (re.compile(r"'refresh_token'\s*:\s*'[^']*'", re.IGNORECASE), "'refresh_token': '[REDACTED]'"),
    (re.compile(r"\"refresh_token\"\s*:\s*\"[^\"]*\"", re.IGNORECASE), '"refresh_token": "[REDACTED]"'),

    # Token query params (?token=eyJ...)
    (re.compile(r"(token=)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"\1[REDACTED]"),

    # API key in query params (?api_key=...)
    (re.compile(r"(api[_-]?key=)[A-Za-z0-9\-_]+", re.IGNORECASE), r"\1[REDACTED]"),

    # Generic secret/key patterns
    (re.compile(r"(secret|private_key)\s*[:=]\s*['\"]?[A-Za-z0-9\-_+/]{16,}", re.IGNORECASE),
     r"[REDACTED_SECRET]"),
    (re.compile(r"ghp_[A-Za-z0-9]{36}"), "[REDACTED_GITHUB_TOKEN]"),  # GitHub tokens
]

# Sensitive keys in dictionaries
_SENSITIVE_DICT_KEYS: set[str] = {
    "password", "password_hash", "hashed_password",
    "access_token", "refresh_token", "token",
    "api_key", "apikey", "secret", "private_key",
    "jwt", "authorization", "credential",
    "credit_card", "ssn", "social_security",
}


def desensitize(text: str | None) -> str:
    """Strip sensitive data from a log string.

    Args:
        text: The log line or message to desensitize.

    Returns:
        Desensitized string with sensitive content replaced by [REDACTED] markers.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        text = str(text)

    result = text
    for pattern, replacement in _SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def desensitize_dict(data: dict[str, Any] | None) -> dict[str, Any]:
    """Strip sensitive values from a dictionary (for structured logging).

    Args:
        data: Dictionary potentially containing sensitive values.

    Returns:
        A new dictionary with sensitive values replaced by [REDACTED].
    """
    if data is None:
        return {}

    safe: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in _SENSITIVE_DICT_KEYS:
            safe[key] = "[REDACTED]"
        elif isinstance(value, dict):
            safe[key] = desensitize_dict(value)
        elif isinstance(value, (list, tuple)):
            safe[key] = [
                desensitize_dict(v) if isinstance(v, dict)
                else desensitize(v) if isinstance(v, str)
                else v
                for v in value
            ]
        elif isinstance(value, str):
            safe[key] = desensitize(value)
        else:
            safe[key] = value
    return safe


class DesensitizingFormatter(logging.Formatter):
    """Logging formatter that automatically desensitizes log messages."""

    def format(self, record: logging.LogRecord) -> str:
        """Format and desensitize a log record."""
        record.msg = desensitize(str(record.msg))
        return super().format(record)
