import aiohttp
import discord
import re
import modules.utils as utils
from io import BytesIO
from PIL import Image
from modules.http import get_range_data
from modules.file import make_filename_by_seq


# FLACのメタデータブロックを全て取得
async def get_metadata_blocks(url: str):
    async with aiohttp.ClientSession() as session:
        current_idx = 4
        blocks = []
        while True:
            header = await get_range_data(session, url, current_idx, current_idx + 3)
            ids = int.from_bytes(header[0], "big")
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
            data = await get_range_data(session, url, current_idx + 4, current_idx + 3 + size)

            blocks.append({
                "type": data_types[ids & 0b01111111],
                "data": data
            })
            if 0b10000000 & ids:
                break
            else:
                current_idx += 4 + size
        return blocks


# FLACのメタデータを取得
async def get_flac_info(url: str, guild: discord.Guild):
    title = None
    duration = None
    thumbnail = None
    
    blocks = await get_metadata_blocks(url)
    for block in blocks:
        data = block["data"]
        if block["type"] == "STREAMINFO":
            sample_rate = int.from_bytes(data[10:13], "big") // 0x10
            n_samples = int.from_bytes(data[13:18], "big") & 0xFFFFFFFFF
            if sample_rate and n_samples:
                duration = utils.sec_to_text(n_samples // sample_rate)
        elif block["type"] == "VORBIS_COMMENT":
            vendor_length = int.from_bytes(data[:4], "little")

            n_comments = int.from_bytes(data[4 + vendor_length:8 + vendor_length], "little")
            current_idx = 8 + vendor_length
            for _ in range(n_comments):
                comment_length = int.from_bytes(data[current_idx:current_idx + 4], "little")
                comment = data[current_idx + 4:current_idx + 4 + comment_length].decode()
                if match_obj := re.match(r"\w+=", comment):
                    if match_obj.group().lower() == "title=":
                        title = comment[len(match_obj.group()):]
                current_idx += 4 + comment_length
        elif block["type"] == "PICTURE":
            mimetype_length = int.from_bytes(data[4:8], "big")
            mimetype = data[8:8 + mimetype_length].decode()
            description_length = int.from_bytes(data[8 + mimetype_length:12 + mimetype_length], "big")
            image_size = int.from_bytes(data[28 + mimetype_length + description_length:32 + mimetype_length + description_length], "big")
            image_data = data[32 + mimetype_length + description_length:32 + mimetype_length + description_length + image_size]
            img = Image.open(BytesIO(image_data))
            thumbnail = make_filename_by_seq(f"data/temp/cover_{guild.id}.{mimetype.split('/')[-1]}")
            img.save(thumbnail)

    return {
        "title": title,
        "duration": duration,
        "thumbnail": thumbnail
    }