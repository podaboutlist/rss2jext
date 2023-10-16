FROM python:3.11-alpine

#ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=true

RUN apk update && apk add ffmpeg

WORKDIR /app

COPY requirements.txt .

RUN [ "python3", "-m", "pip", "install", "-r", "requirements.txt" ]

COPY . .

VOLUME [ "/app/data" ]

ENTRYPOINT [ "python3", "src/rss2jext.py" ]
