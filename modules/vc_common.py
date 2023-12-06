from .myembed import MyEmbed


EMBED_BOT_NOT_CONNECTED = MyEmbed(notif_type="error", description="私はボイスチャンネルに接続していません。")
EMBED_AUTHOR_NOT_CONNECTED = MyEmbed(notif_type="error", description="先生がボイスチャンネルに接続されていないようです。")
EMBED_BOT_ANOTHER_VC = MyEmbed(notif_type="error", description="私は既に別のボイスチャンネルに接続しています。")
EMBED_NOT_PLAYING = MyEmbed(notif_type="inactive", title="再生していません……。")
EMBED_QUEUE_EMPTY = MyEmbed(notif_type="error", description="再生キューが空です。")
EMBED_FAILED_TO_CREATE_TRACKS = MyEmbed(notif_type="error", description="トラックの生成に失敗しました。")