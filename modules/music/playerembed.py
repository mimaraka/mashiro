import datetime
import typing
from modules.myembed import MyEmbed, NotificationType
from discord.types.embed import EmbedType


class PlayerEmbed(MyEmbed):
    def __init__(self, *, notification_type: NotificationType = "normal", custom_color: int | None = None, custom_icon: NotificationType | None = None, title: typing.Any | None = None, type: EmbedType = 'rich', url: typing.Any | None = None, description: typing.Any | None = None, timestamp: datetime.datetime | None = None, image: str = None):
        super().__init__(notification_type=notification_type, custom_color=custom_color, custom_icon=custom_icon, title=title, type=type, url=url, description=description, timestamp=timestamp, image=image)
        self.set_author(name="🎵 プレイヤー")