__all__ = ['clean_content']


def clean_content(content: str) -> str:
    """Prevents mentions in strings being sent as messages to Discord."""

    return content \
        .replace('@everyone', '@\u200beveryone') \
        .replace('@here', '@\u200bhere') \
        .replace('<@', '<\u200b@')
