import discord
from constants import FFMPEG_OPTIONS


class BaseTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(
            self,
            member: discord.Member,
            title: str,
            url: str,
            original_url: str | None=None,
            duration: int | None=None,
            artist: str | None=None,
            album: str | None=None,
            thumbnail: str | None=None
        ) -> None:
        self.member: discord.Member = member
        self.title: str = title
        self.url: str = url
        self.original_url: str | None = original_url
        self.duration: int | None = duration
        self.artist: str | None = artist
        self.album: str | None = album
        self.thumbnail: str | None = thumbnail

    async def create_source(self, volume: float):
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url, **FFMPEG_OPTIONS),
            volume=volume
        )

    async def release_source(self):
        self.source = None