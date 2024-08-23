import discord
import re
from pyshorteners import Shortener
from typing import List
from urllib.parse import urlparse
import constants as const
from character_config import COMMAND_DESCRIPTION, DEFAULT_MEMBER_SUFFIX


# Discordの文字装飾のエスケープ
def escape_markdown(text: str):
    result = ''
    for c in text:
        if c in ['*', '`', '\\', '|', '-', '_']:
            result += '\\'
        result += c
    return result


def truncate_text(text: str, length: int):
    if len(text) > length:
        result = text[:length - 1] + '…'
    else:
        result = text
    return result


def make_command_args(command: List | str):
    if type(command) == List:
        name = command[-1]
        key = ' '.join(command)
    else:
        name = command
        key = command
    return {
        'name': name,
        'description': COMMAND_DESCRIPTION[key]
    }


def is_url(text: str):
    return re.match(const.RE_PATTERN_URL, text)

def is_niconico_url(text: str):
    return re.match(const.RE_PATTERN_URL_NICONICO, text)


def shorten_url(url: str):
    return Shortener().tinyurl.short(url)

def get_domain(url: str):
    return f'{urlparse(url).scheme}://{urlparse(url).netloc}'

def get_favicon_url(url: str):
    return f'https://www.google.com/s2/favicons?domain={get_domain(url)}&size=64'


def get_member_text(member: discord.Member, bold: bool=True, decoration: bool=True, suffix: str=DEFAULT_MEMBER_SUFFIX):
    result = member.display_name
    if bold and decoration:
        result = f'**{result}**'
    global_name = member.name
    if decoration:
        global_name = f'`{global_name}`'
    result += f'({global_name})'
    if suffix:
        result += f' {suffix}'
    return result