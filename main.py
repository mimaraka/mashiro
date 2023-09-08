import discord
import discord.app_commands
from discord.ext import commands
from dotenv import load_dotenv
import os

from modules.kotobagari import kotobagari_proc
import constants as const

from cogs.mashiro import Mashiro
from cogs.music import Music
from cogs.others import Others


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())

load_dotenv(verbose=True)
load_dotenv(os.path.dirname(__file__) + ".env")


# bot起動時のイベント
@bot.event
async def on_ready():
    print("*" * 64)
    print(const.STR_ON_READY)
    print("*" * 64)
    await bot.tree.sync()
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
@bot.event
async def setup_hook():
    await bot.add_cog(Mashiro(bot))
    await bot.add_cog(Music(bot))
    await bot.add_cog(Others(bot))


# Botを実行
bot.run(os.getenv("DISCORD_BOT_TOKEN"))