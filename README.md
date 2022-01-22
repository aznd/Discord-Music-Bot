# Discord-Music-Bot

Discord Music Bot using discord.py

## How to use this bot?

First, you need to get your discord bot token. After that, create a file named .env in the root directory and put the following into it:

DISCORD_TOKEN=yourtokenhere

On linux, this could be done with

`echo "DISCORD_TOKEN=yourtokenhere" > .env`

After that, you can run this bot with

`python bot.py`

## TODO:

- [ ] Dont use two loggers, only use one. (admin.py and music.py)
- [ ] User should be able to use their own endpoints etc. (use some conf file)
- [X] Implement list command
- [X] Implement loop/repeat command
- [X] Fix issue with blocking heartbeat, when a video takes too long to download.
