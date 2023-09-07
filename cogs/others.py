import discord
from discord.ext import commands
from discord import app_commands
from modules.myembed import MyEmbed


class Others(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Ping値を返します。")
    async def command_ping(self, inter: discord.Interaction):
        # Ping値を秒単位で取得
        raw_ping = self.bot.latency
        # ミリ秒に変換して丸める
        ping = round(raw_ping * 1000, 2)
        await inter.response.send_message(embed=MyEmbed(title="お呼びですか、先生？", description=f"Ping値: `{ping}[ms]`"))