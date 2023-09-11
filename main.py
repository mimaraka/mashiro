import discord
from dotenv import load_dotenv
import os

from modules.kotobagari import kotobagari_proc
from modules.mashilog import mashilog

from cogs.mashiro import Mashiro
from cogs.music import Music
from cogs.others import Others


bot = discord.Bot(intents=discord.Intents.all())

load_dotenv(verbose=True)
load_dotenv(os.path.dirname(__file__) + ".env")


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
bot.add_cog(Mashiro(bot))
bot.add_cog(Music(bot))
bot.add_cog(Others(bot))

# Botを実行
bot.run(os.getenv("DISCORD_BOT_TOKEN"))