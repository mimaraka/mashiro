from typing import Any
import discord
import time
from discord.enums import ButtonStyle
from modules.music.errors import *


# 前のトラックに戻るボタン
class ButtonBack(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        super().__init__(style=ButtonStyle.primary, emoji="⏮️")

    async def callback(self, interaction: discord.Interaction) -> Any:
        if time.time() - self.__player.time_started > 5:
            await self.__player.replay()
        else:
            try:
                await self.__player.back()
            except OperationError:
                await self.__player.replay()
        await self.__player.update_controller(interaction)
    

# 再生のボタン
class ButtonPlay(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        super().__init__(style=ButtonStyle.primary, emoji="▶️")

    async def callback(self, interaction: discord.Interaction) -> Any:
        await self.__player.resume()
        await self.__player.update_controller(interaction)
    

# 一時停止のボタン
class ButtonPause(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        super().__init__(style=ButtonStyle.primary, emoji="⏸️")

    async def callback(self, interaction: discord.Interaction) -> Any:
        await self.__player.pause()
        await self.__player.update_controller(interaction)
    

# 次のトラックに進むボタン
class ButtonSkip(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        super().__init__(style=ButtonStyle.primary, emoji="⏭️")

    async def callback(self, interaction: discord.Interaction) -> Any:
        self.__player.skip()
        # インタラクションの無視
        await interaction.response.edit_message()
        

# シャッフルのボタン
class ButtonShuffle(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        style = ButtonStyle.primary if player.shuffle else ButtonStyle.secondary
        super().__init__(style=style, emoji="🔀")

    async def callback(self, interaction: discord.Interaction) -> Any:
        self.__player.shuffle = not self.__player.shuffle
        await self.__player.update_controller(interaction)


# リピートのボタン
class ButtonRepeat(discord.ui.Button):
    def __init__(self, player):
        self.__player = player
        style = ButtonStyle.primary
        emoji = "🔁"
        if player.repeat == 2:
            emoji = "🔂"
        elif player.repeat == 0:
            style = ButtonStyle.secondary
        super().__init__(style=style, emoji=emoji)

    async def callback(self, interaction: discord.Interaction) -> Any:
        if self.__player.repeat == 2:
            self.__player.repeat = 0
        else:
            self.__player.repeat += 1
        await self.__player.update_controller(interaction)
    

class PlayerView(discord.ui.View):
    def __init__(self, player):
        super().__init__(timeout=None)
        
        self.add_item(ButtonRepeat(player))
        self.add_item(ButtonBack(player))
        if player.is_playing:
            self.add_item(ButtonPause(player))
        elif player.is_paused:
            self.add_item(ButtonPlay(player))
        self.add_item(ButtonSkip(player))
        self.add_item(ButtonShuffle(player))
