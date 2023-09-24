import discord
import json
from modules.myembed import MyEmbed



# ギルド毎に作成されるニックネーム変更クラス
class NickChanger:
    # ギルドメンバーの元のニックネームを保存するjsonファイルのパス
    DATA_PATH = "data/old_nicks.json"

    def __init__(self, guild: discord.Guild) -> None:
        self.__guild = guild


    # 任意のメンバーのニックネームに任意の文字列を設定
    async def __set_nick(self, member: discord.Member, nick: str) -> bool:
        try:
            await member.edit(nick=nick)
            return True
        # Botよりも上位のロールがついたメンバーまたは管理者のプロフィールを更新しようとしたとき
        except discord.errors.Forbidden:
            return False
        
    
    # 全メンバーの元のニックネームが格納された辞書をjsonファイルから取得する
    def __get_json(self) -> None:
        with open(self.DATA_PATH, "r", encoding="shift-jis") as f:
            return json.load(f)
        

    # 全メンバーの元のニックネームが格納された辞書をjsonファイルに書き込む
    def __set_json(self, nick_dict: dict) -> None:
        with open(self.DATA_PATH, "w", encoding="shift-jis") as f:
            json.dump(nick_dict, f, indent=4)
          

    # 任意のメンバーのニックネームをjsonファイルから取得する
    # ユーザーIDが登録されていない場合、Falseを返す
    # ユーザーIDは登録されているが、元のニックネームが存在しない場合、Noneを返す
    def __get_old_nick(self, member: discord.Member) -> str | bool | None:
        data = self.__get_json()
        try:
            return data[str(self.__guild.id)][str(member.id)]
        except KeyError:
            return False
   

    # 任意のメンバーのユーザーIDと元のニックネームをjsonファイルに書き込む
    def __save_old_nick(self, member: discord.Member) -> None:
        data = self.__get_json()
        data[str(self.__guild.id)][str(member.id)] = member.nick
        self.__set_json(data)


    # 任意のメンバーのユーザーIDと元のニックネームをjsonファイルから削除
    def __delete_old_nick(self, member: discord.Member) -> None:
        data = self.__get_json()
        data[str(self.__guild.id)].pop(str(member.id))
        self.__set_json(data)


    # 置き換えられるニックネームをjsonファイルから取得
    def __get_replaced_nick(self):
        data = self.__get_json()
        try:
            return data[str(self.__guild.id)]["nick"]
        except KeyError:
            return False
        
    
    # 置き換えられるニックネームをjsonファイルに保存
    def __save_replaced_nick(self, nick):
        data = self.__get_json()
        data[str(self.__guild.id)]["nick"] = nick
        self.__set_json(data)

    
    # ギルド情報をjsonファイルから削除
    def __clear_guild_data(self):
        data = self.__get_json()
        data.pop(str(self.__guild.id))
        self.__set_json(data)


    # 指定したサーバーのメンバー全員のニックネームを変更
    async def change_nick(self, nick: str) -> None:
        for member in self.__guild.members:
            # 現在のニックネームが置き換え予定のnickと異なる場合
            if member.nick != nick:
                # ユーザー情報をjsonに追加していない場合
                if not self.is_changed(member):
                    # ユーザーID、元のニックネームをjsonに保存
                    self.__save_old_nick(member)
                # ニックネームを変更
                await self.__set_nick(member, nick)

    
    # ニックネームを元に戻す
    async def restore_old_nick(self) -> None:
        for member in self.__guild.members:
            # ニックネームが変更されている場合
            if self.is_changed(member):
                nick = self.__get_old_nick(member)
                self.__delete_old_nick(member)
                await self.__set_nick(member, nick)
        # ギルド情報をjsonファイルから削除
        self.__clear_guild_data()


    # ニックネームが変更されているかどうか(jsonに自分のユーザーIDが登録されているか)
    def is_changed(self, member: discord.Member):
        return self.__get_old_nick(member) is not False



