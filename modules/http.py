import aiohttp


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
        

async def bin_startswith(url: str, bin: bytes):
    async with aiohttp.ClientSession() as session:
        if (data := await get_range_data(session, url, 0, len(bin) - 1)) is not None:
            return data.startswith(bin)
        return False
    

async def get_mimetype(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return resp.headers.get("Content-type", "").lower()
        

