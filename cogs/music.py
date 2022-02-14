import discord
import os
from discord.ext import commands
from yt_dlp import YoutubeDL
import logging
import typing
import random
import functools
import yt_dlp
import asyncio
logging.basicConfig(level=logging.WARNING)

video_unavailable = "This video is no longer available. It will be skipped."
queue_empty = "Queue is now empty, leaving the voice channel."
user_not_in_vc = "You need to be in a voice channel to use this command."
warn_long_video = """This seems like a long video. The download could take longer than normal.""" \
             """The bot will still respond during download."""


def to_thread(func: typing.Callable) -> typing.Coroutine:
    global queue_of_titles
    global queue_of_urls

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper


class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.is_playing = False
        self.should_repeat = False
        self.YDL_OPTIONS = {'format': 'bestaudio/best',
                            'extract_flat': 'in_playlist'}
        self.data_dict = ""
        self.music_queue = []
        self.music_queue_titles = []
        self.now_playing_url = ""
        self.long_video = False

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

    def search_yt(self, arg, ctx):
        try:
            with YoutubeDL(self.YDL_OPTIONS) as ydl:
                if arg.startswith('http'):
                    self.data_dict = ydl.extract_info(arg, download=False)
                else:
                    self.data_dict = ydl.extract_info(f"ytsearch:{arg}",
                                                      download=False)['entries'][0]
            if self.data_dict.get("duration") >= 1800:
                self.long_video = True
                return self.data_dict
            else:
                self.long_video = False
                return self.data_dict
        except Exception:
            self.client.loop.create_task(ctx.send(video_unavailable))

    def clear_queue_lists(self):
        self.music_queue = []
        self.music_queue_titles = []

    @to_thread
    def dl_long_video(self, ctx, m_url):
        self.dl_video(ctx, m_url)

    def dl_video(self, ctx, m_url):
        try:
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                ydl.download(m_url)
        except Exception as e:
            self.client.loop.create_task(ctx.send(e))
            self.client.loop.create_task(ctx.send("The video will be skipped."))
            self.play_next(ctx)

    def play_next(self, ctx):
        if self.should_repeat:
            voice = discord.utils.get(self.client.voice_clients,
                                      guild=ctx.guild)
            voice.play(discord.FFmpegPCMAudio("song.webm"),
                       after=lambda: self.play_next(ctx))
        else:
            if len(self.music_queue) > 0:
                self.is_playing = True
                # Get the first URL in the list
                m_url = self.music_queue[0]
                self.now_playing_url = m_url
                voice = discord.utils.get(self.client.voice_clients,
                                          guild=ctx.guild)
                # Pop the first element, because we just stored it in m_url
                self.music_queue.pop(0)
                self.music_queue_titles.pop(0)
                song_there = os.path.isfile("song.webm")
                if song_there:
                    try:
                        os.remove("song.webm")
                    except Exception:
                        self.client.loop.create_task(ctx.send("Please restart server."))
                        self.clear_queue_lists()
                        self.client.loop.create_task(voice.disconnect())
                if self.long_video is True:
                    self.client.loop.create_task(ctx.send(warn_long_video))
                    self.client.loop.create_task(self.dl_long_video(ctx, m_url))
                else:
                    self.dl_video(ctx, m_url)
                for file in os.listdir("./"):
                    if file.endswith(".webm"):
                        os.rename(file, "song.webm")
                        voice.play(discord.FFmpegPCMAudio("song.webm"),
                                   after=lambda e: self.play_next(ctx))
            else:
                self.is_playing = False
                voice = discord.utils.get(self.client.voice_clients,
                                          guild=ctx.guild)
                if voice is not None:
                    self.client.loop.create_task(ctx.send(queue_empty))
                    self.client.loop.create_task(voice.disconnect())

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0]
            self.now_playing_url = m_url
            voicechannel_author = ctx.message.author.voice.channel
            voiceChannel = discord.utils.get(ctx.guild.voice_channels,
                                             name=str(voicechannel_author))
            voice = discord.utils.get(self.client.voice_clients,
                                      guild=ctx.guild)
            # Try to connect, if it fails, just pass. We are already connected.
            if voice is None:
                voice = await voiceChannel.connect()
            self.music_queue.pop(0)
            self.music_queue_titles.pop(0)
            song_there = os.path.isfile("song.webm")
            if song_there:
                os.remove("song.webm")
            if self.long_video is True:
                await ctx.send(warn_long_video)
                await self.dl_long_video(ctx, m_url)
            else:
                self.dl_video(ctx, m_url)
            for file in os.listdir("./"):
                if file.endswith(".webm"):
                    os.rename(file, "song.webm")
                    voice.play(discord.FFmpegPCMAudio("song.webm"),
                               after=lambda e: self.play_next(ctx))

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print('Bot is online.')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('Unknown command. Use -help to see all commands.')

    # Commands
    @commands.command(aliases=['p'])
    async def play(self, ctx, *, args):
        try:
            try:
                voice_channel = ctx.message.author.voice.channel
            except Exception:
                await ctx.send(user_not_in_vc)
            if voice_channel is None:
                # author not connected to any voice channel
                await ctx.send(user_not_in_vc)
            else:
                if "list" in str(args):
                    # We have a playlist
                    self.download_playlist(args, self.music_queue)
                    await ctx.send("Added playlist to queue.")
                    if self.is_playing is False:
                        await self.play_music(ctx)
                else:
                    song_dict: typing.Dict = self.search_yt(args, ctx)
                    if "webpage_url" in song_dict:
                        url = song_dict.get("webpage_url")
                        title = song_dict.get("title")
                        self.music_queue_titles
                    else:
                        url = song_dict.get("url")
                        title = song_dict.get("title")
                    self.music_queue.append(url)
                    self.music_queue_titles.append(title)
                    await ctx.send("Song added to the queue.")
                    if self.is_playing is False:
                        await self.play_music(ctx)
        except Exception as e:
            print(e)

    @commands.command()
    async def stop(self, ctx):
        voice = discord.utils.get(self.client.voice_clients,
                                  guild=ctx.guild)
        is_playing = voice.is_playing()
        if is_playing:
            self.clear_queue_lists()
            await ctx.send("Bot stopped and cleared the queue. "
                           "(If you didnt want to clear the queue, "
                           "use the pause command next time instead of stop.)")
            voice.stop()
        else:
            await ctx.send("Bot is currently not playing anything.")

    @commands.command(aliases=['l'])
    async def leave(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        if voice is not None:
            self.clear_queue_lists()
            await voice.disconnect()
            await ctx.send("Bot left the channel and cleared the queue.")
        else:
            await ctx.send("Bot is currently not connected to any channel.")

    @commands.command()
    async def join(self, ctx):
        try:
            voicechannel_author = ctx.message.author.voice.channel
            voiceChannel = discord.utils.get(ctx.guild.voice_channels,
                                             name=str(voicechannel_author))
            await voiceChannel.connect()
        except AttributeError:
            await ctx.send(user_not_in_vc)

    @commands.command(aliases=['queue'])
    async def list(self, ctx):
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
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nothing is in the queue.")

    @commands.command()
    async def skip(self, ctx):
        try:
            voice = discord.utils.get(self.client.voice_clients,
                                      guild=ctx.guild)
            if voice is None or len(self.music_queue) < 0:
                await ctx.send("Nothing is in the queue, or playing.")
            elif len(self.music_queue) > 0:
                # Dont use stop(), because that would call the after func
                # which we dont want...
                # Using pause, we bypass that
                voice.pause()
                self.play_next(ctx)
                await ctx.send("Skipped song.")
            elif voice.is_playing():
                voice.stop()
        except Exception as e:
            print(e)

    @commands.command()
    async def shuffle(self, ctx):
        if len(self.music_queue) > 0:
            temp = list(zip(self.music_queue, self.music_queue_titles))
            random.shuffle(temp)
            self.music_queue, self.music_queue_titles = list(zip(*temp))
            # This returns tuples, for whatever reasons. so we have to convert.
            self.music_queue = list(self.music_queue)
            self.music_queue_titles = list(self.music_queue_titles)
            await ctx.send("Shuffled the queue.")
        else:
            await ctx.send("Nothing is in the queue.")

    @commands.command()
    async def np(self, ctx):
        if self.is_playing is False:
            await ctx.send("Nothing is currently playing.")
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
                await ctx.send(embed=embed)

    @commands.command()
    async def pause(self, ctx):
        if self.is_playing:
            voice = discord.utils.get(self.client.voice_clients,
                                      guild=ctx.guild)
            voice.pause()
            self.is_playing = False
        else:
            await ctx.send("Nothing is currently playing.\n"
                           "Did you maybe want to use the resume command?")

    @commands.command()
    async def resume(self, ctx):
        voice = discord.utils.get(self.client.voice_clients,
                                  guild=ctx.guild)
        if voice:
            if self.is_playing is False:
                voice = discord.utils.get(self.client.voice_clients,
                                          guild=ctx.guild)
                voice.resume()
                self.is_playing = True
            else:
                await ctx.send("Nothing is currently paused.")
        else:
            logging.error("No voice_client found.")
            await ctx.send("Nothing is currently playing.")

    @commands.command(aliases=['loop'])
    async def repeat(self, ctx):
        if self.is_playing is False:
            await ctx.send("Nothing is currently playing.")
        else:
            if self.should_repeat is False:
                self.should_repeat = True
                await ctx.send("Now looping current song. To end this, use this command again.")
            elif self.should_repeat:
                self.should_repeat = False
                await ctx.send("No longer looping the current song.")

    @commands.command()
    async def playnext(self, ctx, *, args):
        try:
            ctx.message.author.voice.channel
        except Exception:
            await ctx.send(user_not_in_vc)
            return
        song_dict: typing.Dict = self.search_yt(args, ctx)
        if "webpage_url" in song_dict:
            url = song_dict.get("webpage_url")
            title = song_dict.get("title")
            self.music_queue_titles
        else:
            url = song_dict.get("url")
            title = song_dict.get("title")
        self.music_queue.insert(0, url)
        self.music_queue_titles.insert(0, title)
        await ctx.send(f"{title} will be played after the current title ends.")


def setup(client):
    client.add_cog(Music(client))
