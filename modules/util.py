import re
from pyshorteners import Shortener
from constants import RE_PATTERN_URL


# Discordの文字装飾のエスケープ
def escape_markdown(text: str):
    result = ""
    for c in text:
        if c in ["*", "`", "\\", "|", "-", "_"]:
            result += "\\"
        result += c
    return result


def truncate_text(text: str, length: int):
    if len(text) > length:
        result = text[:length - 1] + "…"
    else:
        result = text
    return result


def is_url(text: str):
    return re.match(RE_PATTERN_URL, text)


def shorten_url(url: str):
    return Shortener().tinyurl.short(url)