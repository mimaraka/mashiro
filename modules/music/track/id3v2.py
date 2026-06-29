import aiohttp
import discord
import os
from functools import reduce
from io import BytesIO
from mutagen.mp3 import MP3
from PIL import Image
from modules.file import make_filename_by_seq
from modules.http import get_range_data
from .base import BaseTrack
from ...duration import Duration


class ID3V2Track(BaseTrack):
    @classmethod
    async def from_url(cls, url: str, member: discord.Member):
        async with aiohttp.ClientSession() as session:
            if (size_data := await get_range_data(session, url, 0, 9)) is None:
                return None

            # ID3v2ヘッダの6〜9バイト目がsynchsafe形式のタグサイズ
            size_encorded = bytearray(size_data[6:10])
            size = reduce(lambda a, b: a * 128 + b, size_encorded, 0)

            header = BytesIO()
            data = await get_range_data(session, url, 0, size + 2881)
            header.write(data)
            header.seek(0)

        audio = MP3(header)

        if (apic := audio.tags.get('APIC:')) is not None:
            img = Image.open(BytesIO(apic.data))
            ext = apic.mime.split('/')[-1] if apic.mime else 'jpeg'
            thumbnail = make_filename_by_seq(f'data/temp/cover_{member.guild.id}.{ext}')
            img.save(thumbnail)
        else:
            thumbnail = None

        filename = os.path.splitext(url.split('/')[-1])[0]

        def tag_str(key):
            value = audio.tags.get(key)
            return str(value) if value is not None else None

        return cls(
            member=member,
            title=tag_str('TIT2') or filename,
            source_url=url,
            original_url=url,
            duration=Duration(audio.info.length),
            artist=tag_str('TPE1'),
            album=tag_str('TALB'),
            thumbnail=thumbnail
        )