import discord
from dotenv import load_dotenv
import os

# 各モジュールのimport時に環境変数を参照するため、先に読み込む
load_dotenv(verbose=True)
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

from character_config import CHARACTER_TEXT
from modules.mylog import mylog

from cogs.image import CogImage
from cogs.character import CogCharacter
from cogs.music import CogMusic
from cogs.nick_changer import CogNickChanger
from cogs.downloader import CogDownloader
from cogs.message_sender import CogMessageSender
from cogs.wordhunt import CogWordhunt
from cogs.vc_util import CogVCUtil
from cogs.url_replacer import CogURLReplacer
from cogs.others import CogOthers

bot = discord.Bot(intents=discord.Intents.all())


# bot起動時のイベント
@bot.event
async def on_ready():
    mylog(CHARACTER_TEXT['on_ready'])
    activity = discord.Activity(name='/play', type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)


# コグの設定
bot.add_cog(CogImage(bot))
bot.add_cog(CogCharacter(bot))
bot.add_cog(CogMusic(bot))
bot.add_cog(CogNickChanger(bot))
bot.add_cog(CogDownloader(bot))
bot.add_cog(CogMessageSender(bot))
bot.add_cog(CogWordhunt(bot))
bot.add_cog(CogVCUtil(bot))
bot.add_cog(CogURLReplacer(bot))
bot.add_cog(CogOthers(bot))

# Botを実行
bot.run(os.getenv('DISCORD_BOT_TOKEN'))