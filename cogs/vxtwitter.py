import discord
import json
import re
from modules.myembed import MyEmbed


class Vxtwitter(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    def get_data(self) -> dict:
        with open("data/vxtwitter.json", "r") as f:
            return json.load(f)

    def save_data(self, data):
        with open("data/vxtwitter.json", "w") as f:
            json.dump(data, f, indent=4)


    @discord.slash_command(name="vxtwitter", description="X(Twitter)のURLを自動でvxtwitter.comに変換します。(私にメッセージの管理権限が必要です。)")
    async def command_vxtwitter(self, ctx: discord.ApplicationContext):
        data = self.get_data()

        # 既にオンの場合
        if ctx.guild.id in data.get("guilds"):
            data["guilds"] = [id for id in data.get("guilds") if id != ctx.guild.id]
            await ctx.respond(embed=MyEmbed(title="URL変換を無効化しました。"), delete_after=10)
        # オフの場合
        else:
            if not ctx.channel.permissions_for(ctx.me).manage_messages:
                await ctx.respond(embed=MyEmbed(notif_type="error", description="私にメッセージの管理権限がありません。"), ephemeral=True)
                return
            
            data.get("guilds").append(ctx.guild.id)
            await ctx.respond(embed=MyEmbed(notif_type="succeed", title="URL変換を有効化しました。"), delete_after=10)

        self.save_data(data)
        

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if re.fullmatch(r"https?://(x|twitter).com/\w+/status/\d+(\?[\w=&\-]*)?", message.content):
            new_url = re.sub(r"(x|twitter).com", "vxtwitter.com", message.content)
            new_url = re.sub(r"\?[\w=&\-]*", "", new_url)
            result = f"**{message.author.display_name}** 先生が共有しました！ | [X]({new_url})"
            manage_messages = message.channel.permissions_for(message.guild.me)
            data = self.get_data()
            if message.guild.id in data.get("guilds") and manage_messages:
                # attachmentsがついたメッセージは削除しない
                if not message.attachments:
                    await message.delete()
                await message.channel.send(result)