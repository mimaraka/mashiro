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


    @app_commands.command(name="help", description="何かお困りですか？")
    async def command_help(self, inter: discord.Interaction):
        embed = MyEmbed(title="コマンド一覧")
        for item in self.bot.tree.walk_commands():
            if type(item) == app_commands.Command:
                embed.add_field(name=f"/{item.name}", value=item.description, inline=False)
        await inter.response.send_message(embed=embed)