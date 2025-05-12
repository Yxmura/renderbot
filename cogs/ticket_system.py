import discord
import asyncio
import pytz
import json
import sqlite3
from datetime import datetime
import chat_exporter
import io
from discord.ext import commands
from discord import app_commands, Embed, Color, File, Interaction, Member, ui

#This will get everything from the config.json file
with open("config.json", mode="r") as config_file:
    config = json.load(config_file)

GUILD_ID = config["guild_id"]
TICKET_CHANNEL = config["ticket_channel_id"]
CATEGORY_ID = config["category_id"]
TEAM_ROLE = config["team_role_id"]
LOG_CHANNEL = config["log_channel_id"]
TIMEZONE = config["timezone"]
EMBED_TITLE = config["embed_title"]
EMBED_DESCRIPTION = config["embed_description"]

#This will create and connect to the database
conn = sqlite3.connect('Database.db')
cur = conn.cursor()

#Create the table if it doesn't exist
cur.execute("""CREATE TABLE IF NOT EXISTS ticket
           (id INTEGER PRIMARY KEY AUTOINCREMENT, discord_name TEXT, discord_id INTEGER UNIQUE, ticket_channel INTEGER UNIQUE, ticket_created TEXT)""")
conn.commit()

# Modal for entering the close reason
class CloseReasonModal(ui.Modal, title="Close Ticket"):
    reason = ui.TextInput(label="Reason for closing", style=discord.TextStyle.paragraph, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        # Store the reason and user for later use
        self.view.close_reason = self.reason.value
        self.view.closer = interaction.user
        await interaction.response.send_message("Reason submitted. Requesting confirmation from ticket creator...", ephemeral=True)
        await self.view.request_creator_confirmation(interaction)


# View for confirming ticket closure with the creator
class CreatorConfirmationView(ui.View):
    def __init__(self, bot, original_interaction: discord.Interaction, close_reason: str, closer: discord.User):
        super().__init__(timeout=600)  # Timeout after 10 minutes
        self.bot = bot
        self.original_interaction = original_interaction
        self.close_reason = close_reason
        self.closer = closer
        self.confirmed = False

    @ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: ui.Button):
        self.confirmed = True
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Ticket closure confirmed. Deleting ticket...", ephemeral=False)
        await self.delete_ticket(self.original_interaction, self.close_reason, self.closer)
        self.stop()

    @ui.button(label="Keep Open", style=discord.ButtonStyle.secondary)
    async def keep_open(self, interaction: discord.Interaction, button: ui.Button):
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Ticket will remain open.", ephemeral=False)
        self.stop()

    async def on_timeout(self):
        if not self.confirmed:
            for item in self.children:
                item.disabled = True
            await self.original_interaction.message.edit(view=self)
            await self.original_interaction.channel.send("Ticket closure confirmation timed out.")

    async def delete_ticket(self, interaction: discord.Interaction, close_reason: str, closer: discord.User):
        guild = self.bot.get_guild(GUILD_ID)
        log_channel = self.bot.get_channel(LOG_CHANNEL)
        ticket_id = interaction.channel.id

        cur.execute("SELECT id, discord_id, ticket_created FROM ticket WHERE ticket_channel=?", (ticket_id,))
        ticket_data = cur.fetchone()

        if not ticket_data:
            # This should ideally not happen if confirmation view was sent, but for safety
            await interaction.channel.send("Error: Could not find ticket data in the database during deletion.")
            return

        id, ticket_creator_id, ticket_created = ticket_data
        ticket_creator = guild.get_member(ticket_creator_id)

        ticket_created_unix = self.convert_to_unix_timestamp(ticket_created)
        timezone = pytz.timezone(TIMEZONE)
        ticket_closed = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        ticket_closed_unix = self.convert_to_unix_timestamp(ticket_closed)

        # Creating the Transcript
        military_time: bool = True
        transcript = await chat_exporter.export(interaction.channel, limit=200, tz_info=TIMEZONE, military_time=military_time, bot=self.bot)

        if transcript is None:
             # Send a message in the channel if transcript generation fails before deletion
            await interaction.channel.send("Warning: Could not generate transcript for this ticket.")
            transcript_file_user = None
            transcript_file_log = None
        else:
            transcript_file_user = File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{interaction.channel.name}.html")
            transcript_file_log = File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{interaction.channel.name}.html")


        transcript_info = Embed(title=f"Ticket Deleted | {interaction.channel.name}", color=Color.purple())
        transcript_info.add_field(name="ID", value=id, inline=True)
        transcript_info.add_field(name="Opened by", value=ticket_creator.mention if ticket_creator else "Unknown User", inline=True)
        transcript_info.add_field(name="Closed by", value=closer.mention, inline=True)
        transcript_info.add_field(name="Close Reason", value=close_reason, inline=False)
        transcript_info.add_field(name="Ticket Created", value=f"<t:{ticket_created_unix}:f>", inline=True)
        transcript_info.add_field(name="Ticket Closed", value=f"<t:{ticket_closed_unix}:f>", inline=True)

        if ticket_creator:
            try:
                await ticket_creator.send(embed=transcript_info, file=transcript_file_user)
            except discord.errors.Forbidden:
                transcript_info.add_field(name="Error", value="Ticket Creator DM`s are disabled", inline=True)
        else:
             transcript_info.add_field(name="Note", value="Ticket creator no longer in the server.", inline=True)


        if log_channel:
            if transcript_file_log:
                await log_channel.send(embed=transcript_info, file=transcript_file_log)
            else:
                 await log_channel.send(embed=transcript_info) # Send embed without file if transcript failed
        else:
            print("Log channel not found. Transcript not sent to log channel.")

        # Add a small delay before deleting the channel
        await asyncio.sleep(3)
        await interaction.channel.delete(reason=f"Ticket Closed by {closer.name} - Reason: {close_reason}")
        cur.execute("DELETE FROM ticket WHERE ticket_channel=?", (ticket_id,))
        conn.commit()


    def convert_to_unix_timestamp(self, date_string):
        date_format = "%Y-%m-%d %H:%M:%S"
        dt_obj = datetime.strptime(date_string, date_format)
        try:
            local_tz = pytz.timezone(TIMEZONE)
            dt_obj = local_tz.localize(dt_obj)
            dt_obj_utc = dt_obj.astimezone(pytz.utc)
            return int(dt_obj_utc.timestamp())
        except pytz.UnknownTimeZoneError:
            print(f"Warning: Unknown timezone '{TIMEZONE}'. Using UTC.")
            return int(dt_obj.timestamp())


