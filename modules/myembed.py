import datetime
import discord
from discord.types.embed import EmbedType
from typing import Any, Literal


EMBED_THUMBNAIL = {
    "normal": "https://media.discordapp.net/attachments/1142318975829676104/1142319072709718036/mashiro_normal.png?width=662&height=662",
    "error": "https://media.discordapp.net/attachments/1142318975829676104/1142319099150598184/mashiro_error.png?width=662&height=662",
    "inactive": "https://media.discordapp.net/attachments/1142318975829676104/1142321489769660496/mashiro_sleeping.png?width=662&height=662",
    "succeed": "https://media.discordapp.net/attachments/1142318975829676104/1142713236718887024/mashiro_smile.png?width=662&height=662",
    "question": "https://media.discordapp.net/attachments/1142318975829676104/1142793060128927944/mashiro_question.png?width=662&height=662",
    "warning": "https://media.discordapp.net/attachments/1142318975829676104/1142793794518003762/mashiro_warning.png?width=662&height=662"
}

EMBED_COLOR = {
    "normal": 0x8d5ee6,
    "error": 0xe70c17,
    "inactive": 0x858585,
    "warning": 0xfbf65f,
    "question": 0x2eb2ff,
    "succeed": 0x3ae20c
}

NotificationType = Literal["normal", "error", "warning", "inactive", "question", "succeed"]

# オリジナルの埋め込みクラス
class MyEmbed(discord.Embed):
    def __init__(self, *, notification_type: NotificationType = "normal", custom_color: int | None = None, custom_icon: NotificationType | None = None, title: Any | None = None, type: EmbedType = 'rich', url: Any | None = None, description: Any | None = None, timestamp: datetime.datetime | None = None, image: str = None):
        title_ = None
        # 通知タイプ毎のカラー・タイトルの設定
        if notification_type == "error":
            title_ = "❌ エラーが発生しました……"
        elif notification_type == "warning":
            title_ = "⚠️ 警告です！"

        # カスタムカラー・タイトルの設定
        color = custom_color or EMBED_COLOR[notification_type]
        title_ = title or title_
        
        # 基底クラスの初期化
        super().__init__(colour=color, color=color, title=title_, type=type, url=url, description=description, timestamp=timestamp)

        self.set_thumbnail(url=EMBED_THUMBNAIL[custom_icon or notification_type])
        if image:
            self.set_image(image)