import aiohttp
import discord
import re
import typing
from modules.myembed import MyEmbed
from modules.http import get_mimetype


# URLが有効ならメッセージのオブジェクトを返し、無効ならNoneを返す
async def get_message_from_url(mes_url: str, bot: discord.Bot) -> discord.Message | None:
    if re.fullmatch(r'^https://discord.com/channels/\d+/\d+/\d+$', mes_url):
        parts = mes_url.split('/')
        channel_id = int(parts[-2])
        message_id = int(parts[-1])
        channel = bot.get_channel(channel_id)
        if type(channel) is discord.TextChannel:
            try:
                return await channel.fetch_message(message_id)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass
    return None


# メッセージから有効なURLを探す関数
async def find_valid_urls(message: discord.Message, mimetypes_list=None) -> typing.List[str] | None:
    matches = re.findall(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-]+', message.content)
    urls = []
    valid_urls = []
    # リンク先のメッセージにファイルが添付されていた場合
    if message.attachments:
        urls += [a.url for a in message.attachments]
    # メッセージの中にURLが含まれていた場合
    if matches:
        urls += [m for m in matches] # which is m str or match object?????
    for url in urls:
        if mimetypes_list and await get_mimetype(url) not in mimetypes_list:
            continue
        else:
            valid_urls.append(url)
    return valid_urls


# MediaType = typing.Literal['image', 'gif', 'audio', 'video']

# 添付ファイルを取得する関数
async def get_attachments(ctx: discord.ApplicationContext, mimetypes, message_url: str=None, return_url=False, silent=False):
    # media_mime = {
    #     'image':            ['image/png', 'image/pjpeg', 'image/jpeg', 'image/x-icon', 'image/bmp'],
    #     'gif':              ['image/gif'],
    #     'audio':            ['audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/aac', 'audio/ogg', 'audio/flac'],
    #     'video':            ['video/mpeg', 'video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']
    # }
    
    if type(mimetypes) is str:
        mimetypes = [mimetypes]

    valid_urls: typing.List[str] = []

    # メッセージURLが指定されている場合
    if message_url:
        message = await get_message_from_url(message_url, ctx.bot)
        # メッセージURLが無効の場合
        if not message:
            if not silent:
                await ctx.respond(
                    embed=MyEmbed(
                        notif_type='error',
                        description='リンクからのメッセージの取得に失敗しました。'
                    ),
                    ephemeral=True
                )
            return None
        valid_urls = await find_valid_urls(message, mimetypes)
        # リンク先のメッセージにファイルやURLが添付されていなかった場合
        if not valid_urls:
            if not silent:
                await ctx.respond(
                    embed=MyEmbed(
                        notif_type='error',
                        description='リンク先のメッセージにファイルやURLが添付されていないようです。'
                    ),
                    ephemeral=True
                )
            return None

    else:
        #直近10件のメッセージの添付ファイル・URLの取得を試みる
        async for message in ctx.channel.history(limit=10):
            valid_urls = await find_valid_urls(message, mimetypes)
            # 有効なURLが存在すればループを抜ける
            if valid_urls:
                break
        #どちらも存在しない場合
        else:
            if not silent:
                embed = MyEmbed(
                    notif_type='error',
                    description='ファイルやURLが添付されたメッセージの近くでコマンドを実行するか、メッセージのリンクを指定してください。'
                )
                await ctx.respond(embed=embed, ephemeral=True)
            return None

    # URLのリストを返す
    if return_url:
        return valid_urls
    # バイナリのリストを返す
    else:
        result = []
        for url in valid_urls:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    result.append(await resp.read())
        return result