# Buttons to reopen or delete the Ticket (This view is triggered after the close button)
class TicketOptions(ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)
        self.close_reason = None
        self.closer = None

    async def request_creator_confirmation(self, interaction: discord.Interaction):
        # Get the ticket creator
        cur.execute("SELECT discord_id FROM ticket WHERE ticket_channel=?", (interaction.channel.id,))
        ticket_creator_id_data = cur.fetchone()
        if ticket_creator_id_data:
            ticket_creator_id = ticket_creator_id_data[0]
            ticket_creator = self.bot.get_user(ticket_creator_id)

            if ticket_creator and ticket_creator.id != self.closer.id: # Don't ask the closer for confirmation if they are the creator
                 confirmation_view = CreatorConfirmationView(self.bot, interaction, self.close_reason, self.closer)
                 await interaction.channel.send(
                     f"{ticket_creator.mention}, {self.closer.mention} wants to close this ticket. Reason: **{self.close_reason}**",
                     view=confirmation_view
                 )
            else:
                 # If creator not found or closer is creator, proceed directly to deletion
                 await interaction.channel.send("Ticket creator not found or closer is the creator. Proceeding with deletion...")
                 await asyncio.sleep(2) # Small delay
                 await self.delete_ticket(interaction, self.close_reason, self.closer) # Call delete from here

        else:
            await interaction.channel.send("Could not find the ticket creator in the database. Proceeding with deletion.")
            await asyncio.sleep(2) # Small delay
            await self.delete_ticket(interaction, self.close_reason, self.closer) # Call delete from here


    async def delete_ticket(self, interaction: discord.Interaction, close_reason: str, closer: discord.User):
        guild = self.bot.get_guild(GUILD_ID)
        log_channel = self.bot.get_channel(LOG_CHANNEL)
        ticket_id = interaction.channel.id

        cur.execute("SELECT id, discord_id, ticket_created FROM ticket WHERE ticket_channel=?", (ticket_id,))
        ticket_data = cur.fetchone()

        if not ticket_data:
            await interaction.channel.send("Error: Could not find ticket data in the database during deletion.")
            return

        id, ticket_creator_id, ticket_created = ticket_data
        ticket_creator = guild.get_member(ticket_creator_id)

        ticket_created_unix = self.convert_to_unix_timestamp(ticket_created)
        timezone = pytz.timezone(TIMEZONE)
        ticket_closed = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        ticket_closed_unix = self.convert_to_unix_timestamp(ticket_closed)

        # Creating the Transcript
        military_time: bool = True
        transcript = await chat_exporter.export(interaction.channel, limit=200, tz_info=TIMEZONE, military_time=military_time, bot=self.bot)

        if transcript is None:
            await interaction.channel.send("Warning: Could not generate transcript for this ticket.")
            transcript_file_user = None
            transcript_file_log = None
        else:
            transcript_file_user = File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{interaction.channel.name}.html")
            transcript_file_log = File(
                io.BytesIO(transcript.encode()),
                filename=f"transcript-{interaction.channel.name}.html")

        transcript_info = Embed(title=f"Ticket Deleted | {interaction.channel.name}", color=Color.purple())
        transcript_info.add_field(name="ID", value=id, inline=True)
        transcript_info.add_field(name="Opened by", value=ticket_creator.mention if ticket_creator else "Unknown User", inline=True)
        transcript_info.add_field(name="Closed by", value=closer.mention, inline=True)
        transcript_info.add_field(name="Close Reason", value=close_reason, inline=False)
        transcript_info.add_field(name="Ticket Created", value=f"<t:{ticket_created_unix}:f>", inline=True)
        transcript_info.add_field(name="Ticket Closed", value=f"<t:{ticket_closed_unix}:f>", inline=True)


        if ticket_creator:
            try:
                await ticket_creator.send(embed=transcript_info, file=transcript_file_user)
            except discord.errors.Forbidden:
                transcript_info.add_field(name="Error", value="Ticket Creator DM`s are disabled", inline=True)
        else:
             transcript_info.add_field(name="Note", value="Ticket creator no longer in the server.", inline=True)


        if log_channel:
            if transcript_file_log:
                await log_channel.send(embed=transcript_info, file=transcript_file_log)
            else:
                 await log_channel.send(embed=transcript_info) # Send embed without file if transcript failed
        else:
            print("Log channel not found. Transcript not sent to log channel.")

        # Add a small delay before deleting the channel
        await asyncio.sleep(3)
        await interaction.channel.delete(reason=f"Ticket Closed by {closer.name} - Reason: {close_reason}")
        cur.execute("DELETE FROM ticket WHERE ticket_channel=?", (ticket_id,))
        conn.commit()

    def convert_to_unix_timestamp(self, date_string):
        date_format = "%Y-%m-%d %H:%M:%S"
        dt_obj = datetime.strptime(date_string, date_format)
        try:
            local_tz = pytz.timezone(TIMEZONE)
            dt_obj = local_tz.localize(dt_obj)
            dt_obj_utc = dt_obj.astimezone(pytz.utc)
            return int(dt_obj_utc.timestamp())
        except pytz.UnknownTimeZoneError:
            print(f"Warning: Unknown timezone '{TIMEZONE}'. Using UTC.")
            return int(dt_obj.timestamp())


