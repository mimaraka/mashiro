import asyncio
import csv
import discord
import discord.app_commands
from discord.ext import commands
import datetime
import os

from modules.kotobagari import kotobagari_proc
from env.config import Config
import constants as const

from cogs.mashiro import Mashiro
from cogs.music import Music
from cogs.others import Others


# 名前変更開始時間(年, 月, 日, 時, 分, 秒)(省略すると0)
DATETIME_FROM = datetime.datetime(2023, 6, 5)
# 名前変更終了時間
DATETIME_TO = datetime.datetime(2023, 6, 5)
# 旧ニックネームを保存するCSVのパス
CSV_PATH = "old_nicks.csv"
# 置き換える名前
REPLACED_NICK = "静山マシロ"
# ニックネームを置き換えるサーバーID
GUILD_ID = 1002875196522381322

bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())
tree = bot.tree

config = Config()


# ニックネームを変更
async def change_nick():
    # ブルアカ鯖のギルドオブジェクト
    guild = bot.get_guild(GUILD_ID)


    # 現在時刻が名前変更期間内で、まだニックネームが変更されていない場合
    if datetime.datetime.now() >= DATETIME_FROM and datetime.datetime.now() < DATETIME_TO and not os.path.isfile(CSV_PATH):
        # メンバー名を変更(し、旧ニックネームをCSVに保存)
        with open(CSV_PATH, "w", encoding="shift-jis") as f:
            writer = csv.writer(f)
            for member in guild.members:
                try:
                    data = [str(member.id)]
                    if member.nick:
                        data += [member.nick]
                    await member.edit(nick=REPLACED_NICK)
                    writer.writerow(data)
                # 上位ロールのユーザーまたは管理者のプロフィールを更新しようとしたとき
                except discord.errors.Forbidden:
                    pass

                # APIリクエスト制限対策
                await asyncio.sleep(0.04)

    # 名前変更終了時間後で、すでにニックネームが変更されている場合
    elif datetime.datetime.now() >= DATETIME_TO and os.path.isfile(CSV_PATH):
        # 変更前のニックネームを保存する辞書(キー：ユーザーID、値：ニックネーム(無ければNone))
        old_nicks = {}

        # csvファイルを読み込み
        with open(CSV_PATH, "r+", encoding="shift-jis") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 1:
                    old_nicks[int(row[0])] = row[1]
                elif len(row) > 0:
                    old_nicks[int(row[0])] = None

        # CSVファイルを削除
        os.remove(CSV_PATH)

        # メンバー名を戻す
        for member in guild.members:
            try:
                if member.id in old_nicks.keys():
                    await member.edit(nick=old_nicks[member.id])
            # 上位ロールのユーザーまたは管理者のプロフィールを更新しようとしたとき
            except discord.errors.Forbidden:
                pass

            # APIリクエスト制限対策
            await asyncio.sleep(0.04)

    # 60秒後に再度チェック
    if datetime.datetime.now() < DATETIME_TO:
        await asyncio.sleep(60)
        await change_nick()


# bot起動時のイベント
@bot.event
async def on_ready():
    print("*" * 64)
    print(const.STR_ON_READY)
    print("*" * 64)
    await tree.sync()
    await change_nick()

    activity = discord.Activity(name="/play", type=discord.ActivityType.listening)
    await bot.change_presence(activity=activity)


# プロフィール編集時のイベント
@bot.event
async def on_member_update(before, after):
    # 期間中にニックネームが変更された場合
    if os.path.isfile(CSV_PATH) and datetime.datetime.now() < DATETIME_TO:
        if after.display_name != REPLACED_NICK:
            try:
                await after.edit(nick=REPLACED_NICK)
            except discord.errors.Forbidden:
                pass


# メッセージ送信時のイベント
@bot.event
async def on_message(message):
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
bot.run(config.bot_token)