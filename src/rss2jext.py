import argparse
import json
import os

import requests
from dotenv import load_dotenv
from ffmpeg import FFmpeg, Progress
from mutagen.oggvorbis import OggVorbis
from rss_parser import Parser
from rss_parser.models.item import Item
from rss_parser.models.types.tag import Tag

from minecraft import ResourcePack
from pterodactyl import Client

__version__ = "1.0.0"

__cwd__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
__data_dir__ = os.path.realpath(os.path.join(__cwd__, "../data"))

# TODO: Pull version string from pyproject.toml
USER_AGENT = f"rss2jext/{__version__}"


def load_servers() -> dict:
    with open(
        os.path.join(__data_dir__, "servers.json"), encoding="utf-8"
    ) as servers_json:
        return json.load(servers_json)


def rss_feed(feed_url: str):
    print(f"[RSS] Downloading feed from {feed_url}...")

    feed_req = requests.get(feed_url, timeout=1000, headers={"User-Agent": USER_AGENT})
    feed_req.raise_for_status()

    return Parser.parse(feed_req.text)


def rss_latest_episode(rss) -> Tag[Item]:
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
def download_mp3(url: str) -> str:
    # TODO: Don't hardcode timeout
    req = requests.get(
        url, headers={"User-Agent": USER_AGENT}, timeout=1000, stream=True
    )

    req.raise_for_status()

    outfile = os.path.join(__data_dir__, "tmp", "episode.mp3")

    with open(outfile, "wb") as of:
        # not sure if there's a better value for chunk_size
        for chunk in req.iter_content(chunk_size=1024):
            of.write(chunk)

        return outfile


def mp3_to_ogg(infile: str, *, verbose=False) -> str:
    outfile = os.path.join(__data_dir__, "tmp", "episode.ogg")
    # Re-encode the audio file using ffmpeg
    # ffmpeg flags to reproduce the format of vanilla records appear to be
    #   -c:a libvorbis -q:a 2 -ar 44100 -ac 1

    # TODO: Check if we can pass None to options that don't take an argument (-vn)
    output_settings = {
        "vn": None,
        "codec:a": "libvorbis",
        "qscale:a": 2,
        "ar": 44100,
        "ac": 1,
    }

    if os.getenv("AUDIO_QUALITY"):
        output_settings["qscale:a"] = int(os.getenv("AUDIO_QUALITY"))
        print(f"[ffmpeg] qscale:a set to {output_settings['qscale:a']}")

    if os.getenv("AUDIO_SAMPLERATE"):
        output_settings["ar"] = int(os.getenv("AUDIO_SAMPLERATE"))
        print(f"[ffmpeg] audio sample rate set to {output_settings['ar']}")

    if int(os.getenv("AUDIO_NORMALIZE")):
        output_settings["af"] = "loudnorm"
        print("[ffmpeg] loudness normalization enabled.")

    ffmpeg = (
        FFmpeg()
        .option("y")
        .input(infile)
        .output(
            outfile,
            output_settings,
        )
    )

    @ffmpeg.on("progress")
    def on_progress(progress: Progress) -> None:
        if verbose:
            print(f"[ffmpeg] {progress}")

    ffmpeg.execute()

    return outfile


def build_packs(versions: list, *, pack_description: str):
    for rp_version in versions:
        print(f"[minecraft] Building resourcepack version {rp_version}...")

        rp = ResourcePack(
            pack_version=rp_version,
            pack_description=f"Podcast About List {pack_description}",
            data_dir=__data_dir__,
            # shutil.make_archive appends .zip already
            output_file=os.path.join(
                __data_dir__, "out", str(os.getenv("RESOURCE_PACK_NAME"))
            ),
        )

        rp_filename = rp.build()
        print(f"[minecraft] Resource pack built: {rp_filename}")


def build_jext_config(*, oggfile, rss_feed):
    # TODO: write this. Taco Bell time yum!!!
    pass


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="rss2jext",
        description="Listen to the latest episode a podcast in Minecraft!",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-encode", action="store_true")
    args = parser.parse_args()

    feed = rss_feed(os.getenv("RSS_URL"))
    episode = rss_latest_episode(feed)

    ptero_servers = load_servers()

    print(f"[RSS] Latest episode Title: {episode.title}")
    print(f"[RSS] Latest episode GUID: {episode.guid}")

    ep_url = extract_mp3_url(episode=episode)

    print(f"[RSS] Latest episode URL: {ep_url}")

    if args.skip_download:
        print("[mp3] Not downloading the episode sue to --skip-download")
    else:
        print("[RSS] Downloading episode mp3...")
        mp3_file = download_mp3(ep_url)
        print("[RSS] Finished downloading episode file!")

    if args.skip_encode:
        print("[ffmpeg] Skipping mp3 -> ogg encoding due to --skip-encode")
    else:
        print(f"[ffmpeg] encoding {mp3_file} -> ogg")
        ogg_file = mp3_to_ogg(mp3_file)
        print(f"[ffmpeg] done: {ogg_file}")

    build_packs([15, 18], pack_description=episode.title)

    audio_duration = OggVorbis(ogg_file).info.length


if __name__ == "__main__":
    main()
