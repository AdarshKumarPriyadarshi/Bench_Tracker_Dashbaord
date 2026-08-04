FROM artifact.swf.i.mercedes-benz.com/dockerhub/python:3.8-slim

RUN apt-get update && apt-get install -y \
    iputils-ping \
    && apt-get clean

WORKDIR /repo

COPY ./requirement*.txt /repo/


ENV VIRTUAL_ENV=/repo/src/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN pip3 install -r requirements-dev.txt

COPY . /repo/
