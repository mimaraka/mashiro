import discord
import jaconv
import random
import re
import constants as const
from modules.common_embed import *
from modules.json import JSONLoader


class CogKotobagari(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.json_loader = JSONLoader("kotobagari")

    # 正規表現を用いた少しゆるめの検索
    def searchex(self, lis, target_text, looseness, ignore_katahira=False, ignore_dakuten=False):
        TRANS_UL = str.maketrans("ぁぃぅぇぉっゃゅょゎ～", "あいうえおつやゆよわー")
        TRANS_DAKUTEN = str.maketrans("がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ", "かきくけこさしすせそだぢづでどはひふへほはひふへほ")
        # re.search()に用いるパターンの用意
        pattern = r""
        # リストの要素を取り出す
        for i, el in enumerate(lis):
            # リストの要素の型がリストであった場合(一文字ずつリストが用意されている)
            if type(el) == list:
                # 文字ごとの正規表現(〇|〇|...)を用意
                rchar = r""
                # リスト内の一単語ごとにforループ
                for j, s in enumerate(el):
                    # 一文字ずつ正規表現に変換し、or記号(|)で区切る
                    # 末端処理
                    if j == len(el) - 1:
                        rchar += r"{}".format(s)
                    else:
                        rchar += r"{}".format(s) + r"|"
                # 末端処理
                if i == len(lis) - 1:
                    pattern += r"(" + rchar + r")"
                else:
                    pattern += r"(" + rchar + r")" + r"((\s*|᠎*)*|.{," + r"{}".format(looseness) + r"})"
            # リストの要素の型が文字列であった場合
            elif type(el) == str:
                # 文字列ごとの正規表現を用意
                rstr = r""
                # 文字列内の一文字ごとにforループ
                for j, c in enumerate(el):
                    # 末端処理
                    if j == len(el) - 1:
                        rstr += r"{}".format(c)
                    else:
                        rstr += r"{}".format(c) + r"((\s*|᠎*)*|.{," + r"{}".format(looseness) + r"})"
                # 末端処理
                if i == len(lis) - 1:
                    pattern += r"(" + rstr + r")"
                else:
                    pattern += r"(" + rstr + r")" + r"|"
            # リストの要素の型が上のいずれでもなかった場合
            else:
                return 0
        # 検索
        target = jaconv.kata2hira(target_text) if ignore_katahira else target_text
        target = target.lower().translate(TRANS_UL)
        if ignore_dakuten:
            target = target.translate(TRANS_DAKUTEN)
        return re.findall(pattern, target)


    async def kotobagari(self, message: discord.Message):
        for _ in self.searchex(["ひつす", "必須"], str(message.content), 0, True):
            images = [const.URL_IMAGE_HISSU_01, const.URL_IMAGE_HISSU_02]
            await message.channel.send(random.choice(images))

        for _ in self.searchex(["あいす", "ふえら"], str(message.content), 0, True):
            await message.channel.send(const.URL_IMAGE_ICECREAM)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild is not None:
            disabled_channels = self.json_loader.get_guild_data(message.guild) or []
            if message.channel.id in disabled_channels:
                return
        await self.kotobagari(message)

    @discord.slash_command(name="kotobagari", description="現在のチャンネルでの言葉狩りの有効/無効を切り替えます (管理者のみ実行可)。")
    @discord.option("switch", description="言葉狩りの有効化/無効化")
    async def command_kotobagari(self, ctx: discord.ApplicationContext, switch: bool):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_DIRECT_MESSAGE, ephemeral=True)
            return

        if not any([role.permissions.administrator for role in ctx.author.roles]) and ctx.author != ctx.guild.owner:
            await ctx.respond(embed=EMBED_NOT_ADMINISTRATOR, ephemeral=True)
            return
        
        disabled_channels = self.json_loader.get_guild_data(ctx.guild) or []

        if switch:
            disabled_channels = [ch for ch in disabled_channels if ch != ctx.channel.id]
        elif ctx.channel.id not in disabled_channels:
            disabled_channels.append(ctx.channel.id)

        self.json_loader.set_guild_data(disabled_channels, ctx.guild)

        await ctx.respond(
            embed=MyEmbed(title=f"このチャンネルでの言葉狩りを{'有効' if switch else '無効'}にしました。")
        )
