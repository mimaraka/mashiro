import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import time
from typing import Dict

import modules.utils as utils
import modules.attachments as atc
from modules.myembed import MyEmbed
from modules.music.track import ytdl_create_tracks
from modules.music.player import Player
from modules.music.errors import *
from modules.attachments import find_valid_urls
from modules.mashilog import mashilog


EMBED_BOT_NOT_CONNECTED = MyEmbed(notification_type="error", description="私はボイスチャンネルに接続していません。")
EMBED_NOT_PLAYING = MyEmbed(notification_type="inactive", title="再生していません……。")
EMBED_QUEUE_EMPTY = MyEmbed(notification_type="error", description="再生キューが空です。")
EMBED_BOT_ANOTHER_VC = MyEmbed(notification_type="error", description="私は既に別のボイスチャンネルに接続しています。")
EMBED_AUTHOR_NOT_CONNECTED = MyEmbed(notification_type="error", description="先生がボイスチャンネルに接続されていないようです。")
EMBED_FAILED_TRACK_CREATION = MyEmbed(notification_type="error", description="トラックの生成に失敗しました。")


class Music(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot: commands.Bot = bot
        self.__player: Dict[int, Player] = {}
        self.__time_bot_only: Dict[int, float] = {}


    # マシロをプレーヤーとしてボイスチャンネルに接続させるときの共通処理
    async def connect(self, vc: discord.VoiceChannel):
        await vc.connect()
        # ここで処理が打ち切られることがたまにある(VCに接続はするがPlayerが作成されない)
        if not vc.guild.id in self.__player:
            self.__player[vc.guild.id] = Player(self.bot.loop, vc.guild.voice_client)
        mashilog("ボイスチャンネルに接続しました。")
        return self.__player[vc.guild.id]


    # マシロをボイスチャンネルから切断させるときの共通処理
    async def disconnect(self, guild: discord.Guild):
        if guild.id in self.__player:
            old_msg = self.__player[guild.id].controller_msg
            self.__player.pop(guild.id)
            try:
                if old_msg:
                    await old_msg.delete()
            except discord.errors.NotFound:
                pass
        await guild.voice_client.disconnect()
        mashilog("ボイスチャンネルから切断しました。")


    # メンバーのボイス状態が更新されたとき
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 自分自身のイベントの場合
        if member.id == self.bot.user.id:
            # 自分がボイスチャンネルに接続したとき
            if after.channel is not None and before.channel is None:
                # Playerが作成されていない場合は作成する
                if not member.guild.id in self.__player:
                    self.__player[member.guild.id] = Player(self.bot.loop, member.guild.voice_client)
            # 自分がボイスチャンネルから切断した/されたとき
            if after.channel is None and before.channel is not None:
                # まだPlayerが残っていれば削除する
                if member.guild.id in self.__player:
                    self.__player.pop(member.guild.id)
            return
        
        # マシロがボイスチャンネルに接続していない場合は無視する
        if member.guild.voice_client is None:
            return

        # マシロが現在接続しているボイスチャンネルでメンバーが抜けた場合
        if member.guild.voice_client.channel == before.channel and member.guild.voice_client.channel != after.channel:
            mashilog("私が接続しているボイスチャンネルから1人のメンバーが切断しました。")
            # 現在のボイスチャンネルにBotしかいないかどうか
            bot_only = all([m.bot for m in member.guild.voice_client.channel.members])

            # ボイスチャンネルにBotしかいない場合
            if bot_only:
                mashilog("現在、ボイスチャンネルはBotのみです。")
                # Unix時間を記録
                self.__time_bot_only[member.guild.id] = time.time()
                # 1分待つ
                await asyncio.sleep(60)
                # 1分後に
                # ・マシロがボイスチャンネルに接続しており
                # ・ボイスチャンネルにBotしかおらず
                # ・最後にボイスチャンネルがBotのみになってから1分が経過した場合
                if member.guild.voice_client is not None:
                    if member.guild.id in self.__time_bot_only:
                        if time.time() - self.__time_bot_only[member.guild.id] > 59:
                            # ボイスチャンネルから切断
                            await self.disconnect(member.guild)
        # マシロが現在接続しているボイスチャンネルにメンバーが入った場合
        elif member.guild.voice_client.channel != before.channel and member.guild.voice_client.channel == after.channel:
            mashilog("私が接続しているボイスチャンネルに1人のメンバーが接続しました。")
            # それまでボイスチャンネルにBotしかおらず、新たに入ったメンバーがBotでない場合
            if member.guild.id in self.__time_bot_only and not member.bot:
                # 辞書を削除
                self.__time_bot_only.pop(member.guild.id)

    
    # メッセージが削除されたとき
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        for player in self.__player.values():
            mashilog("プレイヤーメッセージが削除されました。")
            if player.controller_msg and message.id == player.controller_msg.id and not player.is_stopped:
                await player.regenerate_controller(message.channel)


    # /connect
    @app_commands.command(name="connect", description="ボイスチャンネルに接続します。")
    async def command_connect(self, inter: discord.Interaction):
        member = inter.guild.get_member(inter.user.id)
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if member.voice is None:
            await inter.response.send_message(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        # 既に接続している場合
        if inter.guild.voice_client and inter.guild.voice_client.is_connected():
            # コマンドを送ったメンバーと同じボイスチャンネルにいる場合
            if inter.guild.voice_client.channel == member.voice.channel:
                await inter.response.send_message(
                    embed=MyEmbed(notification_type="error", description="既に接続しています。"),
                    ephemeral=True
                )
            # 同じギルド内の他のボイスチャンネルに接続している場合
            else:
                await inter.response.send_message(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return

        # ボイスチャンネルに接続する
        player = await self.connect(member.voice.channel)
        await inter.response.send_message(
            embed=MyEmbed(title=f"接続しました！ (🔊 {utils.escape_markdown(member.voice.channel.name)})"),
            delete_after=10
        )
        # 0.5秒後にランダムにボイスを再生する
        await asyncio.sleep(0.5)
        await player.play_random_voice(inter, on_connect=True)


    # /disconnect
    @app_commands.command(name="disconnect", description="ボイスチャンネルから切断します。")
    async def command_disconnect(self, inter: discord.Interaction):
        key = inter.guild.id
        # Botがボイスチャンネルに居ない場合
        if inter.guild.voice_client is None or not inter.guild.voice_client.is_connected():
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        # time_bot_onlyの辞書が存在する場合、削除する
        if key in self.__time_bot_only:
            self.__time_bot_only.pop(key)

        await self.disconnect(inter.guild)
        await inter.response.send_message(embed=MyEmbed(title="切断しました。"), delete_after=10)
    
        
    # /play
    @app_commands.command(name="play", description="指定されたURLまたはキーワードの曲を再生します。")
    @app_commands.describe(text="再生したい曲のURL、またはYouTube上で検索するキーワード")
    @app_commands.rename(text="url-or-keyword")
    async def command_play(self, inter: discord.Interaction, text: str):
        author = inter.guild.get_member(inter.user.id)
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if author.voice is None:
            await inter.response.send_message(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(inter.guild.id) or await self.connect(author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if inter.guild.voice_client.channel != author.voice.channel:
            await inter.response.send_message(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return

        await inter.response.defer()
        tracks = await ytdl_create_tracks(self.bot.loop, text, author)
        if not tracks:
            await inter.followup.send(embed=EMBED_FAILED_TRACK_CREATION, ephemeral=True)
            return
        await player.register_tracks(inter, tracks)
        

    # /stop
    @app_commands.command(name="stop", description="トラックの再生を停止します。")
    async def command_stop(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.abort(clear=True)
            await inter.response.send_message(
                embed=MyEmbed(notification_type="inactive", title="再生を停止します。"),
                delete_after=10
            )
        except NotPlayingError:
            await inter.response.send_message(embed=EMBED_NOT_PLAYING, ephemeral=True)


    # /pause
    @app_commands.command(name="pause", description="トラックの再生を一時停止します。")
    async def command_pause(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return

        try:
            await player.pause()
            await inter.response.send_message(embed=MyEmbed(notification_type="inactive", title="一時停止しました。"), delete_after=10)
        except NotPlayingError:
            await inter.response.send_message(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await inter.response.send_message(
                embed=MyEmbed(notification_type="error", description=e),
                ephemeral=True
            )


    # /resume
    @app_commands.command(name="resume", description="トラックの再生を再開します。")
    async def command_resume(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.resume()
            await inter.response.send_message(embed=MyEmbed(title="再生を一再開しました。"), delete_after=10)
        except NotPlayingError:
            await inter.response.send_message(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await inter.response.send_message(
                embed=MyEmbed(notification_type="error", description=e),
                ephemeral=True
            )


    # /skip
    @app_commands.command(name="skip", description="再生中のトラックをスキップします。")
    async def command_skip(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        try:
            await player.skip()
        except NotPlayingError:
            await inter.response.send_message(embed=EMBED_NOT_PLAYING, ephemeral=True)


    # /clear
    @app_commands.command(name="clear", description="再生キューをクリアします。")
    async def command_clear(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if not player.queue:
            await inter.response.send_message(embed=EMBED_QUEUE_EMPTY, ephemeral=True)
        else:
            player.clear_queue()
            await inter.response.send_message(embed=MyEmbed(title="再生キューをクリアしました。"), delete_after=10)


    # /replay
    @app_commands.command(name="replay", description="再生中の、または最後に再生したトラックをリプレイします。")
    async def command_replay(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.replay()
        except PlayerError as e:
            await inter.response.send_message(
                embed=MyEmbed(notification_type="error", description=e)
            )

    
    # /repeat
    @app_commands.command(name="repeat", description="リピート再生の設定を変更します。")
    @app_commands.describe(option="リピート再生のオプション")
    @app_commands.choices(option=[
        app_commands.Choice(name="オフ", value=0),
        app_commands.Choice(name="プレイリスト", value=1),
        app_commands.Choice(name="トラック", value=2)
    ])
    async def command_repeat(self, inter: discord.Interaction, option: app_commands.Choice[int]):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        player.repeat = option.value
        await player.update_controller()
        await inter.response.send_message(
            embed=MyEmbed(title="リピート再生の設定を変更しました。", description=option.name),
            delete_after=10
        )

    
    # /volume
    @app_commands.command(name="volume", description="現在のボリュームを表示・変更します。")
    @app_commands.describe(volume="ボリューム(0～100)(指定なしで現在のボリュームを表示)")
    async def command_volume(self, inter: discord.Interaction, volume: int=None):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if volume is not None:
            title = "ボリュームを変更しました。"
            player.volume = volume / 100
        else:
            title = "現在のボリューム"
        new_volume = int(player.volume * 100)
        if new_volume < 10:
            volume_icon = "🔈"
        elif new_volume < 50:
            volume_icon = "🔉"
        else:
            volume_icon = "🔊"
        description = f"{volume_icon} **{new_volume}**\n🔈 0 {'-' * (new_volume // 2)}●{'-' * (50 - new_volume // 2)} 🔊 100"
        if not player.is_stopped and volume is not None:
            remark = " (次回再生時に適応されます)"
        else:
            remark = ""
        await inter.response.send_message(
            embed=MyEmbed(title=f"{title}{remark}", description=description),
            delete_after=10
        )


    # /queue
    @app_commands.command(name="queue", description="現在の再生キューを表示します。")
    async def command_queue(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        await inter.response.defer()
        await inter.followup.send(embed=player.get_queue_embed(), ephemeral=True)


    # /player
    @app_commands.command(name="player", description="プレイヤー操作メッセージを移動させます。")
    async def command_player(self, inter: discord.Interaction):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if player.is_stopped:
            await inter.response.send_message(embed=EMBED_NOT_PLAYING, ephemeral=True)
            return
        await player.regenerate_controller(inter.channel)
        await inter.response.send_message(embed=MyEmbed(title=f"プレイヤーを移動しました。"), delete_after=10)


    # /shuffle
    @app_commands.command(name="shuffle", description="シャッフル再生のオン/オフを変更します。")
    @app_commands.describe(onoff="シャッフル再生のオン/オフ(True/False)")
    @app_commands.rename(onoff="on-off")
    async def command_shuffle(self, inter: discord.Interaction, onoff: bool):
        player = self.__player.get(inter.guild.id)
        if player is None:
            await inter.response.send_message(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        player.shuffle = onoff
        
        await inter.response.send_message(
            embed=MyEmbed(title=f"🔀 シャッフル再生を{'オン' if onoff else 'オフ'}にしました。"),
            delete_after=10
        )


    # /play-channel
    @app_commands.command(name="play-channel", description="指定したチャンネルに貼られたリンクからトラックを取得し、プレイリストに追加します。")
    @app_commands.describe(channel="URLを検索するチャンネル")
    @app_commands.describe(n="検索するメッセージの件数(デフォルト: 20件)")
    async def command_play_channel(self, inter: discord.Interaction, channel: discord.TextChannel, n: int=20):
        author = inter.guild.get_member(inter.user.id)
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if author.voice is None:
            await inter.response.send_message(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(inter.guild.id) or await self.connect(author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if inter.guild.voice_client.channel != author.voice.channel:
            await inter.response.send_message(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        await inter.response.defer()
        msg_proc = await inter.channel.send(embed=MyEmbed(notification_type="inactive", title="⏳ 検索中です……。"))

        tasks = []
        async for message in channel.history(limit=n):
            tasks += [ytdl_create_tracks(self.bot.loop, url, author) for url in await find_valid_urls(message)]

        results = await asyncio.gather(*tasks)
        tracks = []
        for result in results:
            if result:
                tracks += result

        await msg_proc.delete()

        if not tracks:
            await inter.followup.send(
                embed=MyEmbed(notification_type="error", description="チャンネル内に有効なトラックが見つかりませんでした。"),
                ephemeral=True
            )
            return
        
        await player.register_tracks(inter, tracks)


    # /play-file
    @app_commands.command(name="play-file", description="添付したファイルの音声を再生します。")
    @app_commands.describe(attachment="再生する音声の添付ファイル(音声・動画)")
    async def command_play_file(self, inter: discord.Interaction, attachment: discord.Attachment):
        author = inter.guild.get_member(inter.user.id)
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if author.voice is None:
            await inter.response.send_message(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(inter.guild.id) or await self.connect(author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if inter.guild.voice_client.channel != author.voice.channel:
            await inter.response.send_message(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        # 添付ファイルの形式を調べる
        if not await atc.is_mimetype(attachment.url, atc.MIMETYPES_FFMPEG):
            await inter.response.send_message(
                embed=MyEmbed(notification_type="error", description="添付ファイルの形式が正しくありません。"),
                ephemeral=True
            )
            return
        
        await inter.response.defer()
        tracks = await ytdl_create_tracks(self.bot.loop, attachment.url, author)
        if not tracks:
            await inter.response.send_message(
                embed=MyEmbed(notification_type="error", description="トラックの生成に失敗しました。"),
                ephemeral=True
            )
            return
        await player.register_tracks(inter, tracks)


    # /voice
    @app_commands.command(name="voice", description="私の声が聞きたいのですか？")
    async def voice(self, inter: discord.Interaction):
        author = inter.guild.get_member(inter.user.id)
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if author.voice is None:
            await inter.response.send_message(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(inter.guild.id) or await self.connect(author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if inter.guild.voice_client.channel != author.voice.channel:
            await inter.response.send_message(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        await player.play_random_voice(inter)