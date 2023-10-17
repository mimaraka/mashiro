import discord
import json
from modules.myembed import MyEmbed


class CogNickChanger(discord.Cog):
    DATA_PATH = "data/saves/old_nicks.json"

    # コンストラクタ
    def __init__(self, bot: discord.Bot) -> None:
        self.bot: discord.Bot = bot

    # 全メンバーの元のニックネームが格納された辞書をjsonファイルから取得する
    def __get_json(self) -> dict:
        with open(self.DATA_PATH, "r", encoding="shift-jis") as f:
            return json.load(f)
        
    # 全メンバーの元のニックネームが格納された辞書をjsonファイルに書き込む
    def __set_json(self, nick_dict: dict) -> None:
        with open(self.DATA_PATH, "w", encoding="shift-jis") as f:
            json.dump(nick_dict, f, indent=4)
            
    # 指定したギルドメンバーのニックネームに任意の文字列を設定する
    async def __set_member_nick(self, member: discord.Member, nick: str) -> bool:
        try:
            await member.edit(nick=nick)
            return True
        except discord.errors.Forbidden:
            return False
    
    # 指定したギルドメンバーのニックネームを変更
    # 変更されればTrue、変更されなければFalseを返す
    async def __change_member_nick(self, member: discord.Member) -> bool:
        if (nick := self.__get_guild_replaced_nick(member.guild)) is not None:
            if member.nick != nick:
                return await self.__set_member_nick(member, nick)
        return False

    # ニックネーム変更コマンドが適用されたギルドであるかどうか
    def __guild_is_changed(self, guild: discord.Guild) -> bool:
        return str(guild.id) in self.__get_json()
    
    # メンバーのニックネームが変更されているか(jsonファイルに元のニックネームが保存されているか)
    def __member_is_changed(self, member: discord.Member) -> bool:
        data = self.__get_json()
        return self.__guild_is_changed(member.guild) and str(member.id) in data[str(member.guild.id)]
    
    # メンバーの元のニックネームをjsonファイルに登録
    def __save_member_old_nick(self, member: discord.Member):
        data = self.__get_json()
        data[str(member.guild.id)][str(member.id)] = member.nick
        self.__set_json(data)

    # ギルド毎の置き換え後のニックネームをjsonファイルから取得
    def __get_guild_replaced_nick(self, guild: discord.Guild) -> str | None:
        data = self.__get_json()
        return data.get(str(guild.id)) and data.get(str(guild.id)).get("nick")

    # ギルド毎の置き換え後のニックネームをjsonファイルに登録
    def __set_guild_replaced_nick(self, guild: discord.Guild, nick: str) -> None:
        data = self.__get_json()
        if data.get(str(guild.id)) is None:
            data[str(guild.id)] = {}
        data[str(guild.id)]["nick"] = nick
        self.__set_json(data)

    # 指定したギルドのメンバー全員のニックネームを変更
    async def __change_guild_nick(self, guild: discord.Guild, nick: str=None) -> None:
        if nick is not None:
            self.__set_guild_replaced_nick(guild, nick)
        elif self.__get_guild_replaced_nick(guild) is None:
            return
            
        for member in guild.members:
            # ユーザー情報をjsonに追加していない場合
            if not self.__member_is_changed(member):
                # ユーザーID、元のニックネームをjsonに保存
                self.__save_member_old_nick(member)
            # ニックネームを変更
            await self.__change_member_nick(member)

    # 指定したギルドのメンバー全員のニックネームを元に戻す
    async def __restore_guild_nick(self, guild: discord.Guild) -> bool:
        data = self.__get_json()
        if not str(guild.id) in data:
            return False
        
        old_nicks = data.pop(str(guild.id))
        self.__set_json(data)

        for key, old_nick in old_nicks.items():
            if key != "nick":
                if (member := guild.get_member(int(key))) is not None:
                    await self.__set_member_nick(member, old_nick)
        return True

    # Bot起動時
    @discord.Cog.listener()
    async def on_ready(self):
        data = self.__get_json()
        guilds = [self.bot.get_guild(int(key)) for key in data.keys()]

        for guild in guilds:
            await self.__change_guild_nick(guild)

	# プロフィールが編集されたとき
    @discord.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
    	# ニックネーム置き換えコマンドを実行中のギルドの場合
        if self.__guild_is_changed(before.guild):
            await self.__change_member_nick(after)
        
    # メンバーが新しく入ってきたとき
    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # ニックネーム置き換えコマンドを実行中のギルドの場合
        if self.__guild_is_changed(member.guild):
            await self.__change_member_nick(member)

    # ギルドメンバー全員のニックネームを変更するコマンド
    @discord.slash_command(name="change-nick", description="サーバーメンバー全員のニックネームを変更します (管理者のみ実行可)")
    async def command_change_nick(self, ctx: discord.ApplicationContext, nick: str):
        can_bot_manage_nicknames = any([role.permissions.manage_nicknames for role in ctx.me.roles])
        is_author_administrator = any([role.permissions.administrator for role in ctx.author.roles])
        if ctx.guild is None:
            await ctx.respond(
                embed=MyEmbed(
                    notif_type="error",
                    description="ダイレクトメッセージでは実行できません。"
                ),
                ephemeral=True
            )
            return
        elif not can_bot_manage_nicknames:
            await ctx.respond(
                embed=MyEmbed(
                    notif_type="error",
                    description="私にこのサーバーのメンバーのニックネームを変更する権限がありません。"
                ),
                ephemeral=True
            )
            return
        elif not is_author_administrator and ctx.author != ctx.guild.owner:
            await ctx.respond(
                embed=MyEmbed(
                    notif_type="error",
                    description="管理者権限のないメンバーは実行できません。"
                ),
                ephemeral=True
            )
            return
        
        await ctx.defer()
        await self.__change_guild_nick(ctx.guild, nick)
        await ctx.respond(
            embed=MyEmbed(
                notif_type="succeed",
                title="ニックネームを変更しました！",
                description=f"サーバーメンバーのニックネームを\n**{nick}**\nに変更しました。"
            ),
            delete_after=10
        )

    # ギルドメンバー全員のニックネームを元に戻すコマンド
    @discord.slash_command(name="restore-nick", description="サーバーメンバー全員のニックネームを元に戻します (管理者のみ実行可)")
    async def command_restore_nick(self, ctx: discord.ApplicationContext):
        can_bot_manage_nicknames = any([role.permissions.manage_nicknames for role in ctx.me.roles])
        is_author_administrator = any([role.permissions.administrator for role in ctx.author.roles])
        if ctx.guild is None:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="ダイレクトメッセージでは実行できません。"), ephemeral=True)
            return
        elif not can_bot_manage_nicknames:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="私にこのサーバーのメンバーのニックネームを変更する権限がありません。"), ephemeral=True)
            return
        elif not is_author_administrator and ctx.author != ctx.guild.owner:
            await ctx.respond(embed=MyEmbed(notif_type="error", description="管理者権限のないメンバーは実行できません。"))
            return
        
        await ctx.defer()
        if not await self.__restore_guild_nick(ctx.guild):
            await ctx.respond(
                embed=MyEmbed(
                    notif_type="error",
                    description="ニックネームは変更されていません。"
                ),
                ephemeral=True
            )
        else:
            await ctx.respond(
                embed=MyEmbed(notif_type="succeed", title="ニックネームを元に戻しました。"),
                delete_after=10
            )