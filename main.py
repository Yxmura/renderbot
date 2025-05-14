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
ROLE_ID = 1317607057687576696

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    await bot.tree.sync()
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='you | /help'))

@bot.command(name="sync")
async def sync_command(ctx):
    ROLE_ID = 1317607057687576696

    if any(role.id == ROLE_ID for role in ctx.author.roles):
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await ctx.send(f"✅ Synced {len(synced)} command(s) to this guild.")
        print("Command tree synced.")
    else:
        await ctx.send("❌ You do not have permission to use this command.")


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
