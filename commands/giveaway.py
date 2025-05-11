import discord
from discord import app_commands
import json
import os
import asyncio
from datetime import datetime, timedelta
import random
from typing import Optional, List

GIVEAWAY_FILE = "giveaways.json"
REQUIRED_ROLE_ID = 1317607057687576696

class Giveaway:
    def __init__(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
        prize: str,
        description: str,
        winners: int,
        end_time: datetime,
        host_id: int,
        required_role_id: Optional[int] = None,
        min_account_age: Optional[int] = None,
        min_messages: Optional[int] = None,
        allowed_roles: Optional[List[int]] = None,
        excluded_roles: Optional[List[int]] = None,
        color: int = 0x2F3136
    ):
        self.message_id = message_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.prize = prize
        self.description = description
        self.winners = winners
        self.end_time = end_time
        self.host_id = host_id
        self.required_role_id = required_role_id
        self.min_account_age = min_account_age
        self.min_messages = min_messages
        self.allowed_roles = allowed_roles or []
        self.excluded_roles = excluded_roles or []
        self.color = color
        self.entries = []

class GiveawayManager:
    def __init__(self):
        self.giveaways = {}
        self.load_giveaways()

    def load_giveaways(self):
        if os.path.exists(GIVEAWAY_FILE):
            with open(GIVEAWAY_FILE, 'r') as f:
                data = json.load(f)
                for giveaway_id, giveaway_data in data.items():
                    giveaway_data['end_time'] = datetime.fromisoformat(giveaway_data['end_time'])
                    self.giveaways[giveaway_id] = Giveaway(**giveaway_data)

    def save_giveaways(self):
        data = {
            giveaway_id: {
                'message_id': giveaway.message_id,
                'channel_id': giveaway.channel_id,
                'guild_id': giveaway.guild_id,
                'prize': giveaway.prize,
                'description': giveaway.description,
                'winners': giveaway.winners,
                'end_time': giveaway.end_time.isoformat(),
                'host_id': giveaway.host_id,
                'required_role_id': giveaway.required_role_id,
                'min_account_age': giveaway.min_account_age,
                'min_messages': giveaway.min_messages,
                'allowed_roles': giveaway.allowed_roles,
                'excluded_roles': giveaway.excluded_roles,
                'color': giveaway.color,
                'entries': giveaway.entries
            }
            for giveaway_id, giveaway in self.giveaways.items()
        }
        with open(GIVEAWAY_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_giveaway(self, giveaway_id: str, giveaway: Giveaway):
        self.giveaways[giveaway_id] = giveaway
        self.save_giveaways()

    def get_giveaway(self, giveaway_id: str) -> Optional[Giveaway]:
        return self.giveaways.get(giveaway_id)

    def remove_giveaway(self, giveaway_id: str):
        if giveaway_id in self.giveaways:
            del self.giveaways[giveaway_id]
            self.save_giveaways()

giveaway_manager = GiveawayManager()

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway: Giveaway):
        super().__init__(timeout=None)
        self.giveaway = giveaway

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.primary, custom_id="enter_giveaway")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.giveaway.entries:
            await interaction.response.send_message(
                "You have already entered this giveaway!",
                ephemeral=True
            )
            return

        # Check requirements
        if self.giveaway.required_role_id:
            if not any(role.id == self.giveaway.required_role_id for role in interaction.user.roles):
                await interaction.response.send_message(
                    f"You need the required role to enter this giveaway!",
                    ephemeral=True
                )
                return

        if self.giveaway.min_account_age:
            account_age = (datetime.now() - interaction.user.created_at).days
            if account_age < self.giveaway.min_account_age:
                await interaction.response.send_message(
                    f"Your account must be at least {self.giveaway.min_account_age} days old to enter!",
                    ephemeral=True
                )
                return

        if self.giveaway.allowed_roles:
            if not any(role.id in self.giveaway.allowed_roles for role in interaction.user.roles):
                await interaction.response.send_message(
                    "You don't have any of the allowed roles to enter this giveaway!",
                    ephemeral=True
                )
                return

        if self.giveaway.excluded_roles:
            if any(role.id in self.giveaway.excluded_roles for role in interaction.user.roles):
                await interaction.response.send_message(
                    "You have a role that is excluded from this giveaway!",
                    ephemeral=True
                )
                return

        self.giveaway.entries.append(interaction.user.id)
        giveaway_manager.save_giveaways()

        await interaction.response.send_message(
            "You have entered the giveaway! Good luck! 🎉",
            ephemeral=True
        )

