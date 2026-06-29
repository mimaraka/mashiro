import asyncio
import discord
import glob
import json
import math
import os
import random
import re
import time
import traceback
import typing

import modules.util as util
from modules.myembed import MyEmbed
from modules.mylog import mylog
from modules.http import is_url_valid
from modules.util import get_member_text
from .track.track import Track, LocalTrack
from .player_view import PlayerView
from .errors import *
from ..duration import Duration


class Player:
    def __init__(self, loop: asyncio.AbstractEventLoop, voice_client: discord.VoiceClient) -> None:
        self.__loop: asyncio.AbstractEventLoop = loop
        self.__voice_client: discord.VoiceClient = voice_client
        self.__playlist: typing.List[Track] = []
        self.__queue_idcs: typing.List[int] = []
        self.__history_idcs: typing.List[int] = []
        self.__current_index: int | None = None
        self.__current_track: Track | None = None
        self.__last_track: Track | None = None
        self.__volume: float = 1
        self.__repeat: int = 0
        self.__shuffle: bool = False
        self.__flag_aborted: bool = False
        self.__controller_msg: discord.Message | None = None
        self.__channel: discord.TextChannel | None = None
        self.__time_started: float | None = None

    @property
    def current_track(self) -> Track | None:
        return self.__current_track
    
    @property
    def volume(self) -> float:
        return self.__volume
    
    @volume.setter
    def volume(self, vol: float):
        if vol < 0:
            vol = 0
        elif 1 < vol:
            vol = 1
        self.__volume = vol

    @property
    def repeat(self):
        return self.__repeat
    
    @repeat.setter
    def repeat(self, rep: int):
        if rep == 2:
            self.__repeat = 2
        elif rep == 1:
            self.__repeat = 1
        else:
            self.__repeat = 0

    @property
    def shuffle(self):
        return self.__shuffle
    
    @shuffle.setter
    def shuffle(self, switch: bool):
        self.__shuffle = switch
        if switch:
            random.shuffle(self.__queue_idcs)
        else:
            if self.__current_index is not None:
                self.__queue_idcs = [i for i in range(self.__current_index + 1, len(self.__playlist))]

    @property
    def queue(self) -> typing.List[Track]:
        return [self.__playlist[i] for i in self.__queue_idcs]
    
    @property
    def is_playing(self) -> bool:
        return self.__current_index is not None and self.__voice_client.is_playing()
    
    @property
    def is_paused(self) -> bool:
        return self.__current_index is not None and self.__voice_client.is_paused()
    
    @property
    def is_stopped(self) -> bool:
        return not (self.is_playing or self.is_paused)
    
    @property
    def time_started(self) -> float:
        return self.__time_started
    
    @property
    def controller_msg(self) -> discord.Message:
        return self.__controller_msg
    
    @controller_msg.setter
    def controller_msg(self, message: discord.Message):
        self.__controller_msg = message

    @property
    def vc(self) -> discord.VoiceChannel | discord.StageChannel:
        return self.__voice_client.channel

    # トラック情報のテキストを生成
    @staticmethod
    def track_text(track: Track, italic: bool=False, link: bool=False, queue: bool=False):
        max_title = 40 if queue else 100
        title = util.truncate_text(re.sub(r'(https?)://', '\\1:𝘐𝘐', track.title.translate(str.maketrans({'*': '∗', '[': '［', ']': '］'}))), max_title)
        if link and track.original_url is not None:
            max_title_url = 145 if queue else 1000
            if len(title) + len(track.original_url) > max_title_url:
                url = util.shorten_url(track.original_url)
            else:
                url = track.original_url
            result = f'[{title}]({url})'
        else:
            result = title
        decoration = '***' if italic else '**'
        result = decoration + result + decoration
        if track.duration is not None:
            result += f' | {str(track.duration)}'
        return result
    
    # 複数のトラック情報のテキストを生成(最大10件まで表示)
    def tracks_text(self, tracks: typing.List[Track], start_index: int=1):
        track_text_list = []
        for i, track in enumerate(tracks[:10]):
            track_text_list.append(f'{i + start_index}. {self.track_text(track, queue=True)}')
        if len(tracks) > 10:
            track_text_list.append(f'(他{len(tracks) - 10}曲)')
        result = '\n'.join(track_text_list)
        return result
    

    # キューとプレイリストにトラックを積む
    async def register_tracks(
        self,
        channel: discord.TextChannel,
        tracks: typing.List[Track],
        msg_loading: discord.Message | None=None,
        ctx: discord.ApplicationContext | None=None,
        interrupt: bool=False,
        silent: bool=False
    ):
        self.__channel = channel

        # 割り込み再生の場合
        if interrupt:
            insert_idx = self.__current_index + 1 if self.__current_index is not None else 0
            # カレントトラックの後ろに挿入
            self.__playlist[insert_idx:insert_idx] = tracks
            # 挿入した分だけ、カレントトラックの後ろのインデックスがずれる(指し示すトラック自体は変わらない)
            self.__queue_idcs = [i + len(tracks) if i >= insert_idx else i for i in self.__queue_idcs]
            # キューの先頭に追加するトラックのインデックスを追加
            self.__queue_idcs[0:0] = [i for i in range(insert_idx, insert_idx + len(tracks))]
        else:
            self.__playlist += tracks
            self.__queue_idcs += [i for i in range(len(self.__playlist) - len(tracks), len(self.__playlist))]
            if self.__shuffle:
                random.shuffle(self.__queue_idcs)

        # 停止していない場合
        if not self.is_stopped:
            if interrupt:
                self.__history_idcs.append(self.__current_index)
                await self.abort()
                await self.__play(msg_loading=msg_loading, silent=silent)
                return
            if not silent:
                if msg_loading:
                    await msg_loading.delete()
                embed = MyEmbed(notif_type='succeeded', title='再生キューに追加しました！', description=self.tracks_text(tracks))
                await (ctx.respond if ctx else channel.send)(embed=embed, delete_after=10)
            await self.update_controller()
        else:
            await self.__play(msg_loading=msg_loading, silent=silent)


    # キューの先頭のインデックスに該当するトラックを取り出し再生する
    async def __play(self, msg_loading: discord.Message=None, silent=False) -> None:
        self.__current_index = self.__queue_idcs.pop(0)
        self.__current_track = self.__playlist[self.__current_index]

        await self.__current_track.create_source(self.__volume)

        after = lambda e: asyncio.run_coroutine_threadsafe(self.__after_callback(e), self.__loop)
        self.__voice_client.play(self.__current_track.source, after=after)
        mylog(
            'トラックの再生を開始します。',
            guild=self.__voice_client.guild,
            channel=self.__voice_client.channel,
            title=self.__current_track.title,
            url=self.__current_track.original_url
        )

        self.__time_started = time.time()
        if msg_loading:
            await msg_loading.delete()
        # 再生失敗等でawait中に__after_callbackが走り、カレントトラックがクリアされた場合
        if self.__current_track is None:
            return
        # コントローラーの更新
        if not silent:
            controller = await self.get_controller()
            if self.__controller_msg:
                try:
                    await self.__controller_msg.edit(**controller, attachments=[])
                    return
                except discord.errors.NotFound:
                    pass
            self.__controller_msg = await self.__channel.send(**controller)


    # 指定したトラックを強制的に再生
    async def __play_track(self, track: Track):
        if not self.is_stopped:
            await self.abort()
        self.__current_track = track
        await track.create_source(self.__volume)
        after = lambda e: asyncio.run_coroutine_threadsafe(self.__after_callback(e), self.__loop)
        self.__voice_client.play(track.source, after=after)
        self.__time_started = time.time()


    # 音楽再生後(及びエラー発生時)に呼ばれるコールバック
    async def __after_callback(self, error):
        await self.__current_track.release_source()

        if error:
            mylog('音声の再生中にエラーが発生しました。', log_type='error')
            traceback.print_exception(error)
            # ユーザーに再生失敗を通知し、再生情報をリセットする
            if self.__channel is not None:
                try:
                    embed = MyEmbed(notif_type='error', title='再生中にエラーが発生しました……。')
                    await self.__channel.send(embed=embed, delete_after=10)
                except discord.errors.HTTPException:
                    pass
            await self.__clear_data()
            return

        # 中断により停止された場合
        if self.__flag_aborted:
            mylog('再生を中断しました。', guild=self.__voice_client.guild)
            self.__flag_aborted = False
            return
        
        # リピート(トラックごと)がオンの場合
        if self.__repeat == 2:
            await self.__play_track(self.__current_track)
            return
        
        # キュー内にトラックがある場合
        if self.__queue_idcs:
            self.__history_idcs.append(self.__current_index)
            await self.__play()
        # キューが空である場合
        else:
            # リピート(プレイリストごと)がオンの場合
            if self.__repeat == 1:
                self.__queue_idcs = [i for i in range(len(self.__playlist))]
                self.__history_idcs.clear()
                if self.__shuffle:
                    random.shuffle(self.__queue_idcs)
                await self.__play()
            else:
                self.__last_track = self.__current_track
                # 再生情報をリセット
                await self.__clear_data()


    # 再生情報をリセット
    async def __clear_data(self):
        self.__playlist.clear()
        self.__queue_idcs.clear()
        self.__history_idcs.clear()
        self.__current_index = None
        self.__current_track = None
        await self.delete_controller()

        for f in glob.glob(f'data/temp/cover_{self.__voice_client.guild.id}_*.*'):
            os.remove(f)
        mylog('再生情報をリセットしました。', guild=self.__voice_client.guild)


    # キューを空にする
    def clear_queue(self):
        self.__queue_idcs.clear()


    # コントローラーを取得
    async def get_controller(self):
        file = None
        # カレントトラックが存在しない場合(再生失敗やコールバックによるクリア後)
        if self.__current_track is None:
            embed = MyEmbed(notif_type='inactive', title='再生していません……。')
            return {'embed': embed, 'view': None}
        # 再生中または一時停止中の場合
        if self.is_playing or self.is_paused:
            if self.is_playing:
                title = '▶️ 再生中です！'
                notif_type = 'normal'
            elif self.is_paused:
                title = '⏸️ 一時停止中です……。'
                notif_type = 'inactive'
            title += f' (🔊 {self.__voice_client.channel.name})'
            description = f'🎶 {self.track_text(self.__current_track, link=True, italic=True)}\n'
            description += f'👤 {util.truncate_text(self.__current_track.artist or "-", 72)}\n'
            description += f'💿 {util.truncate_text(self.__current_track.album or "-", 72)}'
            embed = MyEmbed(notif_type=notif_type, title=title, description=description)
            # 再生キューにトラックが入っている場合
            if self.__queue_idcs:
                next_track = self.__playlist[self.__queue_idcs[0]]
                name = f'再生キュー ({len(self.__queue_idcs)}曲)'
                value = f'次に再生 : {self.track_text(next_track)}'
                embed.add_field(name=name, value=value, inline=False)
            
            # サムネイルを表示
            if thumbnail := self.__current_track.thumbnail:
                # URLの場合
                if util.is_url(thumbnail):
                    embed.set_image(url=thumbnail)
                # ローカルファイルのパスの場合
                else:
                    filename = 'thumbnail' + os.path.splitext(thumbnail)[-1]
                    file = discord.File(fp=thumbnail, filename=filename)
                    url = f'attachment://{filename}'
                    embed.set_image(url=url)
            
            # ボタンを表示
            view = PlayerView(self)
        # 停止中の場合
        else:
            embed = MyEmbed(notif_type='inactive', title='再生していません……。')
            view = None

        author_name = 'プレイヤー'

        # original_urlが存在しない場合
        if self.__current_track.original_url is None:
            author_icon = None
            author_url = None
        else:
            if not await is_url_valid(self.__current_track.original_url):
                author_icon = None
            else:
                author_icon = util.get_favicon_url(self.__current_track.original_url)
            author_url = util.get_domain(self.__current_track.original_url)

        if author_icon is None:
            author_name = '🎵 ' + author_name

        embed.set_author(name=author_name, url=author_url, icon_url=author_icon)
        member = self.__current_track.member
        embed.set_footer(text=f'{get_member_text(member, decoration=False)}が追加', icon_url=member.display_avatar.url)

        result = {
            'embed': embed,
            'view': view
        }
        if file is not None:
            result['file'] = file

        return result
    

    # コントローラーを更新
    async def update_controller(self, inter: discord.Interaction=None):
        controller = await self.get_controller()
        if inter:
            await inter.response.edit_message(**controller, attachments=[])
        elif self.__controller_msg:
            await self.__controller_msg.edit(**controller, attachments=[])


    # コントローラーを再生成
    async def regenerate_controller(self, channel: discord.TextChannel):
        self.__channel = channel
        old_msg = self.__controller_msg
        self.__controller_msg = await channel.send(**(await self.get_controller()))

        if old_msg:
            try:
                await old_msg.delete()
            except discord.errors.NotFound:
                pass


    async def delete_controller(self):
        if self.__controller_msg:
            try:
                await self.__controller_msg.delete()
            except discord.errors.NotFound:
                pass
            self.__controller_msg = None
    

    # 再生キューのEmbedを取得
    def get_queue_msg(self, page: int=1, edit: bool=False):
        n_pages = math.ceil(len(self.queue) / 10)

        class ButtonPreviousPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page <= 1, emoji='⬅️')
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.edit_message(interaction.message.id, **self.get_queue_msg(page=btn_self.page - 1, edit=True))

        class ButtonNextPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page >= n_pages, emoji='➡️')
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.defer()
                await interaction.followup.edit_message(interaction.message.id, **self.get_queue_msg(page=btn_self.page + 1, edit=True))

        if self.queue:
            page = min(max(page, 1), n_pages)
            start_index = (page - 1) * 10
            description = f'{"⏸️" if self.is_paused else "▶️"} {self.track_text(self.current_track, italic=True, queue=True)}\n\n'
            description += self.tracks_text(self.queue[start_index:start_index + 10], start_index=start_index + 1)
            if len(self.queue) > 10:
                description += f'\n\n**{page}** / {n_pages}ページ'
                view = discord.ui.View(timeout=None)
                view.add_item(ButtonPreviousPage(page))
                view.add_item(ButtonNextPage(page))
            else:
                view = None
            seconds_sum = sum([track.duration.seconds if track.duration is not None else 0 for track in self.queue])
            embed = MyEmbed(title=f'再生キュー ({len(self.queue)}曲 | {Duration(seconds_sum)})', description=description)
        else:
            embed = MyEmbed(notif_type='inactive', title='再生キューは空です。')
            view = None
        result = {
            'embed': embed
        }
        if edit or view is not None:
            result['view'] = view
        return result


    # 1つ前の曲に戻る
    async def back(self):
        if self.is_stopped:
            raise NotPlayingError('再生していません。')
        
        # 現在のトラック及び一つ前のトラックをキューに戻す
        if self.__history_idcs:
            self.__queue_idcs.insert(0, self.__current_index)
            self.__queue_idcs.insert(0, self.__history_idcs.pop(-1))
        else:
            raise OperationError('前の曲がありません。')
        await self.abort()
        await self.__play()


    # 再生中/最後に再生していた曲を再度再生する
    async def replay(self):        
        replay_track = self.__current_track or self.__last_track
        if not replay_track:
            raise PlayerError('再生中、または最後に再生していたトラックがありません。')
        await self.__play_track(replay_track)


    # 1つ先の曲に進む
    def skip(self):
        if self.is_stopped:
            raise NotPlayingError('再生していません。')
        self.__voice_client.stop()


    # 再生後のコールバックの処理を行わずに再生を停止させる
    async def abort(self, clear=False):
        if self.is_stopped:
            raise NotPlayingError('再生していません。')
        
        self.__flag_aborted = True
        self.__voice_client.stop()
        if clear:
            self.__last_track = self.__current_track
            await self.__clear_data()
            # __after_callback()が呼ばれるより__clear_data()が呼ばれる方が先なのかもしれない
            # ので__flag_abortedを元に戻しておく
            self.__flag_aborted = False


    # 再生を一時停止する
    async def pause(self):
        if self.is_stopped:
            raise NotPlayingError('再生していません。')
        elif self.is_paused:
            raise OperationError('既に一時停止しています。')
        else:
            self.__voice_client.pause()
            await self.update_controller()


    # 再生を再開する
    async def resume(self):
        if self.is_stopped:
            raise NotPlayingError('再生していません。')
        elif self.is_playing:
            raise OperationError('既に再生しています。')
        else:
            self.__voice_client.resume()
            await self.update_controller()


    # マシロのボイスをランダムで再生する
    async def play_random_voice(self, ctx: discord.ApplicationContext, on_connect=False, msg_loading: discord.Message=None):
        voice_dir = 'data/assets/voice'

        # セリフのインデックス・テキスト・入室時フラグを保持したマニフェストを読み込む
        with open(f'{voice_dir}/voices.json', encoding='utf-8') as f:
            voices = json.load(f)

        # 入室時は on_connect=True のセリフのみ、/voice は全セリフが対象
        candidates = [
            i for i, v in enumerate(voices)
            if not on_connect or v.get('on_connect', False)
        ]
        picked_index = random.choice(candidates)

        # 音声ファイルは3桁ゼロパディングのインデックス名 (例: 002.ogg)。拡張子は問わない。
        picked_voice = glob.glob(f'{voice_dir}/{picked_index:03d}.*')[0]
        await self.register_tracks(
            ctx.channel,
            [LocalTrack(member=ctx.author, filepath=picked_voice, title=voices[picked_index]['title'])],
            ctx=ctx,
            silent=on_connect,
            msg_loading=msg_loading
        )