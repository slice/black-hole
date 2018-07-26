__all__ = ['clean_content']

import re

MENTION_RE = re.compile(r'<@[!&]?(\d+)>')


def _replacer(match):
    return match.group(0).strip('<>')


def clean_content(content: str) -> str:
    """Prevent mentions in strings being sent as messages to Discord."""

    content = content \
        .replace('@everyone', '@\u200beveryone') \
        .replace('@here', '@\u200bhere')

    content = MENTION_RE.sub(_replacer, content)
    return content
