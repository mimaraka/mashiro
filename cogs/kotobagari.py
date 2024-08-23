import discord
import jaconv
import random
import re
import modules.util as util
from character_config import KOTOBAGARI_CONFIG
from modules.common_embed import *
from modules.json import JSONLoader


class CogKotobagari(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        self.json_loader = JSONLoader('kotobagari')

    # 正規表現を用いた少しゆるめの検索
    def searchex(self, lis, target_text, looseness, ignore_katahira=False, ignore_dakuten=False):
        TRANS_UL = str.maketrans('ぁぃぅぇぉっゃゅょゎ～', 'あいうえおつやゆよわー')
        TRANS_DAKUTEN = str.maketrans('がぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ', 'かきくけこさしすせそだぢづでどはひふへほはひふへほ')
        # re.search()に用いるパターンの用意
        pattern = ''
        # リストの要素を取り出す
        for i, el in enumerate(lis):
            # リストの要素の型がリストであった場合(一文字ずつリストが用意されている)
            if type(el) == list:
                # 文字ごとの正規表現(〇|〇|...)を用意
                rchar = ''
                # リスト内の一単語ごとにforループ
                for j, s in enumerate(el):
                    # 一文字ずつ正規表現に変換し、or記号(|)で区切る
                    rchar += s
                    if j < len(el) - 1:
                        rchar += '|'
                pattern += f'({rchar})'
                if i < len(lis) - 1:
                    pattern += rf'((\s*|᠎*)*|.{{,{looseness}}})'
            # リストの要素の型が文字列であった場合
            elif type(el) == str:
                # 文字列ごとの正規表現を用意
                rstr = ''
                # 文字列内の一文字ごとにforループ
                for j, c in enumerate(el):
                    rstr += c
                    if j < len(el) - 1:
                        rstr += rf'((\s*|᠎*)*|.{{,{looseness}}})'
                pattern += f'({rstr})'
                if i < len(lis) - 1:
                    pattern += '|'
            # リストの要素の型が上のいずれでもなかった場合
            else:
                return []
        # 検索
        target = jaconv.kata2hira(target_text) if ignore_katahira else target_text
        target = target.lower().translate(TRANS_UL)
        if ignore_dakuten:
            target = target.translate(TRANS_DAKUTEN)
        return re.findall(pattern, target)


    async def kotobagari(self, message: discord.Message):
        for info in KOTOBAGARI_CONFIG:
            for _ in self.searchex(info['keywords'], str(message.content), info['looseness'], info['ignore_katahira'], info['ignore_dakuten']):
                await message.channel.send(random.choice(info['messages']))


    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return
        if message.guild is not None:
            disabled_channels = self.json_loader.get_guild_data(message.guild) or []
            if message.channel.id in disabled_channels:
                return
        await self.kotobagari(message)

    @discord.slash_command(**util.make_command_args('kotobagari'))
    @discord.option('switch', description='言葉狩りの有効化/無効化')
    async def command_kotobagari(self, ctx: discord.ApplicationContext, switch: bool):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
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
            embed=MyEmbed(title=f'{CHARACTER_TEXT['kotobagari_prefix']}{'有効' if switch else '無効'}{CHARACTER_TEXT['kotobagari_suffix']}')
        )
