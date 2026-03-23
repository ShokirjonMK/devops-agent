import re

_BLOCKED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"rm\s+(-[rf]+\s+)?/\s", re.I),
    re.compile(r"rm\s+-rf\s+[\'\"]?\s*/", re.I),
    re.compile(r"\bdd\b", re.I),
    re.compile(r"\bmkfs\b", re.I),
    re.compile(r":\s*\(\)\s*\{\s*:\s*\|:\s*&\s*\}\s*;", re.I),
    re.compile(r"\bshutdown\b", re.I),
    re.compile(r"\breboot\b", re.I),
    re.compile(r"\bhalt\b", re.I),
    re.compile(r"\bpoweroff\b", re.I),
    re.compile(r"\binit\s+0\b", re.I),
    re.compile(r">\s*/dev/sd", re.I),
    re.compile(r"\bwipefs\b", re.I),
    re.compile(r"\bchmod\s+[-+]?\s*777\s+/", re.I),
    re.compile(r"\bchown\s+.*\s+/", re.I),
    re.compile(r"curl\s+.*\|\s*(ba)?sh", re.I),
    re.compile(r"\bwget\s+.*\|\s*(ba)?sh", re.I),
]


def is_command_allowed(command: str) -> tuple[bool, str | None]:
    raw = (command or "").strip()
    if not raw:
        return False, "Empty command"
    if "\n" in raw or "\r" in raw:
        return False, "Multi-line commands are not allowed"
    if len(raw) > 4000:
        return False, "Command too long"
    lower = raw.lower()
    for pat in _BLOCKED_PATTERNS:
        if pat.search(lower):
            return False, f"Blocked pattern: {pat.pattern}"
    return True, None
