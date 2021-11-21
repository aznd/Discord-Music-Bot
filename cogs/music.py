import discord
import os
from discord.ext import commands
from yt_dlp import YoutubeDL
import logging
import typing
import functools
import asyncio
import random

import yt_dlp
logging.basicConfig(level=logging.WARNING)

def to_thread(func: typing.Callable) -> typing.Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)
    return wrapper

YDL_OPTIONS = {'format': 'bestaudio', 'ignoreerrors': 'True'}
@to_thread
def download_playlist(playlist_url, music_queue):
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        playlist_dict = ydl.extract_info(playlist_url, download=False)
        for i in playlist_dict['entries']:
            music_queue.append(i['webpage_url'])


class Music(commands.Cog):
    
    def __init__(self, client):
        self.client = client
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.is_playing = False
        self.YDL_OPTIONS = {'format': 'bestaudio', 'ignoreerrors': 'True'}
        self.data_dict = ""
        self.music_queue = []
        self.vc = ""

    def search_yt(self, arg):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            if arg.startswith('http'):
                self.data_dict = ydl.extract_info(arg, download=False)
            else:
                self.data_dict = ydl.extract_info(f"ytsearch:{arg}",download=False)['entries'][0]
        return self.data_dict
    
    def play_next(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            # Get the first URL in the list
            m_url = self.music_queue[0] 

            # Pop the first element, because we just stored it in the var m_url
            self.music_queue.pop(0)
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                ydl.download(m_url)
            for file in os.listdir("./"):
                if file.endswith(".webm"):
                    os.rename(file, "song.webm")
                    self.vc.play(discord.FFmpegPCMAudio("song.webm"), after=lambda e: self.play_next(ctx))
        else:
            self.is_playing = False

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0]
            voicechannel_author = ctx.message.author.voice.channel
            voiceChannel = discord.utils.get(ctx.guild.voice_channels, name=str(voicechannel_author))
            self.vc = await voiceChannel.connect()
            self.music_queue.pop(0)
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                ydl.download(m_url)
            for file in os.listdir("./"):
                if file.endswith(".webm"):
                    os.rename(file, "song.webm")
                    self.vc.play(discord.FFmpegPCMAudio("song.webm"), after=lambda e: self.play_next(ctx))

    # Events
    @commands.Cog.listener()
    async def on_ready(self):
        print('Bot is online.')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('Unknown command. Use -help to see all commands.')

    # Commands
    @commands.command()
    async def play(self, ctx, *, args):
        try:
            voice_channel = ctx.message.author.voice.channel
        except:
            await ctx.send("You need to be in a voice channel to use this command.")
        if voice_channel is None:
            # author not connected to any voice channel
            await ctx.send("You need to be in a voice channel to use this command.")
        else:
            if "list" in str(args):
                # We have a playlist
                print("We have playlist")
                await download_playlist(args, self.music_queue)
                if self.is_playing is False:
                    print("eins yep")
                    await self.play_music(ctx)
            else:
                print("Now in else")
                song_dict = self.search_yt(args)
                webpage_url = song_dict.get("webpage_url")
                self.music_queue.append(webpage_url)
                if self.is_playing is False:
                    print("zwei yep")
                    await self.play_music(ctx)
    
    @commands.command()
    async def stop(self, ctx):
        try:
            is_playing = self.vc.is_playing()
            if is_playing:
                self.music_queue = []
                await ctx.send("Bot stopped and cleared the queue. "
                               "(If you didnt want to clear the queue, "
                               "use the pause command next time instead of stop.)")
                self.vc.stop()
            else:
                await ctx.send("Bot is currently not playing anything.")
        except Exception as e:
            print(e)

    @commands.command()
    async def leave(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        if voice is not None:
            self.music_queue = []
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
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            await voiceChannel.connect()
        except AttributeError:
            await ctx.send("You need to be in a voice channel to use this command.")

    @commands.command()
    async def list(self, ctx):
        if len(self.music_queue) > 0:
            for i in self.music_queue:
                await ctx.send(i)
        else:
            await ctx.send("Nothing is in the queue.")

    @commands.command()
    async def skip(self, ctx):
        if len(self.music_queue) > 0:
            self.play_next(ctx)
            await ctx.send("Skipped song.")
        else:
            await ctx.send("Nothing is in the queue.")
        
    @commands.command()
    async def shuffle(self, ctx):
        if len(self.music_queue) > 0:
            random.shuffle(self.music_queue)
            await ctx.send("Shuffled the queue.")
        else:
            await ctx.send("Nothing is in the queue.")

def setup(client):
    client.add_cog(Music(client))