class NickChanger(discord.Cog):
    DATA_PATH = "data/old_nicks.json"

    # コンストラクタ
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot


    # 全メンバーの元のニックネームが格納された辞書をjsonファイルから取得する
    def __get_json(self) -> dict:
        with open(self.DATA_PATH, "r", encoding="shift-jis") as f:
            return json.load(f)
        

    # 全メンバーの元のニックネームが格納された辞書をjsonファイルに書き込む
    def __set_json(self, nick_dict: dict) -> None:
        with open(self.DATA_PATH, "w", encoding="shift-jis") as f:
            json.dump(nick_dict, f, indent=4)


    # 任意のメンバーのニックネームに任意の文字列を設定
    async def __set_nick(self, member: discord.Member, nick: str) -> bool:
        try:
            await member.edit(nick=nick)
            return True
        # Botよりも上位のロールがついたメンバーまたは管理者のプロフィールを更新しようとしたとき
        except discord.errors.Forbidden:
            return False
    

    # 指定したギルドメンバーのニックネームを変更
    # 変更されればTrue、変更されなければFalseを返す
    async def __change_member_nick(self, member: discord.Member, nick: str) -> bool:
        if member.nick != nick:
            try:
                await member.edit(nick=nick)
                return True
            except discord.errors.Forbidden:
                pass
        return False
    

    # ニックネーム変更コマンドが適用されたギルドであるかどうか
    def __guild_is_nick_changed(self, guild) -> bool:
        data = self.__get_json()
        return str(guild.id) in data.keys()
    

    # ギルドメンバー毎の元のニックネームをjsonファイルに登録
    def __save_member_old_nick(self, member: discord.Member):
        data = self.__get_json()
        data[str(member.guild.id)][str(member.id)] = member.nick


    # ギルド毎の置き換え後のニックネームをjsonファイルから取得
    def __get_guild_replaced_nick(self, guild: discord.Guild, nick: str) -> str | None:
        data = self.__get_json()
        try:
            return data[str(guild.id)]["nick"]
        except KeyError:
            return None


    # ギルド毎の置き換え後のニックネームをjsonファイルに登録
    def __save_guild_replaced_nick(self, guild: discord.Guild, nick: str) -> None:
        data = self.__get_json()
        data[str(guild.id)]["nick"] = nick
        

    # 指定したギルドのメンバー全員のニックネームを変更
    async def __change_nick(self, guild: discord.Guild, nick: str) -> None:
        for member in self.__guild.members:
            # 現在のニックネームが置き換え予定のnickと異なる場合
            if member.nick != nick:
                # ユーザー情報をjsonに追加していない場合
                if not self.is_changed(member):
                    # ユーザーID、元のニックネームをjsonに保存
                    self.__save_old_nick(member)
                # ニックネームを変更
                await self.__set_nick(member, nick)


    # Bot起動時
    @discord.Cog.listener()
    async def on_ready(self):
        data = self.__get_json()
        guilds = [self.bot.get_guild(int(key)) for key in data.keys()]

        for guild in guilds:
            # ギルド毎に設定された、置き換えるニックネーム
            nick = data[str(guild.id)]["nick"]
            self.__change_nick(guild, nick)


    @discord.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # ニックネームがBotによって変更されたユーザーの場合
        nc = NickChanger(after.guild)
        if nc.is_changed():
            await nc.change_nick()

        
    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if self.__guild_is_nick_changed(member.guild):
            self.__change_member_nick(member, self.__get_guild_replaced_nick(member.guild))
        pass


    # ギルドメンバー全員のニックネームを変更するコマンド
    @discord.slash_command(name="change-nick", description="サーバーメンバー全員のニックネームを変更します (管理者のみ実行可)")
    async def change_nick(self, ctx: discord.ApplicationContext, nick: str):
        if ctx.guild is None:
            ctx.respond(embed=MyEmbed(notif_type="error", description="ダイレクトメッセージでは実行できません。"), ephemeral=True)
            return
        elif not ctx.me.top_role.permissions.manage_nicknames:
            ctx.respond(embed=MyEmbed(notif_type="error", description="私にこのサーバーのメンバーのニックネームを変更する権限がありません。"), ephemeral=True)
            return
        elif not ctx.author.top_role.permissions.administrator and ctx.author != ctx.guild.owner:
            ctx.respond(embed=MyEmbed(notif_type="error", description="管理者権限のないメンバーは実行できません。"))
            return
        
        # このコマンドがすでに実行されている場合
        if self.__guild_is_nick_changed(ctx.guild):
            ctx.respond(embed=MyEmbed(notif_type="error", description="このコマンドはすでに実行されているようです。"))
            return
        # 警告ダイアログ
        self.__save_guild_replaced_nick(ctx.guild, nick)
        for member in ctx.guild.members:
            self.__save_member_old_nick(member)
            self.__change_member_nick(member, nick)


    # ギルドメンバー全員のニックネームを元に戻すコマンド
    @discord.slash_command(name="restore-nick", description="サーバーメンバー全員のニックネームを元に戻します (管理者のみ実行可)")
    async def restore_nick(self, ctx: discord.ApplicationContext):
        pass