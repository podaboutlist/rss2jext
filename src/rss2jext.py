import json
import os

# import re
import requests
from dotenv import load_dotenv
from ffmpeg import FFmpeg, Progress
from rss_parser import Parser

from pterodactyl.api import Client

__cwd__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))


def main() -> None:
    load_dotenv()

    feed_url = os.getenv("RSS_URL")

    servers = None

    with open(
        os.path.join(__cwd__, "data", "servers.json"), encoding="utf-8"
    ) as servers_json:
        servers = json.load(servers_json)

    # TODO: Pull version string from pyproject.toml
    user_agent = "rss2jext/1.0.0"

    # TODO: Validate RSS_URL
    # TODO: Don't hardcode timeout value
    feed_req = requests.get(feed_url, timeout=1000, headers={"User-Agent": user_agent})
    feed_req.raise_for_status()

    rss = Parser.parse(feed_req.text)

    print(f"[RSS] Feed language: {rss.channel.language}")
    print(f"[RSS] Feed version: {rss.version}")

    rss_items = rss.channel.items
    rss_items.reverse()

    latest_full_episode = None
    i = 0

    while True:
        i = i + 1

        latest_rss_item = rss_items.pop()
        title = latest_rss_item.title.lower()

        if not title.startswith("teaser"):
            latest_full_episode = latest_rss_item
            break

        if i > 5:  # abort after 5 iterations so we're not here all day
            raise RuntimeError("Could not find a non-teaser episode after 5 tries.")

    print(f"[RSS] Latest episode Title: {latest_full_episode.title}")
    print(f"[RSS] Latest episode GUID: {latest_full_episode.guid}")

    ep_url = json.loads(
        str(latest_full_episode.enclosure.attributes).replace("'", '"')
    )["url"]

    print(f"[RSS] Latest episode URL: {ep_url}")

    ep_raw = requests.get(
        ep_url, headers={"User-Agent": user_agent}, timeout=1000, stream=True
    )

    ep_raw.raise_for_status()

    print("[RSS] Downloading episode file", end="")

    with open(os.path.join(__cwd__, "data", "out", "episode.mp3"), "wb") as outfile:
        # not sure if there's a better value for chunk_size
        for chunk in ep_raw.iter_content(chunk_size=1024):
            outfile.write(chunk)

    print("[RSS] Finished downloading episode file!")

    # Re-encode the audio file using ffmpeg
    # ffmpeg flags to reproduce the format of vanilla records appear to be
    #   -c:a libvorbis -q:a 2 -ar 44100 -ac 1

    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(os.path.join(__cwd__, "data", "out", "episode.mp3"))
        .output(
            os.path.join(__cwd__, "data", "out", "episode.ogg"),
            {"codec:a": "libvorbis", "qscale:a": 2, "ar": 44100, "ac": 1},
        )
    )

    @ffmpeg.on("progress")
    def on_progress(progress: Progress) -> None:
        print(f"[ffmpeg] {progress}")

    print("[ffmpeg] encoding mp3 -> ogg")
    ffmpeg.execute()


if __name__ == "__main__":
    main()
