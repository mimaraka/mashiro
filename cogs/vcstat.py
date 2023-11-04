from datetime import datetime
import discord
from modules.myembed import MyEmbed


class CogVcstat(discord.Cog):
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
                    self.vc_info[member.guild.id][after.channel.id] = datetime.now()
            # 移動前のチャンネルからメンバーがいなくなった場合
            if before.channel and len(before.channel.members) == 0:
                self.vc_info[member.guild.id].pop(before.channel.id)

    # /vcstat
    @discord.slash_command(name='vcstat', description='通話の情報を表示します。')
    async def command_vcstat(self, ctx: discord.ApplicationContext):
        if ctx.author.voice.channel is None:
            await ctx.respond(
                embed=MyEmbed(notif_type='error', description='先生がボイスチャンネルに接続されていないようです。'),
                ephemeral=True
            )
            return

        start_time: datetime = self.vc_info[ctx.guild.id][ctx.author.voice.channel.id]
        total_seconds = int((datetime.now() - start_time).total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        length = ''
        if 0 < hours:
            length += f'{hours}時間'
        if 0 < minutes:
            length += f'{minutes}分'
        if 0 < seconds:
            length += f'{seconds}秒'

        await ctx.respond(embed=MyEmbed(
            title='ボイスチャット情報',
            description=f'通話開始時刻 : **{start_time.strftime("%H:%M:%S %m/%d/%Y")}**\n通話時間 : **{length or "-"}**'
        ))