FROM debian:latest

WORKDIR /ezstream

COPY MyMusic/*.py ./
RUN chmod 755 *.py

RUN apt-get update
RUN apt-get install -y ezstream madplay procps
RUN apt-get install -y python3-pip
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
