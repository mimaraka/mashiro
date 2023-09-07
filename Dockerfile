FROM debian:bullseye-slim
RUN apt update -y && apt install -y python3.11 python3.11-pip ffmpeg
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
COPY . /bot
CMD ["python3", "main.py"]