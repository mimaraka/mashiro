import asyncio
import discord
import os
import re
import yt_dlp
import urllib.request, urllib.error
from typing import List
from niconico import NicoNico
from modules.mashilog import mashilog


# yt_dlp
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best*[acodec=aac]",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    "source_address": "0.0.0.0",                                # bind to ipv4 since ipv6 addresses cause issues sometimes
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_delay_max 3",
    "options": "-vn",
}


class YTDLTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, loop, url, original_url, title, thumbnail, duration, member) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.url: str | None = url
        self.original_url: str | None = original_url
        self.title: str = title
        self.thumbnail: str | None = thumbnail
        self.duration: str | None = duration
        self.member: discord.Member = member

    # 生成されたURLは一定時間後に無効になるため、この関数を再生直前に実行する
    async def create_source(self, volume):
        # 以前に生成したURLがまだ使えるか試してみる
        try:
            r = urllib.request.urlopen(self.url)
            r.close()
        # URLが切れている場合、再生成
        except urllib.error.HTTPError:
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

    async def release_source(self):
        self.source = None


class NicoNicoTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, original_url, title, thumbnail, duration, member) -> None:
        self.url: str | None = None
        self.original_url: str | None = original_url
        self.title: str = title
        self.thumbnail: str | None = thumbnail
        self.duration: str | None = duration
        self.member: discord.Member = member
        self.__video = None

    # video.connect() ~ video.close_connection()の間のみURLが有効？
    async def create_source(self, volume):
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


class LocalTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, filepath, member) -> None:
        self.url: str | None = filepath
        self.original_url: str | None = None
        self.title: str = os.path.splitext(os.path.basename(filepath))[0]
        self.thumbnail : str | None = None
        self.duration : str | None = None
        self.member: discord.Member = member
        
    async def create_source(self, volume):
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url, **FFMPEG_OPTIONS),
            volume=volume
        )

    async def release_source(self):
        self.source = None


Track = YTDLTrack | NicoNicoTrack | LocalTrack


# YTDLを用いてテキストからトラックのリストを生成
async def ytdl_create_tracks(loop, text: str, member: discord.Member) -> List[Track]:
    def zfill_duration(duration_string: str):
        if duration_string is not None:
            hms = duration_string.split(":")
            if len(hms) == 1:
                return f"0:{hms[0].zfill(2)}"
        return duration_string
    
    with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ytdl:
        try:
            info = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(text, download=False)
            )
        except yt_dlp.DownloadError as e:
            print(e)
            return None
        
    if not info:
        return None
        
    # キー"entries"が存在すればプレイリスト
    info_list = info.get("entries") or [info]

    result = []
    for i in info_list:
        if i:
            if re.search(r"^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+", i.get("original_url")):
                result.append(NicoNicoTrack(i.get("original_url"), i.get("title"), i.get("thumbnail"), zfill_duration(i.get("duration_string")), member))
            else:
                result.append(YTDLTrack(loop, i.get("url"), i.get("original_url"), i.get("title"), i.get("thumbnail"), zfill_duration(i.get("duration_string")), member))

    return result