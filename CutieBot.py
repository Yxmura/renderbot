import discord
from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv
import os
import sys
import asyncio

from keep_alive import keep_alive
from commands import (
    hello, dadjoke, help_command,
    rps, meme, create_embed, coinflip, random_fact, ping,
    ticket, setup_tickets, flagguess,
    setbirthday, mybirthday, setup_birthdays, check_birthdays,
    createrolemenu, deleterolemenu,
    setup,
    welcome_setup, goodbye_setup,
    creategiveaway, setupgiveaway, check_giveaways,
    remind, check_reminders,
    kiss,
    createpoll, setuppoll, check_polls
)

load_dotenv(".env")
TOKEN = os.getenv("DISCORD_TOKEN")

# Exit if the token is not loaded
if not TOKEN:
    print("Error: Discord token not found in .env file.")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)

async def setup_commands():
    await bot.tree.add_command(hello)
    await bot.tree.add_command(dadjoke)
    await bot.tree.add_command(help_command)
    await bot.tree.add_command(rps)
    await bot.tree.add_command(meme)
    await bot.tree.add_command(create_embed)
    await bot.tree.add_command(coinflip)
    await bot.tree.add_command(random_fact)
    await bot.tree.add_command(ticket)
    await bot.tree.add_command(setup_tickets)
    await bot.tree.add_command(flagguess)
    await bot.tree.add_command(setbirthday)
    await bot.tree.add_command(mybirthday)
    await bot.tree.add_command(setup_birthdays)
    await bot.tree.add_command(createrolemenu)
    await bot.tree.add_command(deleterolemenu)
    await bot.tree.add_command(setup)
    await bot.tree.add_command(creategiveaway)
    await bot.tree.add_command(setupgiveaway)
    await bot.tree.add_command(remind)
    await bot.tree.add_command(kiss)
    await bot.tree.add_command(createpoll)
    await bot.tree.add_command(setuppoll)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await setup_commands()
    welcome_setup(bot)
    goodbye_setup(bot)
    asyncio.create_task(check_birthdays(bot))
    asyncio.create_task(check_giveaways(bot))
    asyncio.create_task(check_reminders(bot))
    asyncio.create_task(check_polls(bot))
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Main Function
def main():
    keep_alive()  # Start the keep-alive server
    try:
        print("Starting bot...")
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("Error: Invalid Discord token. Please check your .env file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
