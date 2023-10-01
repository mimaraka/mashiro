import discord
from dotenv import load_dotenv
import openai
import os
import rembg

from modules.kotobagari import kotobagari_proc
from modules.mashilog import mashilog

from cogs.image import CogImage
from cogs.mashiro import CogMashiro
from cogs.music import CogMusic
from cogs.nick_changer import CogNickChanger
from cogs.others import CogOthers


load_dotenv(verbose=True)
load_dotenv(os.path.dirname(__file__) + ".env")

bot = discord.Bot(intents=discord.Intents.all())
openai.api_key = os.getenv("OPENAI_API_KEY")


# bot起動時のイベント
@bot.event
async def on_ready():
    mashilog("ようこそ、先生。今日も一緒に、正義のために頑張りましょう。")
    activity = discord.Activity(name="/play", type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)


# メッセージ送信時のイベント
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # 言葉狩り
    await kotobagari_proc(message)


# コグの設定
bot.add_cog(CogImage(bot))
bot.add_cog(CogMashiro(bot))
bot.add_cog(CogMusic(bot))
bot.add_cog(CogNickChanger(bot))
bot.add_cog(CogOthers(bot))

# rembgのモデルをダウンロードしておく
#rembg.new_session()

# Botを実行
bot.run(os.getenv("DISCORD_BOT_TOKEN"))