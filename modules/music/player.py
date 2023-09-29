import asyncio
import discord
import glob
import math
import os
import random
import re
import time
import traceback
import typing

import modules.utils as utils
import constants as const
from modules.myembed import MyEmbed
from modules.mashilog import mashilog
from .track.track import Track, LocalTrack
from .playerview import PlayerView
from .errors import *


class Player:
    def __init__(self, loop: asyncio.AbstractEventLoop, voice_client: discord.VoiceClient) -> None:
        self.__loop: asyncio.AbstractEventLoop = loop
        self.__voice_client: discord.VoiceClient = voice_client
        self.__playlist: typing.List[Track] = []
        self.__queue_idcs: typing.List[int] = []
        self.__history_idcs: typing.List[int] = []
        self.__current_track: Track | None = None
        self.__current_index: int = 0
        self.__last_track: Track | None = None
        self.__volume: float = 1
        self.__repeat: int = 0
        self.__shuffle: bool = False
        self.__flag_aborted: bool = False
        self.__controller_msg: discord.Message | None = None
        self.__channel: discord.TextChannel | None = None
        self.__time_started: float | None = None

    @property
    def current_track(self):
        return self.__current_track
    
    @property
    def volume(self):
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
            self.__queue_idcs = [i for i in range(self.__current_index + 1, len(self.__playlist))]

    @property
    def queue(self) -> typing.List[Track]:
        return [self.__playlist[i] for i in self.__queue_idcs]
    
    @property
    def current_track(self) -> Track:
        return self.__current_track
    
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

    # トラック情報のテキストを生成
    @staticmethod
    def track_text(track: Track, italic: bool=False, queue: bool=False):
        max_title = 40 if queue else 200
        title = utils.limit_text_length(re.sub(r"(https?)://", "\\1:𝘐𝘐", track.title.translate(str.maketrans({"*": "∗", "[": "［", "]": "］"}))), max_title)
        if track.original_url is not None:
            max_title_url = 145 if queue else 1000
            if len(title) + len(track.original_url) > max_title_url:
                url = utils.shorten_url(track.original_url)
            else:
                url = track.original_url
            result = f"[{title}]({url})"
        else:
            result = title
        decoration = "***" if italic else "**"
        result = f"{decoration}{result}{decoration}"
        if track.duration is not None:
            result += f" | {utils.make_duration_text(track.duration)}"
        return result
    
    # 複数のトラック情報のテキストを生成(最大10件まで表示)
    def tracks_text(self, tracks: typing.List[Track], start_index: int=1):
        track_text_list = []
        for i, track in enumerate(tracks[:10]):
            track_text_list.append(f"{i + start_index}. {self.track_text(track, queue=True)}")
        if len(tracks) > 10:
            track_text_list.append(f"(他{len(tracks) - 10}曲)")
        result = "\n".join(track_text_list)
        return result
    

    # キューとプレイリストにトラックを積む
    async def register_tracks(self, ctx: discord.ApplicationContext, tracks: typing.List[Track], msg_proc: discord.Message=None, interrupt=False, silent=False):
        self.__channel = ctx.channel

        if interrupt:
            self.__playlist[self.__current_index + 1:self.__current_index + 1] = tracks
            self.__queue_idcs = [i + len(tracks) if i > self.__current_index else i for i in self.__queue_idcs]
            self.__queue_idcs[0:0] = [i for i in range(self.__current_index + 1, self.__current_index + 5)]
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
                await self.__play(msg_proc=msg_proc, silent=silent)
                return
            if not silent:
                if msg_proc:
                    await msg_proc.delete()
                embed = MyEmbed(notif_type="succeed", title="再生キューに追加しました！", description=self.tracks_text(tracks))
                await ctx.respond(embed=embed, delete_after=10)
            await self.update_controller()
        else:
            await self.__play(msg_proc=msg_proc, silent=silent)


    # キューの先頭のインデックスに該当するトラックを取り出し再生する
    async def __play(self, msg_proc: discord.Message=None, silent=False) -> None:
        self.__current_index = self.__queue_idcs.pop(0)
        self.__current_track = self.__playlist[self.__current_index]

        await self.__current_track.create_source(self.__volume)
        after = lambda e: asyncio.run_coroutine_threadsafe(self.__after_callback(e), self.__loop)
        self.__voice_client.play(self.__current_track.source, after=after)
        self.__time_started = time.time()
        if msg_proc:
            await msg_proc.delete()
        # コントローラーの更新
        if not silent:
            controller = self.get_controller()
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
            print(f"An error occurred while playing.")
            traceback.print_exception(error)
            return
        
        # 中断により停止された場合
        if self.__flag_aborted:
            mashilog("再生を中断しました。", guild=self.__voice_client.guild)
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
        self.__current_index = 0
        self.__current_track = None
        await self.__controller_msg.delete()
        self.__controller_msg = None

        for f in glob.glob(f"data/temp/cover_{self.__voice_client.guild.id}_*.*"):
            os.remove(f)
        mashilog("再生情報をリセットしました。", guild=self.__voice_client.guild)


    # キューを空にする
    def clear_queue(self):
        self.__queue_idcs.clear()


    # コントローラーを取得
    def get_controller(self):
        file = None
        # 再生中または一時停止中の場合
        if self.is_playing or self.is_paused:
            if self.is_playing:
                title = "▶️ 再生中です！"
                notif_type = "normal"
            elif self.is_paused:
                title = "⏸️ 一時停止中です……。"
                notif_type = "inactive"
            title += f" (🔊 {self.__voice_client.channel.name})"
            description = f"🎶 {self.track_text(self.__current_track, italic=True)}\n"
            description += f"👤 {utils.limit_text_length(self.__current_track.artist or '-', 500)}\n"
            description += f"💿 {utils.limit_text_length(self.__current_track.album or '-', 500)}"
            embed = MyEmbed(notif_type=notif_type, title=title, description=description)
            # 再生キューにトラックが入っている場合
            if self.__queue_idcs:
                next_track = self.__playlist[self.__queue_idcs[0]]
                name = f"再生キュー ({len(self.__queue_idcs)}曲)"
                value = f"次に再生 : {self.track_text(next_track)}"
                embed.add_field(name=name, value=value, inline=False)
            
            # サムネイルを表示
            if thumbnail := self.__current_track.thumbnail:
                # URLの場合
                if re.fullmatch(const.RE_URL_PATTERN, thumbnail):
                    embed.set_image(url=thumbnail)
                # ローカルファイルのパスの場合
                else:
                    filename = "thumbnail" + os.path.splitext(thumbnail)[-1]
                    file = discord.File(fp=thumbnail, filename=filename)
                    embed.set_image(url=f"attachment://{filename}")
            
            # ボタンを表示
            view = PlayerView(self)
        # 停止中の場合
        else:
            embed = MyEmbed(notif_type="inactive", title="再生していません……。")
            view = None

        embed.set_author(name="🎵 プレイヤー")
        member = self.__current_track.member
        embed.set_footer(text=f"{member.display_name} 先生が追加", icon_url=member.display_avatar.url)

        result = {
            "embed": embed,
            "view": view
        }
        if file is not None:
            result["file"] = file

        return result
    

    # コントローラーを更新
    async def update_controller(self, inter: discord.Interaction=None):
        controller = self.get_controller()
        if inter:
            await inter.response.edit_message(**controller, attachments=[])
        else:
            await self.__controller_msg.edit(**controller, attachments=[])


    # コントローラーを再生成
    async def regenerate_controller(self, channel: discord.TextChannel):
        self.__channel = channel
        old_msg = self.__controller_msg
        self.__controller_msg = await channel.send(**self.get_controller())

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
    

    # 再生キューのEmbedを取得
    def get_queue_msg(self, page: int=1, edit: bool=False):
        n_pages = math.ceil(len(self.queue) / 10)

        class ButtonPreviousPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page <= 1, emoji="⬅️")
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.edit_message(**self.get_queue_msg(page=btn_self.page - 1, edit=True))

        class ButtonNextPage(discord.ui.Button):
            def __init__(btn_self, page: int):
                btn_self.page: int = page
                super().__init__(style=discord.enums.ButtonStyle.primary, disabled=page >= n_pages, emoji="➡️")
            
            async def callback(btn_self, interaction: discord.Interaction):
                await interaction.response.edit_message(**self.get_queue_msg(page=btn_self.page + 1, edit=True))

        if self.queue:
            page = min(max(page, 1), n_pages)
            start_index = (page - 1) * 10
            description = f"▶️ {self.track_text(self.current_track, italic=True, queue=True)}\n\n"
            description += self.tracks_text(self.queue[start_index:start_index + 10], start_index=start_index + 1)
            if len(self.queue) > 10:
                description += f"\n\n**{page}** / {n_pages}ページ"
                view = discord.ui.View(timeout=None)
                view.add_item(ButtonPreviousPage(page))
                view.add_item(ButtonNextPage(page))
            else:
                view = None
            duration_sum = sum([track.duration if track.duration is not None else 0 for track in self.queue])
            embed = MyEmbed(title=f"再生キュー ({len(self.queue)}曲 | {utils.make_duration_text(duration_sum)})", description=description)
        else:
            embed = MyEmbed(notif_type="inactive", title="再生キューは空です。")
            view = None
        result = {
            "embed": embed
        }
        if edit or view is not None:
            result["view"] = view
        return result


    # 1つ前の曲に戻る
    async def back(self):
        if self.is_stopped:
            raise NotPlayingError("再生していません。")
        
        # 現在のトラック及び一つ前のトラックをキューに戻す
        if self.__history_idcs:
            self.__queue_idcs.insert(0, self.__current_index)
            self.__queue_idcs.insert(0, self.__history_idcs.pop(-1))
        else:
            raise OperationError("前の曲がありません。")
        await self.abort()
        await self.__play()


    # 再生中/最後に再生していた曲を再度再生する
    async def replay(self):        
        replay_track = self.__current_track or self.__last_track
        if not replay_track:
            raise PlayerError("再生中、または最後に再生していたトラックがありません。")
        await self.__play_track(replay_track)


    # 1つ先の曲に進む
    def skip(self):
        if self.is_stopped:
            raise NotPlayingError("再生していません。")
        self.__voice_client.stop()


    # 再生後のコールバックの処理を行わずに再生を停止させる
    async def abort(self, clear=False):
        if self.is_stopped:
            raise NotPlayingError("再生していません。")
        
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
            raise NotPlayingError("再生していません。")
        elif self.is_paused:
            raise OperationError("既に一時停止しています。")
        else:
            self.__voice_client.pause()
            await self.update_controller()


    # 再生を再開する
    async def resume(self):
        if self.is_stopped:
            raise NotPlayingError("再生していません。")
        elif self.is_playing:
            raise OperationError("既に再生しています。")
        else:
            self.__voice_client.resume()
            await self.update_controller()


    # マシロのボイスをランダムで再生する
    async def play_random_voice(self, ctx: discord.ApplicationContext, on_connect=False, msg_proc: discord.Message=None):
        # 入室時のボイス
        if on_connect:
            voices = glob.glob("data/assets/voices/on_connect/*.*")
        else:
            voices = glob.glob("data/assets/voices/**/*.*", recursive=True)

        picked_voice = random.choice(voices)
        await self.register_tracks(ctx, [LocalTrack(member=ctx.author, filepath=picked_voice)], silent=on_connect, msg_proc=msg_proc)