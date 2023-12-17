from datetime import datetime, timezone, timedelta
import discord
from typing import Literal

LogType = Literal["info", "error"]

def mashilog(content, ctx: discord.ApplicationContext=None, log_type: LogType="info", guild: discord.Guild=None, channel: discord.TextChannel | discord.VoiceChannel=None, member: discord.Member=None, **options):
    if log_type == "error":
        type_text = "\033[1;31mERROR\033[m"
        content_ = f"\033[1;31m{content}\033[m"
    else:
        type_text = "\033[1;36mINFO\033[m"
        content_ = content

    if ctx and hasattr(ctx.command, "name"):
        content_ = f"[{ctx.command.name}] {content_}"

    now_str = datetime.now(timezone(timedelta(hours=9), 'JST')).strftime("%Y-%m-%d %H:%M:%S")
    log_text = f"\033[1;94m{now_str}\033[m {type_text}\t\033[1;32m静山マシロ\033[m {content_}"
    print(log_text)

    if guild:
        print(f"\t\t\t\t\t\033[1;33mguild:\033[m {guild.name} ({guild.id})")
    if channel:
        print(f"\t\t\t\t\t\033[1;33mchannel:\033[m {channel.name} ({channel.id})")
    if member:
        print(f"\t\t\t\t\t\033[1;33mmember:\033[m {member.name} ({member.id})")
    for key in options:
        print(f"\t\t\t\t\t\033[1;33m{key}:\033[m {options[key]}")