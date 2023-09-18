import aiohttp
import discord
import os
import re
from io import BytesIO
from PIL import Image
from modules.http import get_range_data
from modules.file import make_filename_by_seq
from .base import BaseTrack


# FLACのメタデータブロックを全て取得
async def get_metadata_blocks(original_url: str):
    async with aiohttp.ClientSession() as session:
        current_idx = 4
        blocks = []
        while True:
            header = await get_range_data(session, original_url, current_idx, current_idx + 3)
            ids = header[0]
            size = int.from_bytes(header[1:], "big")
            data_types = [
                "STREAMINFO",
                "PADDING",
                "APPLICATION",
                "SEEKTABLE",
                "VORBIS_COMMENT",
                "CUESHEET",
                "PICTURE"
            ]
            data = await get_range_data(session, original_url, current_idx + 4, current_idx + 3 + size)

            blocks.append({
                "type": data_types[ids & 0b01111111],
                "data": data
            })
            if 0b10000000 & ids:
                break
            else:
                current_idx += 4 + size
        return blocks


# FLAC音声リンクのトラック
class FLACTrack(BaseTrack):
    @classmethod
    async def from_url(cls, original_url: str, member: discord.Member):
        title = None
        artist = None
        album = None
        duration = None
        thumbnail = None

        blocks = await get_metadata_blocks(original_url)
        # メタデータブロック毎に処理
        for block in blocks:
            data = block["data"]
            # STREAMINFO(音声データ情報)の場合
            if block["type"] == "STREAMINFO":
                sample_rate = int.from_bytes(data[10:13], "big") // 0x10
                n_samples = int.from_bytes(data[13:18], "big") & 0xFFFFFFFFF
                if sample_rate and n_samples:
                    duration = n_samples // sample_rate
            # VORBIS_COMMENT(タグ等)の場合
            elif block["type"] == "VORBIS_COMMENT":
                vendor_length = int.from_bytes(data[:4], "little")
                n_comments = int.from_bytes(data[4 + vendor_length:8 + vendor_length], "little")
                current_idx = 8 + vendor_length
                # コメント毎に処理
                for _ in range(n_comments):
                    comment_length = int.from_bytes(data[current_idx:current_idx + 4], "little")
                    comment = data[current_idx + 4:current_idx + 4 + comment_length].decode()
                    attribute = comment[len(match_obj.group()):]
                    if match_obj := re.match(r"\w+=", comment):
                        tag_name = match_obj.group().lower()[:-1]
                        if tag_name == "title":
                            title = attribute
                        elif tag_name == "artist":
                            artist = attribute
                        elif tag_name == "album":
                            album = attribute
                    current_idx += 4 + comment_length
            # PICTURE(アートワーク)の場合
            elif block["type"] == "PICTURE":
                mimetype_length = int.from_bytes(data[4:8], "big")
                mimetype = data[8:8 + mimetype_length].decode()
                description_length = int.from_bytes(data[8 + mimetype_length:12 + mimetype_length], "big")
                image_size = int.from_bytes(data[28 + mimetype_length + description_length:32 + mimetype_length + description_length], "big")
                image_data = data[32 + mimetype_length + description_length:32 + mimetype_length + description_length + image_size]
                img = Image.open(BytesIO(image_data))
                ext = mimetype.split('/')[-1] if mimetype else "jpeg"
                thumbnail = make_filename_by_seq(f"data/temp/cover_{member.guild.id}.{ext}")
                img.save(thumbnail)
        
        filename = os.path.splitext(original_url.split("/")[-1])[0]
        return cls(
            original_url,
            original_url,
            title or filename,
            artist,
            album,
            thumbnail,
            duration,
            member
        )