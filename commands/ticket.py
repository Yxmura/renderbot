import discord
from discord import app_commands
from discord.ext import commands
import datetime
import json
import os
from typing import Optional

# vars that are like constants lol
TICKET_CATEGORIES = ["General Support", "Resource Issue", "Partner- or sponsorship", "Staff Applications (if open)", "Other"]
STAFF_ROLE_ID = 1317607057687576696
TICKETS_CHANNEL_ID = 1317685619467485225
TICKET_CATEGORY_ID = 1361033906597531811
TICKET_LOGS_CHANNEL_ID = 1361035162611220521

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CloseTicketModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.get_role(STAFF_ROLE_ID):
            await interaction.response.send_message("You don't have permission to claim tickets!", ephemeral=True)
            return

        ticket_data = self.get_ticket_data(interaction.channel.id)
        if ticket_data["claimed_by"]:
            await interaction.response.send_message("This ticket is already claimed!", ephemeral=True)
            return

        ticket_data["claimed_by"] = interaction.user.id
        self.save_ticket_data(interaction.channel.id, ticket_data)

        await interaction.channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        for role in interaction.guild.roles:
            if role.id == STAFF_ROLE_ID:
                await interaction.channel.set_permissions(role, read_messages=False, send_messages=False)

        await interaction.response.send_message(f"Ticket claimed by {interaction.user.mention}")

    def get_ticket_data(self, channel_id: int) -> dict:
        try:
            with open(f"tickets/{channel_id}.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"claimed_by": None, "created_by": None, "category": None, "created_at": None}

    def save_ticket_data(self, channel_id: int, data: dict):
        os.makedirs("tickets", exist_ok=True)
        with open(f"tickets/{channel_id}.json", "w") as f:
            json.dump(data, f)

class CloseTicketModal(discord.ui.Modal, title="Close Ticket"):
    reason = discord.ui.TextInput(
        label="Reason for closing",
        placeholder="Enter the reason for closing this ticket...",
        required=True,
        style=discord.TextStyle.paragraph
    )

    async def on_submit(self, interaction: discord.Interaction):
        ticket_data = self.get_ticket_data(interaction.channel.id)
        creator = interaction.guild.get_member(ticket_data["created_by"])
        
        embed = discord.Embed(
            title="Ticket Close Confirmation",
            description=f"Reason: {self.reason.value}",
            color=discord.Color.purple()
        )
        
        view = CloseConfirmationView(self.reason.value)
        await interaction.response.send_message(
            f"{creator.mention} Please confirm if you're ready to close this ticket.",
            embed=embed,
            view=view
        )

    def get_ticket_data(self, channel_id: int) -> dict:
        try:
            with open(f"tickets/{channel_id}.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"claimed_by": None, "created_by": None, "category": None, "created_at": None}

class CloseConfirmationView(discord.ui.View):
    def __init__(self, reason: str):
        super().__init__(timeout=None)
        self.reason = reason

    @discord.ui.button(label="Confirm Close", style=discord.ButtonStyle.danger)
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticket_data = self.get_ticket_data(interaction.channel.id)
        
        messages = []
        staff_messages = 0
        async for message in interaction.channel.history(limit=None):
            if message.author.get_role(STAFF_ROLE_ID):
                staff_messages += 1
            messages.append(f"{message.author}: {message.content}")

        transcript = "\n".join(reversed(messages))

        embed = discord.Embed(
            title="Ticket Closed",
            color=discord.Color.purple()
        )
        embed.add_field(name="Category", value=ticket_data["category"], inline=True)
        embed.add_field(name="Created At", value=ticket_data["created_at"], inline=True)
        embed.add_field(name="Created By", value=f"<@{ticket_data['created_by']}>", inline=True)
        embed.add_field(name="Claimed By", value=f"<@{ticket_data['claimed_by']}>", inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Close Reason", value=self.reason, inline=True)
        embed.add_field(name="Staff Messages", value=str(staff_messages), inline=True)
        embed.add_field(name="Transcript", value=f"```{transcript[:1000]}...```", inline=False)

        logs_channel = interaction.guild.get_channel(TICKET_LOGS_CHANNEL_ID)
        await logs_channel.send(embed=embed)

        await interaction.channel.delete()

    def get_ticket_data(self, channel_id: int) -> dict:
        try:
            with open(f"tickets/{channel_id}.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"claimed_by": None, "created_by": None, "category": None, "created_at": None}

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=category, value=category)
            for category in TICKET_CATEGORIES
        ]
        super().__init__(
            placeholder="Select ticket category...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        guild = interaction.guild
        user = interaction.user

        # create ticket channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        staff_role = guild.get_role(STAFF_ROLE_ID)
        if staff_role:
            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(
            f"ticket-{user.name}-{category.lower().replace(' ', '-')}",
            category=guild.get_channel(TICKET_CATEGORY_ID),
            overwrites=overwrites
        )

        ticket_data = {
            "created_by": user.id,
            "category": category,
            "created_at": datetime.datetime.now().isoformat(),
            "claimed_by": None
        }
        os.makedirs("tickets", exist_ok=True)
        with open(f"tickets/{channel.id}.json", "w") as f:
            json.dump(ticket_data, f)

        creation_embed = discord.Embed(
            title="Ticket Created",
            description=f"Category: {category}\nCreated by: {user.mention}",
            color=discord.Color.purple()
        )
        creation_embed.add_field(name="Created At", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        creation_embed.add_field(name="Ticket Channel", value=channel.mention, inline=True)
        
        logs_channel = guild.get_channel(TICKET_LOGS_CHANNEL_ID)
        await logs_channel.send(embed=creation_embed)

        # Send ticket message
        view = TicketView()
        message = await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=creation_embed,
            view=view
        )
        await message.pin()

        await interaction.response.send_message(f"Ticket created in {channel.mention}!", ephemeral=True)

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@app_commands.command(name="ticket", description="Create a new ticket")
async def ticket(interaction: discord.Interaction):
    if interaction.channel_id != TICKETS_CHANNEL_ID:
        await interaction.response.send_message("Please use this command in the tickets channel!", ephemeral=True)
        return

    view = TicketPanel()
    await interaction.response.send_message("Select a category to create a ticket:", view=view)

@app_commands.command(name="setup_tickets", description="Setup the ticket system")
@app_commands.default_permissions(administrator=True)
async def setup_tickets(
    interaction: discord.Interaction,
    staff_role: discord.Role,
    tickets_channel: discord.TextChannel,
    ticket_category: discord.CategoryChannel,
    logs_channel: discord.TextChannel
):
    global STAFF_ROLE_ID, TICKETS_CHANNEL_ID, TICKET_CATEGORY_ID, TICKET_LOGS_CHANNEL_ID
    STAFF_ROLE_ID = staff_role.id
    TICKETS_CHANNEL_ID = tickets_channel.id
    TICKET_CATEGORY_ID = ticket_category.id
    TICKET_LOGS_CHANNEL_ID = logs_channel.id

    embed = discord.Embed(
        title="Ticket System Setup",
        description="The ticket system has been configured with the following settings:",
        color=discord.Color.purple()
    )
    embed.add_field(name="Staff Role", value=staff_role.mention, inline=True)
    embed.add_field(name="Tickets Channel", value=tickets_channel.mention, inline=True)
    embed.add_field(name="Ticket Category", value=ticket_category.name, inline=True)
    embed.add_field(name="Logs Channel", value=logs_channel.mention, inline=True)

    view = TicketPanel()
    await tickets_channel.send("Select a category to create a ticket:", view=view)
    await interaction.response.send_message(embed=embed, ephemeral=True) 