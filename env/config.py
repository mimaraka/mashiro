import configparser
import os

class Config():
    def __init__(self):
        path = os.path.join(os.path.dirname(__file__), 'config.ini')
        self.config = configparser.ConfigParser()
        self.config.read(path, 'UTF-8')

    @property
    def bot_token(self) -> str:
        return str(self.config['TOKENS']['BOT_TOKEN'])
    
    @property
    def youtube_api_key(self) -> str:
        return str(self.config["YOUTUBE"]["API_KEY"])
    
    @property
    def spotify_client_id(self) -> str:
        return str(self.config["SPOTIFY"]["CLIENT_ID"])
    
    @property
    def spotify_client_secret(self) -> str:
        return str(self.config["SPOTIFY"]["CLIENT_SECRET"])