FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
COPY . /bot
CMD ["python3", "-u", "main.py"]