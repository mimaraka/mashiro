import discord
import math
import modules.util as util
from constants import GITHUB_REPOSITORY_URL
from character_config import CHARACTER_TEXT
from modules.myembed import MyEmbed


class CogOthers(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    @discord.slash_command(**util.make_command_args('ping'))
    async def command_ping(self, ctx: discord.ApplicationContext):
        # Ping値を秒単位で取得
        raw_ping = self.bot.latency
        # ミリ秒に変換して丸める
        ping = round(raw_ping * 1000, 2)
        await ctx.respond(embed=MyEmbed(title=CHARACTER_TEXT['on_pong'], description=f'Ping値: `{ping}ms`'))


    # コマンド一覧のメッセージを取得
    def get_help_msg(self, page: int):
        commands = []
        for item in self.bot.walk_application_commands():
            if type(item) == discord.SlashCommand:
                name = item.name
                while item.parent is not None:
                    item = item.parent
                    name = item.name + ' ' + name
                commands.append({
                    'name': name,
                    'description': item.description
                })

        n_pages = math.ceil(len(commands) / 10)

        class ButtonPreviousPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page <= 1, emoji='⬅️')
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.edit_message(interaction.message.id, **self.get_help_msg(page=btn_self.page - 1))

        class ButtonNextPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page >= n_pages, emoji='➡️')
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.edit_message(interaction.message.id, **self.get_help_msg(page=btn_self.page + 1))

        embed = MyEmbed(title='コマンド一覧')
        view = discord.ui.View(timeout=None)
        page = min(max(page, 1), n_pages)
        start_index = (page - 1) * 10
        for command in commands[start_index:start_index + 10]:
            embed.add_field(name='/' + command['name'], value=command['description'], inline=False)

        if len(commands) > 10:
            embed.description = f'**{page}** / {n_pages}ページ'
            view.add_item(ButtonPreviousPage(page))
            view.add_item(ButtonNextPage(page))
        view.add_item(discord.ui.Button(label='GitHubリポジトリ', url=GITHUB_REPOSITORY_URL))

        result = {
            'embed': embed,
            'view': view
        }
        return result


    @discord.slash_command(**util.make_command_args('help'))
    async def command_help(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        await ctx.respond(**self.get_help_msg(page=1))