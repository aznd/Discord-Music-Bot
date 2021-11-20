import discord
import os
from discord import client
from discord.ext import commands
from discord.ext.commands.converter import VoiceChannelConverter
from yt_dlp import YoutubeDL
import logging

import yt_dlp
logging.basicConfig(level=logging.WARNING)


class Music(commands.Cog):

    def __init__(self, client):
        self.client = client
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.is_playing = False
        self.YDL_OPTIONS = {'format': 'bestaudio'}
        self.data_dict = ""
        self.music_queue = []
        self.vc = ""

    def search_yt(self, arg):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            if arg.startswith('http'):
                self.data_dict = ydl.extract_info(arg, download=False)
            else:
                self.data_dict = ydl.extract_info(f"ytsearch:{arg}",
                                                  download=False)['entries'][0]
        return self.data_dict

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            
            # get the first url
            # STILL HAVE TO IMPLEMENT !!! 
            # remove the first element as we are currently playing it
            self.music_queue.pop(0)
            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                            after=lambda e: self.play_next())
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
                    self.vc.play(discord.FFmpegPCMAudio("song.webm"), after=lambda e: self.play_next())

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
        except Exception as e:
            await ctx.send("You need to be in a voice channel to use this command.")
        if voice_channel is None:
            # author not connected to any voice channel
            await ctx.send("You need to be in a voice channel to use this command.")
        else:
            song_dict = self.search_yt(args)
            webpage_url = song_dict.get("webpage_url")
            self.music_queue.append(webpage_url)
            if self.is_playing is False:
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
            await voice.disconnect()
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

def setup(client):
    client.add_cog(Music(client))
