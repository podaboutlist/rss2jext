FROM python:3.11-alpine

#ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=true

ARG UID
ARG GID

RUN apk add --no-cache ffmpeg==6.0-r15

WORKDIR /app

COPY requirements.txt .

RUN [ "python3", "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt" ]

COPY . .

VOLUME [ "/app/data" ]

USER $UID:$GID

ENTRYPOINT [ "python3", "src/rss2jext.py" ]