class TicketClaimButton(ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label="Claim Ticket", style=discord.ButtonStyle.green, custom_id="claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: ui.Button):
        team_role = interaction.guild.get_role(TEAM_ROLE)
        if team_role and team_role in interaction.user.roles:
            ticket_channel = interaction.channel
            # Remove view permissions for default role
            await ticket_channel.set_permissions(interaction.guild.default_role, view_channel=False)
            # Ensure the user claiming has permissions (already set during creation, but good to re-confirm)
            await ticket_channel.set_permissions(interaction.user, send_messages=True, read_messages=True)

            # Add view permissions for other staff members
            if team_role:
                 await ticket_channel.set_permissions(team_role, view_channel=True, read_messages=True, send_messages=True)

            await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}!", ephemeral=False)
            # Remove the claim button after claiming
            self.remove_item(button)
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message("You do not have permission to claim tickets.", ephemeral=True)


# First Button for the Ticket
class CloseButton(ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @ui.button(label="Close Ticket 🎫", style=discord.ButtonStyle.blurple, custom_id="close")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        # Optional: Check if the user closing has permissions (e.g., is staff or the ticket creator)
        is_staff = interaction.guild.get_role(TEAM_ROLE) in interaction.user.roles if TEAM_ROLE else False
        cur.execute("SELECT discord_id FROM ticket WHERE ticket_channel=?", (interaction.channel.id,))
        ticket_creator_id_data = cur.fetchone()
        is_creator = ticket_creator_id_data and ticket_creator_id_data[0] == interaction.user.id

        if not is_staff and not is_creator:
             await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)
             return

        # Create and show the modal for the close reason
        modal = CloseReasonModal()
        # Attach this view to the modal so we can access its data later
        modal.view = self
        await interaction.response.send_modal(modal)


    async def request_creator_confirmation(self, interaction: discord.Interaction):
        # This method will be called by the modal on submission
        # Get the ticket creator
        cur.execute("SELECT discord_id FROM ticket WHERE ticket_channel=?", (interaction.channel.id,))
        ticket_creator_id_data = cur.fetchone()
        if ticket_creator_id_data:
            ticket_creator_id = ticket_creator_id_data[0]
            ticket_creator = self.bot.get_user(ticket_creator_id)

            if ticket_creator and ticket_creator.id != self.closer.id: # Don't ask the closer for confirmation if they are the creator
                 confirmation_view = CreatorConfirmationView(self.bot, interaction, self.close_reason, self.closer)
                 await interaction.channel.send(
                     f"{ticket_creator.mention}, {self.closer.mention} wants to close this ticket. Reason: **{self.close_reason}**",
                     view=confirmation_view
                 )
            else:
                 # If creator not found or closer is creator, proceed directly to deletion
                 await interaction.channel.send("Ticket creator not found or closer is the creator. Proceeding with deletion...")
                 await asyncio.sleep(2) # Small delay
                 # Pass the necessary information for deletion
                 await TicketOptions(self.bot).delete_ticket(interaction, self.close_reason, self.closer)

        else:
            await interaction.channel.send("Could not find the ticket creator in the database. Proceeding with deletion.")
            await asyncio.sleep(2) # Small delay
            # Pass the necessary information for deletion
            await TicketOptions(self.bot).delete_ticket(interaction, self.close_reason, self.closer)


