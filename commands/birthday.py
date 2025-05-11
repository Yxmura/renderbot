import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import datetime, timedelta
import asyncio
from typing import Optional

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

class BirthdayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(self.setbirthday)
        self.bot.tree.add_command(self.mybirthday)
        self.bot.tree.add_command(self.setupbirthdays)
        self.manager = BirthdayManager()
        self.birthday_channel_id = None
        self.bot.loop.create_task(self.check_birthdays_loop())

    # Slash command: /setbirthday
    @app_commands.command(name="setbirthday", description="Set your birthday (can only be set once)")
    @app_commands.describe(month="Your birth month (1-12)", day="Your birth day (1-31)")
    async def set_birthday(self, interaction: discord.Interaction, month: app_commands.Range[int, 1, 12], day: app_commands.Range[int, 1, 31]):
        try:
            datetime(2000, month, day)
        except ValueError:
            await interaction.response.send_message(
                "Invalid date! Please provide a valid month and day.",
                ephemeral=True
            )
            return

        current = self.manager.get_birthday(str(interaction.user.id))
        if current:
            await interaction.response.send_message(
                "You can only set your birthday once! Contact a server administrator to change it.",
                ephemeral=True
            )
            return

        self.manager.set_birthday(str(interaction.user.id), month, day)
        embed = discord.Embed(
            title="🎂 Birthday Set!",
            description=f"Your birthday has been set to {month}/{day}.",
            color=discord.Color.pink()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Slash command: /mybirthday
    @app_commands.command(name="mybirthday", description="View your set birthday")
    async def my_birthday(self, interaction: discord.Interaction):
        birthday = self.manager.get_birthday(str(interaction.user.id))
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

    # Slash command: /setup_birthdays
    @app_commands.command(name="setup_birthdays", description="Setup the birthday announcement channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_birthdays(self, interaction: discord.Interaction, birthday_channel: discord.TextChannel):
        self.birthday_channel_id = birthday_channel.id

        embed = discord.Embed(
            title="🎂 Birthday System Setup",
            description="Birthday announcements will be sent to:",
            color=discord.Color.pink()
        )
        embed.add_field(name="Channel", value=birthday_channel.mention)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Background task
    async def check_birthdays_loop(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            now = datetime.now()
            next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(wait_seconds)

            birthdays_today = self.manager.get_todays_birthdays()
            if not birthdays_today or not self.birthday_channel_id:
                continue

            for guild in self.bot.guilds:
                channel = guild.get_channel(self.birthday_channel_id)
                if not channel:
                    continue
                for user_id in birthdays_today:
                    user = guild.get_member(int(user_id))
                    if user:
                        embed = discord.Embed(
                            title="🎂 Happy Birthday!",
                            description=f"Today is {user.mention}'s birthday! 🎉",
                            color=discord.Color.pink()
                        )
                        embed.set_thumbnail(url=user.display_avatar.url)
                        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(BirthdayCog(bot))
