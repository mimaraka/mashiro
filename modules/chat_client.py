import discord
import g4f.client
import google.generativeai as genai
import os
import time
import typing
from constants import GEMINI_AVAILABLE_GUILDS
from character_config import CHATBOT_SYSTEM_INSTRUCTION


class ChatClient:
    def __init__(self):
        self.conversations: typing.Dict[int, typing.Dict[str, typing.List[dict] | genai.ChatSession]] = {}

        self.g4f_client = g4f.client.Client()
        genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
        self.gemini_pro = genai.GenerativeModel(model_name='gemini-1.5-pro', system_instruction=[CHATBOT_SYSTEM_INSTRUCTION])

    def is_gemini_available(self, channel: discord.TextChannel | discord.DMChannel | None) -> bool:
        """Check if Gemini is available for the given guild."""
        return channel and type(channel) == discord.TextChannel and channel.guild.id in GEMINI_AVAILABLE_GUILDS


    def start_conversation(self, channel: discord.TextChannel):
        """Start a new conversation for the specified channel."""
        if channel.id not in self.conversations:
            if self.is_gemini_available(channel):
                self.conversations[channel.id] = {
                    'time': time.time(),
                    'conversation': self.gemini_pro.start_chat()
                }
            else:
                self.conversations[channel.id] = {
                    'time': time.time(),
                    'conversation': [{'role': 'system', 'content': CHATBOT_SYSTEM_INSTRUCTION}]
                }


    def reset_conversation(self, channel: discord.TextChannel):
        """Reset the conversation for a specific channel."""
        if channel.id in self.conversations:
            del self.conversations[channel.id]

    
    def generate_response(self, channel: discord.TextChannel, user_input: str) -> str:
        """Generate a response based on the user input."""
        if channel.id not in self.conversations or self.conversations[channel.id]['time'] + 43200 < time.time():
            self.start_conversation(channel)

        info = self.conversations[channel.id]
        info['time'] = time.time()

        if self.is_gemini_available(channel):
            session = info.get('conversation')
            response = session.send_message(
                user_input,
                safety_settings={
                    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT : genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH : genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT : genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT : genai.types.HarmBlockThreshold.BLOCK_NONE
                }
            )
            return response.text
        else:
            conversation = info.get('conversation')
            conversation.append({'role': 'user', 'content': user_input})
            response = self.g4f_client.chat.completions.create(
                model='gpt-4o-mini',
                messages=conversation
            )
            result = response.choices[0].message.content
            conversation.append({'role': 'assistant', 'content': result})
            return result