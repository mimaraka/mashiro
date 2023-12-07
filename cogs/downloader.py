import discord
import re
import yt_dlp
from modules.myembed import MyEmbed
from modules.util import shorten_url
from constants import RE_PATTERN_URL_NICONICO, RE_PATTERN_URL


class CogDownloader(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    async def get_info(self, query: str, format: str | None=None):
        options = {
            "format": format,
            "quiet": True,
            "ignoreerrors": True,
            "default_search": "auto",
            "source_address": "0.0.0.0"
        }
        
        try:
            with yt_dlp.YoutubeDL(options) as ytdl:
                info = await self.bot.loop.run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False)
                )

            if info.get("entries") is not None:
                info = info[0]

            if re.search(RE_PATTERN_URL_NICONICO, query):
                url = f"https://www.nicovideodl.jp/watch/{info.get('webpage_url_basename')}"
            else:
                url = info.get("url")
                if len(url) > 512:
                    url = shorten_url(url)
            
            return {
                "title": info.get("title"),
                "uploader": info.get("uploader"),
                "thumbnail": info.get("thumbnail"),
                "webpage_url": info.get("webpage_url"),
                "url": url
            }
        except yt_dlp.DownloadError as e:
            print(e)
            return None

    async def download(self, ctx: discord.ApplicationContext, media_type: str, query):
        await ctx.defer()

        if media_type == "video":
            format = "best"
            author = "🎬 ダウンローダー(動画)"
        else:
            format = "bestaudio"
            author = "💿 ダウンローダー(音声)"
        info = await self.get_info(query, format)

        if info is None:
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description="ダウンロードリンクの取得に失敗しました。"),
                delete_after=10
            )
            return

        embed = MyEmbed(
            title=info.get("title"),
            description=f"👤 {info.get('uploader') or '-'}",
            url=info.get("webpage_url"),
            image=info.get("thumbnail")
        )
        embed.set_author(name=author)
        embed.set_footer(text="※ダウンロードリンクは一定時間後に無効になる可能性があります。")

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="ダウンロード", url=info.get("url")))

        await ctx.respond(embed=embed, view=view)

    # メッセージコマンド共通の処理
    async def message_command_common(self, ctx: discord.ApplicationContext, message: discord.Message, media_type: str):
        if message.attachments:
            query = message.attachments[0].url
            await self.download(ctx, media_type, query)
        elif message.clean_content:
            # メッセージにURLが含まれる場合は抽出
            query = re.search(RE_PATTERN_URL, message.clean_content).group() or message.clean_content
            await self.download(ctx, media_type, query)
        else:
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description="指定されたメッセージにテキストまたは添付ファイルがありません。"),
                ephemeral=True
            )
    
    # /dl-video
    @discord.slash_command(name="dl-video", description="動画のダウンロードリンクを取得します。")
    @discord.option("query", description="URLまたはYouTube上で検索するキーワード")
    async def command_dl_video(self, ctx: discord.ApplicationContext, query: str):
        await self.download(ctx, "video", query)

    # メッセージコマンド (ダウンロード(動画))
    @discord.message_command(name="ダウンロード(動画)")
    async def message_command_dl_video(self, ctx: discord.ApplicationContext, message: discord.Message):
        await self.message_command_common(ctx, message, "video")

    # /dl-audio
    @discord.slash_command(name="dl-audio", description="音声のダウンロードリンクを取得します。")
    @discord.option("query", description="URLまたはYouTube上で検索するキーワード")
    async def command_dl_audio(self, ctx: discord.ApplicationContext, query: str):
        await self.download(ctx, "audio", query)

    # メッセージコマンド (ダウンロード(音声))
    @discord.message_command(name="ダウンロード(音声)")
    async def message_command_dl_video(self, ctx: discord.ApplicationContext, message: discord.Message):
        await self.message_command_common(ctx, message, "audio")