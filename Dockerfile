FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
RUN pip3 install -U https://github.com/coletdjnz/yt-dlp-youtube-oauth2/archive/refs/heads/master.zip
COPY . /bot
CMD ["python3", "-u", "main.py"]