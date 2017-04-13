FROM ubuntu:yakkety
RUN apt-get update && apt-get install -y python3.6 python3.6-dev python3-pip \
    netcat vim net-tools curl wget bsdgames libzmq5-dev

ADD requirements.txt /root/hmbot/requirements.txt
RUN python3.6 -m pip install --upgrade pip
RUN python3.6 -m pip install -r /root/hmbot/requirements.txt

ADD . /root/hmbot
WORKDIR /root/hmbot

CMD python3.6 endpoint.py & python3.6 sysproxy.py
