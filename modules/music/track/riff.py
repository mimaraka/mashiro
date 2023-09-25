import aiohttp
import discord
import math
import os
from modules.http import get_range_data
from .base import BaseTrack


# RIFFのdataを除くチャンクを全て取得
async def get_chunks(url: str):
    chunks = []
    async with aiohttp.ClientSession() as session:
        file_size = int.from_bytes(await get_range_data(session, url, 4, 7), "little") + 8
        current_idx = 12
        while current_idx < file_size:
            header = await get_range_data(session, url, current_idx, current_idx + 7)
            chunk_id = header[:4]
            chunk_size = int.from_bytes(header[4:], "little")
            if chunk_id != b"data":
                chunk_data = await get_range_data(session, url, current_idx + 8, current_idx + 7 + chunk_size)
                chunks.append({
                    "type": chunk_id,
                    "data": chunk_data
                })
            else:
                samples_size = chunk_size
            # データサイズが奇数の場合はパディングが起こる
            current_idx += 8 + math.ceil(chunk_size / 2) * 2
    return chunks, samples_size


def get_subchunks(chunk_data: bytes):
    chunks = []
    current_idx = 0
    while current_idx < len(chunk_data):
        chunk_id = chunk_data[current_idx:current_idx + 4]
        chunk_size = int.from_bytes(chunk_data[current_idx + 4:current_idx + 8], "little")
        data = chunk_data[current_idx + 8:current_idx + 8 + chunk_size]
        chunks.append({
            "type": chunk_id,
            "data": data
        })
        # データサイズが奇数の場合はパディングが起こる
        current_idx += 8 + math.ceil(chunk_size / 2) * 2
    return chunks


class RIFFTrack(BaseTrack):
    @classmethod
    async def from_url(cls, url: str, member: discord.Member):
        duration = None
        tags = {}

        chunks, samples_size = await get_chunks(url)
        for chunk in chunks:
            data = chunk["data"]
            if chunk["type"] == b"fmt ":
                avr_sample_size = int.from_bytes(data[8:12], "little")
                duration = samples_size // avr_sample_size
            elif chunk["type"] == b"LIST":
                if data[:4] == b"INFO":
                    subchunks = get_subchunks(data[4:])
                    for subchunk in subchunks:
                        if subchunk["type"] == b"INAM":
                            tags["title"] = subchunk["data"][:-1].decode("shift-jis")
                        elif subchunk["type"] == b"IART":
                            tags["artist"] = subchunk["data"][:-1].decode("shift-jis")
                        elif subchunk["type"] == b"IPRD":
                            tags["album"] = subchunk["data"][:-1].decode("shift-jis")

        filename = os.path.splitext(url.split("/")[-1])[0]
        return cls(
            member=member,
            title=tags.get("title") or filename,
            source_url=url,
            original_url=url,
            duration=duration,
            artist=tags.get("artist"),
            album=tags.get("album"),
            thumbnail=None
        )