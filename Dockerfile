FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
RUN pip3 install git+https://github.com/Pycord-Development/pycord@16c696cd9948b016b097e1c0b03c54a5bfc4b994
COPY . /bot
CMD ["python3", "-u", "main.py"]