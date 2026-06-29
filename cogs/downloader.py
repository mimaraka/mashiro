import discord
import re
import yt_dlp
import modules.util as util
from character_config import CHARACTER_TEXT
from modules.myembed import MyEmbed
from constants import RE_PATTERN_URL_NICONICO, RE_PATTERN_URL, YTDL_EXTRACTOR_ARGS, YTDL_COOKIEFILE


class CogDownloader(discord.Cog):
    group_dl = discord.SlashCommandGroup(**util.make_command_args('dl'))

    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    async def get_info(self, query: str, format: str | None=None):
        OPTIONS = {
            'format': format,
            'quiet': True,
            'ignoreerrors': True,
            'default_search': 'auto',
            'source_address': '0.0.0.0',
            'usenetrc': True,
            'netrc_location': './.netrc',
            'extractor_args': YTDL_EXTRACTOR_ARGS,
        }
        if YTDL_COOKIEFILE:
            OPTIONS['cookiefile'] = YTDL_COOKIEFILE

        try:
            with yt_dlp.YoutubeDL(OPTIONS) as ytdl:
                info = await self.bot.loop.run_in_executor(
                    None, lambda: ytdl.extract_info(query, download=False)
                )

            if info.get('entries') is not None:
                info = info.get('entries')[0]

            if re.search(RE_PATTERN_URL_NICONICO, query):
                url = f'https://www.nicovideodl.jp/watch/{info.get("webpage_url_basename")}'
            else:
                url = info.get('url')
                if url is None:
                    return None
                if len(url) > 512:
                    url = util.shorten_url(url)
            
            return {
                'title': info.get('title'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
                'webpage_url': info.get('webpage_url'),
                'url': url
            }
        except yt_dlp.DownloadError as e:
            print(e)
            return None

    async def download(self, ctx: discord.ApplicationContext, media_type: str, query, bestvideo=False):
        await ctx.defer()

        if media_type == 'video':
            if bestvideo:
                format = 'bestvideo*'
            else:
                format = 'best'
            author = '🎬 ダウンローダー(動画)'
        else:
            format = 'bestaudio'
            author = '💿 ダウンローダー(音声)'
        info = await self.get_info(query, format)

        if info is None:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_failed_to_get_download_link']),
                delete_after=10
            )
            return

        embed = MyEmbed(
            title=info.get('title'),
            description=f'👤 {info.get("uploader") or "-"}',
            url=info.get('webpage_url'),
            image=info.get('thumbnail')
        )
        embed.set_author(name=author)
        embed.set_footer(text='※ダウンロードリンクは一定時間後に無効になる可能性があります。')

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label='ダウンロード', url=info.get('url')))

        await ctx.respond(embed=embed, view=view)

    # メッセージコマンド共通の処理
    async def message_command_common(self, ctx: discord.ApplicationContext, message: discord.Message, media_type: str):
        if message.attachments:
            query = message.attachments[0].url
            await self.download(ctx, media_type, query)
        elif message.clean_content:
            # メッセージにURLが含まれる場合は抽出
            if m := re.search(RE_PATTERN_URL, message.clean_content):
                query = m.group()
            else:
                query = message.clean_content
            await self.download(ctx, media_type, query)
        else:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_no_text_or_attachment']),
                ephemeral=True
            )
    
    # /dl-video
    @group_dl.command(**util.make_command_args(['dl', 'video']))
    @discord.option('query', description='URLまたはYouTube上で検索するキーワード')
    @discord.option('bestvideo', description='最高画質の動画のリンクを取得しますが、音声が含まれない可能性があります。', default=False)
    async def command_dl_video(self, ctx: discord.ApplicationContext, query: str, bestvideo: bool):
        await self.download(ctx, 'video', query, bestvideo=bestvideo)

    # メッセージコマンド (ダウンロード(動画))
    @discord.message_command(name='ダウンロード(動画)')
    async def message_command_dl_video(self, ctx: discord.ApplicationContext, message: discord.Message):
        await self.message_command_common(ctx, message, 'video')

    # /dl-audio
    @group_dl.command(**util.make_command_args(['dl', 'audio']))
    @discord.option('query', description='URLまたはYouTube上で検索するキーワード')
    async def command_dl_audio(self, ctx: discord.ApplicationContext, query: str):
        await self.download(ctx, 'audio', query)

    # メッセージコマンド (ダウンロード(音声))
    @discord.message_command(name='ダウンロード(音声)')
    async def message_command_dl_audio(self, ctx: discord.ApplicationContext, message: discord.Message):
        await self.message_command_common(ctx, message, 'audio')