class MyView(ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @ui.select(
        custom_id="support",
        placeholder="Choose a Ticket option",
        options=[
            discord.SelectOption(
                label="General Question",
                description="A general question regarding the Discord server or our website",
                emoji="❓",
                value="support1"
            ),
            discord.SelectOption(
                label="Resource issue",
                description="If an asset on our website has wrong or no credit, or if it caused copyright issues",
                emoji="⚠️",
                value="support2"
            ),
            discord.SelectOption(
                label="Partner- or sponshorship",
                description="Partner with us or sponsor",
                emoji="💸",
                value="support3"
            ),
            discord.SelectOption(
                label="Staff application",
                description="ONLY IF STAFF APPS ARE OPEN",
                emoji="🔒",
                value="support4"
            ),
            discord.SelectOption(
                label="Other",
                description="Other things (e.g. bugs)",
                emoji="💫",
                value="support5"
            )
        ]
    )
    async def callback(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.defer() # Defer the interaction
        timezone = pytz.timezone(TIMEZONE)
        creation_date = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        user_name = interaction.user.name
        user_id = interaction.user.id

        cur.execute("SELECT discord_id FROM ticket WHERE discord_id=?", (user_id,)) #Check if the User already has a Ticket open
        existing_ticket = cur.fetchone()

        if existing_ticket is None:
            if interaction.channel.id == TICKET_CHANNEL:
                guild = self.bot.get_guild(GUILD_ID)

                # Fetch the highest current ticket number to ensure uniqueness
                cur.execute("SELECT MAX(id) FROM ticket")
                last_id = cur.fetchone()[0] or 0
                ticket_number = last_id + 1

                cur.execute("INSERT INTO ticket (discord_name, discord_id, ticket_created) VALUES (?, ?, ?)", (user_name, user_id, creation_date))
                conn.commit()

                category = self.bot.get_channel(CATEGORY_ID)
                team_role = guild.get_role(TEAM_ROLE) if TEAM_ROLE else None # Get the team role

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                    interaction.user: discord.PermissionOverwrite(send_messages=True, read_messages=True, add_reactions=False, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True) # Ensure the bot has permissions
                }

                if team_role: # Add overwrites for the team role if it exists
                     overwrites[team_role] = discord.PermissionOverwrite(send_messages=True, read_messages=True, add_reactions=False, embed_links=True, attach_files=True, read_message_history=True, external_emojis=True)


                ticket_channel = await category.create_text_channel(
                    f"ticket-{ticket_number}",
                    category=category,
                    topic=f"Ticket creator ID: {interaction.user.id}", # Use topic for creator ID
                    overwrites=overwrites
                )

                selected_value = interaction.data["values"][0]
                selected_label = next(
                    (option.label for option in select.options if option.value == selected_value),
                    "Unknown"
                )

                embed = Embed(
                    description=f'{interaction.user.mention} has created a new **{selected_label}** ticket,\n'
                                'describe your Problem and please be patient for our Support Team to help you soon.',
                    color=Color.purple()
                )

                initial_message_content = f"{interaction.user.mention}"
                if team_role:
                    initial_message_content += f" {team_role.mention}"

                # Send the initial message with the Close button
                await ticket_channel.send(
                    content=initial_message_content,
                    embed=embed,
                    view=CloseButton(bot=self.bot)
                )
                # Send the claim button as a separate message
                await ticket_channel.send(view=TicketClaimButton(bot=self.bot))


                channel_id = ticket_channel.id
                cur.execute("UPDATE ticket SET ticket_channel = ? WHERE id = ?", (channel_id, ticket_number))
                conn.commit()

                embed = Embed(description=f'📬 Ticket was Created! Look here --> {ticket_channel.mention}',
                                            color=Color.green())
                # Use followup.send after deferring
                await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            embed = Embed(title=f"You already have a open Ticket", color=Color.red())
            # Use followup.send after deferring
            await interaction.followup.send(embed=embed, ephemeral=True)


class Ticket_System(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Bot Loaded  | ticket_system.py ✅')
        # Add persistent views when the bot is ready
        self.bot.add_view(MyView(bot=self.bot))
        self.bot.add_view(CloseButton(bot=self.bot))
        self.bot.add_view(TicketOptions(bot=self.bot))
        self.bot.add_view(TicketClaimButton(bot=self.bot))
        self.bot.add_view(CreatorConfirmationView(bot=self.bot, original_interaction=None, close_reason="", closer=None)) # Add confirmation view for persistence


    #Closes the Connection to the Database when shutting down the Bot
    @commands.Cog.listener()
    async def on_bot_shutdown(self):
        cur.close()
        conn.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket_System(bot))
