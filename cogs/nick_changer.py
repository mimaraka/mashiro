import discord
import modules.util as util
from modules.common_embed import *
from modules.json import JSONLoader


EMBED_NO_PERMISSION = MyEmbed(notif_type='error', description='私にこのサーバーのメンバーのニックネームを変更する権限がありません。')

class CogNickChanger(discord.Cog):
    group_nick = discord.SlashCommandGroup('nick', 'メンバーのニックネームの管理を行います。')

    # コンストラクタ
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot
        self.json_loader = JSONLoader('old_nicks')
            
    # 指定したギルドメンバーのニックネームに任意の文字列を設定する
    async def _set_member_nick(self, member: discord.Member, nick: str) -> bool:
        try:
            await member.edit(nick=nick)
            return True
        except discord.errors.Forbidden:
            return False
    
    # 指定したギルドメンバーのニックネームを変更
    # 変更されればTrue、変更されなければFalseを返す
    async def _change_member_nick(self, member: discord.Member) -> bool:
        if (nick := self._get_guild_replaced_nick(member.guild)) is not None:
            if member.nick != nick:
                return await self._set_member_nick(member, nick)
        return False

    # ニックネーム変更コマンドが適用されたギルドであるかどうか
    def _guild_is_changed(self, guild: discord.Guild) -> bool:
        return bool(self.json_loader.get_guild_data(guild))
    
    # メンバーのニックネームが変更されているか(jsonファイルに元のニックネームが保存されているか)
    def _member_is_changed(self, member: discord.Member) -> bool:
        data = self.json_loader.get_guild_data(member.guild)
        return str(member.id) in data
    
    # メンバーの元のニックネームをjsonファイルに登録
    def _save_member_old_nick(self, member: discord.Member):
        data = self.json_loader.get_guild_data(member.guild)
        if data is None:
            data = {}
        data[str(member.id)] = member.nick
        self.json_loader.set_guild_data(data, member.guild)

    # ギルド毎の置き換え後のニックネームをjsonファイルから取得
    def _get_guild_replaced_nick(self, guild: discord.Guild) -> str | None:
        data = self.json_loader.get_guild_data(guild)
        if data is None:
            return None
        return data.get('nick')

    # ギルド毎の置き換え後のニックネームをjsonファイルに登録
    def _set_guild_replaced_nick(self, guild: discord.Guild, nick: str) -> None:
        data = self.json_loader.get_guild_data(guild)
        if data is None:
            data = {}
        data['nick'] = nick
        self.json_loader.set_guild_data(data, guild)

    # 指定したギルドのメンバー全員のニックネームを変更
    async def _change_guild_nick(self, guild: discord.Guild, nick: str=None) -> None:
        if nick is not None:
            self._set_guild_replaced_nick(guild, nick)
        elif self._get_guild_replaced_nick(guild) is None:
            return
            
        for member in guild.members:
            # ユーザー情報をjsonに追加していない場合
            if not self._member_is_changed(member):
                # ユーザーID、元のニックネームをjsonに保存
                self._save_member_old_nick(member)
            # ニックネームを変更
            await self._change_member_nick(member)

    # 指定したギルドのメンバー全員のニックネームを元に戻す
    async def _restore_guild_nick(self, guild: discord.Guild) -> bool:
        root = self.json_loader.get_root()
        if str(guild.id) not in root:
            return False
        
        old_nicks = root.pop(str(guild.id))
        self.json_loader.set_root(root)

        for key, old_nick in old_nicks.items():
            if key != 'nick':
                if (member := guild.get_member(int(key))) is not None:
                    await self._set_member_nick(member, old_nick)
        return True

    # Bot起動時
    @discord.Cog.listener()
    async def on_ready(self):
        root = self.json_loader.get_root()
        guilds = [self.bot.get_guild(int(key)) for key in root.keys()]

        for guild in guilds:
            await self._change_guild_nick(guild)

	# プロフィールが編集されたとき
    @discord.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
    	# ニックネーム置き換えコマンドを実行中のギルドの場合
        if self._guild_is_changed(before.guild):
            await self._change_member_nick(after)
        
    # メンバーが新しく入ってきたとき
    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # ニックネーム置き換えコマンドを実行中のギルドの場合
        if self._guild_is_changed(member.guild):
            await self._change_member_nick(member)

    # ギルドメンバー全員のニックネームを変更するコマンド
    @group_nick.command(**util.make_command_args(['nick', 'change']))
    async def command_nick_change(self, ctx: discord.ApplicationContext, nick: str):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return

        can_bot_manage_nicknames = any([role.permissions.manage_nicknames for role in ctx.me.roles])
        is_author_administrator = any([role.permissions.administrator for role in ctx.author.roles])
        if not can_bot_manage_nicknames:
            await ctx.respond(embed=EMBED_NO_PERMISSION, ephemeral=True)
            return
        elif not is_author_administrator and ctx.author != ctx.guild.owner:
            await ctx.respond(embed=EMBED_NOT_ADMINISTRATOR, ephemeral=True)
            return
        
        await ctx.defer()
        await self._change_guild_nick(ctx.guild, nick)
        await ctx.respond(
            embed=MyEmbed(
                notif_type='succeeded',
                title='ニックネームを変更しました！',
                description=f'サーバーメンバーのニックネームを\n**{nick}**\nに変更しました。'
            ),
            delete_after=10
        )

    # ギルドメンバー全員のニックネームを元に戻すコマンド
    @group_nick.command(**util.make_command_args(['nick', 'restore']))
    async def command_nick_restore(self, ctx: discord.ApplicationContext):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return
        
        can_bot_manage_nicknames = any([role.permissions.manage_nicknames for role in ctx.me.roles])
        is_author_administrator = any([role.permissions.administrator for role in ctx.author.roles])

        if not can_bot_manage_nicknames:
            await ctx.respond(embed=EMBED_NO_PERMISSION, ephemeral=True)
            return
        elif not is_author_administrator and ctx.author != ctx.guild.owner:
            await ctx.respond(embed=EMBED_NOT_ADMINISTRATOR, ephemeral=True)
            return
        
        await ctx.defer(ephemeral=True)
        if not await self._restore_guild_nick(ctx.guild):
            await ctx.respond(
                embed=MyEmbed(
                    notif_type='error',
                    description='ニックネームは変更されていません。'
                ),
                ephemeral=True
            )
        else:
            await ctx.respond(
                embed=MyEmbed(notif_type='succeeded', title='ニックネームを元に戻しました。'),
                delete_after=10
            )

    @group_nick.command(**util.make_command_args(['nick', 'remove']))
    @discord.option('nick', description='削除するニックネーム')
    async def command_nick_remove(self, ctx: discord.ApplicationContext, nick: str):
        if ctx.guild is None:
            await ctx.respond(embed=EMBED_GUILD_ONLY, ephemeral=True)
            return

        can_bot_manage_nicknames = any([role.permissions.manage_nicknames for role in ctx.me.roles])
        is_author_administrator = any([role.permissions.administrator for role in ctx.author.roles])

        if not can_bot_manage_nicknames:
            await ctx.respond(embed=EMBED_NO_PERMISSION, ephemeral=True)
            return
        elif not is_author_administrator and ctx.author != ctx.guild.owner:
            await ctx.respond(embed=EMBED_NOT_ADMINISTRATOR, ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        for member in ctx.guild.members:
            await self._set_member_nick(member, None)
        await ctx.respond(
            embed=MyEmbed(notif_type='succeeded', title=f'ニックネーム「{nick}」を削除しました。'),
            delete_after=10
        )