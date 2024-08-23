import datetime
import discord
from discord.types.embed import EmbedType
from typing import Any, Literal
from character_config import CHARACTER_ICON, CHARACTER_TEXT

EMBED_COLOR = {
    'normal': 0x8d5ee6,
    'error': 0xe70c17,
    'inactive': 0x858585,
    'warning': 0xfbf65f,
    'question': 0x2eb2ff,
    'succeeded': 0x18db66
}

NotificationType = Literal['normal', 'error', 'warning', 'inactive', 'question', 'succeeded']

# オリジナルの埋め込みクラス
class MyEmbed(discord.Embed):
    def __init__(self, *, notif_type: NotificationType = 'normal', custom_color: int | None = None, custom_icon: NotificationType | None = None, title: Any | None = None, type: EmbedType = 'rich', url: Any | None = None, description: Any | None = None, timestamp: datetime.datetime | None = None, image: str = None):
        title_ = None
        # 通知タイプ毎のカラー・タイトルの設定
        if notif_type == 'error':
            title_ = '❌ ' + CHARACTER_TEXT['on_error']
        elif notif_type == 'warning':
            title_ = '⚠️ ' + CHARACTER_TEXT['on_warning']

        # カスタムカラー・タイトルの設定
        color = custom_color or EMBED_COLOR[notif_type]
        title_ = title or title_
        
        # 基底クラスの初期化
        super().__init__(colour=color, color=color, title=title_, type=type, url=url, description=description, timestamp=timestamp)

        self.set_thumbnail(url=CHARACTER_ICON[custom_icon or notif_type])
        if image:
            self.set_image(url=image)