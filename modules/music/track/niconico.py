import discord
from constants import FFMPEG_OPTIONS
from niconico import NicoNico
from .base import BaseTrack


class NicoNicoTrack(BaseTrack):
    def __init__(
            self,
            member: discord.Member,
            title: str,
            original_url: str,
            duration: int | None=None,
            artist: str | None=None,
            album: str | None=None,
            thumbnail: str | None=None
    ) -> None:
        self.__video = None
        super().__init__(
            member=member,
            title=title,
            source_url=None,
            original_url=original_url,
            duration=duration,
            artist=artist,
            album=album,
            thumbnail=thumbnail
        )
        
    # video.connect() ~ video.close_connection()の間のみURLが有効？
    async def create_source(self, volume: int):
        nc_client = NicoNico()
        self.__video = nc_client.video.get_video(self.original_url)
        self.__video.connect()
        self.source_url = self.__video.download_link
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.source_url, **FFMPEG_OPTIONS),
            volume=volume
        )

    async def release_source(self):
        self.__video.close()
        self.__video = None
        self.source = None
        self.source_url = None