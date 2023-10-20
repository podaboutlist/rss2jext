import argparse
import json
import math
import os
import shutil

import requests
from dotenv import load_dotenv
from ffmpeg import FFmpeg, Progress
from mutagen.oggvorbis import OggVorbis

from minecraft import ResourcePack, populate_discs_json
from pterodactyl import Client
from rss_helper import RSSHelper

__version__ = "1.0.0"

__cwd__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

__resource_dir__ = os.path.realpath(os.path.join(__cwd__, "../res"))

__data_dir__ = os.path.realpath(os.path.join(__cwd__, "../data"))

__out_dir__ = os.path.join(__data_dir__, "out")
__templates_dir__ = os.path.join(__data_dir__, "templates")
__tmp_dir__ = os.path.join(__data_dir__, "tmp")

# TODO: Pull version string from pyproject.toml
USER_AGENT = f"rss2jext/{__version__}"


def first_run_setup():
    """Copy res/ to data/ recursively.

    These files will be accessible on the host machine from the Docker image.
    """
    print("[first run] copying res/ to data/")
    shutil.copytree(__resource_dir__, __data_dir__)


def load_servers() -> dict:
    with open(
        os.path.join(__data_dir__, "servers.json"), encoding="utf-8"
    ) as servers_json:
        return json.load(servers_json)


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


def main() -> None:
    load_dotenv()

    # ./data needs to exist when using a bind mount with docker so we check
    # subdirectories as well
    for dir_to_check in [__data_dir__, __out_dir__, __templates_dir__, __tmp_dir__]:
        if not os.path.isdir(dir_to_check):
            first_run_setup()
            break

    parser = argparse.ArgumentParser(
        prog="rss2jext",
        description="Listen to the latest episode a podcast in Minecraft!",
    )
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-encode", action="store_true")
    args = parser.parse_args()

    ptero_servers = load_servers()

    rss_feed = RSSHelper(os.getenv("RSS_URL"), user_agent=USER_AGENT)
    latest_episode = rss_feed.latest_episode()

    print(f"[RSS] Latest episode Title: {latest_episode.title}")
    print(f"[RSS] Latest episode GUID: {latest_episode.guid}")

    ep_url = rss_feed.episode_file_url(rss_feed.latest_episode())

    print(f"[RSS] Latest episode URL: {ep_url}")

    if args.skip_download:
        print("[mp3] Not downloading the episode sue to --skip-download")
    else:
        print("[RSS] Downloading episode mp3...")
        mp3_file = download_mp3(ep_url)
        print("[RSS] Finished downloading episode file!")

    if args.skip_encode:
        print("[ffmpeg] Skipping mp3 -> ogg encoding due to --skip-encode")
        # Try to assign a default value if we skip encoding
        ogg_file = os.path.join(__data_dir__, "tmp", "episode.ogg")
    else:
        print(f"[ffmpeg] encoding {mp3_file} -> ogg")
        ogg_file = mp3_to_ogg(mp3_file)
        print(f"[ffmpeg] done: {ogg_file}")

    build_packs([15, 18], pack_description=latest_episode.title)

    audio_duration = OggVorbis(ogg_file).info.length
    audio_duration = math.ceil(audio_duration)

    print(f"[ogg] file has a duration of {audio_duration} seconds")

    discs_json = populate_discs_json(
        template_file=os.path.join(__data_dir__, "templates", "discs.json"),
        title=latest_episode.title,
        author=rss_feed.feed().channel.content.title,
        duration=audio_duration,
    )

    print("[discs.json] writing discs.json")
    with open(
        os.path.join(__data_dir__, "out", "discs.json"), "w", encoding="utf-8"
    ) as discs_file:
        json.dump(discs_json, discs_file, allow_nan=False, indent=4)


if __name__ == "__main__":
    main()
