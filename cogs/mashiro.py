import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import csv
import datetime
import random


MASHIRO_QUOTES_BIRTHDAY = [
    "そうですか。今日が私の誕生日だったんですね…。すっかり忘れてました。気にかけてくださって、ありがとうございます。",
    "誕生日プレゼント、ですか？そうですね……先生と一緒にアイスキャンディーを食べられれば、それで充分です。"
]

MASHIRO_QUOTES_HALLOWEEN = [
    "トリニティのすべての聖人を称える祝日が始まりました。カボチャのお化け…？悪い夢でも見ましたか？",
    "学食で出てくるあの、温かいかぼちゃスープが恋しくなる季節ですね。"
]

MASHIRO_QUOTES_CHRISTMAS = [
    "トリニティの聖なる日ですね。このような日でも、ゲヘナの悪党たちは悪行をなしているんでしょうか…。",
    "いつの間に、夏が過ぎてクリスマスに……楽しい時間が経つのは早いですね。"
]

MASHIRO_QUOTES_NEWYEAR = [
    "明けましておめでとうございます。今年の夏の訓練も、楽しみにしていますね。"
]


class Mashiro(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot


    # ランダムでマシロのセリフを返す関数
    def get_mashiro_quote(self):
        mashiro_quotes = []
        # CSVファイルからセリフのリストを読み込み
        with open("data/mashiro_quotes.csv", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                quote = row[0]
                # 改行文字を変換
                backslash = False
                for i, c in enumerate(quote):
                    if backslash:
                        if c == "n":
                            quote = quote[:i - 1] + "\n" + quote[i + 1:]
                        backslash = False
                    if c == "\\":
                        backslash = True

                mashiro_quotes.append(row[0])
        
        # 誕生日の場合
        today = datetime.date.today()
        if today == datetime.date(today.year, 6, 5):
            mashiro_quotes += MASHIRO_QUOTES_BIRTHDAY
        elif today == datetime.date(today.year, 10, 31):
            mashiro_quotes += MASHIRO_QUOTES_HALLOWEEN
        elif today == datetime.date(today.year, 12, 25):
            mashiro_quotes += MASHIRO_QUOTES_CHRISTMAS
        elif today == datetime.date(today.year, 1, 1):
            mashiro_quotes += MASHIRO_QUOTES_NEWYEAR

        return random.choice(mashiro_quotes)


    # マシロのセリフをランダムに送信
    @app_commands.command(name="mashiro", description="私に何かご用ですか？")
    async def mashiro(self, itrc: discord.Interaction, n: int = 1):
        for _ in range(n):
            mashiro_quote = self.get_mashiro_quote()
            try:
                await itrc.response.send_message(mashiro_quote)
            except discord.InteractionResponded:
                await itrc.channel.send(mashiro_quote)


    # メンションされたとき
    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user.mentioned_in(message):
            # 自撮りを送る
            if "自撮り" in message.content:
                async with message.channel.typing():
                    images = ["jidori_01.png", "jidori_02.png", "jidori_03.png", "jidori_04.png"]
                    messages = ["少々お待ちください……。", "少々お待ちくださいね。", "今撮りますね。"]
                    await asyncio.sleep(3)
                    await message.channel.send(random.choice(messages))
                    await asyncio.sleep(6)
                    await message.channel.send(file=discord.File(f"data/assets/{random.choice(images)}"))
            # ランダムでセリフを送る
            else:
                async with message.channel.typing():
                    await asyncio.sleep(4)
                    await message.channel.send(self.get_mashiro_quote())