import json
import os

# import re
import requests
from dotenv import load_dotenv
from ffmpeg import FFmpeg, Progress
from rss_parser import Parser
from rss_parser.models.item import Item
from rss_parser.models.types.tag import Tag

from pterodactyl.api import Client

__cwd__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# TODO: Pull version string from pyproject.toml
USER_AGENT = "rss2jext/1.0.0"


def load_servers() -> dict:
    with open(
        os.path.join(__cwd__, "data", "servers.json"), encoding="utf-8"
    ) as servers_json:
        return json.load(servers_json)


def rss_latest_episode(feed_url: str) -> Tag[Item]:
    # TODO: Validate RSS_URL
    # TODO: Don't hardcode timeout value
    feed_req = requests.get(feed_url, timeout=1000, headers={"User-Agent": USER_AGENT})
    feed_req.raise_for_status()

    rss = Parser.parse(feed_req.text)

    print(f"[RSS] Feed language: {rss.channel.language}")
    print(f"[RSS] Feed version: {rss.version}")

    rss_items = rss.channel.items
    # The feed is ordered by date ascending so the newest episodes are at the end
    # of rss_items
    rss_items.reverse()

    i = 0

    # TODO: Check the number of items in rss_items before entering this loop
    while True:
        i = i + 1

        latest_rss_item = rss_items.pop()
        title = latest_rss_item.title.lower()

        # TODO: Make this filter customizable
        if not title.startswith("teaser"):
            return latest_rss_item

        # HACK: Find a better way of handling this edge case
        if i > 5:  # abort after 5 iterations so we're not here all day
            raise RuntimeError("Could not find a non-teaser episode after 5 tries.")


def extract_mp3_url(episode: Item) -> str:
    return episode.enclosure.attributes["url"]


# TODO: Maybe add an extra argument to this that lets us specify where to save the file
def download_mp3(url: str):
    # TODO: Don't hardcode timeout
    req = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=1000, stream=True
    )

    req.raise_for_status()

    with open(os.path.join(__cwd__, "data", "tmp", "episode.mp3"), "wb") as outfile:
        # not sure if there's a better value for chunk_size
        for chunk in req.iter_content(chunk_size=1024):
            outfile.write(chunk)


def mp3_to_ogg(infile: str, verbose=False):
    # Re-encode the audio file using ffmpeg
    # ffmpeg flags to reproduce the format of vanilla records appear to be
    #   -c:a libvorbis -q:a 2 -ar 44100 -ac 1

    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(infile)
        .output(
            os.path.join(__cwd__, "data", "tmp", "episode.ogg"),
            {"codec:a": "libvorbis", "qscale:a": 2, "ar": 44100, "ac": 1},
        )
    )

    @ffmpeg.on("progress")
    def on_progress(progress: Progress) -> None:
        if verbose:
            print(f"[ffmpeg] {progress}")

    ffmpeg.execute()


def main() -> None:
    load_dotenv()

    episode = rss_latest_episode(os.getenv("RSS_URL"))
    servers = load_servers()

    print(f"[RSS] Latest episode Title: {episode.title}")
    print(f"[RSS] Latest episode GUID: {episode.guid}")

    ep_url = extract_mp3_url(episode=episode)

    print(f"[RSS] Latest episode URL: {ep_url}")

    print("[RSS] Downloading episode mp3...")

    download_mp3(ep_url)

    print("[RSS] Finished downloading episode file!")

    print("[ffmpeg] encoding mp3 -> ogg")
    mp3_to_ogg(os.path.join(__cwd__, "data", "out", "episode.mp3"))


if __name__ == "__main__":
    main()
