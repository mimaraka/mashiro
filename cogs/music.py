import asyncio
import discord
import re
import time
from typing import Dict
from youtubesearchpython import VideosSearch

import constants as const
import modules.utils as utils
from modules.attachments import MIMETYPES_FFMPEG
from modules.myembed import MyEmbed
from modules.music.track.track import create_tracks, YTDLTrack
from modules.music.player import Player
from modules.music.errors import *
from modules.attachments import find_valid_urls
from modules.mashilog import mashilog
from modules.http import get_mimetype


EMBED_BOT_NOT_CONNECTED = MyEmbed(notif_type="error", description="私はボイスチャンネルに接続していません。")
EMBED_NOT_PLAYING = MyEmbed(notif_type="inactive", title="再生していません……。")
EMBED_QUEUE_EMPTY = MyEmbed(notif_type="error", description="再生キューが空です。")
EMBED_BOT_ANOTHER_VC = MyEmbed(notif_type="error", description="私は既に別のボイスチャンネルに接続しています。")
EMBED_AUTHOR_NOT_CONNECTED = MyEmbed(notif_type="error", description="先生がボイスチャンネルに接続されていないようです。")
EMBED_FAILED_TRACK_CREATION = MyEmbed(notif_type="error", description="トラックの生成に失敗しました。")


async def yt_title_autocomplete(ctx: discord.AutocompleteContext):
    if not ctx.value:
        return []
    search_result = await ctx.bot.loop.run_in_executor(
        None, lambda: VideosSearch(ctx.value, limit=6)
    )
    return [info.get("title") for info in search_result.result().get("result")]


