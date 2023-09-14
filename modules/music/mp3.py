import aiohttp
import modules.utils as utils
from modules.file import make_filename_by_seq
from functools import reduce
from io import BytesIO
from mutagen.mp3 import MP3
from PIL import Image


async def get_range_data(session: aiohttp.ClientSession, url: str, start: int, end: int):
    headers = {
        "Range": f"bytes={start}-{end}"
    }
    async with session.get(url, headers=headers) as response:
        try:
            response.raise_for_status()
            return await response.read()
        except aiohttp.ClientResponseError:
            return None
        

async def is_id3v2(url: str):
    async with aiohttp.ClientSession() as session:
        if (data := await get_range_data(session, url, 0, 2)) is not None:
            return data.startswith(b"ID3")
    

async def get_id3v2_info(url: str):
    async with aiohttp.ClientSession() as session:
        if (size_data := await get_range_data(session, url, 0, 10)) is None:
            return None
    
        size_encorded = bytearray(size_data[6:])
        size = reduce(lambda a, b: a * 128 + b, size_encorded, 0)

        header = BytesIO()
        data = await get_range_data(session, url, 0, size + 2881)
        header.write(data)
        header.seek(0)

    audio = MP3(header)
    
    if (apic := audio.tags.get("APIC:")) is not None:
        img = Image.open(BytesIO(apic.data))
        filepath = make_filename_by_seq("data/temp/cover." + apic.mime.split("/")[-1])
        img.save(filepath)
    else:
        filepath = None

    return {
        "title": audio.tags.get("TIT2"),
        "duration": utils.sec_to_text(round(audio.info.length)),
        "thumbnail": filepath
    }