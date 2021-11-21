from discord.ext import commands
import os
from keep_alive import keep_alive
TOKEN = os.environ['DISCORD_TOKEN']
client = commands.Bot(command_prefix='-')


@client.command()
async def load(ctx, extension):
    client.load_extension(f'cogs.{extension}')
    await ctx.send("Loaded cog.")

@client.command()
async def unload(ctx, extension):
    client.unload_extension(f'cogs.{extension}')
    await ctx.send("Unloaded cog.")


@client.command()
async def reload(ctx, extension):
    try:
        client.unload_extension(f'cogs.{extension}')
        client.load_extension(f'cogs.{extension}')
        await ctx.send("Reloaded cog.")
    except Exception as e:
        print(e)

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

keep_alive()
client.run(TOKEN)