async def check_giveaways(bot):
    while True:
        now = datetime.now()
        for giveaway_id, giveaway in list(giveaway_manager.giveaways.items()):
            if now >= giveaway.end_time:
                channel = bot.get_channel(giveaway.channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(giveaway.message_id)
                        if giveaway.entries:
                            winners = random.sample(giveaway.entries, min(giveaway.winners, len(giveaway.entries)))
                            winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
                            
                            embed = discord.Embed(
                                title="🎉 Giveaway Ended!",
                                description=f"Prize: **{giveaway.prize}**\n\n"
                                          f"Winners: {', '.join(winner_mentions)}",
                                color=giveaway.color
                            )
                            await message.edit(embed=embed, view=None)
                            await channel.send(
                                f"Congratulations {', '.join(winner_mentions)}! "
                                f"You won the **{giveaway.prize}** giveaway!",
                                allowed_mentions=discord.AllowedMentions(users=True)
                            )
                        else:
                            embed = discord.Embed(
                                title="🎉 Giveaway Ended!",
                                description=f"Prize: **{giveaway.prize}**\n\n"
                                          f"No valid entries were received.",
                                color=giveaway.color
                            )
                            await message.edit(embed=embed, view=None)
                    except:
                        pass
                giveaway_manager.remove_giveaway(giveaway_id)
        await asyncio.sleep(60)

@app_commands.command(name="creategiveaway", description="Create a new giveaway")
@app_commands.describe(
    channel="The channel to host the giveaway in",
    prize="The prize for the giveaway",
    description="Description of the giveaway",
    winners="Number of winners",
    duration="Duration in hours",
    required_role="Role required to enter (optional)",
    min_account_age="Minimum account age in days (optional)",
    min_messages="Minimum messages required (optional)",
    allowed_roles="Roles allowed to enter (optional, comma-separated)",
    excluded_roles="Roles excluded from entering (optional, comma-separated)",
    color="Color of the embed (hex code, optional)"
)
async def creategiveaway(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    prize: str,
    description: str,
    winners: app_commands.Range[int, 1, 10],
    duration: app_commands.Range[int, 1, 168],
    required_role: Optional[discord.Role] = None,
    min_account_age: Optional[app_commands.Range[int, 1, 3650]] = None,
    min_messages: Optional[app_commands.Range[int, 1, 10000]] = None,
    allowed_roles: Optional[str] = None,
    excluded_roles: Optional[str] = None,
    color: Optional[str] = None
):
    if not any(role.id == REQUIRED_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message(
            "You don't have permission to create giveaways!",
            ephemeral=True
        )
        return

    try:
        if color:
            color = int(color.strip('#'), 16)
        else:
            color = 0x2F3136
    except ValueError:
        await interaction.response.send_message(
            "Invalid color code! Please provide a valid hex color code.",
            ephemeral=True
        )
        return

    allowed_role_ids = []
    if allowed_roles:
        for role_id in allowed_roles.split(','):
            try:
                role = interaction.guild.get_role(int(role_id.strip()))
                if role:
                    allowed_role_ids.append(role.id)
            except:
                continue

    excluded_role_ids = []
    if excluded_roles:
        for role_id in excluded_roles.split(','):
            try:
                role = interaction.guild.get_role(int(role_id.strip()))
                if role:
                    excluded_role_ids.append(role.id)
            except:
                continue

    end_time = datetime.now() + timedelta(hours=duration)
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY",
        description=f"**Prize:** {prize}\n\n"
                   f"{description}\n\n"
                   f"**Winners:** {winners}\n"
                   f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                   f"Click the button below to enter!",
        color=color
    )

    if required_role:
        embed.add_field(name="Required Role", value=required_role.mention, inline=True)
    if min_account_age:
        embed.add_field(name="Minimum Account Age", value=f"{min_account_age} days", inline=True)
    if min_messages:
        embed.add_field(name="Minimum Messages", value=str(min_messages), inline=True)
    if allowed_role_ids:
        embed.add_field(name="Allowed Roles", value=", ".join([f"<@&{role_id}>" for role_id in allowed_role_ids]), inline=False)
    if excluded_role_ids:
        embed.add_field(name="Excluded Roles", value=", ".join([f"<@&{role_id}>" for role_id in excluded_role_ids]), inline=False)

    embed.set_footer(text=f"Hosted by {interaction.user.name}")
    
    giveaway = Giveaway(
        message_id=0,  # Will be set after sending
        channel_id=channel.id,
        guild_id=interaction.guild_id,
        prize=prize,
        description=description,
        winners=winners,
        end_time=end_time,
        host_id=interaction.user.id,
        required_role_id=required_role.id if required_role else None,
        min_account_age=min_account_age,
        min_messages=min_messages,
        allowed_roles=allowed_role_ids,
        excluded_roles=excluded_role_ids,
        color=color
    )

    view = GiveawayView(giveaway)
    message = await channel.send(embed=embed, view=view)
    
    giveaway.message_id = message.id
    giveaway_manager.add_giveaway(str(message.id), giveaway)

    await interaction.response.send_message(
        f"Giveaway created in {channel.mention}!",
        ephemeral=True
    )

@app_commands.command(name="setupgiveaway", description="Setup the giveaway system")
@app_commands.default_permissions(administrator=True)
async def setupgiveaway(
    interaction: discord.Interaction,
    required_role: discord.Role
):
    global REQUIRED_ROLE_ID
    REQUIRED_ROLE_ID = required_role.id

    embed = discord.Embed(
        title="🎉 Giveaway System Setup",
        description="The giveaway system has been configured with the following settings:",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Required Role",
        value=required_role.mention,
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True) 