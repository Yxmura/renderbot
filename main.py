import discord
import json
# Remove this import as we're importing specific things from discord
# from discord import *
from discord.ext import commands, tasks
from cogs.ticket_system import Ticket_System
from cogs.ticket_commands import Ticket_Command
from cogs.fun import FunCommands
from cogs.utilities import Utilities
# Import the new welcomer cog
from cogs.welcomer import WelcomeGoodbyeCog
from keep_alive import keep_alive
from dotenv import load_dotenv
import os

#This will get everything from the config.json file
with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = os.getenv('guild_id')
GUILD_ID = config["guild_id"]
CATEGORY_ID = config["category_id"]

# Use the correct way to initialize the bot with intents
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all()) # Add a command_prefix, though not strictly needed for slash commands

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'you | /help'))
    print("Syncing slash commands...")
    try:        
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Synced {len(synced)} command(s) to guild {GUILD_ID}.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


async def load_cogs():
    print("Loading cogs...")
    await bot.add_cog(Ticket_System(bot))
    await bot.add_cog(Ticket_Command(bot))
    await bot.add_cog(FunCommands(bot))
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(WelcomeGoodbyeCog(bot))
    print("Cogs loaded.")


def main():
    print("Calling keep_alive()...")
    keep_alive()
    print("keep_alive() done.")
    try:
        print("Starting bot...")
        asyncio.run(run_bot())
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

async def run_bot():
    await load_cogs()
    await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    import asyncio
    main()
