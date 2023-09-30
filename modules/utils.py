import re
from pyshorteners import Shortener


# Discordの文字装飾のエスケープ
def escape_markdown(text: str):
    result = ""
    for c in text:
        if c in ["*", "`", "\\", "|", "-", "_"]:
            result += "\\"
        result += c
    return result


def limit_text_length(text: str, length: int):
    if len(text) > length:
        result = text[:length - 1] + "…"
    else:
        result = text
    return result


def is_url(text: str):
    return re.match(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", text)


def shorten_url(url: str):
    shortener = Shortener()
    shortened_url = shortener.tinyurl.short(url)
    return shortened_url