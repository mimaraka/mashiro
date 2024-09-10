import asyncio
import datetime
import discord
import g4f.client
import random
import re
import time
import typing
import character_config as cc
import constants as const
import modules.util as util
from modules.attachments import find_valid_urls
from modules.myembed import MyEmbed


g_conversations: typing.Dict[int, typing.List[dict]] = {}

class CogCharacter(discord.Cog):
    def __init__(self, bot) -> None:
        self.bot: discord.Bot = bot
        self.g4f_client = g4f.client.Client()


    # ランダムでキャラクターのセリフを返す関数
    def get_character_quote(self):
        special_quotes = []
        today = datetime.date.today()
        # 誕生日の場合
        if today == datetime.date(today.year, cc.CHARACTER_BIRTHMONTH, cc.CHARACTER_BIRTHDAY):
            special_quotes = cc.CHARACTER_QUOTES_BIRTHDAY
        # ハロウィン、クリスマス、正月の場合
        elif today == datetime.date(today.year, 10, 31):
            special_quotes = cc.CHARACTER_QUOTES_HALLOWEEN
        elif today == datetime.date(today.year, 12, 25):
            special_quotes = cc.CHARACTER_QUOTES_CHRISTMAS
        elif today == datetime.date(today.year, 1, 1):
            special_quotes = cc.CHARACTER_QUOTES_NEWYEAR

        if special_quotes:
            return random.choice(random.choice([cc.CHARACTER_QUOTES, special_quotes]))
        else:
            return random.choice(cc.CHARACTER_QUOTES)


    # キャラクターのセリフをランダムに送信
    @discord.slash_command(name=cc.CHARACTER_COMMAND_NAME, description=cc.CHARACTER_COMMAND_DESCRIPTION)
    @discord.option('n', description='送信する回数(1~99)', min_value=1, max_value=99, default=1, required=False)
    async def command_character(self, ctx: discord.ApplicationContext, n: int):
        for _ in range(n):
            await ctx.respond(self.get_character_quote())


    @discord.slash_command(**util.make_command_args('reset-conversation'))
    async def command_reset_conversation(self, ctx: discord.ApplicationContext):
        global g_conversations
        if not ctx.channel_id in g_conversations:
            await ctx.respond(embed=MyEmbed(notif_type='error', description=cc.CHARACTER_TEXT['error_no_conversation']), ephemeral=True)
            return
        g_conversations.pop(ctx.channel.id)
        await ctx.respond(embed=MyEmbed(title=cc.CHARACTER_TEXT['reset_conversation']), delete_after=10)


    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        # メッセージにBotへのメンションが含まれているとき
        if self.bot.user.id in [m.id for m in message.mentions]:
            # メンションの後に何か文字があった場合、ChatGPTにより返答
            if content := re.sub(rf'[#*_\-|~]{{0,2}}<@{const.BOT_USER_ID}>[*_\-|~]{{0,2}}\s*', '', message.content):
                global g_conversations
                conversation = {}
                prompt_content = [
                    {'type': 'text', 'text': content}
                ]

                async with message.channel.typing():
                    if g_conversations.get(message.channel.id):
                        conversation = g_conversations.pop(message.channel.id)

                    # Vision
                    if valid_urls := await find_valid_urls(message, const.MIMETYPES_IMAGE):
                        for url in valid_urls:
                            prompt_content.append({
                                'type': 'image_url',
                                'image_url': {'url': url}
                            })

                    # 過去の会話が存在しないか、最後の回答から12時間以上経過した場合
                    if not conversation.get('messages') or time.time() - conversation['time'] > 43200:
                        initial_message = {
                            'role': 'system',
                            'content': cc.GPT_PROMPT
                        }
                        # 会話をリセット
                        conversation['messages'] = [initial_message]
                    conversation['messages'].append({
                        'role': 'user',
                        'content': prompt_content
                    })

                    # 時間を記録
                    conversation['time'] = time.time()

                    response = self.g4f_client.chat.completions.create(
                        model='gpt-4o-mini',
                        messages=conversation['messages']
                    )

                    result = response.choices[0].message.content

                    # 回答文のコマンド処理
                    # {play:曲名}が含まれている場合、音楽再生
                    pattern_play = re.compile(r'\{play:(.+?)\}\s*')
                    if m := re.search(pattern_play, result):
                        query = m.group(1)
                        result = re.sub(pattern_play, '', result)
                        cog_music = self.bot.get_cog('CogMusic')
                        await cog_music.play(message.channel, message.author, [query], interrupt=True)

                    # {selfie}が含まれている場合、自撮りを送信
                    pattern_selfie = re.compile(r'\{selfie\}\s*')
                    if re.search(pattern_selfie, result):
                        result = re.sub(pattern_selfie, '', result)
                        images = ['selfie_01.png', 'selfie_02.png', 'selfie_03.png', 'selfie_04.png']
                        await asyncio.sleep(3)
                        await message.channel.send(file=discord.File(f'data/assets/{random.choice(images)}'))

                    result_list = [result[i:i + 2000] for i in range(0, len(result), 2000)]
                    for r in result_list:
                        await message.channel.send(r)
                
                # ChatGPTの回答を追加
                conversation['messages'].append(response.choices[0].message.to_json())
                # 会話を記録
                g_conversations[message.channel.id] = conversation
                return
                
            # キャラクターのセリフをランダムで送信
            async with message.channel.typing():
                await asyncio.sleep(4)
                await message.channel.send(self.get_character_quote())