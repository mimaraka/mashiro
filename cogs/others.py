import discord
from modules.myembed import MyEmbed


class CogOthers(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    @discord.slash_command(name="ping", description="Ping値を返します。")
    async def command_ping(self, ctx: discord.ApplicationContext):
        # Ping値を秒単位で取得
        raw_ping = self.bot.latency
        # ミリ秒に変換して丸める
        ping = round(raw_ping * 1000, 2)
        await ctx.respond(embed=MyEmbed(title="お呼びですか、先生？", description=f"Ping値: `{ping}ms`"))


    @discord.slash_command(name="help", description="何かお困りですか？")
    async def command_help(self, ctx: discord.ApplicationContext):
        embed = MyEmbed(title="コマンド一覧")
        for item in self.bot.walk_application_commands():
            if type(item) == discord.SlashCommand:
                embed.add_field(name=f"/{item.name}", value=item.description, inline=False)
        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label='GitHubリポジトリ', url='https://github.com/mimaraka/mashiro'))
        await ctx.respond(embed=embed, view=view, ephemeral=True)