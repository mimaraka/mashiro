import json
import discord
import re
from .myembed import MyEmbed
from .util import get_member_text


class URLReplacer:
    JSON_PATH = "data/saves/url_replacer.json"

    def __init__(self, name: str, url_pattern: re.Pattern, replacing_pattern : re.Pattern, replaced_str: str, link_text: str) -> None:
        self._name: str = name
        self._url_pattern = url_pattern
        self._replacing_pattern = replacing_pattern
        self._replaced_str = replaced_str
        self._link_text = link_text

    @property
    def url_pattern(self):
        return self._url_pattern

    def _get_data(self) -> dict:
        root: dict = self._get_root()
        return root.get(self._name)
        
    def _get_root(self) -> dict:
        with open(self.JSON_PATH, "r") as f:
            try:
                ret = json.load(f)
            except json.decoder.JSONDecodeError:
                ret = {}
            return ret

    def _save_data(self, data):
        with open(self.JSON_PATH, "w") as f:
            root = self._get_root()
            root[self._name] = data
            json.dump(root, f, indent=4)

    async def switch_replacer(self, ctx: discord.ApplicationContext, switch: bool):
        data = self._get_data() or {"guilds": []}

        if switch:
            if not data.get("guilds"):
                data["guilds"] = []
            if ctx.guild.id not in data["guilds"]:
                data["guilds"].append(ctx.guild.id)
            embed = MyEmbed(notif_type="succeeded", title="URL変換を有効化しました。")
            embed.set_author(name=self._name)
            await ctx.respond(embed=embed, delete_after=10)
        else:
            if data.get("guilds"):
                data["guilds"] = [id for id in data.get("guilds") if id != ctx.guild.id]
            embed = MyEmbed(title="URL変換を無効化しました。")
            embed.set_author(name=self._name)
            await ctx.respond(embed=embed, delete_after=10)

        self._save_data(data)

    def get_replaced_urls(self, content: str, guild_id: int, delete_query: bool = True):
        ret = []

        if self._get_data() and guild_id in self._get_data().get("guilds"):
            for url in re.findall(self._url_pattern, content):
                print(re.search(self._replacing_pattern, url))
                new_url = re.sub(self._replacing_pattern, self._replaced_str, url)
                if delete_query:
                    new_url = re.sub(r'\?[\w=&\-]*', '', url)
                ret.append(new_url)

        return ret

    async def send(self, message: discord.Message, deleted: bool):
        new_urls = self.get_replaced_urls(message.content, message.guild.id)
        for new_url in new_urls:
            link = f'[{self._link_text}]({new_url})'
            if deleted:
                result = f'{get_member_text(message.author)}が共有しました！ | {link}'
                await message.channel.send(result)
            else:
                await message.reply(link, mention_author=False)