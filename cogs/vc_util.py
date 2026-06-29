import asyncio
from datetime import datetime, timezone, timedelta
import discord
import modules.util as util
from modules.myembed import MyEmbed
from modules.duration import Duration
from modules.common_embed import *


JST = timezone(timedelta(hours=9), 'JST')

class CogVCUtil(discord.Cog):
    vc = discord.SlashCommandGroup(**util.make_command_args('vc'))

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
                    self.vc_info[member.guild.id][member.voice.channel.id] = {
                        'time': datetime.now(JST),
                        'member': member
                    }
            # 移動前のチャンネルからメンバーがいなくなった場合
            if before.channel and len(before.channel.members) == 0:
                if self.vc_info.get(member.guild.id):
                    self.vc_info[member.guild.id].pop(before.channel.id, None)

    # /vc stats
    @vc.command(**util.make_command_args(['vc', 'stats']))
    async def command_vc_stats(self, ctx: discord.ApplicationContext):
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.respond(
                embed=EMBED_AUTHOR_NOT_CONNECTED,
                ephemeral=True
            )
            return

        info = self.vc_info.get(ctx.guild.id, {}).get(ctx.author.voice.channel.id)
        if info is None:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description='このボイスチャンネルの通話開始情報が記録されていません。'),
                ephemeral=True
            )
            return

        start_time: datetime = info['time']
        duration = Duration((datetime.now(JST) - start_time).total_seconds())

        embed = MyEmbed(title=f'ボイスチャット情報 (🔊 {ctx.author.voice.channel.name})')
        embed.add_field(name='通話開始時刻(JST)', value=start_time.strftime('%H:%M:%S (%m/%d/%Y)'), inline=False)
        embed.add_field(name='通話時間', value=duration.japanese_str() or '-', inline=False)
        member = info['member']
        embed.add_field(name='通話を開始した先生', value=util.get_member_text(member, bold=False, suffix=None), inline=False)

        await ctx.respond(
            embed=embed,
            ephemeral=True
        )

    # /vc kick-timer
    @vc.command(**util.make_command_args(['vc', 'kick-timer']))
    @discord.option('hours', description='時間', min_value=0, default=0)
    @discord.option('minutes', description='分', min_value=0, max_value=59, default=0)
    @discord.option('seconds', description='秒', min_value=0, max_value=59, default=0)
    async def command_vckickalarm(self, ctx: discord.ApplicationContext, hours: int, minutes: int, seconds: int):
        # コマンドを送ったメンバーがボイスチャンネルに居ない場合
        if ctx.author.voice is None:
            await ctx.respond(embed=EMBED_AUTHOR_NOT_CONNECTED, ephemeral=True)
            return
        
        duration = Duration(hours * 3600 + minutes * 60 + seconds)

        embed = MyEmbed(
            notif_type='succeeded',
            title='⏱️ ボイスチャンネル切断タイマーを設定しました。',
            description=f'{util.get_member_text(ctx.author)}は、**{duration.japanese_str()}** 後もボイスチャンネルに接続していた場合、切断されます。'
        )
        await ctx.respond(embed=embed, delete_after=10)
        await asyncio.sleep(duration.seconds)
        
        if ctx.author.voice and ctx.author.voice.channel is not None:
            try:
                await ctx.author.move_to(None, reason='ボイスチャンネル切断タイマー(/vckicktimer)により切断')
                await ctx.channel.send(
                    embed=MyEmbed(
                        title='⏱️ ボイスチャンネル切断タイマー',
                        description=f'{util.get_member_text(ctx.author)}をボイスチャンネルから切断しました。'
                    ),
                    delete_after=10
                )
            except discord.Forbidden:
                await ctx.channel.send(
                    embed=MyEmbed(
                        notif_type='error', description='先生が接続しているボイスチャンネルでは、私に先生を切断する権限が与えられていません。'),
                    delete_after=10
                )