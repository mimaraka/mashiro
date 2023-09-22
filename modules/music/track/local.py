import discord
import os
from .base import BaseTrack


class LocalTrack(BaseTrack):
    def __init__(self, member: discord.Member, filepath: str) -> None:
        title = os.path.splitext(os.path.basename(filepath))[0]
        super().__init__(
            member=member,
            title=title,
            source_url=filepath,
            original_url=None,
            duration=None,
            artist=None,
            album=None,
            thumbnail=None
        )