import discord
import asyncio
import pytz
import json
import sqlite3
from datetime import datetime
import chat_exporter
import io
from discord.ext import commands
from discord import app_commands, Embed, Color, File, Interaction, Member

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

# Buttons to reopen or delete the Ticket
class TicketOptions(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(label="Delete Ticket 🎫", style=discord.ButtonStyle.red, custom_id="delete")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = self.bot.get_guild(GUILD_ID)
        channel = self.bot.get_channel(LOG_CHANNEL)
        ticket_id = interaction.channel.id

        cur.execute("SELECT id, discord_id, ticket_created FROM ticket WHERE ticket_channel=?", (ticket_id,))
        ticket_data = cur.fetchone()

        if not ticket_data:
            await interaction.response.send_message("Could not find ticket data in the database.", ephemeral=True)
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
            await interaction.response.send_message("Could not generate transcript for this ticket.", ephemeral=True)
            return

        transcript_file_user = File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html")
        transcript_file_log = File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html")

        embed = Embed(description=f'Ticket is deleting in 5 seconds.', color=Color.red())
        transcript_info = Embed(title=f"Ticket Deleted | {interaction.channel.name}", color=Color.purple())
        transcript_info.add_field(name="ID", value=id, inline=True)
        transcript_info.add_field(name="Opened by", value=ticket_creator.mention if ticket_creator else "Unknown User", inline=True)
        transcript_info.add_field(name="Closed by", value=interaction.user.mention, inline=True)
        transcript_info.add_field(name="Ticket Created", value=f"<t:{ticket_created_unix}:f>", inline=True)
        transcript_info.add_field(name="Ticket Closed", value=f"<t:{ticket_closed_unix}:f>", inline=True)

        await interaction.response.send_message(embed=embed)

        if ticket_creator:
            try:
                await ticket_creator.send(embed=transcript_info, file=transcript_file_user)
            except discord.errors.Forbidden:
                transcript_info.add_field(name="Error", value="Ticket Creator DM`s are disabled", inline=True)
        else:
             transcript_info.add_field(name="Note", value="Ticket creator no longer in the server.", inline=True)


        if channel:
            await channel.send(embed=transcript_info, file=transcript_file_log)
        else:
            print("Log channel not found. Transcript not sent to log channel.")

        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket Deleted")
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

class TicketClaimButton(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.green, custom_id="claim")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
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
class CloseButton(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket 🎫", style=discord.ButtonStyle.blurple, custom_id="close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Optional: Check if the user closing has permissions (e.g., is staff or the ticket creator)
        is_staff = interaction.guild.get_role(TEAM_ROLE) in interaction.user.roles if TEAM_ROLE else False
        cur.execute("SELECT discord_id FROM ticket WHERE ticket_channel=?", (interaction.channel.id,))
        ticket_creator_id_data = cur.fetchone()
        is_creator = ticket_creator_id_data and ticket_creator_id_data[0] == interaction.user.id

        if not is_staff and not is_creator:
             await interaction.response.send_message("You do not have permission to close this ticket.", ephemeral=True)
             return

        embed = Embed(title="Close Ticket 🎫", description="Are you sure you want to close this Ticket?", color=Color.green())
        await interaction.response.send_message(embed=embed, view=TicketOptions(bot=self.bot))
        await interaction.message.edit(view=self) # Keep the close button message with the button

class MyView(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.select(
        custom_id="support",
        placeholder="Choose a Ticket option",
        options=[
            discord.SelectOption(
                label="General Question",  #Name of the 1 Select Menu Option
                description="A general question regarding the Discord server or our website",  #Description of the 1 Select Menu Option
                emoji="❓",        #Emoji of the 1 Option  if you want a Custom Emoji read this  https://github.com/Simoneeeeeeeee/Discord-Select-Menu-Ticket-Bot/tree/main#how-to-use-custom-emojis-from-your-discors-server-in-the-select-menu
                value="support1"   #Don't change this value otherwise the code will not work anymore!!!!
            ),
            discord.SelectOption(
                label="Resource issue",  #Name of the 2 Select Menu Option
                description="If an asset on our website has wrong or no credit, or if it caused copyright issues", #Description of the 2 Select Menu Option
                emoji="⚠️",        #Emoji of the 2 Option  if you want a Custom Emoji read this  https://github.com/Simoneeeeeeeee/Discord-Select-Menu-Ticket-Bot/tree/main#how-to-use-custom-emojis-from-your-discors-server-in-the-select-menu
                value="support2"   #Don't change this value otherwise the code will not work anymore!!!!
            ),
            discord.SelectOption(
                label="Partner- or sponshorship",  #Name of the 2 Select Menu Option
                description="Partner with us or sponsor", #Description of the 2 Select Menu Option
                emoji="💸",        #Emoji of the 2 Option  if you want a Custom Emoji read this  https://github.com/Simoneeeeeeeee/Discord-Select-Menu-Ticket-Bot/tree/main#how-to-use-custom-emojis-from-your-discors-server-in-the-select-menu
                value="support3"   #Don't change this value otherwise the code will not work anymore!!!!
            ),
            discord.SelectOption(
                label="Staff application",  #Name of the 2 Select Menu Option
                description="ONLY IF STAFF APPS ARE OPEN", #Description of the 2 Select Menu Option
                emoji="🔒",        #Emoji of the 2 Option  if you want a Custom Emoji read this  https://github.com/Simoneeeeeeeee/Discord-Select-Menu-Ticket-Bot/tree/main#how-to-use-custom-emojis-from-your-discors-server-in-the-select-menu
                value="support4"   #Don't change this value otherwise the code will not work anymore!!!!
            ),
            discord.SelectOption(
                label="Other",  #Name of the 2 Select Menu Option
                description="Other things (e.g. bugs)", #Description of the 2 Option  if you want a Custom Emoji read this  https://github.com/Simoneeeeeeeee/Discord-Select-Menu-Ticket-Bot/tree/main#how-to-use-custom-emojis-from-your-discors-server-in-the-select-menu
                emoji="💫",        #Emoji of the 2 Option
                value="support5"   #Don't change this value otherwise the code will not work anymore!!!!
            )
        ]
    )
    async def callback(self, interaction: discord.Interaction, select: discord.ui.Select):
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

                await ticket_channel.send(
                    content=initial_message_content,
                    embed=embed,
                    view=CloseButton(bot=self.bot) # Keep the close button here
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

class Ticket_Command(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Bot Loaded  | ticket_commands.py ✅')
        # Add persistent views when the bot is ready
        self.bot.add_view(MyView(bot=self.bot))
        self.bot.add_view(CloseButton(bot=self.bot))
        self.bot.add_view(TicketOptions(bot=self.bot))
        self.bot.add_view(TicketClaimButton(bot=self.bot))


    #Closes the Connection to the Database when shutting down the Bot
    @commands.Cog.listener()
    async def on_bot_shutdown(self):
        cur.close()
        conn.close()

    #Slash Command to show the Ticket Menu in the Ticket Channel only needs to be used once
    @app_commands.command(name="ticket", description="Sends the ticket creation panel.")
    @app_commands.default_permissions(administrator=True)
    async def ticket(self, interaction: discord.Interaction):
        channel = self.bot.get_channel(TICKET_CHANNEL)
        if channel:
            embed = Embed(title=EMBED_TITLE, description=EMBED_DESCRIPTION, color=Color.purple())
            # Send the ticket creation panel with the MyView
            await channel.send(embed=embed, view=MyView(self.bot))
            await interaction.response.send_message("Ticket Menu was sent!", ephemeral=True)
        else:
             await interaction.response.send_message("Ticket channel not found. Please check your config.", ephemeral=True)


    #Slash Command to add Members to the Ticket
    @app_commands.command(name="add", description="Add a Member to the Ticket")
    @app_commands.describe(member="The member you want to add to the ticket")
    async def add(self, interaction: discord.Interaction, member: discord.Member):
        if "ticket-" in interaction.channel.name or "ticket-closed-" in interaction.channel.name:
            await interaction.channel.set_permissions(member, send_messages=True, read_messages=True, add_reactions=False,
                                                embed_links=True, attach_files=True, read_message_history=True,
                                                external_emojis=True)
            embed = Embed(description=f'Added {member.mention} to this Ticket <#{interaction.channel.id}>! \n Use `/remove` to remove a User.', color=Color.green())
            await interaction.response.send_message(embed=embed)
        else:
            embed = Embed(description=f'You can only use this command in a Ticket!', color=Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    #Slash Command to remove Members from the Ticket
    @app_commands.command(name="remove", description="Remove a Member from the Ticket")
    @app_commands.describe(member="The member you want to remove from the ticket")
    async def remove(self, interaction: discord.Interaction, member: discord.Member):
        if "ticket-" in interaction.channel.name or "ticket-closed-" in interaction.channel.name:
            await interaction.channel.set_permissions(member, send_messages=False, read_messages=False, add_reactions=False,
                                                embed_links=False, attach_files=False, read_message_history=False,
                                                external_emojis=False)
            embed = Embed(description=f'Removed {member.mention} from this Ticket <#{interaction.channel.id}>! \n Use `/add` to add a User.', color=Color.green())
            await interaction.response.send_message(embed=embed)
        else:
            embed = Embed(description=f'You can only use this command in a Ticket!', color=Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="delete", description="Delete the Ticket")
    async def delete_ticket(self, interaction: discord.Interaction):
        if "ticket-" not in interaction.channel.name and "ticket-closed-" not in interaction.channel.name:
             embed = Embed(description=f'You can only use this command in a Ticket!', color=Color.red())
             await interaction.response.send_message(embed=embed, ephemeral=True)
             return

        guild = self.bot.get_guild(GUILD_ID)
        log_channel = self.bot.get_channel(LOG_CHANNEL)
        ticket_id = interaction.channel.id

        cur.execute("SELECT id, discord_id, ticket_created FROM ticket WHERE ticket_channel=?", (ticket_id,))
        ticket_data = cur.fetchone()

        if not ticket_data:
            await interaction.response.send_message("Could not find ticket data in the database.", ephemeral=True)
            return

        id, ticket_creator_id, ticket_created = ticket_data
        ticket_creator = guild.get_member(ticket_creator_id)

        ticket_created_unix = self.convert_to_unix_timestamp(ticket_created)
        timezone = pytz.timezone(TIMEZONE)
        ticket_closed = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        ticket_closed_unix = self.convert_to_unix_timestamp(ticket_closed)

        #Creating the Transcript
        military_time: bool = True
        transcript = await chat_exporter.export(interaction.channel, limit=200, tz_info=TIMEZONE, military_time=military_time, bot=self.bot)

        if transcript is None:
            await interaction.response.send_message("Could not generate transcript for this ticket.", ephemeral=True)
            return

        transcript_file_user = File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html")
        transcript_file_log = File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html")

        embed = Embed(description=f'Ticket is deleting in 5 seconds.', color=Color.red())
        transcript_info = Embed(title=f"Ticket Deleted | {interaction.channel.name}", color=Color.purple())
        transcript_info.add_field(name="ID", value=id, inline=True)
        transcript_info.add_field(name="Opened by", value=ticket_creator.mention if ticket_creator else "Unknown User", inline=True)
        transcript_info.add_field(name="Closed by", value=interaction.user.mention, inline=True)
        transcript_info.add_field(name="Ticket Created", value=f"<t:{ticket_created_unix}:f>", inline=True)
        transcript_info.add_field(name="Ticket Closed", value=f"<t:{ticket_closed_unix}:f>", inline=True)

        await interaction.response.send_message(embed=embed)

        if ticket_creator:
            try:
                await ticket_creator.send(embed=transcript_info, file=transcript_file_user)
            except discord.errors.Forbidden:
                transcript_info.add_field(name="Error", value="Ticket Creator DM`s are disabled", inline=True)
        else:
             transcript_info.add_field(name="Note", value="Ticket creator no longer in the server.", inline=True)


        if log_channel:
            await log_channel.send(embed=transcript_info, file=transcript_file_log)
        else:
            print("Log channel not found. Transcript not sent to log channel.")

        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket Deleted")
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


async def setup(bot: commands.Bot):
    await bot.add_cog(Ticket_Command(bot))
