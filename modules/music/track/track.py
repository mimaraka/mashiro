import aiohttp
import asyncio
import discord
import yt_dlp
import modules.util as util
from constants import YTDL_OPTIONS
from typing import List
from .id3v2 import ID3V2Track
from .flac import FLACTrack
from .riff import RIFFTrack
from .ytdl import YTDLTrack
from .niconico import NicoNicoTrack
from .local import LocalTrack
from modules.http import bin_startswith
from modules.http import get_mimetype
from modules.mylog import mylog
from ...duration import Duration


Track = ID3V2Track | FLACTrack | RIFFTrack | YTDLTrack | NicoNicoTrack | LocalTrack


async def create_tracks(loop: asyncio.AbstractEventLoop, query: str, member: discord.Member) -> List[Track]:
    # URLの場合
    if util.is_url(query):
        # クエリを消すとURLが無効になってしまうようになった
        # Discordの添付ファイルのURLの場合、URLのクエリを消す
        # if re.match(r'https?://cdn.discordapp.com/attachments/', query):
        #     query = re.sub(r'\?.*', '', query)
        try:
            # ID3V2直リンクの場合
            if await get_mimetype(query) == 'audio/mpeg' and await bin_startswith(query, b'ID3'):
                return [await ID3V2Track.from_url(query, member)]
            # FLAC直リンクの場合
            elif await get_mimetype(query) == 'audio/flac' and await bin_startswith(query, b'fLaC'):
                return [await FLACTrack.from_url(query, member)]
            # RIFF直リンクの場合
            elif await get_mimetype(query) in ['audio/wav', 'audio/x-wav'] and await bin_startswith(query, b'RIFF'):
                return [await RIFFTrack.from_url(query, member)]
            # ニコニコの場合
            elif util.is_niconico_url(query):
                return [await NicoNicoTrack.from_url(query, member)]
        # URLが見つからない場合
        except aiohttp.ClientResponseError as e:
            mylog(e, log_type='error')
            return None

    # その他はyt-dlpで処理
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
        try:
            info = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(query, download=False)
            )
        except yt_dlp.DownloadError as e:
            print(e)
            return None
        
    if not info:
        return None
        
    # キー'entries'が存在すればプレイリスト
    info_list: List[dict] = info.get('entries') or [info]

    result = []
    for i in info_list:
        if i:
            result.append(
                YTDLTrack(
                    loop,
                    member=member,
                    title=i.get('title'),
                    source_url=i.get('url'),
                    original_url=i.get('webpage_url') or i.get('original_url'),
                    duration=i.get('duration') and Duration(i.get('duration')),
                    artist=i.get('artist') or i.get('uploader'),
                    album=i.get('album'),
                    thumbnail=i.get('thumbnail')
                )
            )
    return result