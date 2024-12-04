import discord
import re
import modules.util as util
from modules.url_replacer import URLReplacer



class CogURLReplacer(discord.Cog):
    JSON_PATH = 'data/saves/vxtwitter.json'
    group_replace_url = discord.SlashCommandGroup(**util.make_command_args('replace-url'))

    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot
        self.replacer_vxtwitter = URLReplacer(
            name='vxtwitter',
            url_pattern=re.compile(r'https?://(?:x|twitter).com/\w+/status/\d+(?:\?[\w=&\-]*)?'),
            replacing_pattern=re.compile(r'(x|twitter).com'),
            replaced_str='vxtwitter.com',
            link_text='ポストを表示'
        )
        self.replacer_phixiv = URLReplacer(
            name='phixiv',
            url_pattern=re.compile(r'https?://(?:www\.)?pixiv.net/(?:en/)?artworks/\d+'),
            replacing_pattern=re.compile(r'pixiv.net'),
            replaced_str='phixiv.net',
            link_text='作品を表示'
        )


    # vxtwitterのURL変換機能の有効/無効化
    @group_replace_url.command(**util.make_command_args(['replace-url', 'vxtwitter']))
    @discord.option('switch', description='URL変換機能の有効化/無効化')
    async def command_vxtwitter(self, ctx: discord.ApplicationContext, switch: bool):
        await self.replacer_vxtwitter.switch_replacer(ctx, switch)


    # phixivのURL変換機能の有効/無効化
    @group_replace_url.command(**util.make_command_args(['replace-url', 'phixiv']))
    @discord.option('switch', description='URL変換機能の有効化/無効化')
    async def command_phixiv(self, ctx: discord.ApplicationContext, switch: bool):
        await self.replacer_phixiv.switch_replacer(ctx, switch)
        

    # メッセージ送信時
    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        # とりあえずループしないようにする
        if message.author.bot:
            return
        flag_delete_msg = False
        enabled_vxtwitter = self.replacer_vxtwitter.is_enabled(message.guild.id)
        enabled_phixiv = self.replacer_phixiv.is_enabled(message.guild.id)

        if enabled_vxtwitter and enabled_phixiv:
            if re.fullmatch(rf'^(\s*({self.replacer_vxtwitter.url_pattern.pattern})|({self.replacer_phixiv.url_pattern.pattern})\s*)+$', message.content):
                flag_delete_msg = True
        elif enabled_vxtwitter:
            if re.fullmatch(rf'^(\s*{self.replacer_vxtwitter.url_pattern.pattern}\s*)+$', message.content):
                flag_delete_msg = True
        elif enabled_phixiv:
            if re.fullmatch(rf'^(\s*{self.replacer_phixiv.url_pattern.pattern}\s*)+$', message.content):
                flag_delete_msg = True

        if flag_delete_msg:
            manage_messages = message.channel.permissions_for(message.guild.me)
            # attachmentsがなく、Botにメッセージ管理権限がある場合、元のメッセージを削除
            if manage_messages and not message.attachments:
                try:
                    await message.delete()
                except discord.Forbidden:
                    flag_delete_msg = False
            else:
                flag_delete_msg = False

        # 変換後のURLを送信
        await self.replacer_vxtwitter.send(message, deleted=flag_delete_msg)
        await self.replacer_phixiv.send(message, deleted=flag_delete_msg)