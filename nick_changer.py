import csv
import discord
import discord.app_commands
import datetime
import os


DATETIME_FROM = datetime.datetime(2023, 6, 5)
# 名前変更終了時間
DATETIME_TO = datetime.datetime(2023, 6, 5)
# 旧ニックネームを保存するCSVのパス
CSV_PATH = "old_nicks.csv"
# 置き換える名前
REPLACED_NICK = "静山マシロ"
# ニックネームを置き換えるサーバーID
GUILD_ID = 1002875196522381322

