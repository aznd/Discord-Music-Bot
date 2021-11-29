from threading import ExceptHookArgs
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


YDL_OPTIONS = {'format': 'bestaudio', 'ignoreerrors' : 'true'}

class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.is_playing = False

        self.YDL_OPTIONS = {'format': 'bestaudio/best', 'ingoreerrors': 'true'}
        self.data_dict = ""
        self.music_queue = []
        self.now_playing_url = ""

    
    @to_thread
    def download_playlist(self, playlist_url, x):
       with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
           playlist_dict = ydl.extract_info(playlist_url, download=False)
           for i in playlist_dict['entries']:
               try:
                   x.append(i['webpage_url'])
               except Exception:
                pass


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
            self.now_playing_url = m_url
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            # Pop the first element, because we just stored it in the var m_url
            self.music_queue.pop(0)
            song_there = os.path.isfile("song.webm")
            if song_there:
                    os.remove("song.webm")
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                    ydl.download(m_url)
            for file in os.listdir("./"):
                    if file.endswith(".webm"):
                        os.rename(file, "song.webm")
                        voice.play(discord.FFmpegPCMAudio("song.webm"),
                                                    after=lambda e: self.play_next(ctx))
        else:
            self.is_playing = False
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            self.client.loop.create_task(ctx.send("Queue is now empty, leaving the channel."))
            self.client.loop.create_task(voice.disconnect())

    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0]
            self.now_playing_url = m_url
            voicechannel_author = ctx.message.author.voice.channel
            voiceChannel = discord.utils.get(ctx.guild.voice_channels, name=str(voicechannel_author))
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            #Try to connect, if it fails, just pass. We are already connected.
            if voice is None:
                voice = await voiceChannel.connect()
            self.music_queue.pop(0)
            song_there = os.path.isfile("song.webm")
            if song_there:
                os.remove("song.webm")
            with yt_dlp.YoutubeDL(self.YDL_OPTIONS) as ydl:
                ydl.download(m_url)
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
            voice_channel = ctx.message.author.voice.channel
        except:
            await ctx.send("You need to be in a voice channel to use this command.")
        if voice_channel is None:
            # author not connected to any voice channel
            await ctx.send("You need to be in a voice channel to use this command.")
        else:
            if "list" in str(args):
                try:
                    # We have a playlist
                    await ctx.send("Adding playlist to the queue, might take a minute, "
                                                    "depending on the length of your playlist.")
                    await self.download_playlist(args, self.music_queue)
                    if self.is_playing is False:
                            await self.play_music(ctx)
                except Exception as e:
                    print(e)
            else:
                song_dict = self.search_yt(args)
                webpage_url = song_dict.get("webpage_url")
                self.music_queue.append(webpage_url)
                if self.is_playing is False:
                        await self.play_music(ctx)
    
    @commands.command()
    async def stop(self, ctx):
        voice = discord.utils.get(self.client.voice_clients, 															guild=ctx.guild)
        is_playing = voice.is_playing()
        if is_playing:
            self.music_queue = []
            await ctx.send("Bot stopped and cleared the queue. "
                                            "(If you didnt want to clear the queue, "
                                            "use the pause command next time instead of stop.)")
            voice.stop()
        else:
            await ctx.send("Bot is currently not playing 												anything.")

    @commands.command(aliases=['l'])
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
        works = False
        if works is False:
            await ctx.send("Sorry, not yet implemented.")
            for i in self.music_queue:
                print(i)
        else:
            if len(self.music_queue) > 0:
                embed = discord.Embed(title="Queue:",
                                      description=" ",
                                      color=0xFF6733)
                i = 1
                for e in self.music_queue:
                    embed.add_field(name=str(i) + ":",
                                    value=str(e))
                    i += 1
            else:
                await ctx.send("Nothing is in the queue.")

    @commands.command()
    async def skip(self, ctx):
        if len(self.music_queue) > 0:   
            voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
            # Dont use stop(), because that would call the after func, which we dont wantself.
            # Using pause, we bypass that
            voice.pause()
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

    @commands.command()
    async def np(self, ctx):
        if self.is_playing is False:
            await ctx.send("Nothing is currently playing.")
        else:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                data = ydl.extract_info(self.now_playing_url, download=False)
                title = data.get("title")
                artist = data.get("artist")
                thumbnail = data.get("thumbnail") 
                embed = discord.Embed(title="Now Playing:",
                                      description="Title: " + str(title),
                                      color=0xFF6733)
                if artist is None:
                    embed.add_field(name="Unknown artist.", value=self.now_playing_url )
                else:
                    embed.add_field(name="Artist: " + str(artist), value=self.now_playing_url)
                embed.set_thumbnail(url=thumbnail)
                await ctx.send(embed=embed)

def setup(client):
    client.add_cog(Music(client))
