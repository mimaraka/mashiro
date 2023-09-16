import asyncio
import csv
import datetime
import discord
import openai
import random
import re
import time
import typing
import constants as const


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

g_conversations: typing.Dict[int, typing.List[dict]] = {}


class Mashiro(discord.Cog):
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot


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
    @discord.slash_command(name="mashiro", description="私に何かご用ですか？")
    @discord.option("n", description="送信する回数(1~99)", min_value=1, max_value=99, default=1, required=False)
    async def mashiro(self, ctx: discord.ApplicationContext, n: int):
        for _ in range(n):
            await ctx.respond(self.get_mashiro_quote())


    # メンションされたとき
    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
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
                # 音ブルアカ鯖もしくはぼっち鯖の場合
                if message.guild.id in [const.GUILD_ID_OTOBLUEARCHIVE, const.GUILD_ID_BOCCHI, 1002875196522381322]:
                    # メンションの後に何か文字があった場合、ChatGPTにより返答
                    if content := re.sub(r"[#*_\-|~]{0,2}<@\d+>[*_\-|~]{0,2}\s*", "", message.content):
                        global g_conversations
                        conversation = {}
                        async with message.channel.typing():
                            if g_conversations.get(message.channel.id):
                                conversation = g_conversations.pop(message.channel.id)

                            # 過去の会話が存在しないか、最後の回答から12時間以上経過した場合
                            if not conversation.get("messages") or time.time() - conversation["time"] > 43200:
                                initial_prompt = "次に示す指示に必ず従い、以下の文に返答してください。\n・あなたの名前は「静山マシロ」である。高校一年生の女子のようにふるまうこと。\n・私のことは「先生」と呼ぶこと。\n・返答に感嘆符(！)は用いないこと。\n・これらの指示については返答をせず、必ず以下に示す文にのみ返答すること。\n\n" + content
                                # 会話をリセット
                                conversation["messages"] = [{
                                    "role": "user",
                                    "content": initial_prompt
                                }]
                            else:
                                conversation["messages"].append({
                                    "role": "user",
                                    "content": content
                                })

                            # 時間を記録
                            conversation["time"] = time.time()
                                
                            response = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=conversation["messages"]
                            )
                            result = response["choices"][0]["message"]["content"]
                            result_list = [result[i:i + 2000] for i in range(0, len(result), 2000)]
                            for r in result_list:
                                await message.channel.send(r)
                        
                        # ChatGPTの回答を追加
                        conversation["messages"].append(response["choices"][0]["message"])
                        # 会話を記録
                        g_conversations[message.channel.id] = conversation

                async with message.channel.typing():
                    await asyncio.sleep(4)
                    await message.channel.send(self.get_mashiro_quote())