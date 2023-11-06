import discord
import json
import re
from modules.myembed import MyEmbed


class CogVxtwitter(discord.Cog):
    JSON_PATH = "data/saves/vxtwitter.json"

    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    def get_data(self) -> dict:
        with open(self.JSON_PATH, "r") as f:
            return json.load(f)

    def save_data(self, data):
        with open(self.JSON_PATH, "w") as f:
            json.dump(data, f, indent=4)


    @discord.slash_command(name="vxtwitter", description="X(Twitter)のURLを自動でvxtwitter.comに変換する機能を有効/無効にします。")
    @discord.option("switch", description="URL変換機能の有効化/無効化")
    async def command_vxtwitter(self, ctx: discord.ApplicationContext, switch: bool):
        data = self.get_data()

        if switch:
            data["guilds"].append(ctx.guild.id)
            await ctx.respond(embed=MyEmbed(notif_type="succeed", title="URL変換を有効化しました。"), delete_after=10)
        else:
            data["guilds"] = [id for id in data.get("guilds") if id != ctx.guild.id]
            await ctx.respond(embed=MyEmbed(title="URL変換を無効化しました。"), delete_after=10)

        self.save_data(data)
        

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        RE_PATTERN_X = r'https?://(?:x|twitter).com/\w+/status/\d+(?:\?[\w=&\-]*)?'
        new_urls = []

        data = self.get_data()
        if message.guild.id in data.get('guilds'):
            # X(Twitter)のURLを全て検出し、変換
            for url in re.findall(RE_PATTERN_X, message.content):
                new_url = re.sub(r'(x|twitter).com', 'vxtwitter.com', url)
                new_url = re.sub(r'\?[\w=&\-]*', '', new_url)
                new_urls.append(new_url)

            deleted = False
            # X(Twitter)のURLのみのとき
            if re.fullmatch(rf'^(\s*{RE_PATTERN_X}\s*)+$', message.content):
                manage_messages = message.channel.permissions_for(message.guild.me)
                # attachmentsがなく、マシロにメッセージ管理権限がある場合、元のメッセージを削除
                if manage_messages and not message.attachments:
                    try:
                        await message.delete()
                        deleted = True
                    except discord.Forbidden:
                        pass

            if deleted:
                results = [f'**{message.author.display_name}**(`{message.author.name}`) 先生が共有しました！ | [ポストを見る]({url})' for url in new_urls]
            else:
                results = [f'[ポストを見る]({url})' for url in new_urls]
            for result in results:
                if deleted:
                    await message.channel.send(result)
                else:
                    await message.reply(result, mention_author=False)