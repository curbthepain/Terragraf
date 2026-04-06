"""
query/parser.py — Intent parser for native tab queries.

Tokenizes user input and extracts verb, target, and modifiers.
Pure pattern matching — no LLM.
"""

from dataclasses import dataclass, field


# Recognized verbs — order matters for prefix matching
VERBS = [
    "analyze", "solve", "check", "create", "run", "show", "list",
    "search", "generate", "launch", "train", "tune", "dispatch",
    "render", "test", "scaffold", "sharpen", "scan", "verify",
    "new", "hot", "session",
]


@dataclass
class Intent:
    """Parsed user intent."""
    verb: str = ""
    target: str = ""
    modifiers: list[str] = field(default_factory=list)
    raw: str = ""


class IntentParser:
    """
    Parse free-text input into structured Intent.

    Extracts a verb from the known vocabulary, a target (remaining
    non-modifier tokens), and modifier flags (--foo, --bar=baz).
    """

    def __init__(self, extra_verbs: list[str] | None = None):
        self._verbs = set(VERBS)
        if extra_verbs:
            self._verbs.update(v.lower() for v in extra_verbs)

    def parse(self, text: str) -> Intent:
        """Parse raw text into an Intent."""
        raw = text.strip()
        if not raw:
            return Intent(raw=raw)

        tokens = raw.split()
        modifiers = []
        words = []

        for tok in tokens:
            if tok.startswith("--"):
                modifiers.append(tok)
            else:
                words.append(tok)

        if not words:
            return Intent(modifiers=modifiers, raw=raw)

        # Check if first word is a known verb
        verb = ""
        target_words = words

        if words[0].lower() in self._verbs:
            verb = words[0].lower()
            target_words = words[1:]

        target = " ".join(target_words).strip()

        return Intent(
            verb=verb,
            target=target,
            modifiers=modifiers,
            raw=raw,
        )
