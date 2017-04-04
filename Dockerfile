FROM ubuntu:yakkety
RUN apt-get update && apt-get install -y python3.6 python3.6-dev python3-pip \
    netcat vim net-tools curl wget
COPY . /root/hmbot
WORKDIR /root/hmbot
RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install -r requirements.txt
EXPOSE 8080
CMD python3.6 hmbot.py
