import discord
from discord import app_commands, Embed, Color
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import List, Dict, Optional

POLLS_FILE = "polls.json"
# These should ideally be loaded from a config file or database on startup
# For simplicity in this example, we'll use global variables for now,
# but a more robust solution would load these in __init__
POLL_CHANNEL_ID: Optional[int] = None
POLL_ROLE_ID: Optional[int] = None
REQUIRED_ROLE_ID: Optional[int] = None

class Poll:
    def __init__(
        self,
        message_id: int,
        channel_id: int,
        title: str,
        description: str,
        options: List[str],
        end_time: datetime,
        creator_id: int,
        votes: Optional[Dict[str, List[int]]] = None # Make votes optional for initial creation
    ):
        self.message_id = message_id
        self.channel_id = channel_id
        self.title = title
        self.description = description
        self.options = options
        self.end_time = end_time
        self.creator_id = creator_id
        self.votes: Dict[str, List[int]] = votes if votes is not None else {option: [] for option in options}

class PollManager:
    def __init__(self):
        self.polls = {}
        self.load_polls()

    def load_polls(self):
        if os.path.exists(POLLS_FILE):
            with open(POLLS_FILE, 'r') as f:
                try:
                    data = json.load(f)
                    for poll_id, poll_data in data.items():
                        poll_data['end_time'] = datetime.fromisoformat(poll_data['end_time'])
                        # Ensure votes dictionary is properly initialized if missing or incomplete
                        if 'votes' not in poll_data or not isinstance(poll_data['votes'], dict):
                             poll_data['votes'] = {option: [] for option in poll_data.get('options', [])}
                        else:
                             # Clean up votes for options that no longer exist or add missing ones
                             valid_votes = {option: [] for option in poll_data.get('options', [])}
                             for option, user_ids in poll_data['votes'].items():
                                 if option in valid_votes:
                                     valid_votes[option] = user_ids
                             poll_data['votes'] = valid_votes

                        # Poll ID should be the message ID for persistence
                        self.polls[str(poll_data['message_id'])] = Poll(**poll_data)
                except json.JSONDecodeError:
                    self.polls = {}

    def save_polls(self):
        data = {
            str(poll.message_id): { # Use message_id as the key
                'message_id': poll.message_id,
                'channel_id': poll.channel_id,
                'title': poll.title,
                'description': poll.description,
                'options': poll.options,
                'end_time': poll.end_time.isoformat(),
                'creator_id': poll.creator_id,
                'votes': poll.votes
            }
            for poll in self.polls.values() # Iterate over values as message_id is the key
        }
        with open(POLLS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_poll(self, poll: Poll):
        self.polls[str(poll.message_id)] = poll # Use message_id as the key
        self.save_polls()

    def get_poll(self, message_id: int) -> Optional[Poll]:
        return self.polls.get(str(message_id)) # Look up by message_id string

    def remove_poll(self, message_id: int):
        if str(message_id) in self.polls:
            del self.polls[str(message_id)]
            self.save_polls()

poll_manager = PollManager()

class PollView(discord.ui.View):
    def __init__(self, poll: Poll):
        super().__init__(timeout=None) # Keep the view persistent
        self.poll = poll
        for option in poll.options:
            button = discord.ui.Button(
                label=option,
                custom_id=f"poll_{self.poll.message_id}_{option}", # Include message_id in custom_id for persistence
                style=discord.ButtonStyle.primary
            )
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        # Extract message_id and option from custom_id
        parts = interaction.data['custom_id'].split('_')
        if len(parts) < 3 or not parts[1].isdigit():
            await interaction.response.send_message("Invalid button interaction.", ephemeral=True)
            return

        message_id = int(parts[1])
        option = '_'.join(parts[2:]) # Handle options with underscores if any

        poll = poll_manager.get_poll(message_id)
        if not poll:
            await interaction.response.send_message("This poll is no longer active.", ephemeral=True)
            return

        if datetime.now() >= poll.end_time:
             await interaction.response.send_message("This poll has already ended.", ephemeral=True)
             return

        # Remove user's previous votes
        for opt in poll.options:
            if interaction.user.id in poll.votes[opt]:
                poll.votes[opt].remove(interaction.user.id)

        # Add new vote
        if option in poll.votes:
            poll.votes[option].append(interaction.user.id)
            poll_manager.save_polls()

            await interaction.response.send_message(
                f"You voted for: {option}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("Invalid option.", ephemeral=True)


# You can keep this outside the cog or integrate it as a task method
async def end_poll(bot: commands.Bot, poll: Poll):
    channel = bot.get_channel(poll.channel_id)
    if not channel:
        poll_manager.remove_poll(poll.message_id)
        return

    try:
        message = await channel.fetch_message(poll.message_id)

        # Calculate results
        total_votes = sum(len(votes) for votes in poll.votes.values())
        results = []

        for option, votes in poll.votes.items():
            percentage = (len(votes) / total_votes * 100) if total_votes > 0 else 0
            results.append(f"{option}: {len(votes)} votes ({percentage:.1f}%)")

        embed = Embed(
            title=f"📊 Poll Results: {poll.title}",
            description=poll.description,
            color=Color.purple()
        )
        embed.add_field(
            name="Results",
            value="\n".join(results),
            inline=False
        )
        embed.set_footer(text=f"Total votes: {total_votes}")

        # Remove the view so buttons are disabled
        await message.edit(embed=embed, view=None)
        await channel.send(
            f"Poll '{poll.title}' has ended! Here are the results:",
            embed=embed
        )
    except discord.NotFound:
        print(f"Poll message {poll.message_id} not found in channel {poll.channel_id}. Removing poll.")
    except Exception as e:
        print(f"Error ending poll {poll.message_id}: {e}")
    finally:
        poll_manager.remove_poll(poll.message_id)


class PollCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_ending_polls.start()
        self.load_config() # Load configuration on cog initialization

    def cog_unload(self):
        self.check_ending_polls.cancel()

    def load_config(self):
        global POLL_CHANNEL_ID, POLL_ROLE_ID, REQUIRED_ROLE_ID
        # Ideally load from a persistent config file
        if os.path.exists("poll_config.json"):
            with open("poll_config.json", "r") as f:
                try:
                    config_data = json.load(f)
                    POLL_CHANNEL_ID = config_data.get("poll_channel_id")
                    POLL_ROLE_ID = config_data.get("poll_role_id")
                    REQUIRED_ROLE_ID = config_data.get("required_role_id")
                except json.JSONDecodeError:
                     print("Error loading poll_config.json. Using default/None values.")
                     POLL_CHANNEL_ID = None
                     POLL_ROLE_ID = None
                     REQUIRED_ROLE_ID = None

    def save_config(self):
         config_data = {
             "poll_channel_id": POLL_CHANNEL_ID,
             "poll_role_id": POLL_ROLE_ID,
             "required_role_id": REQUIRED_ROLE_ID
         }
         with open("poll_config.json", "w") as f:
             json.dump(config_data, f, indent=4)

    @commands.Cog.listener()
    async def on_ready(self):
        print("PollCog ready.")
        # Add persistent views for active polls
        for poll in poll_manager.polls.values():
             # Ensure the message exists before adding the view
             channel = self.bot.get_channel(poll.channel_id)
             if channel:
                 try:
                     await channel.fetch_message(poll.message_id)
                     self.bot.add_view(PollView(poll))
                 except discord.NotFound:
                     print(f"Poll message {poll.message_id} not found on startup. Removing poll.")
                     poll_manager.remove_poll(poll.message_id)
                 except Exception as e:
                      print(f"Error adding persistent view for poll {poll.message_id}: {e}")
             else:
                 print(f"Poll channel {poll.channel_id} not found on startup. Removing poll.")
                 poll_manager.remove_poll(poll.message_id)


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
        if interaction.guild is None:
             await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
             return

        if REQUIRED_ROLE_ID is not None:
            required_role = interaction.guild.get_role(REQUIRED_ROLE_ID)
            if required_role not in interaction.user.roles:
                await interaction.response.send_message(
                    f"You need the {required_role.name} role to create polls!",
                    ephemeral=True
                )
                return
        elif REQUIRED_ROLE_ID is None and interaction.user.guild_permissions.administrator:
             # Allow administrators to create polls if no required role is set
             pass
        elif REQUIRED_ROLE_ID is None:
             await interaction.response.send_message(
                 "The poll system needs to be set up by an administrator first.",
                 ephemeral=True
             )
             return


        if POLL_CHANNEL_ID is None:
            await interaction.response.send_message(
                "Poll channel is not configured! An administrator needs to use `/setuppoll` first.",
                ephemeral=True
            )
            return

        channel = interaction.guild.get_channel(POLL_CHANNEL_ID)
        if not channel:
             await interaction.response.send_message(
                 "The configured poll channel was not found!",
                 ephemeral=True
             )
             return


        option_list = [opt.strip() for opt in options.split(',') if opt.strip()]
        if len(option_list) < 2:
            await interaction.response.send_message(
                "You need at least 2 options for a poll!",
                ephemeral=True
            )
            return

        if len(option_list) > 5: # Limit to 5 options for button clarity
            await interaction.response.send_message(
                "You can't have more than 5 options!",
                ephemeral=True
            )
            return

        end_time = datetime.now() + timedelta(hours=duration)

        # Create a temporary Poll object to pass to the view
        # message_id will be set after sending
        temp_poll = Poll(
            message_id=0, # Placeholder
            channel_id=POLL_CHANNEL_ID,
            title=title,
            description=description,
            options=option_list,
            end_time=end_time,
            creator_id=interaction.user.id
        )


        embed = Embed(
            title=f"📊 {title}",
            description=f"{description}\n\n"
                    f"Ends: <t:{int(end_time.timestamp())}:R>",
            color=Color.purple()
        )
        embed.set_footer(text=f"Created by {interaction.user.name}")

        view = PollView(temp_poll) # Pass the temporary poll object to the view

        notification_message = "New poll!"
        if POLL_ROLE_ID:
            notification_role = interaction.guild.get_role(POLL_ROLE_ID)
            if notification_role:
                 notification_message = f"{notification_role.mention} New poll!"

        # Defer the interaction before sending the message
        await interaction.response.defer()

        try:
            message = await channel.send(
                notification_message,
                embed=embed,
                view=view
            )

            # Now that the message is sent, update the message_id in the poll object and the view
            poll = Poll(
                message_id=message.id,
                channel_id=POLL_CHANNEL_ID,
                title=title,
                description=description,
                options=option_list,
                end_time=end_time,
                creator_id=interaction.user.id,
                votes={option: [] for option in option_list} # Initialize votes
            )
            poll_manager.add_poll(poll)

            # Update the custom_ids in the view's items now that we have the message_id
            # This is important for persistence if the bot restarts before a vote
            updated_view = PollView(poll)
            await message.edit(view=updated_view)


            await interaction.followup.send(
                f"Poll created in {channel.mention}!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"An error occurred while creating the poll: {e}", ephemeral=True)


    @app_commands.command(name="setuppoll", description="Setup the poll system")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        poll_channel="The channel where polls will be posted",
        poll_role="The role to mention for new polls",
        required_role="The role required to create polls"
    )
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

        self.save_config() # Save configuration

        embed = Embed(
            title="📊 Poll System Setup",
            description="The poll system has been configured with the following settings:",
            color=Color.green()
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
    async def check_ending_polls(self):
        now = datetime.now()
        # Iterate over a copy of the polls dictionary to avoid issues during removal
        for poll_id, poll in list(poll_manager.polls.items()):
            if now >= poll.end_time:
                await end_poll(self.bot, poll)

    @check_ending_polls.before_loop
    async def before_check_ending_polls(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(PollCog(bot))
