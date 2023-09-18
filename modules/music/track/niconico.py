import discord
from constants import FFMPEG_OPTIONS
from niconico import NicoNico
from .base import BaseTrack


class NicoNicoTrack(BaseTrack):
    def __init__(self, original_url: str, title: str, artist: str, thumbnail: str, duration: int, member: discord.Member) -> None:
        self.__video = None
        super().__init__(original_url, None, title, artist, None, thumbnail, duration, member)
        
    # video.connect() ~ video.close_connection()の間のみURLが有効？
    async def create_source(self, volume: int):
        nc_client = NicoNico()
        self.__video = nc_client.video.get_video(self.original_url)
        self.__video.connect()
        self.url = self.__video.download_link
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url, **FFMPEG_OPTIONS),
            volume=volume
        )

    async def release_source(self):
        self.__video.close()
        self.__video = None
        self.source = None
        self.url = None