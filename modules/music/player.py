import asyncio
import discord
import glob
import random
import time
import traceback
import typing
import modules.utils as utils
from modules.myembed import MyEmbed
from modules.music.track import Track, LocalTrack
from modules.music.playerview import PlayerView
from modules.music.errors import *


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
    def shuffle(self, onoff: bool):
        self.__shuffle = onoff
        if onoff:
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
    def __track_text(track: Track, italic=False):
        if track.original_url is not None:
            result = f"[{utils.escape_markdown(track.title)}]({track.original_url})"
        else:
            result = utils.escape_markdown(track.title)
        decoration = "***" if italic else "**"
        result = f"{decoration}{result}{decoration}"
        if track.duration:
            result += f" ({track.duration})"
        return result
    

    # キューとプレイリストにソースを積む
    async def register_tracks(self, inter: discord.Interaction, tracks: typing.List[Track], silent=False):
        self.__channel = inter.channel
        self.__playlist += tracks
        self.__queue_idcs += [i for i in range(len(self.__playlist) - len(tracks), len(self.__playlist))]
        if self.__shuffle:
            random.shuffle(self.__queue_idcs)

        # 停止していない場合
        if not self.is_stopped:
            if not silent:
                description = "\n".join([self.__track_text(s) for s in tracks][:5])
                if len(tracks) > 5:
                    description += f"\n(他{len(tracks) - 5}曲)"
                embed = MyEmbed(title="再生キューに追加しました！", description=description)
                message = await inter.followup.send(embed=embed)
            await self.update_controller()
            await asyncio.sleep(10)
            await message.delete()
        else:
            if not silent:
                embed = MyEmbed(notification_type="inactive", title="⏳ 処理中です……。")
                msg_proc = await inter.followup.send(embed=embed)
            else:
                msg_proc = None
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
            if self.__controller_msg:
                try:
                    await self.__controller_msg.edit(**self.get_controller())
                    return
                except discord.errors.NotFound:
                    pass
            self.__controller_msg = await self.__channel.send(**self.get_controller())


    # 指定したトラックを強制的に再生
    async def __play_track(self, track: Track):
        if not self.is_stopped:
            await self.abort()
        await track.create_source(self.__volume)
        after = lambda e: asyncio.run_coroutine_threadsafe(self.__after_callback(e), self.__loop)
        self.__voice_client.play(track.source, after=after)
        self.__time_started = time.time()


    # 音楽再生後(及びエラー発生時)に呼ばれるコールバック
    async def __after_callback(self, error):
        if error:
            print(f"An error occurred while playing.")
            traceback.print_exception(error)
            return
        
        # 中断により停止された場合
        if self.__flag_aborted:
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


    # キューを空にする
    def clear_queue(self):
        self.__queue_idcs.clear()


    # コントローラーを取得
    def get_controller(self):
        # 再生中または一時停止中の場合
        if self.is_playing or self.is_paused:
            if self.is_playing:
                title = "▶️ 再生中です！"
                notification_type = "normal"
            elif self.is_paused:
                title = "⏸️ 一時停止中です……。"
                notification_type = "inactive"
            title += f" (🔊 {utils.escape_markdown(self.__voice_client.channel.name)})"
            description = f"💿 {self.__track_text(self.__current_track, italic=True)}"
            embed = MyEmbed(notification_type=notification_type, title=title, description=description)
            # 再生キューにトラックが入っている場合
            if self.__queue_idcs:
                next_track = self.__playlist[self.__queue_idcs[0]]
                name = f"再生キュー ({len(self.__queue_idcs)}曲)"
                value = f"次に再生 : {self.__track_text(next_track)}"
                embed.add_field(name=name, value=value, inline=False)
            # サムネイルを表示
            embed.set_image(url=self.__current_track.thumbnail)
            
            # ボタンを表示
            view = PlayerView(self)
        # 停止中の場合
        else:
            embed = MyEmbed(notification_type="inactive", title="再生していません……。")
            view = None

        embed.set_author(name="🎵 プレイヤー")
        author = self.__current_track.author
        embed.set_footer(text=f"{author.display_name} さんが追加", icon_url=author.display_avatar.url)
        return {
            "embed": embed,
            "view": view
        }
    
    async def update_controller(self, inter: discord.Interaction=None):
        if inter:
            await inter.response.edit_message(**self.get_controller())
        else:
            await self.__controller_msg.edit(**self.get_controller())
    

    def get_queue_embed(self):
        if self.queue:
            count = 0
            while 1:
                track_titles = [f"▶️ {self.__track_text(self.current_track, italic=True)}"]
                for i, track in enumerate(self.queue[:-count] if count else self.queue):
                    track_titles.append(f"{i + 1}. {self.__track_text(track)}")
                if count:
                    track_titles.append(f"(他{count}曲)")
                description = "\n".join(track_titles)
                if len(description) < 4096:
                    break
                count += 1
            embed = MyEmbed(title=f"再生キュー ({len(self.queue)}曲)", description=description)
        else:
            embed = MyEmbed(notification_type="inactive", title="再生キューは空です。")
        return embed

    
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


    # 1つ前の曲に戻る
    async def back(self):
        if self.is_stopped:
            raise NotPlayingError("再生していません。")
        
        # 現在の曲をキューに戻す
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
    async def play_random_voice(self, inter: discord.Interaction, on_connect=False):
        author = inter.guild.get_member(inter.user.id)
        # 入室時のボイス
        if on_connect:
            voices = glob.glob("data/assets/voices/on_connect/*.*")
        else:
            voices = glob.glob("data/assets/voices/**/*.*", recursive=True)

        picked_voice = random.choice(voices)
        await inter.response.defer()
        await self.register_tracks(inter, [LocalTrack(picked_voice, author)], silent=on_connect)