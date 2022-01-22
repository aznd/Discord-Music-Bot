import os
import requests
import logging
from discord.ext import commands
from dotenv import load_dotenv
load_dotenv("../.env")

api_token = os.environ.get("API_TOKEN")
server_id = os.environ.get("SERVER_ID")
schedule_id = os.environ.get("SCHEDULE_ID")
logging.basicConfig(level=logging.WARNING)


class Administration(commands.Cog):
    def __init__(self, client):
        self.client = client

    def executeschedule(self):
        url = f'''https://panel.discordbothosting.com/api/client/servers/{server_id}/schedules/{schedule_id}/execute'''
        headers = {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json"
        }
        response = requests.request('POST', url, headers=headers)
        print(response.text)

    @commands.command()
    async def restartserver(self, ctx):
        await ctx.send("Now restarting the server...")
        try:
            self.executeschedule()
        except Exception as e:
            logging.log(logging.ERROR, e)


def setup(client):
    client.add_cog(Administration(client))
