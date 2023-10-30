import discord
import yt_dlp
from modules.myembed import MyEmbed


class CogDownloader(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    async def get_info(self, format: str):
        options = {
            "format": format,

        }
        with yt_dlp.YoutubeDL(options) as ytdl:
            info = await self.bot.loop.run_in_executor(
                None, lambda: ytdl.extract_info(download=False)
            )
        return {
            "title": info.get("title")
        }

    # /dl-video
    @discord.slash_command(name="dl-video")
    @discord.option("query", description="URLまたはYouTube上で検索するキーワード")
    async def command_dl_video(self, ctx: discord.ApplicationContext, query: str):
        await ctx.respond(
            embed=MyEmbed(
                notif_type="succeed",
                title="ダウンロードが完了しました！",
                description=f"***[]()***"
            )
        )
        pass

    # /dl-audio
    @discord.slash_command(name="dl-audio")
    @discord.option("query", description="URLまたはYouTube上で検索するキーワード")
    async def command_dl_audio(self, ctx: discord.ApplicationContext, query: str):
        pass