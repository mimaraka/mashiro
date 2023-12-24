import asyncio
import discord
import datetime

from discord.ui.input_text import InputText
from modules.myembed import MyEmbed


class CogMessageSender(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot: discord.Bot = bot

    # メッセージ送信用のコールバック
    async def send_message_callback(self, time: datetime.datetime, channel: discord.TextChannel, content: str, embed: MyEmbed):
        # 既に指定時間を過ぎている場合
        if time <= datetime.datetime.now():
            await channel.send(content, embed=embed)
            return True
        return False


    # /send_message
    @discord.slash_command(name="send_message", description="指定した時間に指定したメッセージを送信します。")
    @discord.option("channel", description="メッセージを送信するチャンネル (省略した場合はコマンドを実行したチャンネル)", default=None)
    @discord.option("day", description="送信する日付 (省略した場合は今日)", default=None, min_value=1, max_value=31)
    @discord.option("hour", description="送信する時間 (24時間表記、省略した場合は現在の時間)", default=None, min_value=0, max_value=23)
    @discord.option("minute", description="送信する分 (省略した場合は現在の分)", default=None, min_value=0, max_value=59)
    async def command_send_message(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, day: int, hour: int, minute: int):
        channel = channel or ctx.channel
        now = datetime.datetime.now()
        day = day or now.day
        hour = hour or now.hour
        minute = minute or now.minute

        try:
            time = datetime.datetime(now.year, now.month, day, hour, minute)
        except ValueError:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="日時の指定が無効です。"), ephemeral=True)
            return

        class MessageModal(discord.ui.Modal):
            def __init__(self_) -> None:
                super().__init__(title="メッセージの設定", timeout=None)

                print(discord.ui.InputText.__init__().__code__.co_varnames[:discord.ui.InputText.__init__().__code__.co_argcount])
                # content
                self_.input_content = discord.ui.InputText(
                    label="メッセージの内容",
                    required=False,
                    style=discord.InputTextStyle.paragraph
                )

                # embed_title
                self_.input_embed_title = discord.ui.InputText(
                    label="埋め込みのタイトル",
                    required=False,
                    style=discord.InputTextStyle.short
                )

                # embed_description
                self_.input_embed_description = discord.InputText(
                    label="埋め込みの説明",
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
                    await ctx.respond(embed=MyEmbed(notif_type="error", description="送信する文章と埋め込みの内容のいずれか一方を必ず指定してください。"), ephemeral=True)
                    return

                await inter.response.send_message(
                    embed=MyEmbed(
                        notif_type="succeeded",
                        title="メッセージの送信を設定しました！",
                        description=f"指定したメッセージは`{time.strftime('%H:%M:%S (%m/%d/%Y)')}`に #{channel.name} にて送信されます。"
                    ),
                    delete_after=10
                )
                while not await self.send_message_callback(time, channel, content, embed):
                    asyncio.sleep(10)
        
        modal_message = MessageModal()
        await ctx.send_modal(modal_message)

        
        