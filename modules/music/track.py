import asyncio
import discord
import os
import re
import yt_dlp
import urllib.request, urllib.error
from typing import List
from niconico import NicoNico


# yt_dlp
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best*[acodec=aac]",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    "source_address": "0.0.0.0",                                # bind to ipv4 since ipv6 addresses cause issues sometimes
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}


class YTDLTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, loop, url, original_url, title, thumbnail, duration) -> None:
        self.loop: asyncio.AbstractEventLoop = loop
        self.url: str | None = url
        self.original_url: str | None = original_url
        self.title: str = title
        self.thumbnail: str | None = thumbnail
        self.duration: str | None = duration

    # 生成されたURLは一定時間後に無効になるため、この関数を再生直前に実行する
    async def create_source(self, volume):
        # 以前に生成したURLがまだ使えるか試してみる
        try:
            r = urllib.request.urlopen(self.url)
            r.close()
        # URLが切れている場合、再生成
        except urllib.error.HTTPError:
            with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ytdl:
                info = await self.loop.run_in_executor(
                    None, lambda: ytdl.extract_info(self.original_url, download=False)
                )
                self.url = info.get("url")
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url),
            volume=volume
        )


class NicoNicoTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, original_url, title, thumbnail, duration) -> None:
        self.url: str | None = None
        self.original_url: str | None = original_url
        self.title: str = title
        self.thumbnail: str | None = thumbnail
        self.duration: str | None = duration

    # 生成されたURLは一定時間後に無効になるため、この関数を再生直前に実行する
    async def create_source(self, volume):
        nc_client = NicoNico()
        # 以前に生成したURLがまだ使えるか試してみる
        try:
            assert self.url is not None
            r = urllib.request.urlopen(self.url)
            r.close()
        # URLが存在しない/切れている場合、再生成
        except (AssertionError, urllib.error.HTTPError):
            with nc_client.video.get_video(self.original_url) as video:
                self.url = video.download_link
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url),
            volume=volume
        )


class LocalTrack:
    source: discord.PCMVolumeTransformer | None = None

    def __init__(self, filepath) -> None:
        self.url: str | None = filepath
        self.original_url: str | None = None
        self.title: str = os.path.splitext(os.path.basename(filepath))[0]
        self.thumbnail = None
        self.duration = None
        
    async def create_source(self, volume):
        self.source = discord.PCMVolumeTransformer(
            original=discord.FFmpegPCMAudio(self.url),
            volume=volume
        )


Track = YTDLTrack | NicoNicoTrack | LocalTrack


# YTDLを用いてテキストからトラックのリストを生成
async def ytdl_create_tracks(loop, text: str) -> List[Track]:
    def zfill_duration(duration_string: str):
        if duration_string is not None:
            hms = duration_string.split(":")
            if len(hms) == 1:
                return f"0:{hms[0]}"
        return duration_string
    
    with yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS) as ytdl:
        try:
            info = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(text, download=False)
            )
        except yt_dlp.DownloadError as e:
            print(e)
            return None
        
    # キー"entries"が存在すればプレイリスト
    info_list = info.get("entries") or [info]

    result = [
        NicoNicoTrack(i.get("original_url"), i.get("title"), i.get("thumbnail"), zfill_duration(i.get("duration_string")))
        if re.search(r"^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+", i.get("original_url"))
        else YTDLTrack(loop, i.get("url"), i.get("original_url"), i.get("title"), i.get("thumbnail"), zfill_duration(i.get("duration_string")))
        for i in info_list
    ]
    return result