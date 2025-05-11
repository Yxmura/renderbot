import discord
from discord import app_commands
import json
import os
from datetime import datetime
import asyncio
from typing import Optional

# Constants
BIRTHDAY_CHANNEL_ID = None  # Set this to your birthday announcement channel ID
BIRTHDAY_FILE = "birthdays.json"

class BirthdayManager:
    def __init__(self):
        self.birthdays = {}
        self.load_birthdays()

    def load_birthdays(self):
        if os.path.exists(BIRTHDAY_FILE):
            with open(BIRTHDAY_FILE, 'r') as f:
                self.birthdays = json.load(f)

    def save_birthdays(self):
        with open(BIRTHDAY_FILE, 'w') as f:
            json.dump(self.birthdays, f, indent=4)

    def set_birthday(self, user_id: str, month: int, day: int):
        self.birthdays[str(user_id)] = {
            "month": month,
            "day": day
        }
        self.save_birthdays()

    def get_birthday(self, user_id: str) -> Optional[dict]:
        return self.birthdays.get(str(user_id))

    def get_todays_birthdays(self) -> list:
        today = datetime.now()
        return [
            user_id for user_id, data in self.birthdays.items()
            if data["month"] == today.month and data["day"] == today.day
        ]

birthday_manager = BirthdayManager()

@app_commands.command(name="setbirthday", description="Set your birthday (can only be set once)")
@app_commands.describe(
    month="Your birth month (1-12)",
    day="Your birth day (1-31)"
)
async def setbirthday(
    interaction: discord.Interaction,
    month: app_commands.Range[int, 1, 12],
    day: app_commands.Range[int, 1, 31]
):
    try:
        datetime(2000, month, day)
    except ValueError:
        await interaction.response.send_message(
            "Invalid date! Please provide a valid month and day.",
            ephemeral=True
        )
        return

    current = birthday_manager.get_birthday(str(interaction.user.id))
    if current:
        await interaction.response.send_message(
            "You can only set your birthday once! Contact a server administrator if you need to change it.",
            ephemeral=True
        )
        return

    birthday_manager.set_birthday(str(interaction.user.id), month, day)
    
    embed = discord.Embed(
        title="🎂 Birthday Set!",
        description=f"Your birthday has been set to {month}/{day}.",
        color=discord.Color.pink()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="mybirthday", description="View your set birthday")
async def mybirthday(interaction: discord.Interaction):
    birthday = birthday_manager.get_birthday(str(interaction.user.id))
    if not birthday:
        await interaction.response.send_message(
            "You haven't set your birthday yet! Use `/setbirthday` to set it.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎂 Your Birthday",
        description=f"Your birthday is set to {birthday['month']}/{birthday['day']}",
        color=discord.Color.pink()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

async def check_birthdays(bot):
    while True:
        now = datetime.now()
        # Wait until midnight
        next_run = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run.replace(day=now.day + 1)
        await asyncio.sleep((next_run - now).total_seconds())

        # Get today's birthdays
        birthdays = birthday_manager.get_todays_birthdays()
        if birthdays:
            # Get the birthday channel
            for guild in bot.guilds:
                channel = guild.get_channel(BIRTHDAY_CHANNEL_ID)
                if channel:
                    for user_id in birthdays:
                        user = guild.get_member(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="🎂 Happy Birthday!",
                                description=f"Today is {user.mention}'s birthday! 🎉",
                                color=discord.Color.pink()
                            )
                            embed.set_thumbnail(url=user.display_avatar.url)
                            await channel.send(embed=embed)

@app_commands.command(name="setup_birthdays", description="Setup the birthday system")
@app_commands.default_permissions(administrator=True)
async def setup_birthdays(
    interaction: discord.Interaction,
    birthday_channel: discord.TextChannel
):
    global BIRTHDAY_CHANNEL_ID
    BIRTHDAY_CHANNEL_ID = birthday_channel.id

    embed = discord.Embed(
        title="🎂 Birthday System Setup",
        description="The birthday system has been configured with the following settings:",
        color=discord.Color.pink()
    )
    embed.add_field(
        name="Birthday Channel",
        value=birthday_channel.mention,
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True) 