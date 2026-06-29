import os
import shutil
import tempfile

################################################################################
# Botに関する設定
################################################################################

BOT_USER_ID = 1105880759857860709
GITHUB_REPOSITORY_URL = 'https://github.com/mimaraka/mashiro'

GEMINI_AVAILABLE_GUILDS = [
    732902508787269655, # Mimaraka server
    1134922279051075724, # Kochiyoko server
    733998377074688050, # RRUM server
    911795089355964438, # BlueArchive OtoMAD server
]

# ローディングアイコンの絵文字ID
EMOJI_ID_LOADING = 1154011417029128242


################################################################################
# その他の定数
################################################################################

# URLの正規表現
RE_PATTERN_URL = r'^https?://[\w/:%#\$&\?\(\)~\.=\+\-]+'
RE_PATTERN_URL_NICONICO = r'^(https?://)?(www\.|sp\.)?(nicovideo\.jp/watch|nico\.ms)/sm\d+'

FAVICON = {

}

# yt_dlp

# データセンターIP(OCI等)ではYouTubeのbot検出を回避するためPO Tokenが必要。
# bgutil-ytdlp-pot-provider のトークン生成サーバーのベースURLを指定する。
# docker-compose のサービス名を既定とし、環境変数で上書き可能にする。
YTDLP_POT_BASE_URL = os.getenv('YTDLP_POT_BASE_URL', 'http://bgutil-provider:4416')

# yt-dlp の extractor_args（全YoutubeDL呼び出しで共有）
# 値はリストで渡すのがyt-dlpの仕様。別コンテナのサーバーを参照するため base_url の明示が必須。
YTDL_EXTRACTOR_ARGS = {
    'youtubepot-bgutilhttp': {
        'base_url': [YTDLP_POT_BASE_URL],
    },
}

# cookies.txt が存在する場合のみ cookiefile を指定する
# (存在しないパスを指定すると無駄な副作用やエラーの原因になるため)
#
# yt-dlp は close() 時に cookiefile へクッキーを書き戻すため、読み取り専用で
# マウントされた cookies.txt (docker-compose の :ro マウント) をそのまま渡すと
# OCI 等の環境で OSError: Read-only file system になる。
# 書き込み可能な一時ファイルへコピーして、そのコピーを使わせることで回避する。
#
# yt-dlp (Python標準の MozillaCookieJar) は先頭行が Netscape ヘッダで始まる
# ファイルしか受け付けない。空ファイルや非Netscape形式を渡すと LoadError になるため、
# 事前に検証して不正なら cookiefile を使わない (None を返す)。
def _looks_like_netscape_cookiefile(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
    except OSError:
        return False
    # 標準ライブラリの magic 判定 "#( Netscape)? HTTP Cookie File" と同等
    return 'HTTP Cookie File' in first_line


def _prepare_cookiefile():
    source = './cookies.txt'
    if not os.path.isfile(source):
        return None
    # 空 or 非Netscape形式の cookies.txt は「Cookie無し」として扱う
    # (deploy.sh が docker の空ディレクトリ生成を避けるために空ファイルを置くケースに対応)
    if not _looks_like_netscape_cookiefile(source):
        return None
    try:
        fd, dest = tempfile.mkstemp(prefix='ytdl_cookies_', suffix='.txt')
        os.close(fd)
        shutil.copyfile(source, dest)
        return dest
    except OSError:
        # コピーに失敗した場合は元ファイルを使用する (読み取り専用でなければ動作する)
        return source

YTDL_COOKIEFILE = _prepare_cookiefile()

YTDL_OPTIONS = {
    'format': 'ba/b*[acodec!=none]/b*',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': False,
    'no_warnings': True,
    'default_search': 'auto',                                   # 非URLのテキストが投げられたときにキーワード検索をしてくれる
    'source_address': '0.0.0.0',                                # bind to ipv4 since ipv6 addresses cause issues sometimes
    # 'usenetrc': True,
    # 'netrc_location': './.netrc',
    'extractor_args': YTDL_EXTRACTOR_ARGS,
    'http_headers': {
        'Accept-Language': 'ja-JP'
    }
}

if YTDL_COOKIEFILE:
    YTDL_OPTIONS['cookiefile'] = YTDL_COOKIEFILE

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_at_eof 1 -reconnect_delay_max 3',
    'options': '-vn',
}

MIMETYPES_IMAGE = ['image/png', 'image/pjpeg', 'image/jpeg', 'image/x-icon', 'image/bmp']

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