import discord
import re
from pyshorteners import Shortener
import constants as const


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
    return re.match(const.RE_PATTERN_URL, text)

def is_full_url(text: str):
    return re.match(const.RE_PATTERN_FULL_URL, text)

def is_youtube_url(text: str):
    return re.match(const.RE_PATTERN_URL_YOUTUBE, text)

def is_soundcloud_url(text: str):
    return re.match(const.RE_PATTERN_URL_SOUNDCLOUD, text)

def is_niconico_url(text: str):
    return re.match(const.RE_PATTERN_URL_NICONICO, text)

def shorten_url(url: str):
    return Shortener().tinyurl.short(url)


def get_member_text(member: discord.Member, bold: bool=True, decoration: bool=True, suffix: str="先生"):
    result = member.display_name
    if bold and decoration:
        result = f"**{result}**"
    global_name = member.name
    if decoration:
        global_name = f"`{global_name}`"
    result += f"({global_name})"
    if suffix:
        result += f" {suffix}"
    return result