class Music(discord.Cog):
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot
        self.__player: Dict[int, Player] = {}
        self.__time_bot_only: Dict[int, float] = {}


    # マシロをプレーヤーとしてボイスチャンネルに接続させるときの共通処理
    async def connect(self, vc: discord.VoiceChannel):
        await vc.connect()
        self.__player[vc.guild.id] = Player(self.bot.loop, vc.guild.voice_client)
        mashilog("ボイスチャンネルに正常に接続しました。")
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
        mashilog("ボイスチャンネルから正常に切断しました。")


    # 処理中のEmbedを取得
    def get_proc_embed(self, channel: discord.TextChannel, prefix=""):
        external_emojis = channel.permissions_for(channel.guild.me).external_emojis
        if external_emojis:
            emoji = str(self.bot.get_emoji(const.EMOJI_ID_LOADING))
        else:
            emoji = "⌛"
        embed=MyEmbed(notif_type="inactive", title=f"{emoji} {prefix}処理中です……。")
        return embed


    # メンバーのボイス状態が更新されたとき
    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 自分自身のイベントの場合
        if member.id == self.bot.user.id:
            # 自分がボイスチャンネルに接続したとき
            if after.channel is not None and before.channel is None:
                mashilog(f"ボイスチャンネルに接続しました。", guild=member.guild, channel=after.channel)
                # 1秒経ってもPlayerが作成されていない場合は作成する
                await asyncio.sleep(1)
                if not member.guild.id in self.__player:
                    self.__player[member.guild.id] = Player(self.bot.loop, member.guild.voice_client)
                    mashilog("playerオブジェクトが作成されていないため、作成しました。")
            # 自分がボイスチャンネルから切断した/されたとき
            if after.channel is None and before.channel is not None:
                mashilog(f"ボイスチャンネルから切断しました。", guild=member.guild, channel=before.channel)
                # 5秒経ってまだPlayerが残っていれば削除する
                await asyncio.sleep(5)
                if not member.guild.voice_client or not member.guild.voice_client.is_connected():
                    if member.guild.id in self.__player:
                        self.__player.pop(member.guild.id)
                        mashilog("playerオブジェクトが残っていたため、削除しました。")
            return
        
        # マシロがボイスチャンネルに接続していない場合は無視する
        if member.guild.voice_client is None:
            return

        # マシロが現在接続しているボイスチャンネルでメンバーが抜けた場合
        if member.guild.voice_client.channel == before.channel and member.guild.voice_client.channel != after.channel:
            mashilog(f"ボイスチャンネルから1人のメンバーが切断しました。", guild=member.guild, channel=before.channel)
            # 現在のボイスチャンネルにBotしかいないかどうか
            bot_only = all([m.bot for m in member.guild.voice_client.channel.members])

            # ボイスチャンネルにBotしかいない場合
            if bot_only:
                mashilog(f"現在、ボイスチャンネルはBotのみです。", guild=member.guild, channel=before.channel)
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
            mashilog(f"ボイスチャンネルに1人のメンバーが接続しました。", guild=member.guild, channel=after.channel)
            # それまでボイスチャンネルにBotしかおらず、新たに入ったメンバーがBotでない場合
            if member.guild.id in self.__time_bot_only and not member.bot:
                # 辞書を削除
                self.__time_bot_only.pop(member.guild.id)

    
    # メッセージが削除されたとき
    @discord.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        for player in self.__player.values():
            if player.controller_msg and message.id == player.controller_msg.id and not player.is_stopped:
                mashilog(f"プレイヤーメッセージが削除されました。再生成します。", guild=message.guild)
                await player.regenerate_controller(message.channel)


    # /connect
    @discord.slash_command(name="connect", description="ボイスチャンネルに接続します。")
    async def command_connect(self, ctx: discord.ApplicationContext):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        # 既に接続している場合
        if ctx.voice_client and ctx.voice_client.is_connected():
            # コマンドを送ったメンバーと同じボイスチャンネルにいる場合
            if ctx.voice_client.channel == ctx.author.voice.channel:
                await ctx.respond(
                    embed=MyEmbed(notif_type="error", description="既に接続しています。"),
                    ephemeral=True
                )
            # 同じギルド内の他のボイスチャンネルに接続している場合
            else:
                await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return

        # ボイスチャンネルに接続する
        player = await self.connect(ctx.author.voice.channel)
        await ctx.respond(
            embed=MyEmbed(notif_type="succeed", title=f"接続しました！ (🔊 {utils.escape_markdown(ctx.author.voice.channel.name)})"),
            delete_after=10
        )
        # 0.5秒後にランダムにボイスを再生する
        await asyncio.sleep(0.5)
        await player.play_random_voice(ctx, on_connect=True)


    # /disconnect
    @discord.slash_command(name="disconnect", description="ボイスチャンネルから切断します。")
    async def command_disconnect(self, ctx: discord.ApplicationContext):
        key = ctx.guild.id
        # Botがボイスチャンネルに居ない場合
        if ctx.voice_client is None or not ctx.voice_client.is_connected():
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        # time_bot_onlyの辞書が存在する場合、削除する
        if key in self.__time_bot_only:
            self.__time_bot_only.pop(key)

        await self.disconnect(ctx.guild)
        await ctx.respond(embed=MyEmbed(title="切断しました。"), delete_after=10)
    
        
    # /play
    @discord.slash_command(name="play", description="指定されたURLまたはキーワードの曲を再生します。")
    @discord.option(
        parameter_name="text",
        name="input",
        description="再生したい曲のURL、またはYouTube上で検索するタイトル",
        autocomplete=yt_title_autocomplete
    )
    @discord.option("interrupt", description="キューを無視して割り込み再生をさせるかどうか", required=False, default=False)
    async def command_play(self, ctx: discord.ApplicationContext, text: str, interrupt: bool):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(ctx.guild.id) or await self.connect(ctx.author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return

        inter = await ctx.respond(embed=self.get_proc_embed(ctx.channel))
        msg_proc = await inter.original_response()

        tracks = await create_tracks(self.bot.loop, text, ctx.author)
        if not tracks:
            await msg_proc.delete()
            await ctx.respond(embed=EMBED_FAILED_TRACK_CREATION, ephemeral=True)
            return
        await player.register_tracks(ctx, tracks, msg_proc=msg_proc, interrupt=interrupt)
        

    # /stop
    @discord.slash_command(name="stop", description="トラックの再生を停止します。")
    async def command_stop(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.abort(clear=True)
            await ctx.respond(
                embed=MyEmbed(notif_type="inactive", title="再生を停止します。"),
                delete_after=10
            )
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)


    # /pause
    @discord.slash_command(name="pause", description="トラックの再生を一時停止します。")
    async def command_pause(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return

        try:
            await player.pause()
            await ctx.respond(embed=MyEmbed(notif_type="inactive", title="一時停止しました。"), delete_after=10)
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description=e),
                ephemeral=True
            )


    # /resume
    @discord.slash_command(name="resume", description="トラックの再生を再開します。")
    async def command_resume(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.resume()
            await ctx.respond(embed=MyEmbed(title="再生を一再開しました。"), delete_after=10)
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description=e),
                ephemeral=True
            )


    # /skip
    @discord.slash_command(name="skip", description="再生中のトラックをスキップします。")
    async def command_skip(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        try:
            player.skip()
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
        await ctx.respond(embed=MyEmbed(title="⏭️ 再生中の曲をスキップしました。"), delete_after=10)


    # /clear
    @discord.slash_command(name="clear", description="再生キューをクリアします。")
    async def command_clear(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if not player.queue:
            await ctx.respond(embed=EMBED_QUEUE_EMPTY, ephemeral=True)
        else:
            player.clear_queue()
            player.update_controller()
            await ctx.respond(embed=MyEmbed(title="再生キューをクリアしました。"), delete_after=10)


    # /replay
    @discord.slash_command(name="replay", description="再生中の、または最後に再生したトラックをリプレイします。")
    async def command_replay(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        try:
            await player.replay()
            await ctx.respond(embed=MyEmbed(notif_type="succeed", title="🔄 リプレイを開始しました！"), delete_after=10)
        except PlayerError as e:
            await ctx.respond(embed=MyEmbed(notif_type="error", description=e), ephemeral=True)

    
    # /repeat
    @discord.slash_command(name="repeat", description="リピート再生の設定を変更します。")
    @discord.option("option", description="リピート再生のオプション", choices=["オフ", "プレイリスト", "トラック"], required=False)
    async def command_repeat(self, ctx: discord.ApplicationContext, option: str=None): 
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        ICON = "🔁"
        
        if option is None:
            if player.repeat == 1:
                description = "プレイリスト"
            elif player.repeat == 2:
                description = "トラック"
            else:
                description = "オフ"
            embed = MyEmbed(title=f"{ICON} 現在のリピート再生の設定", description=description)
        else:
            if option == "プレイリスト":
                player.repeat = 1
            elif option == "トラック":
                player.repeat = 2
            else:
                player.repeat = 0
            embed = MyEmbed(notif_type="succeed", title=f"{ICON} リピート再生の設定を変更しました。", description=option)
            await player.update_controller()
        await ctx.respond(embed=embed, delete_after=10)

    
    # /volume
    @discord.slash_command(name="volume", description="現在のボリュームを表示・変更します。")
    @discord.option("volume", description="ボリューム(0～100)(指定なしで現在のボリュームを表示)", max_value=100, min_value=0, required=False)
    async def command_volume(self, ctx: discord.ApplicationContext, volume: int=None):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if volume is not None:
            title = "🔊 ボリュームを変更しました。"
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
        await ctx.respond(
            embed=MyEmbed(notif_type="succeed", title=f"{title}{remark}", description=description),
            delete_after=10
        )


    # /queue
    @discord.slash_command(name="queue", description="現在の再生キューを表示します。")
    async def command_queue(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        await ctx.defer(ephemeral=True)
        await ctx.respond(ephemeral=True, **player.get_queue_msg(page=1))


    # /player
    @discord.slash_command(name="player", description="プレイヤー操作メッセージを移動させます。")
    async def command_player(self, ctx: discord.ApplicationContext):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        if player.is_stopped:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
            return
        await player.regenerate_controller(ctx.channel)
        await ctx.respond(embed=MyEmbed(notif_type="succeed", title=f"プレイヤーを移動しました。"), delete_after=10)


    # /shuffle
    @discord.slash_command(name="shuffle", description="シャッフル再生のオン/オフを変更します。")
    @discord.option("switch", description="シャッフル再生のオン/オフ(True/False)。シャッフル再生がオンで、この引数を省略した場合、再生キューが再度シャッフルされます。", required=False)
    async def command_shuffle(self, ctx: discord.ApplicationContext, switch: bool=None):
        if (player := self.__player.get(ctx.guild.id)) is None:
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        ICON = "🔀"

        if switch is None:
            player.shuffle = player.shuffle
            if player.shuffle:
                embed=MyEmbed(title=f"{ICON} 再生キューをシャッフルしました。")
                await player.update_controller()
            else:
                embed=MyEmbed(title=f"{ICON} シャッフル再生はオフです。")
        else:
            player.shuffle = switch
            embed=MyEmbed(notif_type="succeed", title=f"{ICON} シャッフル再生を{'オン' if switch else 'オフ'}にしました。")
            await player.update_controller()

        await ctx.respond(embed=embed, delete_after=10)


    # /play-channel
    @discord.slash_command(name="play-channel", description="指定したチャンネルに貼られたリンクからトラックを取得し、プレイリストに追加します。")
    @discord.option("channel", description="URLを検索するチャンネル", required=False, default=None)
    @discord.option("channel_url", description="URLを検索するチャンネルのリンク(私が所属している全てのサーバーのチャンネルをURLから参照できます)。", required=False, default=None)
    @discord.option("n", description="検索するメッセージの件数(デフォルト: 20件)", min_value=1, default=20, required=False)
    async def command_play_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, channel_url: str, n: int):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        if channel is None and channel_url is None:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="`channel`と`channel_url`のいずれか一方を必ず指定してください。"), ephemeral=True)
            return
        elif channel_url is not None:
            if not re.fullmatch(r"https?://discord.com/channels/\d+/\d+", channel_url):
                await ctx.respond(embed=MyEmbed(notif_type="error", description="チャンネルのURLの形式が正しくありません。"), ephemeral=True)
                return
            c = self.bot.get_channel(int(channel_url.split("/")[-1]))
            if c is None:
                await ctx.respond(embed=MyEmbed(notif_type="error", description="指定されたURLからのチャンネルの取得に失敗しました。"), ephemeral=True)
                return
            else:
                search_channel = c
        else:
            search_channel = channel

        player = self.__player.get(ctx.guild.id) or await self.connect(ctx.author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        embed = MyEmbed(notif_type="inactive", title="🔎 1. 検索中です……。")
        inter = await ctx.respond(embed=embed)
        msg_proc = await inter.original_response()

        # await asyncio.gather()で同時処理しようとすると重すぎて(通信量が多すぎて？)再生が途切れ途切れになってしまう

        tracks = []
        message_count = 1
        async for message in search_channel.history(limit=n):
            for url in await find_valid_urls(message):
                if response := await create_tracks(self.bot.loop, url, ctx.author):
                    description = f"メッセージ : **{message_count}** / {n}\n\n"
                    description += player.tracks_text(response, start_index=len(tracks) + 1)
                    embed.description = description
                    tracks += response
                    await msg_proc.edit(embed=embed)
            message_count += 1
        del message_count

        if not tracks:
            await msg_proc.delete()
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description="チャンネル内に有効なトラックが見つかりませんでした。"),
                ephemeral=True
            )
            return
        
        await msg_proc.edit(embed=self.get_proc_embed(ctx.channel, prefix="2. "))
        await player.register_tracks(ctx, tracks, msg_proc=msg_proc)


    # /play-file
    @discord.slash_command(name="play-file", description="添付したファイルの音声を再生します。")
    @discord.option("attachment", description="再生する音声の添付ファイル(音声・動画)")
    async def command_play_file(self, ctx: discord.ApplicationContext, attachment: discord.Attachment):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(ctx.guild.id) or await self.connect(ctx.author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        # 添付ファイルの形式を調べる
        if await get_mimetype(attachment.url) not in MIMETYPES_FFMPEG:
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description="添付ファイルの形式が正しくありません。"),
                ephemeral=True
            )
            return
        
        inter = await ctx.respond(embed=self.get_proc_embed(ctx.channel))
        msg_proc = await inter.original_response()

        tracks = await create_tracks(self.bot.loop, attachment.url, ctx.author)
        if not tracks:
            await msg_proc.delete()
            await ctx.respond(
                embed=MyEmbed(notif_type="error", description="トラックの生成に失敗しました。"),
                ephemeral=True
            )
            return
        await player.register_tracks(ctx, tracks, msg_proc=msg_proc)


    # /search
    @discord.slash_command(name="search", description="YouTubeの検索結果を再生します。")
    @discord.option("keyword", description="検索語句")
    @discord.option("limit", description="検索する動画の最大件数(デフォルト: 10件)", required=False, default=10)
    async def command_search(self, ctx: discord.ApplicationContext, keyword: str, limit: int):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(ctx.guild.id) or await self.connect(ctx.author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        inter = await ctx.respond(embed=self.get_proc_embed(ctx.channel))
        msg_proc = await inter.original_response()
        
        search_result = await self.bot.loop.run_in_executor(
            None, lambda: VideosSearch(keyword, limit=limit)
        )
        videos = search_result.result().get("result")
        
        tracks = []
        for video in videos:
            tracks += await create_tracks(self.bot.loop, video.get("link"), ctx.author)

        if not tracks:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="検索結果がありませんでした。"), ephemeral=True)
            return
        await player.register_tracks(ctx, tracks, msg_proc=msg_proc)
        


    # /voice
    @discord.slash_command(name="voice", description="私の声が聞きたいのですか？")
    async def command_voice(self, ctx: discord.ApplicationContext):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = self.__player.get(ctx.guild.id) or await self.connect(ctx.author.voice.channel)
        # コマンドを送ったメンバーとは別のボイスチャンネルに接続している場合
        if ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.respond(embed=EMBED_BOT_ANOTHER_VC, ephemeral=True)
            return
        
        inter = await ctx.respond(embed=self.get_proc_embed(ctx.channel))
        msg_proc = await inter.original_response()
        
        await player.play_random_voice(ctx, msg_proc=msg_proc)