import discord
import json
from discord.ext import commands, tasks
from cogs.ticket_system import Ticket_System
from cogs.ticket_commands import Ticket_Command
from cogs.fun import FunCommands
from cogs.utilities import Utilities, MusicCopyrightCog
from cogs.giveaway import GiveawayCog
from cogs.welcomer import WelcomeGoodbyeCog
from keep_alive import keep_alive
from dotenv import load_dotenv
import os

#This will get everything from the config.json file
with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = config["guild_id"]
CATEGORY_ID = config["category_id"]

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'you | /help'))
    print(f"Attempting to sync slash commands to guild ID: {GUILD_ID}")
    try:
        # Sync commands to the specific guild
        guild_object = discord.Object(id=GUILD_ID)
        synced = await bot.tree.sync(guild=guild_object)
        print(f"Successfully synced {len(synced)} command(s) to guild {GUILD_ID}.")
        print(f"Synced command names: {[cmd.name for cmd in synced]}") # Print synced command names

    except Exception as e:
        print(f"Failed to sync commands to guild {GUILD_ID}: {e}")


async def load_cogs():
    print("Loading cogs...")
    try:
        await bot.add_cog(Ticket_System(bot))
        print('Loaded Ticket system')
        await bot.add_cog(Ticket_Command(bot))
        print('Loaded Ticket Commands')
        await bot.add_cog(FunCommands(bot))
        print('Loaded Fun Commands')
        await bot.add_cog(WelcomeGoodbyeCog(bot))
        print('Loaded Welcomer')
        await bot.add_cog(GiveawayCog(bot))
        print('Loaded Giveaway')
        # Load Utilities, which now contains both Utilities and MusicCopyrightCogs
        await bot.add_cog(Utilities(bot))
        print('Loaded Utilities')
        await bot.add_cog(MusicCopyrightCog(bot))
        print('Loaded Music Copyright')
        print("Cogs loaded.")
    except Exception as e:
        print(f"Error loading cogs: {e}")


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
