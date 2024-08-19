import aiohttp
import discord
import random
import re
import string
from .base import BaseTrack
from ...duration import Duration


class NicoNicoTrack(BaseTrack):
    @classmethod
    async def from_url(cls, url: str, member: discord.Member):
        video = None
        thumbnail = None
        artist = None
        video_id = re.search(r"sm\d+", url).group()
        track_id_list = [random.choice(string.ascii_letters) for _ in range(10)] + ["_"] + [random.choice(string.digits) for _ in range(13)]
        track_id = "".join(track_id_list)
        api_endpoint = f"https://www.nicovideo.jp/api/watch/v3_guest/{video_id}?_frontendId=70&_frontendVersion=0&actionTrackId={track_id}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://nicovideodl.jp/download/" + video_id) as response:
                response.raise_for_status()
            async with session.get(api_endpoint) as response:
                info = await response.json()
                data = info.get("data")
                assert data is not None
                video = data.get("video")
                assert video is not None

        if (thumbnails := video.get("thumbnail")) is not None:
            thumbnail = thumbnails.get("ogp") or thumbnails.get("player") or thumbnails.get("largeUrl") or thumbnails.get("middleUrl") or thumbnails.get("url")

        if (owner := data.get("owner")) is not None:
            artist = owner.get("nickname")

        return cls(
            member=member,
            title=video.get("title"),
            source_url=f"https://nicovideodl.jp/cdn/filename/{video_id}.mp3",
            original_url=url,
            duration=Duration(video.get("duration")),
            artist=artist,
            album=None,
            thumbnail=thumbnail
        )