import discord
from constants import FFMPEG_OPTIONS


class BaseTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, original_url: str, url: str, title: str, artist: str, album: str, thumbnail: str, duration: int, member: discord.Member) -> None:
        self.original_url: str = original_url
        self.url: str = url
        self.title: str = title
        self.artist: str | None = artist
        self.album: str | None = album
        self.thumbnail: str | None = thumbnail
        self.duration: int = duration
        self.member: discord.Member = member

    async def create_source(self, volume: float):
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url, **FFMPEG_OPTIONS),
            volume=volume
        )

    async def release_source(self):
        self.source = None