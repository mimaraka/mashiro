URL_IMAGE_HISSU_01 = "https://media.discordapp.net/attachments/1142318975829676104/1142460814163460240/hissu_01.jpg?width=200&height=267"
URL_IMAGE_HISSU_02 = "https://media.discordapp.net/attachments/1142318975829676104/1142460849580167188/hissu_02.jpg?width=196&height=535"
URL_IMAGE_ICECREAM = "https://media.discordapp.net/attachments/1142318975829676104/1142460904777195570/ice.gif?width=1153&height=662"

URL_ICON_YOUTUBE = "https://media.discordapp.net/attachments/1142318975829676104/1275427698965090437/image.png?ex=66c5da1b&is=66c4889b&hm=59b8a49788adb3aa3e45b3a492ef4dba7838ac14b70f2f5632f67db7ceda1bc5&=&format=webp&quality=lossless&width=662&height=662"
URL_ICON_SOUNDCLOUD = "https://media.discordapp.net/attachments/1142318975829676104/1275344983884562513/soundcloud_512_24339.png?ex=66c58d12&is=66c43b92&hm=64491109a1296a06a797c7f3df77cec4cb73b96c8cae774fa8056965e8a4267e&=&format=webp&quality=lossless&width=640&height=640"
URL_ICON_NICONICO = "https://media.discordapp.net/attachments/1142318975829676104/1275345260062576672/lMfN7ih0afMsHzmMfSlJNbOexI6sRNG7LgcwJmgAx8CPvvcCLrf4zOxoHDa_jk68DXw.png?ex=66c58d54&is=66c43bd4&hm=2c5680e3f4027f4b768d318b6b93e32f44666505b123e840a4e5f1f6d6022411&=&format=webp&quality=lossless&width=640&height=640"

RE_PATTERN_URL = r"^(https?://)?[\w/:%#\$&\?\(\)~\.=\+\-]+"
RE_PATTERN_FULL_URL = r"^https?://[\w/:%#\$&\?\(\)~\.=\+\-]+"
RE_PATTERN_URL_YOUTUBE = r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w-]+(&list=)?[\w-]*"
RE_PATTERN_URL_SOUNDCLOUD = r"^(https?://)?(www\.)?(soundcloud\.com|snd\.sc)/"
RE_PATTERN_URL_NICONICO = r"^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+"

# 音ブルアカ鯖のギルドID
GUILD_ID_OTOBLUEARCHIVE = 911795089355964438
# こち横鯖のギルドID
GUILD_ID_KOCHIYOKO = 1134922279051075724
# RRUM鯖のギルドID
GUILD_ID_RRUM = 733998377074688050
# 鯖らか跡地のギルドID
GUILD_ID_SABARAKA = 732902508787269655

GUILD_IDS_CHATGPT = [
    GUILD_ID_OTOBLUEARCHIVE,
    GUILD_ID_KOCHIYOKO,
    GUILD_ID_RRUM,
    GUILD_ID_SABARAKA
]

# ローディングアイコンの絵文字
EMOJI_ID_LOADING = 1154011417029128242

# yt_dlp
YTDL_FORMAT_OPTIONS = {
    "format": "best*[acodec!=none]",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": False,
    "no_warnings": True,
    "default_search": "auto",                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    "source_address": "0.0.0.0",                                # bind to ipv4 since ipv6 addresses cause issues sometimes
    "usenetrc": True,
    "netrc_location": "./.netrc",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_delay_max 3",
    "options": "-vn",
}

MIMETYPES_FFMPEG = [
    "audio/aac",
    "audio/basic",
    "audio/flac",
    "audio/mpeg",
    "audio/ogg",
    "audio/x-aiff",
    "audio/x-ms-wma",
    "audio/wav",
    "audio/x-wav",
    "audio/vnd.qcelp",
    "audio/x-pn-realaudio",
    "audio/x-twinvq",
    "video/quicktime",
    "video/mp4",
    "video/mpeg",
    "video/vnd.rn-realvideo",
    "video/vnd.vivo",
    "video/wavelet",
    "video/webm",
    "video/x-flv",
    "video/x-ms-asf",
    "video/x-msvideo"
]