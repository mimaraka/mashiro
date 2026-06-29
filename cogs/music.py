import asyncio
import discord
import random
import re
import time
from typing import Dict, List

import constants as const
import modules.util as util
from character_config import CHARACTER_TEXT
from modules.myembed import MyEmbed
from modules.music.track.track import create_tracks
from modules.music.player import Player
from modules.music.errors import *
from modules.attachments import find_valid_urls
from modules.mylog import mylog
from modules.http import get_mimetype
from modules.common_embed import *


async def autocomp_yt_title(ctx: discord.AutocompleteContext):
    return [info.get('title') for info in await util.search_youtube(ctx.bot.loop, ctx.value)]


class CogMusic(discord.Cog):
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot
        self.__player: Dict[int, Player] = {}
        self.__time_bot_only: Dict[int, float] = {}


    # 自身をプレーヤーとしてボイスチャンネルに接続させるときの共通処理
    async def connect(self, vc: discord.VoiceChannel, player: Player=None):
        try:
            await vc.connect()
        # 手動切断後しばらくはVCへの接続ができない場合がある
        except discord.ClientException:
            return None
        self.__player[vc.guild.id] = player or Player(self.bot.loop, vc.guild.voice_client)
        mylog('ボイスチャンネルに正常に接続しました。')
        return self.__player[vc.guild.id]


    # 自身をボイスチャンネルから切断させるときの共通処理
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
        mylog('ボイスチャンネルから正常に切断しました。')


    # 指定したボイスチャンネルにBotしかいないかどうか
    def vc_is_bot_only(self, vc: discord.VoiceChannel | discord.StageChannel):
        return all([m.bot for m in vc.members])
    

    # Guildに紐づけられたPlayerオブジェクトを取得する
    async def get_player(self, guild: discord.Guild, *, ctx: discord.ApplicationContext | None=None, channel: discord.TextChannel | None=None, vc: discord.VoiceChannel | discord.StageChannel | None=None):
        # Guildに紐づけられたPlayerオブジェクトが既に存在すればそれを取得する
        player = self.__player.get(guild.id)

        # Playerオブジェクトが存在しない場合
        if player is None:
            # 自動接続先が指定されていない場合
            if vc is None:
                if ctx:
                    await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
                elif channel:
                    await channel.send(embed=EMBED_BOT_NOT_CONNECTED)
                return None
            player = await self.connect(vc)
            if player is None:
                embed = MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_failed_to_connect_vc'])
                if ctx:
                    await ctx.respond(embed=embed, ephemeral=True)
                elif channel:
                    await channel.send(embed=embed)
                return None
        else:
            # 自動接続先とは異なるVCのPlayerが既に存在する場合
            if vc is not None and player.vc != vc:
                embed = EMBED_BOT_ANOTHER_VC
                if ctx:
                    await ctx.respond(embed=embed, ephemeral=True)
                elif channel:
                    await channel.send(embed=embed)
                return None

        return player


    # 処理中のEmbedを取得
    def get_loading_embed(self, channel: discord.TextChannel, prefix=''):
        external_emojis = channel.permissions_for(channel.guild.me).external_emojis
        if external_emojis:
            emoji = str(self.bot.get_emoji(const.EMOJI_ID_LOADING))
        else:
            emoji = '⌛'
        embed = MyEmbed(
            notif_type='inactive',
            title=f'{emoji} {prefix}{CHARACTER_TEXT["processing"]}',
            description=CHARACTER_TEXT['hang_on']
        )
        return embed


    # メンバーのボイス状態が更新されたとき
    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 自分自身のイベントの場合
        if member.id == self.bot.user.id:
            # 自分がボイスチャンネルに接続したとき
            if after.channel is not None and before.channel is None:
                mylog('ボイスチャンネルに接続しました。', guild=member.guild, channel=after.channel)
                # time_bot_onlyの辞書があれば削除
                if member.guild.id in self.__time_bot_only:
                    self.__time_bot_only.pop(member.guild.id)
                # 1秒経ってもPlayerが作成されていない場合は作成する
                await asyncio.sleep(1)
                if not member.guild.id in self.__player:
                    self.__player[member.guild.id] = Player(self.bot.loop, member.guild.voice_client)
                    mylog('playerオブジェクトが作成されていないため、作成しました。')
            # 自分がボイスチャンネルから切断した/されたとき
            if after.channel is None and before.channel is not None:
                mylog('ボイスチャンネルから切断しました。', guild=member.guild, channel=before.channel)

                # Playerオブジェクトが消去されておらず、3秒経っても再接続されない場合は手動での再接続を試みる
                await asyncio.sleep(3)
                if not member.guild.voice_client or not member.guild.voice_client.is_connected():
                    if member.guild.id in self.__player:
                        if player := await self.connect(before.channel, player=self.__player[member.guild.id]):
                            mylog('ボイスチャンネルに再接続しました。')
                            if player.is_playing:
                                await player.pause()
                                await asyncio.sleep(1)
                                await player.resume()
                        else:
                            await self.__player.get(member.guild.id).delete_controller()
                            self.__player.pop(member.guild.id)
                            mylog('playerオブジェクトが残っていたため、削除しました。')
            return
        
        # 自身がボイスチャンネルに接続していない場合は無視する
        if member.guild.voice_client is None:
            return

        # 自身が現在接続しているボイスチャンネルでメンバーが抜けた場合
        if member.guild.voice_client.channel == before.channel and member.guild.voice_client.channel != after.channel:
            mylog('ボイスチャンネルから1人のメンバーが切断しました。', guild=member.guild, channel=before.channel)

            # ボイスチャンネルにBotしかいない場合
            if self.vc_is_bot_only(member.guild.voice_client.channel):
                # メンバーが別のボイスチャンネルに移動した場合は、ついて行く
                if after.channel is not None:
                    await member.guild.voice_client.move_to(after.channel)
                    player = await self.get_player(member.guild)
                    if player.is_playing:
                        await player.pause()
                        await asyncio.sleep(1)
                        await player.resume()
                    else:
                        await player.update_controller()
                else:
                    mylog('現在、ボイスチャンネルはBotのみです。', guild=member.guild, channel=before.channel)
                    # Unix時間を記録
                    self.__time_bot_only[member.guild.id] = time.time()
                    # 1分待つ
                    await asyncio.sleep(60)
                    # 1分後に
                    # ・自身がボイスチャンネルに接続しており
                    # ・ボイスチャンネルにBotしかおらず
                    # ・最後にボイスチャンネルがBotのみになってから1分が経過した場合
                    if member.guild.voice_client is not None:
                        if member.guild.id in self.__time_bot_only:
                            if time.time() - self.__time_bot_only[member.guild.id] > 59:
                                # ボイスチャンネルから切断
                                await self.disconnect(member.guild)
        # 自身が現在接続しているボイスチャンネルにメンバーが入った場合
        elif member.guild.voice_client.channel != before.channel and member.guild.voice_client.channel == after.channel:
            mylog('ボイスチャンネルに1人のメンバーが接続しました。', guild=member.guild, channel=after.channel)
            # それまでボイスチャンネルにBotしかおらず、新たに入ったメンバーがBotでない場合
            if member.guild.id in self.__time_bot_only and not member.bot:
                # 辞書を削除
                self.__time_bot_only.pop(member.guild.id)

    
    # メッセージが削除されたとき
    @discord.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        for player in self.__player.values():
            if player.controller_msg and message.id == player.controller_msg.id and not player.is_stopped:
                mylog('プレイヤーメッセージが削除されました。再生成します。', guild=message.guild)
                await player.regenerate_controller(message.channel)


    # /connect
    @discord.slash_command(**util.make_command_args('connect'))
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
                    embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_already_connected']),
                    ephemeral=True
                )
            return

        # ボイスチャンネルに接続する
        player = await self.get_player(ctx.guild, ctx=ctx, vc=ctx.author.voice.channel)
        if not player:
            return
        await ctx.respond(
            embed=MyEmbed(notif_type='succeeded', title=f'{CHARACTER_TEXT["on_connect"]} (🔊 {util.escape_markdown(ctx.author.voice.channel.name)})'),
            delete_after=10
        )
        # 0.5秒後にランダムにボイスを再生する
        await asyncio.sleep(0.5)
        await player.play_random_voice(ctx, on_connect=True)


    # /disconnect
    @discord.slash_command(**util.make_command_args('disconnect'))
    async def command_disconnect(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return

        key = ctx.guild.id
        # Botがボイスチャンネルに居ない場合
        if ctx.voice_client is None or not ctx.voice_client.is_connected():
            await ctx.respond(embed=EMBED_BOT_NOT_CONNECTED, ephemeral=True)
            return
        
        # time_bot_onlyの辞書が存在する場合、削除する
        if key in self.__time_bot_only:
            self.__time_bot_only.pop(key)

        await self.disconnect(ctx.guild)
        await ctx.respond(embed=MyEmbed(title=CHARACTER_TEXT['on_disconnect']), delete_after=10)


    async def play(
        self,
        channel: discord.TextChannel,
        member: discord.Member,
        queries: List[str],
        ctx: discord.ApplicationContext | None=None,
        interrupt: bool=False,
        silent: bool=False
    ):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if member.voice is None:
            if ctx:
                await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            else:
                await channel.send(embed=EMBED_AUTHOR_NOT_CONNECTED)
            return
        
        player = await self.get_player(channel.guild, ctx=ctx, channel=channel, vc=member.voice.channel)
        if not player:
            return

        if not silent:
            if ctx:
                inter = await ctx.respond(embed=self.get_loading_embed(channel))
                msg_loading = await inter.original_response()
            else:
                msg_loading = await channel.send(embed=self.get_loading_embed(channel))
        else:
            msg_loading = None

        tracks = []
        for query in queries:
            if result := await create_tracks(self.bot.loop, query, member):
                tracks += result

        if not tracks:
            if msg_loading:
                await msg_loading.delete()
            if ctx:
                await ctx.respond(embed=EMBED_FAILED_TO_CREATE_TRACKS, ephemeral=True)
            else:
                await channel.send(embed=EMBED_FAILED_TO_CREATE_TRACKS)
            return
        await player.register_tracks(channel, tracks, ctx=ctx, msg_loading=msg_loading, interrupt=interrupt, silent=silent)
    
        
    # /play
    @discord.slash_command(**util.make_command_args('play'))
    @discord.option('query', description='再生したい曲のURL、またはYouTube上で検索するタイトル', autocomplete=autocomp_yt_title)
    @discord.option('interrupt', description='キューを無視して割り込み再生をします', required=False, default=False)
    async def command_play(self, ctx: discord.ApplicationContext, query: str, interrupt: bool):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return

        await self.play(ctx.channel, ctx.author, [query], ctx=ctx, interrupt=interrupt)


    # メッセージコマンド(再生する)
    @discord.message_command(name='再生する')
    async def message_command_play(self, ctx: discord.ApplicationContext, message: discord.Message):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return

        if message.attachments:
            queries = [a.url for a in message.attachments]
            await self.play(ctx.channel, ctx.author, queries, ctx=ctx)
        elif message.clean_content:
            # メッセージにURLが含まれる場合は抽出
            queries = re.findall(const.RE_PATTERN_URL, message.clean_content) or [message.clean_content]
            await self.play(ctx.channel, ctx.author, queries, ctx=ctx)
        else:
            await ctx.respond(embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_no_text_or_attachment']), ephemeral=True)
            return


    # /search
    @discord.slash_command(**util.make_command_args('search'))
    @discord.option('keyword', description='検索語句')
    @discord.option('limit', description='検索する動画の最大件数(デフォルト: 20件)', required=False, default=20)
    async def command_search(self, ctx: discord.ApplicationContext, keyword: str, limit: int):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = await self.get_player(ctx.guild, ctx=ctx, vc=ctx.author.voice.channel)
        if not player:
            return
        
        inter = await ctx.respond(embed=self.get_loading_embed(ctx.channel))
        msg_loading = await inter.original_response()

        videos = await util.search_youtube(self.bot.loop, keyword, limit)
        
        tracks = []
        for video in videos:
            tracks += await create_tracks(self.bot.loop, video.get('url'), ctx.author)

        if not tracks:
            await msg_loading.delete()
            await ctx.respond(embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_no_search_results']), ephemeral=True)
            return
        await player.register_tracks(ctx.channel, tracks, ctx=ctx, msg_loading=msg_loading)


    # /play-channel
    @discord.slash_command(**util.make_command_args('play-channel'))
    @discord.option('channel', description='トラックを検索するチャンネル', default=None)
    @discord.option('channel_url', description='トラックを検索するチャンネルのURL (私が所属している全てのサーバーのチャンネルをURLから参照できます)', default=None)
    @discord.option('n', description='検索するメッセージの件数 (デフォルト: 20件)', min_value=1, default=20)
    @discord.option('immediately', description='トラックを取得し次第、逐次再生・キューに追加します', default=True)
    @discord.option('order', description='再生キューに追加するトラックの順番 ("immediately"がTrueの場合、"ランダム"は使用できません)', choices=['新しい順', '古い順', 'ランダム'], default=None)
    async def command_play_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel, channel_url: str, n: int, immediately: bool, order: str):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        if channel is None and channel_url is None:
            await ctx.respond(embed=MyEmbed(notif_type='error', description='`channel`と`channel_url`のいずれか一方を必ず指定してください。'), ephemeral=True)
            return
        elif channel_url is not None:
            if not re.fullmatch(r'https?://discord.com/channels/\d+/\d+', channel_url):
                await ctx.respond(embed=MyEmbed(notif_type='error', description='チャンネルのURLの形式が正しくありません。'), ephemeral=True)
                return
            c = self.bot.get_channel(int(channel_url.split('/')[-1]))
            if c is None:
                await ctx.respond(embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_failed_to_fetch_channel_from_url']), ephemeral=True)
                return
            else:
                search_channel = c
        else:
            search_channel = channel

        player = await self.get_player(ctx.guild, ctx=ctx, vc=ctx.author.voice.channel)
        if not player:
            return
        
        embed = MyEmbed(notif_type='inactive', title=f'🔎 1. {CHARACTER_TEXT["searching"]}')
        inter = await ctx.respond(embed=embed)
        msg_loading = await inter.original_response()

        # await asyncio.gather()で同時処理しようとすると重すぎて(通信量が多すぎて？)再生が途切れ途切れになってしまう

        tracks = []
        message_count = 1
        async for message in search_channel.history(limit=n, oldest_first=order == '古い順'):
            for url in await find_valid_urls(message):
                if response := await create_tracks(self.bot.loop, url, ctx.author):
                    if immediately:
                        await player.register_tracks(ctx.channel, response, ctx=ctx, silent=player.queue or player.is_playing)
                    description = f'メッセージ : **{message_count}** / {n}\n\n'
                    description += player.tracks_text(response, start_index=len(tracks) + 1)
                    embed.description = description
                    await msg_loading.edit(embed=embed)
                    tracks += response
            message_count += 1
        del message_count

        if not tracks:
            await msg_loading.delete()
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description=CHARACTER_TEXT['error_no_valid_tracks']),
                ephemeral=True
            )
            return
        
        if immediately:
            await msg_loading.delete()
        else:
            if order == 'ランダム':
                random.shuffle(tracks)

            await msg_loading.edit(embed=self.get_loading_embed(ctx.channel, prefix='2. '))
            await player.register_tracks(ctx.channel, tracks, ctx=ctx, msg_loading=msg_loading)


    # /play-file
    @discord.slash_command(**util.make_command_args('play-file'))
    @discord.option('attachment', description='再生する音声の添付ファイル (音声・動画)')
    async def command_play_file(self, ctx: discord.ApplicationContext, attachment: discord.Attachment):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = await self.get_player(ctx.guild, ctx=ctx, vc=ctx.author.voice.channel)
        if not player:
            return
        
        # 添付ファイルの形式を調べる
        if await get_mimetype(attachment.url) not in const.MIMETYPES_FFMPEG:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description='添付ファイルの形式が正しくありません。'),
                ephemeral=True
            )
            return
        
        inter = await ctx.respond(embed=self.get_loading_embed(ctx.channel))
        msg_loading = await inter.original_response()

        tracks = await create_tracks(self.bot.loop, attachment.url, ctx.author)
        if not tracks:
            await msg_loading.delete()
            await ctx.respond(embed=EMBED_FAILED_TO_CREATE_TRACKS, ephemeral=True)
            return
        await player.register_tracks(ctx.channel, tracks, ctx=ctx, msg_loading=msg_loading)
        

    # /voice
    @discord.slash_command(**util.make_command_args('voice'))
    async def command_voice(self, ctx: discord.ApplicationContext):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return

        player = await self.get_player(ctx.guild, ctx=ctx, vc=ctx.author.voice.channel)
        if not player:
            return
        
        inter = await ctx.respond(embed=self.get_loading_embed(ctx.channel))
        msg_loading = await inter.original_response()
        
        await player.play_random_voice(ctx, msg_loading=msg_loading)


    # /pause
    @discord.slash_command(**util.make_command_args('pause'))
    async def command_pause(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return

        try:
            await player.pause()
            await ctx.respond(embed=MyEmbed(notif_type='inactive', title=CHARACTER_TEXT['paused']), delete_after=10)
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description=e),
                ephemeral=True
            )


    # /resume
    @discord.slash_command(**util.make_command_args('resume'))
    async def command_resume(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        try:
            await player.resume()
            await ctx.respond(embed=MyEmbed(title=CHARACTER_TEXT['resumed']), delete_after=10)
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
        except OperationError as e:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description=e),
                ephemeral=True
            )


    # /stop
    @discord.slash_command(**util.make_command_args('stop'))
    async def command_stop(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        try:
            await player.abort(clear=True)
            await ctx.respond(
                embed=MyEmbed(notif_type='inactive', title=CHARACTER_TEXT['stopped']),
                delete_after=10
            )
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)

    
    # /skip
    @discord.slash_command(**util.make_command_args('skip'))
    async def command_skip(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        try:
            player.skip()
        except NotPlayingError:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
            return
        await ctx.respond(embed=MyEmbed(title=f'⏭️ {CHARACTER_TEXT["skipped"]}'), delete_after=10)


    # /replay
    @discord.slash_command(**util.make_command_args('replay'))
    async def command_replay(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        try:
            await player.replay()
            await ctx.respond(embed=MyEmbed(notif_type='succeeded', title=f'🔄 {CHARACTER_TEXT["replay_start"]}'), delete_after=10)
        except PlayerError as e:
            await ctx.respond(embed=MyEmbed(notif_type='error', description=e), ephemeral=True)


    # /repeat
    @discord.slash_command(name='repeat', description='リピート再生の設定を変更します。')
    @discord.option('option', description='リピート再生のオプション', choices=['オフ', 'プレイリスト', 'トラック'], required=False)
    async def command_repeat(self, ctx: discord.ApplicationContext, option: str=None): 
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        ICON = '🔁'
        
        if option is None:
            if player.repeat == 1:
                description = 'プレイリスト'
            elif player.repeat == 2:
                description = 'トラック'
            else:
                description = 'オフ'
            embed = MyEmbed(title=f'{ICON} 現在のリピート再生の設定', description=description)
        else:
            if option == 'プレイリスト':
                player.repeat = 1
            elif option == 'トラック':
                player.repeat = 2
            else:
                player.repeat = 0
            embed = MyEmbed(notif_type='succeeded', title=f'{ICON} {CHARACTER_TEXT["repeat_mode_changed"]}', description=option)
            await player.update_controller()
        await ctx.respond(embed=embed, delete_after=10)


    # /shuffle
    @discord.slash_command(**util.make_command_args('shuffle'))
    @discord.option('switch', description='シャッフル再生のオン/オフ [True/False] (シャッフル再生がオンで、この引数を省略した場合、再生キューが再度シャッフルされます)', required=False)
    async def command_shuffle(self, ctx: discord.ApplicationContext, switch: bool=None):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        ICON = '🔀'

        if switch is None:
            player.shuffle = player.shuffle
            if player.shuffle:
                embed=MyEmbed(title=f'{ICON} {CHARACTER_TEXT["shuffle_queue"]}')
                if player.controller_msg is not None:
                    await player.update_controller()
            else:
                embed=MyEmbed(title=f'{ICON} {CHARACTER_TEXT["shuffle_off"]}')
        else:
            player.shuffle = switch
            embed=MyEmbed(notif_type='succeeded', title=f'{ICON} {CHARACTER_TEXT["shuffle_prefix"]}{"オン" if switch else "オフ"}{CHARACTER_TEXT["shuffle_suffix"]}')
            if player.controller_msg is not None:
                await player.update_controller()

        await ctx.respond(embed=embed, delete_after=10)


    # /queue
    @discord.slash_command(**util.make_command_args('queue'))
    async def command_queue(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        await ctx.defer(ephemeral=True)
        await ctx.respond(ephemeral=True, **player.get_queue_msg(page=1))


    # /clear
    @discord.slash_command(**util.make_command_args('clear'))
    async def command_clear(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        if not player.queue:
            await ctx.respond(embed=EMBED_QUEUE_EMPTY, ephemeral=True)
        else:
            player.clear_queue()
            await player.update_controller()
            await ctx.respond(embed=MyEmbed(title=CHARACTER_TEXT['clear_queue']), delete_after=10)

    
    # /volume
    @discord.slash_command(**util.make_command_args('volume'))
    @discord.option('volume', description='ボリューム [0～100] (指定なしで現在のボリュームを表示)', max_value=100, min_value=0, required=False)
    async def command_volume(self, ctx: discord.ApplicationContext, volume: int=None):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        if volume is not None:
            title = CHARACTER_TEXT['set_volume']
            notif_type = 'succeeded'
            player.volume = volume / 100
        else:
            title = CHARACTER_TEXT['current_volume']
            notif_type = 'normal'
        new_volume = int(player.volume * 100)
        if new_volume < 10:
            volume_icon = '🔈'
        elif new_volume < 50:
            volume_icon = '🔉'
        else:
            volume_icon = '🔊'
        description = f'{volume_icon} **{new_volume}**\n🔈 0 {"-" * (new_volume // 2)}●{"-" * (50 - new_volume // 2)} 🔊 100'
        if not player.is_stopped and volume is not None:
            remark = ' (次回再生時に適応されます)'
        else:
            remark = ''
        await ctx.respond(
            embed=MyEmbed(notif_type=notif_type, title=f'{title}{remark}', description=description),
            delete_after=10
        )


    # /player
    @discord.slash_command(**util.make_command_args('player'))
    async def command_player(self, ctx: discord.ApplicationContext):
        player = await self.get_player(ctx.guild, ctx=ctx)
        if not player:
            return
        
        if player.is_stopped:
            await ctx.respond(embed=EMBED_NOT_PLAYING, ephemeral=True)
            return
        await player.regenerate_controller(ctx.channel)
        await ctx.respond(embed=MyEmbed(notif_type='succeeded', title=CHARACTER_TEXT['moved_player']), delete_after=10)