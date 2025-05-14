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
import traceback  # Add this for better error reporting

# This will get everything from the config.json file
try:
    with open("config.json", mode="r") as config_file:
        config = json.load(config_file)
    GUILD_ID = config["guild_id"]
    CATEGORY_ID = config["category_id"]
    print(f"Config loaded successfully. Guild ID: {GUILD_ID}")
except Exception as e:
    print(f"Error loading config.json: {e}")
    traceback.print_exc()
    # Default values in case config fails to load
    GUILD_ID = 0  # You'll need to set this if config fails
    CATEGORY_ID = 0

try:
    load_dotenv()
    BOT_TOKEN = os.getenv('DISCORD_TOKEN')
    if not BOT_TOKEN:
        print("WARNING: No DISCORD_TOKEN found in environment variables!")
except Exception as e:
    print(f"Error loading .env file: {e}")
    BOT_TOKEN = None  # Will cause the bot to fail when trying to start

# Setup logging to help with debugging
import logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Flag to track if we've already synced commands
commands_synced = False

@bot.event
async def on_ready():
    global commands_synced
    print("============ BOT READY EVENT ============")
    print(f'Bot Started | {bot.user.name}')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'you | /help'))
    
    # Only sync commands once
    if not commands_synced:
        print("Will attempt to sync commands in 5 seconds...")
        await asyncio.sleep(5)  # Shorter delay since we already loaded cogs before starting the bot
        
        print(f"Attempting to sync slash commands to guild ID: {GUILD_ID}")
        try:
            # Sync commands to the specific guild
            guild_object = discord.Object(id=GUILD_ID)
            synced = await bot.tree.sync(guild=guild_object)
            print(f"✅ Successfully synced {len(synced)} command(s) to guild {GUILD_ID}.")
            if synced:
                print(f"Synced command names: {[cmd.name for cmd in synced]}")
            else:
                print("No commands were synced. This may indicate a problem with command registration in your cogs.")
            commands_synced = True
        except Exception as e:
            print(f"❌ Failed to sync commands to guild {GUILD_ID}: {e}")
            import traceback
            traceback.print_exc()
    
    print("============ BOT READY COMPLETED ============")


async def load_cogs():
    print("============ LOADING COGS ============")
    try:
        # Load cogs one by one with explicit error handling
        cogs_to_load = [
            (Ticket_System(bot), 'Ticket system'),
            (Ticket_Command(bot), 'Ticket Commands'),
            (FunCommands(bot), 'Fun Commands'),
            (WelcomeGoodbyeCog(bot), 'Welcomer'),
            (GiveawayCog(bot), 'Giveaway'),
            (MusicCopyrightCog(bot), 'Music Copyright'),
            (Utilities(bot), 'Utilities')
        ]
        
        # Manual command to sync commands
        try:
            from sync_commands import SyncCommands
            await bot.add_cog(SyncCommands(bot))
            print("✅ Added SyncCommands cog for manual syncing")
        except Exception as e:
            print(f"❌ Error loading SyncCommands: {e}")
            traceback.print_exc()
        
        for cog, name in cogs_to_load:
            try:
                print(f"Attempting to load cog: {name}")
                await bot.add_cog(cog)
                print(f"✅ Successfully loaded: {name}")
            except Exception as e:
                print(f"❌ Error loading {name}: {e}")
                traceback.print_exc()
            
        print("============ COGS LOADING COMPLETED ============")
    except Exception as e:
        print(f"CRITICAL ERROR during cog loading setup: {e}")
        traceback.print_exc()


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