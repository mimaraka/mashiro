FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
# yt-dlp 2026系のYouTube抽出にはJavaScriptランタイムが必須(無いとbot検出を回避できない)。
# yt-dlpのデフォルトランタイムであるDenoのバイナリを公式イメージからコピーする。
COPY --from=denoland/deno:bin-2.9.0 /deno /usr/local/bin/deno
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
COPY . /bot
CMD ["python3", "-u", "main.py"]