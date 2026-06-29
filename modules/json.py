import discord
import json


class JSONLoader:
    def __init__(self, filename: str, guild: discord.Guild=None) -> None:
        self.path = 'data/saves/' + filename + '.json'
        self.guild = guild

    def get_root(self) -> dict:
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                try:
                    ret = json.load(f)
                except json.decoder.JSONDecodeError:
                    ret = {}
                return ret
        except FileNotFoundError:
            return {}

    def set_root(self, data: dict) -> None:
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_guild_data(self, guild: discord.Guild=None) -> dict | None:
        root = self.get_root()
        g = guild or self.guild
        if g:
            return root.get(str(g.id))
        return None
    
    def set_guild_data(self, data: dict, guild: discord.Guild=None) -> None:
        root = self.get_root()
        g = guild or self.guild
        if g:
            root[str(g.id)] = data
            self.set_root(root)

    