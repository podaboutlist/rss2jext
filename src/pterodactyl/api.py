"""Wrapper for the Pterodactyl REST API."""
import os

import requests
from dotenv import load_dotenv

# TODO: resolve circular import crap
# from . import __version__
__version__ = "1.0.0"

DEFAULT_TIMEOUT = 1000


class Client:

    """Wrapper class for the Pterodactyl Client API.

    Handles requests to anything under /api/client
    """

    __api_key: str = None
    __panel_url: str = None
    __user_agent: str = None

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": None,
        "User-Agent": None,
    }

    def __init__(self, user_agent=f"pteropy/{__version__}") -> None:
        """Load values directly from the environment."""
        load_dotenv()

        # TODO: Implement validation of API key/panel URL
        self.__api_key = os.getenv("PTERODACTYL_API_KEY")
        self.__panel_url = os.getenv("PTERODACTYL_URL")

        self.__user_agent = user_agent

        # Add required info for HTTP requests
        self.headers["Authorization"] = f"Bearer {self.__api_key}"
        self.headers["User-Agent"] = self.__user_agent

    def server_details(self, server_id: str, timeout=DEFAULT_TIMEOUT) -> dict:
        """Get the details of a server.

        Easier than checking all servers that belong to a user.
        """
        endpoint = f"{self.__panel_url}/api/client/servers/{server_id}"

        req = requests.get(endpoint, headers=self.headers, timeout=timeout)

        req.raise_for_status()

        # TODO: Handle json() throwing requests.exceptions.JSONDecodeError in
        # the case of bad JSON response data.
        return req.json()

    def has_permission(self, server_id: str, permission_node: str) -> bool:
        """Check if the current user (based on API key) has a permission node."""
        user_permissions = self.server_details(server_id)["meta"]["user_permissions"]

        # TODO: Figure out if we need to handle permission nodes like "control.*"
        return "*" in user_permissions or permission_node in user_permissions

    def is_online(self, server_id: str) -> bool:
        """Parse data from self.server_details() to determine server power state.

        There is currently no API endpoint to check power state, only to set it.
        """
        details = self.server_details(server_id)

        # Multiple things indicate an "offline" power state, namely:
        #   - details.attributes.is_suspended == True
        #   - details.attributes.is_installing == True
        #   - send_command returns False

        if details.attributes.is_suspended or details.attributes.is_installing:
            return False

        # HACK: If send_command returns True, we're online. Otherwise, we're not.
        # I don't think there's a better way of checking a server's power
        # state than sending a command and checking for a 502 response.
        # The API docs show no indication of GET /power, only POST /power.
        # For now we'll just check for a 502.
        return self.send_command(server_id, "ping")

    def send_command(
        self, server_id: str, command: str, timeout=DEFAULT_TIMEOUT
    ) -> bool:
        """Send a command to a server hosted via the panel."""
        endpoint = f"{self.__panel_url}/api/client/servers/{server_id}/command"

        req = requests.post(
            endpoint, headers=self.headers, json={"command": command}, timeout=timeout
        )

        # TODO: Rewrite this as a try/catch based on req.raise_for_status()?
        # We could handle issues more robustly for sure.

        if req.status_code == 502:
            # Endpoint returns 502 if the requested server is offline
            return False

        req.raise_for_status()

        # API request does not return any data besides a success code.
        return True
