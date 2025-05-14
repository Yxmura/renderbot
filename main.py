import discord
import json
from discord import *
from discord.ext import commands, tasks
from cogs.ticket_system import Ticket_System
from cogs.ticket_commands import Ticket_Command
from cogs.fun import FunCommands
from cogs.utilities import Utilities
from cogs.music_copyright import MusicCopyrightCog
from cogs.giveaway import GiveawayCog
from cogs.welcomer import WelcomeGoodbyeCog
from cogs.poll import PollCog
from keep_alive import keep_alive
from dotenv import load_dotenv
import os

with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = config["guild_id"]
CATEGORY_ID = config["category_id"]

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
tree = app_commands.CommandTree(client)

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='you | /help'))

@tree.command(name='sync', description='Owner only')
async def sync(interaction: discord.Interaction):
    if interaction.user.id == 1317607057687576696:
        await tree.sync()
        print('Command tree synced.')
    else:
        await interaction.response.send_message('You must be the owner to use this command!')

def main():
    print('starting keepalive')
    keep_alive()
    print('finished keepalive')
    try:
        print("Starting bot...")
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
