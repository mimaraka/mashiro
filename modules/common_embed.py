from .myembed import MyEmbed
from character_config import CHARACTER_TEXT


EMBED_NOT_ADMINISTRATOR = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_author_not_admin'])
EMBED_GUILD_ONLY = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_guild_only'])
EMBED_BOT_NOT_PERMITTED = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_bot_not_permitted'])
EMBED_USER_NOT_PERMITTED = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_author_not_permitted'])
EMBED_BOT_NOT_CONNECTED = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_bot_not_connected'])
EMBED_AUTHOR_NOT_CONNECTED = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_author_not_connected'])
EMBED_BOT_ANOTHER_VC = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_bot_another_vc'])
EMBED_NOT_PLAYING = MyEmbed(notif_type='inactive', title=CHARACTER_TEXT['not_playing'])
EMBED_QUEUE_EMPTY = MyEmbed(notif_type='error', description=CHARACTER_TEXT['queue_empty'])
EMBED_FAILED_TO_CREATE_TRACKS = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_failed_to_create_tracks'])