import discord
import json
from discord import *
from discord.ext import commands, tasks
from cogs.ticket_system import Ticket_System
from cogs.ticket_commands import Ticket_Command
from cogs.fun import FunCommands
from keep_alive import keep_alive
from dotenv import load_dotenv
import os

#This will get everything from the config.json file
with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

load_dotenv()
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = config["guild_id"] #Your Server ID aka Guild ID
CATEGORY_ID = config["category_id"]

bot = commands.Bot(intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f'Bot Started | {bot.user.name}')
    # Ensure the cog setup functions are awaited
    await bot.add_cog(Ticket_System(bot))
    await bot.add_cog(Ticket_Command(bot))
    await bot.add_cog(FunCommands(bot)) # Add the FunCommands cog
    richpresence.start()


#Bot Status, Counting all opened Tickets in the Server. You need to add/change things if you have more or less than 2 Categories
@tasks.loop(minutes=1)
async def richpresence():
    guild = bot.get_guild(GUILD_ID)
    # You can adjust this to count tickets in specific categories if needed
    ticket_count = sum(1 for channel in guild.channels if isinstance(channel, discord.TextChannel) and channel.category_id == CATEGORY_ID and channel.name.startswith("ticket-"))
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=f'{ticket_count} open tickets | /help'))


def main():
    keep_alive()
    try:
        print("Starting bot...")
        bot.run(BOT_TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
