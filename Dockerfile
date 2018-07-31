FROM python:3.6
WORKDIR /opt/hmbot
ENV DEBIAN_FRONTEND noninteractive

RUN groupadd hmbot -g 65533 \
&& useradd -u 65533 -g hmbot -s /bin/bash -M -d /opt/hmbot hmbot

RUN apt-get update \
&& apt-get upgrade -y \
&& apt-get install -y netcat vim net-tools curl wget bsdgames libzmq5-dev \
&& rm -fr /var/lib/apt/lists/* /var/cache/apt/archives/*

COPY --chown=hmbot . /opt/hmbot
RUN chown -R hmbot.hmbot /opt/hmbot

USER hmbot
RUN python3.6 -m pip install --upgrade pip --user
RUN python3.6 -m pip install --no-cache-dir --user -r /opt/hmbot/requirements.txt
CMD ["python3.6","endpoint.py","&","python3.6","sysproxy.py"]
