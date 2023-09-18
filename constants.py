URL_IMAGE_AVATAR = "https://cdn.discordapp.com/avatars/1105880759857860709/e576533e1eb721058528573c42590fe0.png?size=1024"

URL_IMAGE_HISSU_01 = "https://media.discordapp.net/attachments/1142318975829676104/1142460814163460240/hissu_01.jpg?width=200&height=267"
URL_IMAGE_HISSU_02 = "https://media.discordapp.net/attachments/1142318975829676104/1142460849580167188/hissu_02.jpg?width=196&height=535"
URL_IMAGE_ICECREAM = "https://media.discordapp.net/attachments/1142318975829676104/1142460904777195570/ice.gif?width=1153&height=662"

RE_URL_PATTERN = r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"

# 音ブルアカ鯖のギルドID
GUILD_ID_OTOBLUEARCHIVE = 911795089355964438
# ぼっち鯖のギルドID
GUILD_ID_BOCCHI = 1134922279051075724

# yt_dlp
YTDL_FORMAT_OPTIONS = {
    "format": "bestaudio/best*[acodec=aac]",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    "source_address": "0.0.0.0",                                # bind to ipv4 since ipv6 addresses cause issues sometimes
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_delay_max 3",
    "options": "-vn",
}