import aiofiles
import discord
import os
import rembg
from typing import List
from modules.http import get_mimetype
from modules.myembed import MyEmbed
from modules.attachments import get_attachments
from PIL import Image


MIMETYPES_REMBG = ["image/png", "image/pjpeg", "image/jpeg", "image/x-icon", "image/bmp"]


class CogImage(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot

    # /removebg
    @discord.slash_command(name="removebg", description="画像の背景を透過します。")
    @discord.option("attachment", description="添付する画像ファイル", required=False)
    @discord.option("message_url", description="画像が添付されたメッセージのURL", required=False)
    async def command_removebg(self, ctx: discord.ApplicationContext, attachment: discord.Attachment=None, message_url: str=None):
        path_base = f"data/temp/removebg_{ctx.interaction.id}"
        files_i: List[str] = []
        files_o: List[str] = []
        b_images: List[bytes] = []
        
        if attachment:
            await attachment.save(f"{path_base}_i.png")
            files_i.append(f"{path_base}_i.png")
        else:
            if not (b_images := await get_attachments(ctx, MIMETYPES_REMBG, message_url=message_url)):
                return
            for i, b in enumerate(b_images):
                async with aiofiles.open(f"{path_base}_{str(i).zfill(5)}_i.png", mode="wb") as f:
                    files_i.append(f.name)
                    await f.write(b)

        for file in files_i:
            await attachment.save(file)
            image = Image.open(file)
            result = rembg.remove(image)
            file_o = f"{os.path.splitext(file)[0]}_o.png"
            files_o.append(file_o)
            result.save(file_o)

        await ctx.respond(files=[discord.File(f) for f in files_o])

        # 画像を削除
        for path in files_i + files_o:
            if os.path.isfile(path):
                os.remove(path)