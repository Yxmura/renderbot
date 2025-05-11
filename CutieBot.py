import discord
from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv
import os
import sys
import asyncio

from keep_alive import keep_alive
from commands import (
    hello, spam_ping, dadjoke, help_command,
    rps, meme, create_embed, coinflip, random_fact, ping,
    ticket, setup_tickets, flagguess,
    setbirthday, mybirthday, setup_birthdays, check_birthdays,
    createrolemenu, deleterolemenu,
    help, setup, welcome, goodbye, birthday, reaction_roles, giveaway,
    reminder, kiss, poll
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
    await bot.tree.add_command(spam_ping)
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
    await bot.tree.add_command(help)
    await bot.tree.add_command(setup)
    await bot.tree.add_command(welcome)
    await bot.tree.add_command(goodbye)
    await bot.tree.add_command(birthday.viewbirthday)
    await bot.tree.add_command(reaction_roles.createrolemenu)
    await bot.tree.add_command(reaction_roles.deleterolemenu)
    await bot.tree.add_command(giveaway.creategiveaway)
    await bot.tree.add_command(giveaway.setupgiveaway)
    await bot.tree.add_command(reminder.remind)
    await bot.tree.add_command(kiss.kiss)
    await bot.tree.add_command(poll.createpoll)
    await bot.tree.add_command(poll.setuppoll)

@bot.event
async def on_member_join(member):
    # Get the system channel (default channel for system messages)
    channel = member.guild.system_channel
    if channel is not None:
        # Get member count
        member_count = member.guild.member_count
        
        # Create welcome embed
        embed = discord.Embed(
            title=f"Welcome to {member.guild.name}!",
            description=f"Hey {member.mention}, welcome to our server! 🎉",
            color=discord.Color.green()
        )
        
        # Add fields to the embed
        embed.add_field(
            name="📜 Important",
            value="Please make sure to read our rules to ensure a great experience for everyone!",
            inline=False
        )
        embed.add_field(
            name="👥 Member Count",
            value=f"You are our {member_count}th member!",
            inline=False
        )
        embed.add_field(
            name="🎮 Have Fun!",
            value="We hope you enjoy your stay and make new friends!",
            inline=False
        )
        
        # Set user avatar as thumbnail
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Set server icon as footer
        if member.guild.icon:
            embed.set_footer(text=f"Joined at {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}", 
                           icon_url=member.guild.icon.url)
        else:
            embed.set_footer(text=f"Joined at {member.joined_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        await channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    await setup_commands()
    asyncio.create_task(birthday.check_birthdays(bot))
    asyncio.create_task(giveaway.check_giveaways(bot))
    asyncio.create_task(reminder.check_reminders(bot))
    asyncio.create_task(poll.check_polls(bot))
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
