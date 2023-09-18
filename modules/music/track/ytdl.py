import aiohttp
import asyncio
import discord
import yt_dlp
from constants import YTDL_FORMAT_OPTIONS, FFMPEG_OPTIONS
from modules.mashilog import mashilog
from modules.music.track.base import BaseTrack


class YTDLTrack(BaseTrack):
    def __init__(
            self,
            loop: asyncio.AbstractEventLoop,
            member: discord.Member,
            title: str,
            url: str,
            original_url: str,
            duration: int | None=None,
            artist: str | None=None,
            thumbnail: str | None=None
    ) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        super().__init__(
            member=member,
            title=title,
            url=url,
            original_url=original_url,
            duration=duration,
            artist=artist,
            album=None,
            thumbnail=thumbnail
        )

    # 生成されたURLは一定時間後に無効になるため、この関数を再生直前に実行する
    async def create_source(self, volume: int):
        # 以前に生成したURLがまだ使えるか試してみる
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as resp:
                    resp.raise_for_status()
        # URLが切れている場合、再生成
        except aiohttp.ClientResponseError:
            mashilog("YTDLSourceを再度生成します。")
            with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ytdl:
                info = await self.loop.run_in_executor(
                    None, lambda: ytdl.extract_info(self.original_url, download=False)
                )
                self.url = info.get("url")
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url, **FFMPEG_OPTIONS),
            volume=volume
        )