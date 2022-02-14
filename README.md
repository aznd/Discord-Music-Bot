# Discord-Music-Bot

Discord Music Bot using discord.py

## How to use this bot?

First, you need to get your discord bot token. After that, create a file named .env in the root directory and put the following into it:

`DISCORD_TOKEN=yourtokenhere`

On linux, this could be done with

`echo "DISCORD_TOKEN=yourtokenhere" > .env`

After that, you can run this bot with

`python bot.py`

## Pterodactyl API Support:

If you use a pterodactly panel, have a look at the cogs/admin.py file. Right now the requests are hard coded.

But if you are interested in this, you probably know how to change things accordingly. HINT: You have to set env variables in the .env file.

## TODO:

- [ ] Join Command: User should be able to specify a channel the bot should join. 
- [ ] User should be able to use all media commands even if their are not in a channel, as long as the bot is in a channel.
- [ ] User should be able to use their own endpoints etc. (use some conf file)
- [ ] Dont use two loggers, only use one. (admin.py and music.py)
- [X] Implement list command
- [X] Implement loop/repeat command
- [X] Fix issue with blocking heartbeat, when a video takes too long to download.
