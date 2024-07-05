from .myembed import MyEmbed


EMBED_NOT_ADMINISTRATOR = MyEmbed(notif_type="error", description="管理者権限のない先生は実行できません.")
EMBED_DIRECT_MESSAGE = MyEmbed(notif_type="error", description="ダイレクトメッセージでは実行できません。")
EMBED_BOT_NOT_PERMITTED = MyEmbed(notif_type="error", description="私にこのコマンドを実行する権限がありません。")
EMBED_USER_NOT_PERMITTED = MyEmbed(notif_type="error", description="先生にこのコマンドを実行する権限がありません。")