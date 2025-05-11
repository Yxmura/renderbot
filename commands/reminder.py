import discord
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import json
import os

REMINDERS_FILE = "reminders.json"

class Reminder:
    def __init__(self, user_id: int, channel_id: int, message: str, end_time: datetime):
        self.user_id = user_id
        self.channel_id = channel_id
        self.message = message
        self.end_time = end_time

class ReminderManager:
    def __init__(self):
        self.reminders = {}
        self.load_reminders()

    def load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r') as f:
                data = json.load(f)
                for reminder_id, reminder_data in data.items():
                    reminder_data['end_time'] = datetime.fromisoformat(reminder_data['end_time'])
                    self.reminders[reminder_id] = Reminder(**reminder_data)

    def save_reminders(self):
        data = {
            reminder_id: {
                'user_id': reminder.user_id,
                'channel_id': reminder.channel_id,
                'message': reminder.message,
                'end_time': reminder.end_time.isoformat()
            }
            for reminder_id, reminder in self.reminders.items()
        }
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_reminder(self, reminder_id: str, reminder: Reminder):
        self.reminders[reminder_id] = reminder
        self.save_reminders()

    def remove_reminder(self, reminder_id: str):
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self.save_reminders()

reminder_manager = ReminderManager()

async def check_reminders(bot):
    while True:
        now = datetime.now()
        for reminder_id, reminder in list(reminder_manager.reminders.items()):
            if now >= reminder.end_time:
                channel = bot.get_channel(reminder.channel_id)
                if channel:
                    user = bot.get_user(reminder.user_id)
                    if user:
                        embed = discord.Embed(
                            title="⏰ Reminder",
                            description=reminder.message,
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text=f"Reminder set by {user.name}")
                        await channel.send(f"{user.mention} Here's your reminder!", embed=embed)
                reminder_manager.remove_reminder(reminder_id)
        await asyncio.sleep(60)

@app_commands.command(name="remind", description="Set a reminder")
@app_commands.describe(
    time="When to remind you (e.g., '1h', '30m', '1d')",
    message="What to remind you about"
)
async def remind(
    interaction: discord.Interaction,
    time: str,
    message: str
):
    try:
        # Parse time string
        unit = time[-1].lower()
        value = int(time[:-1])
        
        if unit == 's':
            delta = timedelta(seconds=value)
        elif unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        else:
            await interaction.response.send_message(
                "Invalid time format! Use 's' for seconds, 'm' for minutes, 'h' for hours, or 'd' for days.",
                ephemeral=True
            )
            return

        end_time = datetime.now() + delta
        
        reminder = Reminder(
            user_id=interaction.user.id,
            channel_id=interaction.channel_id,
            message=message,
            end_time=end_time
        )

        reminder_id = f"{interaction.user.id}_{int(end_time.timestamp())}"
        reminder_manager.add_reminder(reminder_id, reminder)

        embed = discord.Embed(
            title="⏰ Reminder Set",
            description=f"I'll remind you about:\n{message}",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Time",
            value=f"<t:{int(end_time.timestamp())}:R>",
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except ValueError:
        await interaction.response.send_message(
            "Invalid time format! Please use a number followed by 's', 'm', 'h', or 'd'.",
            ephemeral=True
        ) 