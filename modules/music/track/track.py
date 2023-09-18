import asyncio
import discord
import re
import yt_dlp
import modules.utils as utils
from constants import YTDL_FORMAT_OPTIONS
from typing import List
from .id3v2 import ID3V2Track
from .flac import FLACTrack
from .ytdl import YTDLTrack
from .niconico import NicoNicoTrack
from .local import LocalTrack
from modules.http import bin_startswith
from modules.http import get_mimetype


Track = ID3V2Track | FLACTrack | YTDLTrack | NicoNicoTrack | LocalTrack


async def create_tracks(loop: asyncio.AbstractEventLoop, text: str, member: discord.Member) -> List[Track]:
    # URLの場合
    if utils.is_url(text):
        # ID3V2直リンクの場合
        if await get_mimetype(text) == "audio/mpeg" and await bin_startswith(text, b"ID3"):
            return [await ID3V2Track.from_url(text, member)]
        # FLAC直リンクの場合
        elif await get_mimetype(text) == "audio/flac" and await bin_startswith(text, b"fLaC"):
            return [await FLACTrack.from_url(text, member)]

    # その他はyt-dlpで処理
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
            # ニコニコの場合
            if re.search(r"^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+", i.get("original_url")):
                if i.get("_api_data") and i["_api_data"].get("series"):
                    series_title = i["_api_data"]["series"].get("title")
                else:
                    series_title = None
                result.append(
                    NicoNicoTrack(
                        member=member,
                        title=i.get("title"),
                        original_url=i.get("original_url"),
                        duration=int(i.get("duration")),
                        artist=i.get("uploader"),
                        album=series_title,
                        thumbnail=i.get("thumbnail")
                    )
                )
            else:
                result.append(
                    YTDLTrack(
                        loop,
                        member=member,
                        title=i.get("title"),
                        url=i.get("url"),
                        original_url=i.get("original_url"),
                        duration=int(i.get("duration")),
                        artist=i.get("uploader"),
                        thumbnail=i.get("thumbnail")
                    )
                )
    return result