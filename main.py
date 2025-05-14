import discord
import json
from discord.ext import commands, tasks
from cogs.ticket_system import Ticket_System
from cogs.ticket_commands import Ticket_Command
from cogs.fun import FunCommands
from cogs.utilities import Utilities
from cogs.music_copyright import MusicCopyrightCog
from cogs.giveaway import GiveawayCog
from cogs.welcomer import WelcomeGoodbyeCog
from keep_alive import keep_alive
from dotenv import load_dotenv
import os
import asyncio 

# This will get everything from the config.json file
with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = config["guild_id"]
CATEGORY_ID = config["category_id"]

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Flag to track if we've already synced commands
commands_synced = False

@bot.event
async def on_ready():
    global commands_synced
    print(f'Bot Started | {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'you | /help'))
    
    # Only sync commands once
    if not commands_synced:
        # Give cogs time to fully initialize before syncing
        print("Waiting for cogs to fully initialize before syncing commands...")
        await asyncio.sleep(10)  # Wait 10 seconds to ensure all cogs are fully set up
        
        print(f"Attempting to sync slash commands to guild ID: {GUILD_ID}")
        try:
            # Sync commands to the specific guild
            guild_object = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild_object)
            print(f"Successfully synced {len(synced)} command(s) to guild {GUILD_ID}.")
            print(f"Synced command names: {[cmd.name for cmd in synced]}")
            commands_synced = True
        except Exception as e:
            print(f"Failed to sync commands to guild {GUILD_ID}: {e}")


async def load_cogs():
    print("Loading cogs...")
    try:
        # Load cogs one by one with small delay to prevent race conditions
        cogs_to_load = [
            (Ticket_System(bot), 'Ticket system'),
            (Ticket_Command(bot), 'Ticket Commands'),
            (FunCommands(bot), 'Fun Commands'),
            (WelcomeGoodbyeCog(bot), 'Welcomer'),
            (GiveawayCog(bot), 'Giveaway'),
            (MusicCopyrightCog(bot), 'Music Copyright'),
            (Utilities(bot), 'Utilities')
        ]
        
        for cog, name in cogs_to_load:
            await bot.add_cog(cog)
            print(f'Loaded {name}')
            await asyncio.sleep(0.5)  # Small delay between cog loads
            
        print("Cogs loaded successfully.")
    except Exception as e:
        print(f"Error during cog loading setup: {e}")


def main():
    try:
        # Print a very clear starting message
        print("======= BOT STARTING =======")
        # Load cogs before starting the web server to ensure they're loaded
        print("Loading cogs before web server...")
        asyncio.run(load_cogs())
        print("Cogs loaded, now starting web server...")
        
        # Start the web server in a separate thread to avoid blocking
        import threading
        keep_alive_thread = threading.Thread(target=keep_alive)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()
        print("Web server started in background thread")
        
        print("Starting bot...")
        # Start the bot
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error during bot runtime: {e}")
        import traceback
        traceback.print_exc()  # Print full error traceback

# We no longer need run_bot() as we're using bot.run() directly


if __name__ == "__main__":
    main()