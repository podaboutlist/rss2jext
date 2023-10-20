"""Simple helper class for managing RSS feeds."""
import requests
from rss_parser import Parser
from rss_parser.models.item import Item
from rss_parser.models.types import Tag


class RSSHelper:

    """Simple helper class for managing RSS feeds."""

    __feed_url: str = ""
    __feed = None
    __user_agent = None

    def __init__(self, url: str, *, user_agent: str):
        """Initialize internal feed URL, feed object, and user-agent."""
        self.__feed_url = url
        self.__user_agent = user_agent

        self.__feed = self.from_url(self.__feed_url)

    def feed(self):
        return self.__feed

    def from_url(self, url: str):
        """Create an RSS object from a feed URL."""
        print(f"[RSS] Downloading feed from {url}...")

        feed_req = requests.get(
            url, timeout=1000, headers={"User-Agent": self.__user_agent}
        )

        feed_req.raise_for_status()

        return Parser.parse(feed_req.text)

    def latest_episode(self, *, feed=None) -> Tag[Item]:
        """Get the latest episode from an RSS feed."""
        if not feed:
            feed = self.__feed

        print(f"[RSS] Feed language: {feed.channel.language}")
        print(f"[RSS] Feed version: {feed.version}")

        feed_items = feed.channel.items

        # The feed is ordered by date ascending so the newest episodes are at
        # the end of rss_items
        feed_items.reverse()

        i = 0

        # TODO: Check the number of items in rss_items before entering this loop
        while True:
            i = i + 1

            latest_rss_item = feed_items.pop()

            title = latest_rss_item.title.lower()

            # TODO: Make this filter customizable
            if not title.startswith("teaser"):
                return latest_rss_item

            # HACK: Find a better way of handling this edge case
            if i > 5:  # abort after 5 iterations so we're not here all day
                raise RuntimeError("Could not find a non-teaser episode after 5 tries.")

    def episode_file_url(self, episode) -> str:
        """Get the URL to download the audio file for an episode."""
        return episode.enclosure.attributes["url"]
