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

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    
    await bot.add_cog(Ticket_System(bot))
    print('loaded ticket system')
    await bot.add_cog(Ticket_Command(bot))
    print('loaded ticket command')
    await bot.add_cog(FunCommands(bot))
    print('loaded funcommands')
    await bot.add_cog(GiveawayCog(bot))
    print('loaded giveawaycog')
    await bot.add_cog(MusicCopyrightCog(bot))
    print('loaded music copyright')
    await bot.add_cog(PollCog(bot))
    print('loaded pollcog')
    await bot.add_cog(WelcomeGoodbyeCog(bot))
    print('loaded welcoming cog')
    await bot.add_cog(Utilities(bot))
    print('loaded utils')
    print('done loading cogs 🎉, starting richpresence')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='you | /help'))

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
