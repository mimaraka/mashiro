################################################################################
# Botに関する設定
################################################################################

GITHUB_REPOSITORY_URL = 'https://github.com/mimaraka/mashiro'

# ローディングアイコンの絵文字ID
EMOJI_ID_LOADING = 1154011417029128242


################################################################################
# その他の定数
################################################################################

# URLの正規表現
RE_PATTERN_URL = r'^https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
RE_PATTERN_URL_NICONICO = r'^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+'

# yt_dlp
YTDL_FORMAT_OPTIONS = {
    'format': 'best*[acodec!=none]',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': True,
    'default_search': 'auto',                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    'source_address': '0.0.0.0',                                # bind to ipv4 since ipv6 addresses cause issues sometimes
    'usenetrc': True,
    'netrc_location': './.netrc',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_delay_max 3',
    'options': '-vn',
}

MIMETYPES_FFMPEG = [
    'audio/aac',
    'audio/basic',
    'audio/flac',
    'audio/mpeg',
    'audio/ogg',
    'audio/x-aiff',
    'audio/x-ms-wma',
    'audio/wav',
    'audio/x-wav',
    'audio/vnd.qcelp',
    'audio/x-pn-realaudio',
    'audio/x-twinvq',
    'video/quicktime',
    'video/mp4',
    'video/mpeg',
    'video/vnd.rn-realvideo',
    'video/vnd.vivo',
    'video/wavelet',
    'video/webm',
    'video/x-flv',
    'video/x-ms-asf',
    'video/x-msvideo'
]