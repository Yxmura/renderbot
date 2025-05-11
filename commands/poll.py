import discord
from discord import app_commands
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict

POLLS_FILE = "polls.json"
POLL_CHANNEL_ID = 1368282389608140822
POLL_ROLE_ID = 1368596260340240514
REQUIRED_ROLE_ID = 1317606142523998258

class Poll:
    def __init__(
        self,
        message_id: int,
        channel_id: int,
        title: str,
        description: str,
        options: List[str],
        end_time: datetime,
        creator_id: int
    ):
        self.message_id = message_id
        self.channel_id = channel_id
        self.title = title
        self.description = description
        self.options = options
        self.end_time = end_time
        self.creator_id = creator_id
        self.votes: Dict[str, List[int]] = {option: [] for option in options}

class PollManager:
    def __init__(self):
        self.polls = {}
        self.load_polls()

    def load_polls(self):
        if os.path.exists(POLLS_FILE):
            with open(POLLS_FILE, 'r') as f:
                data = json.load(f)
                for poll_id, poll_data in data.items():
                    poll_data['end_time'] = datetime.fromisoformat(poll_data['end_time'])
                    self.polls[poll_id] = Poll(**poll_data)

    def save_polls(self):
        data = {
            poll_id: {
                'message_id': poll.message_id,
                'channel_id': poll.channel_id,
                'title': poll.title,
                'description': poll.description,
                'options': poll.options,
                'end_time': poll.end_time.isoformat(),
                'creator_id': poll.creator_id,
                'votes': poll.votes
            }
            for poll_id, poll in self.polls.items()
        }
        with open(POLLS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_poll(self, poll_id: str, poll: Poll):
        self.polls[poll_id] = poll
        self.save_polls()

    def get_poll(self, poll_id: str) -> Poll:
        return self.polls.get(poll_id)

    def remove_poll(self, poll_id: str):
        if poll_id in self.polls:
            del self.polls[poll_id]
            self.save_polls()

poll_manager = PollManager()

class PollView(discord.ui.View):
    def __init__(self, poll: Poll):
        super().__init__(timeout=None)
        self.poll = poll
        for option in poll.options:
            button = discord.ui.Button(
                label=option,
                custom_id=f"poll_{option}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        # Remove user's previous votes
        for option in self.poll.options:
            if interaction.user.id in self.poll.votes[option]:
                self.poll.votes[option].remove(interaction.user.id)

        # Add new vote
        option = interaction.data['custom_id'].replace('poll_', '')
        self.poll.votes[option].append(interaction.user.id)
        poll_manager.save_polls()

        await interaction.response.send_message(
            f"You voted for: {option}",
            ephemeral=True
        )

async def check_polls(bot):
    while True:
        now = datetime.now()
        for poll_id, poll in list(poll_manager.polls.items()):
            if now >= poll.end_time:
                channel = bot.get_channel(poll.channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(poll.message_id)
                        
                        # Calculate results
                        total_votes = sum(len(votes) for votes in poll.votes.values())
                        results = []
                        
                        for option, votes in poll.votes.items():
                            percentage = (len(votes) / total_votes * 100) if total_votes > 0 else 0
                            results.append(f"{option}: {len(votes)} votes ({percentage:.1f}%)")
                        
                        embed = discord.Embed(
                            title=f"📊 Poll Results: {poll.title}",
                            description=poll.description,
                            color=discord.Color.blue()
                        )
                        embed.add_field(
                            name="Results",
                            value="\n".join(results),
                            inline=False
                        )
                        embed.set_footer(text=f"Total votes: {total_votes}")
                        
                        await message.edit(embed=embed, view=None)
                        await channel.send(
                            f"Poll '{poll.title}' has ended! Here are the results:",
                            embed=embed
                        )
                    except:
                        pass
                poll_manager.remove_poll(poll_id)
        await asyncio.sleep(60)

class PollCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_polls.start()

    @app_commands.command(name="createpoll", description="Create a new poll")
    @app_commands.describe(
        title="The title of the poll",
        description="Description of the poll",
        options="Poll options (comma-separated)",
        duration="Duration in hours"
    )
    async def createpoll(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        options: str,
        duration: app_commands.Range[int, 1, 168]
    ):
        if not any(role.id == REQUIRED_ROLE_ID for role in interaction.user.roles):
            await interaction.response.send_message(
                "You don't have permission to create polls!",
                ephemeral=True
            )
            return

        if not POLL_CHANNEL_ID:
            await interaction.response.send_message(
                "Poll channel is not configured!",
                ephemeral=True
            )
            return

        option_list = [opt.strip() for opt in options.split(',')]
        if len(option_list) < 2:
            await interaction.response.send_message(
                "You need at least 2 options for a poll!",
                ephemeral=True
            )
            return

        if len(option_list) > 5:
            await interaction.response.send_message(
                "You can't have more than 5 options!",
                ephemeral=True
            )
            return

        end_time = datetime.now() + timedelta(hours=duration)
        
        poll = Poll(
            message_id=0,  # Will be set after sending
            channel_id=POLL_CHANNEL_ID,
            title=title,
            description=description,
            options=option_list,
            end_time=end_time,
            creator_id=interaction.user.id
        )

        embed = discord.Embed(
            title=f"📊 {title}",
            description=f"{description}\n\n"
                    f"Ends: <t:{int(end_time.timestamp())}:R>",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Created by {interaction.user.name}")

        view = PollView(poll)
        channel = interaction.guild.get_channel(POLL_CHANNEL_ID)
        message = await channel.send(
            f"<@&{POLL_ROLE_ID}> New poll!" if POLL_ROLE_ID else "New poll!",
            embed=embed,
            view=view
        )
        
        poll.message_id = message.id
        poll_manager.add_poll(str(message.id), poll)

        await interaction.response.send_message(
            f"Poll created in {channel.mention}!",
            ephemeral=True
        )

    @app_commands.command(name="setuppoll", description="Setup the poll system")
    @app_commands.default_permissions(administrator=True)
    async def setuppoll(
        self,
        interaction: discord.Interaction,
        poll_channel: discord.TextChannel,
        poll_role: discord.Role,
        required_role: discord.Role
    ):
        global POLL_CHANNEL_ID, POLL_ROLE_ID, REQUIRED_ROLE_ID
        POLL_CHANNEL_ID = poll_channel.id
        POLL_ROLE_ID = poll_role.id
        REQUIRED_ROLE_ID = required_role.id

        embed = discord.Embed(
            title="📊 Poll System Setup",
            description="The poll system has been configured with the following settings:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Poll Channel",
            value=poll_channel.mention,
            inline=True
        )
        embed.add_field(
            name="Notification Role",
            value=poll_role.mention,
            inline=True
        )
        embed.add_field(
            name="Required Role",
            value=required_role.mention,
            inline=True
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(seconds=60)
    async def check_polls(self):
        await check_polls(self.bot)

# Setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    bot.add_cog(PollCog(bot))
