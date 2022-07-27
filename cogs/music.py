import os
import random
import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL
import logging
import typing
import functools
import yt_dlp
import asyncio
logging.basicConfig(level=logging.WARNING)

video_unavailable = "This video is no longer available. It will be skipped."
queue_empty = "Queue is now empty, leaving the voice channel."
user_not_in_vc = "You need to be in a voice channel to use this command."
warn_long_video = """This seems like a long video. The download could take longer than normal.""" \
             """The bot will still respond during download."""

def to_thread(func: typing.Callable):
    global queue_of_titles
    global queue_of_urls

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


class Music(commands.Cog):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.is_playing: bool = False
        self.should_repeat: bool = False
        self.YDL_OPTIONS: dict = {'format': 'bestaudio/best',
                            'extract_flat': 'in_playlist'}
        self.data_dict: str = ""
        self.music_queue: list = []
        self.music_queue_titles: list = []
        self.now_playing_url: str = ""
        self.long_video: bool = False
        self.last_user_voice_channel = None
        self.interaction: discord.Interaction
        super().__init__()

    def download_playlist(self, playlist_url, x):
        with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
            playlist_dict: typing.Dict = ydl.extract_info(playlist_url,
                                                          download=False)
            for i in playlist_dict['entries']:
                try:
                    x.append(i['url'])
                    self.music_queue_titles.append(i['title'])
                except Exception:
                    pass

    def search_yt(self, name):
        try:
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                if name.startswith('http'):
                    self.data_dict = ydl.extract_info(name, download=False)
                else:
                    self.data_dict = ydl.extract_info(f"ytsearch:{name}",
                                                      download=False)['entries'][0]
            if self.data_dict.get("duration") >= 1800:
                self.long_video = True
                return self.data_dict
            else:
                self.long_video = False
                return self.data_dict
        except Exception:
            self.bot.loop.create_task(self.interaction.response.send_message(video_unavailable))

    def clear_queue_lists(self):
        self.music_queue = []
        self.music_queue_titles = []

    @to_thread
    def dl_long_video(self, m_url):
        self.dl_video(m_url)

    def dl_video(self, m_url):
        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                ydl.download(m_url)
        except Exception as e:
            self.bot.loop.create_task(self.interaction.response.send_message(e))
            self.bot.loop.create_task(self.interaction.response.send_message("The video will be skipped."))
            self.play_next()

    def play_next(self):
        if self.should_repeat:
            voice = self.interaction.client.voice_clients[0]
            voice.play(discord.FFmpegPCMAudio("song.webm"),
                       after=lambda: self.play_next())
        else:
            if len(self.music_queue) > 0:
                self.is_playing = True
                # Get the first URL in the list
                m_url = self.music_queue[0]
                self.now_playing_url = m_url
                voice = discord.utils.get(self.bot.voice_clients,
                                          guild=self.interaction.guild)
                # Pop the first element, because we just stored it in m_url
                self.music_queue.pop(0)
                self.music_queue_titles.pop(0)
                song_there = os.path.isfile("song.webm")
                if song_there:
                    try:
                        os.remove("song.webm")
                    except Exception:
                        self.bot.loop.create_task(self.interaction.response.send_message("Please restart server."))
                        self.clear_queue_lists()
                        self.bot.loop.create_task(voice.disconnect(force=True))
                if self.long_video is True:
                    self.bot.loop.create_task(self.interaction.response.send_message(warn_long_video))
                    self.bot.loop.create_task(self.dl_long_video(m_url))
                else:
                    self.dl_video(m_url)
                for file in os.listdir("./"):
                    if file.endswith(".webm"):
                        os.rename(file, "song.webm")
                        voice.play(discord.FFmpegPCMAudio("song.webm"),
                                   after=lambda _: self.play_next())
            else:
                self.is_playing = False
                voice = discord.utils.get(self.bot.voice_clients,
                                          guild=self.interaction.guild)
                if voice is not None:
                    self.bot.loop.create_task(self.interaction.response.send_message(queue_empty))
                    self.bot.loop.create_task(voice.disconnect(force=True))

    async def play_music(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0]
            self.now_playing_url = m_url
            voice = discord.utils.get(self.bot.voice_clients,
                                      guild=self.interaction.guild)
            if voice is None:
                voice = await self.interaction.user.voice.channel.connect()
            self.music_queue.pop(0)
            self.music_queue_titles.pop(0)
            song_there = os.path.isfile("song.webm")
            if song_there:
                os.remove("song.webm")
            if self.long_video is True:
                await self.interaction.response.send_message(warn_long_video)
                self.dl_long_video(m_url)
            else:
                self.dl_video(m_url)
            for file in os.listdir("./"):
                if file.endswith(".webm"):
                    os.rename(file, "song.webm")
                    voice.play(discord.FFmpegPCMAudio("song.webm"),
                               after=lambda _: self.play_next())

    # Commands
    @app_commands.command(name="play", description="Play a given video or a playlist")
    async def play(self, interaction: discord.Interaction, name: str):
        self.interaction = interaction
        try:
            self.last_user_voice_channel = self.interaction.user.voice.channel
        except Exception:
            self.last_user_voice_channel = None
            await interaction.followup.send(user_not_in_vc)
        if self.last_user_voice_channel is None:
            # author not connected to any voice channel
            await interaction.response.send_message(user_not_in_vc)
        else:
            if "list" in str(name):
                # We have a playlist
                self.download_playlist(name, self.music_queue)
                await interaction.response.send_message("Added playlist to queue.")
                if self.is_playing is False:
                    await self.play_music()
            else:
                song_dict: typing.Dict = self.search_yt(name)
                if "webpage_url" in song_dict:
                    url = song_dict.get("webpage_url")
                    title = song_dict.get("title")
                    self.music_queue_titles
                else:
                    url = song_dict.get("url")
                    title = song_dict.get("title")
                self.music_queue.append(url)
                self.music_queue_titles.append(title)
                await interaction.response.send_message("Song added to the queue.")
                if self.is_playing is False:
                    await self.play_music()

    @app_commands.command(name='stop', description='Stop the bot and clear the queue.')
    async def stop(self, interaction: discord.Interaction):
        self.interaction = interaction
        is_playing = interaction.client.voice_clients[0].is_playing()
        if is_playing:
            self.clear_queue_lists()
            await interaction.response.send_message("Bot stopped and cleared the queue. "
                           "(If you didnt want to clear the queue, "
                           "use the pause command next time instead of stop.)")
            interaction.client.voice_clients[0].stop()
        else:
            await interaction.response.send_message("Bot is currently not playing anything.")

    @app_commands.command(name='leave', description='Leave the current channel')
    async def leave(self, interaction: discord.Interaction):
        self.interaction = interaction
        voice = interaction.client.voice_clients[0]
        if voice is not None:
            self.clear_queue_lists()
            await voice.disconnect(force=True)
            await interaction.response.send_message("Bot left the channel and cleared the queue.")
        else:
            await interaction.response.send_message("Bot is currently not connected to any channel.")

    @app_commands.command(name='join', description='Join the channel youre in')
    async def join(self, interaction: discord.Interaction):
        self.interaction = interaction
        try:
            voicechannel_author = interaction.user.voice
            voiceChannel = voicechannel_author.channel
            await voiceChannel.connect()
        except AttributeError:
            await interaction.response.send_message(user_not_in_vc)
        except discord.ClientException:
            await interaction.response.send_message("Bot already connected")

    @app_commands.command(name='list', description='List the current queue')
    async def list(self, interaction: discord.Interaction):
        self.interaction = interaction
        if len(self.music_queue) > 0:
            embed = discord.Embed(title="Queue:",
                                  description=" ",
                                  color=0xFF6733)
            i = 1
            for _ in self.music_queue:
                if i > 25:
                    break
                embed.add_field(name=str(i) + ":",
                                value=str(self.music_queue_titles[i-1]))
                i += 1
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Nothing is in the queue.")

    @app_commands.command(name='skip', description='Skip the current song')
    async def skip(self, interaction: discord.Interaction):
        self.interaction = interaction
        voice = interaction.client.voice_clients[0] 
        if voice is None or len(self.music_queue) < 0:
            await interaction.response.send_message("Nothing is in the queue, or playing.")
        elif len(self.music_queue) > 0:
            # Dont use stop(), because that would call the after func
            # which we dont want...
            # Using pause, we bypass that
            voice.pause()
            self.play_next()
            await interaction.response.send_message("Skipped song.")
        elif voice.is_playing():
            voice.stop()

    @app_commands.command(name='shuffle', description='Shuffle the current queue')
    async def shuffle(self, interaction: discord.Interaction):
        self.interaction = interaction
        if len(self.music_queue) > 0:
            temp = list(zip(self.music_queue, self.music_queue_titles))
            random.shuffle(temp)
            self.music_queue, self.music_queue_titles = list(zip(*temp))
            # TODO: Find out why this returns a tuple
            # This returns tuples, for whatever reasons. so we have to convert.
            self.music_queue = list(self.music_queue)
            self.music_queue_titles = list(self.music_queue_titles)
            await interaction.response.send_message("Shuffled the queue.")
        else:
            await ctx.send("Nothing is in the queue.")

    @app_commands.command(name='np', description='Show information about the currently playing song')
    async def np(self, interaction: discord.Interaction):
        self.interaction = interaction
        if self.is_playing is False:
            await interaction.response.send_message("Nothing is currently playing.")
        else:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                data: typing.Dict = ydl.extract_info(self.now_playing_url,
                                                     download=False)
                title = data.get("title")
                artist = data.get("artist")
                thumbnail = data.get("thumbnail")
                embed = discord.Embed(title="Now Playing:",
                                      description="Title: " + str(title),
                                      color=0xFF6733)
                if artist is None:
                    embed.add_field(name="Unknown artist.",
                                    value=self.now_playing_url)
                else:
                    embed.add_field(name="Artist: " + str(artist),
                                    value=self.now_playing_url)
                embed.set_thumbnail(url=thumbnail)
                await interaction.response.send_message(embed=embed)

    @app_commands.command(name='pause', description='Pause the currently playing song')
    async def pause(self, interaction: discord.Interaction):
        self.interaction = interaction
        if self.is_playing:
            voice = interaction.client.voice_clients[0]
            voice.pause()
            self.is_playing = False
            await interaction.response.send_message("Paused the bot")
        else:
            await interaction.response.send_message("Nothing is currently playing.\n"
                           "Did you maybe want to use the resume command?")

    @app_commands.command(name='resume', description='Resume the currently paused song')
    async def resume(self, interaction: discord.Interaction):
        self.interaction = interaction
        voice = interaction.client.voice_clients[0]
        if voice:
            if self.is_playing is False:
                voice.resume()
                self.is_playing = True
                await interaction.response.send_message("Resumed the bot")
            else:
                await interaction.response.send_message("Nothing is currently paused.")
        else:
            await interaction.response.send_message("No voice_client found.")
            await interaction.response.send_message("Nothing is currently playing.")

    @app_commands.command(name='repeat', description='Repeat/loop the current song')
    async def repeat(self, interaction: discord.Interaction):
        self.interaction = interaction
        if self.is_playing is False:
            await interaction.response.send_message("Nothing is currently playing.")
        else:
            if self.should_repeat is False:
                self.should_repeat = True
                await interaction.response.send_message("Now looping current song. To end this, use this command again.")
            elif self.should_repeat:
                self.should_repeat = False
                await interaction.response.send_message("No longer looping the current song.")

    @app_commands.command(name="playnext", description="Play a given video directly after the currently playing song")
    async def playnext(self, interaction: discord.Interaction, name: str):
        self.interaction = interaction
        try:
            interaction.user.voice.channel
        except Exception:
            await interaction.response.send_message(user_not_in_vc)
            return
        song_dict: typing.Dict = self.search_yt(name)
        if "webpage_url" in song_dict:
            url = song_dict.get("webpage_url")
            title = song_dict.get("title")
            self.music_queue_titles
        else:
            url = song_dict.get("url")
            title = song_dict.get("title")
        self.music_queue.insert(0, url)
        self.music_queue_titles.insert(0, title)
        await interaction.response.send_message(f"{title} will be played after the current title ends.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
