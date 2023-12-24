import asyncio
import discord
import datetime
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
    @discord.option("content", description="送信したい内容(\\nで改行されます。)", default=None)
    @discord.option("channel", description="メッセージを送信するチャンネル (省略した場合はコマンドを実行したチャンネル)", default=None)
    @discord.option("day", description="送信する日付 (省略した場合は今日)", default=None)
    @discord.option("hour", description="送信する時間 (24時間表記、省略した場合は現在の時間)", default=None)
    @discord.option("minute", description="送信する分 (省略した場合は現在の分)", default=None)
    @discord.option("embed_title", description="埋め込みのタイトル", default=None)
    @discord.option("embed_description", description="埋め込みの説明", default=None)
    async def command_send_message(self, ctx: discord.ApplicationContext, content: str, channel: discord.TextChannel, day: int, hour: int, minute: int, embed_title: str, embed_description: str):
        channel = channel or ctx.channel
        now = datetime.datetime.now()
        day = day or now.day
        hour = hour or now.hour
        minute = minute or now.minute

        time = datetime.datetime(now.year, now.month, day, hour, minute)

        if embed_title or embed_description:
            embed = MyEmbed(title=embed_title, description=embed_description)
        else:
            embed = None

        if not content and not embed:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="送信する文章と埋め込みの内容のいずれか一方を必ず指定してください。"), ephemeral=True)
            return
        
        await ctx.respond(
            embed=MyEmbed(
                notif_type="succeeded",
                title="メッセージの送信を設定しました！",
                description=f"指定したメッセージは`{time.strftime('%H:%M:%S (%m/%d/%Y)')}`に #{channel.name} にて送信されます。"
            ),
            delete_after=10
        )

        while not await self.send_message_callback(time, channel, content, embed):
            asyncio.sleep(10)
        