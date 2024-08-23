import asyncio
import discord
import modules.util as util
from character_config import CHARACTER_TEXT
from datetime import datetime, timezone, timedelta

from discord.ui.input_text import InputText
from modules.myembed import MyEmbed

JST = timezone(timedelta(hours=9), 'JST')


class CogMessageSender(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot

    # メッセージ送信用のコールバック
    async def send_message_callback(self, time: datetime, channel: discord.TextChannel, content: str, embed: MyEmbed):
        # 既に指定時間を過ぎている場合
        if time <= datetime.now(JST):
            await channel.send(content, embed=embed)
            return True
        return False


    # /send_message
    @discord.slash_command(**util.make_command_args('send-message'))
    @discord.option('channel', description='メッセージを送信するチャンネル (省略した場合はコマンドを実行したチャンネル)', default=None)
    @discord.option('day', description='送信する日付 (省略した場合は今日)', default=None, min_value=1, max_value=31)
    @discord.option('hour', description='送信する時間 (24時間表記、省略した場合は現在の時間)', default=None, min_value=0, max_value=23)
    @discord.option('minute', description='送信する分 (省略した場合は現在の分)', default=None, min_value=0, max_value=59)
    async def command_send_message(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, day: int, hour: int, minute: int):
        channel = channel or ctx.channel
        now = datetime.now(JST)
        day = day or now.day
        hour = hour if hour is not None else now.hour
        minute = minute if minute is not None else now.minute

        try:
            time = datetime(now.year, now.month, day, hour, minute, tzinfo=JST)
        except ValueError:
            await ctx.respond(embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_invalid_datetime']), ephemeral=True)
            return

        class MessageModal(discord.ui.Modal):
            def __init__(self_) -> None:
                super().__init__(title='メッセージの設定', timeout=None)
            
                # content
                self_.input_content = InputText(
                    label='メッセージの内容',
                    required=False,
                    style=discord.InputTextStyle.paragraph,
                    max_length=2000,
                    placeholder='ユーザーメンション：<@!ユーザーID>\nロールメンション：<@&ロールID>\nカスタム絵文字：<:絵文字名:絵文字ID>\nチャンネルへのリンク：<#チャンネルID>'
                )

                # embed_title
                self_.input_embed_title = InputText(
                    label='埋め込みのタイトル',
                    required=False,
                    style=discord.InputTextStyle.short,
                    max_length=256
                )

                # embed_description
                self_.input_embed_description = InputText(
                    label='埋め込みの説明',
                    required=False,
                    style=discord.InputTextStyle.paragraph
                )

                self_.add_item(self_.input_content)
                self_.add_item(self_.input_embed_title)
                self_.add_item(self_.input_embed_description)

            async def callback(self_, inter: discord.Interaction):
                content = self_.input_content.value
                embed_title = self_.input_embed_title.value
                embed_description = self_.input_embed_description.value

                if embed_title or embed_description:
                    embed = MyEmbed(title=embed_title, description=embed_description)
                else:
                    embed = None

                if not content and not embed:
                    await inter.response.send_message(embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_no_content_or_embed']), ephemeral=True)
                    return

                await inter.response.send_message(
                    embed=MyEmbed(
                        notif_type='succeeded',
                        title=CHARACTER_TEXT['scheduled_message'],
                        description=f'指定したメッセージは`{time.strftime('%H:%M:%S (%m/%d/%Y)')}`に <#{channel.id}> にて送信されます。'
                    ),
                    delete_after=10
                )
                while not await self.send_message_callback(time, channel, content, embed):
                    await asyncio.sleep(10)
        
        modal_message = MessageModal()
        await ctx.send_modal(modal_message)

        
        