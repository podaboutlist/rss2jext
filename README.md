# RSS to Jukebox Extended

1. Checks for a new episode of a podcast from a given RSS feed
2. Downloads the epsiode
3. Converts it to a 64kb/s Ogg Vorbis audio file
4. Creates a Minecraft resource pack with a custom music disc for that episode
5. Generates a `discs.json` file for the Spigot plugin [Jukebox Extended][1]
6. Uploads the resource pack to a CDN
7. Uploads `discs.json` to a Minecraft server
8. Triggers a set of user-defined commands on the server using the [Pterodactyl HTTP API][2]


[1]: https://www.spigotmc.org/resources/103219/
[2]: https://dashflo.net/docs/api/pterodactyl/v1/#req_32da5e33f828438dabae713f7042bab9
