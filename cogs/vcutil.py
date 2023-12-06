import asyncio
from datetime import datetime, timezone, timedelta
import discord
from modules.myembed import MyEmbed
from modules.duration import Duration
from modules.vc_common import *


JST = timezone(timedelta(hours=9), 'JST')

class CogVcutil(discord.Cog):
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot
        self.vc_info = {}

    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # メンバーがVCを移動した場合
        if after.channel != before.channel:
            # VCに接続・移動した場合
            if after.channel is not None:
                # それまでVCに誰も居なかった場合、記録を開始
                if len(after.channel.members) == 1:
                    if self.vc_info.get(member.guild.id) is None:
                        self.vc_info[member.guild.id]  = {}
                    self.vc_info[member.guild.id][after.channel.id] = datetime.now(JST)
            # 移動前のチャンネルからメンバーがいなくなった場合
            if before.channel and len(before.channel.members) == 0:
                self.vc_info[member.guild.id].pop(before.channel.id)

    # /vcstat
    @discord.slash_command(name='vcstat', description='現在アクティブな通話の情報を表示します。')
    async def command_vcstat(self, ctx: discord.ApplicationContext):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description='先生がボイスチャンネルに接続されていないようです。'),
                ephemeral=True
            )
            return

        start_time: datetime = self.vc_info[ctx.guild.id][ctx.author.voice.channel.id]
        duration = Duration((datetime.now(JST) - start_time).total_seconds())

        await ctx.respond(
            embed=MyEmbed(
                title=f'ボイスチャット情報 (🔊 {ctx.author.voice.channel.name})',
                description=f'**通話開始時刻(JST)** : {start_time.strftime("%H:%M:%S (%m/%d/%Y)")}\n**通話時間** : {duration.japanese_str() or "-"}'
            ),
            ephemeral=True
        )

    @discord.slash_command(name='vckicktimer', description='指定した時間の経過後に先生をボイスチャンネルから切断します。')
    @discord.option('hours', description='時間', min_value=0, default=0)
    @discord.option('minutes', description='分', min_value=0, max_value=59, default=0)
    @discord.option('seconds', description='秒', min_value=0, max_value=59, default=0)
    async def command_vckickalarm(self, ctx: discord.ApplicationContext, hours: int, minutes: int, seconds):
        # マシロにメンバーを移動させる権限がない場合
        if not ctx.channel.permissions_for(ctx.guild.me).move_members:
            await ctx.respond(embed=MyEmbed(notif_type='error', description='私に先生をボイスチャンネルから移動させる権限がありません。'), ephemeral=True)
            return
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        duration = Duration(hours * 3600 + minutes * 60 + seconds)

        embed = MyEmbed(
            notif_type='succeeded',
            title='⏱️ ボイスチャンネル切断タイマーを設定しました。',
            description=f'**{ctx.author.display_name}**(`{ctx.author.name}`) 先生は、**{duration.japanese_str()}** 後もボイスチャンネルに接続していた場合、切断されます。'
        )
        await ctx.respond(embed=embed, delete_after=10)
        await asyncio.sleep(duration.seconds)
        
        if ctx.author.voice and ctx.author.voice.channel is not None:
            await ctx.author.move_to(None)
            await ctx.respond(
                embed=MyEmbed(
                    title='⏱️ ボイスチャンネル切断タイマー',
                    description=f'**{ctx.author.display_name}**(`{ctx.author.name}`) 先生をボイスチャンネルから切断しました。'
                ),
                delete_after=10
            )