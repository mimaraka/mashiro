FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
RUN pip3 install -r requirements.txt
WORKDIR /bot
COPY /.env /bot/
COPY . /bot
CMD ["python3", "main.py"]