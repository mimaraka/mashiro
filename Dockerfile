FROM python:3.10
RUN apt update -y && apt install -y ffmpeg
WORKDIR /bot
COPY requirements.txt /bot/
RUN pip3 install -r requirements.txt
RUN pip3 install git+https://github.com/Pycord-Development/pycord@6888b902b60066ade8724e47f68c6236f2fef1f1
COPY . /bot
CMD ["python3", "-u", "main.py"]