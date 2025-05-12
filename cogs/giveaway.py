import discord
from discord.ext import commands, tasks
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
            return await interaction.response.send_message("You have already entered!", ephemeral=True)

        if self.giveaway.required_role_id and not any(role.id == self.giveaway.required_role_id for role in interaction.user.roles):
            return await interaction.response.send_message("You need the required role!", ephemeral=True)

        if self.giveaway.min_account_age:
            if (datetime.utcnow() - interaction.user.created_at).days < self.giveaway.min_account_age:
                return await interaction.response.send_message("Your account is too new!", ephemeral=True)

        if self.giveaway.allowed_roles:
            if not any(role.id in self.giveaway.allowed_roles for role in interaction.user.roles):
                return await interaction.response.send_message("You're not allowed to enter!", ephemeral=True)

        if self.giveaway.excluded_roles:
            if any(role.id in self.giveaway.excluded_roles for role in interaction.user.roles):
                return await interaction.response.send_message("You're excluded from this giveaway.", ephemeral=True)

        self.giveaway.entries.append(interaction.user.id)
        giveaway_manager.save_giveaways()
        await interaction.response.send_message("You've entered the giveaway! 🎉", ephemeral=True)


async def check_giveaways(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.utcnow()
        for giveaway_id, giveaway in list(giveaway_manager.giveaways.items()):
            if now >= giveaway.end_time:
                channel = bot.get_channel(giveaway.channel_id)
                if channel:
                    try:
                        message = await channel.fetch_message(giveaway.message_id)
                        if giveaway.entries:
                            winners = random.sample(giveaway.entries, min(giveaway.winners, len(giveaway.entries)))
                            mentions = ", ".join(f"<@{uid}>" for uid in winners)
                            embed = discord.Embed(
                                title="🎉 Giveaway Ended!",
                                description=f"Prize: **{giveaway.prize}**\nWinners: {mentions}",
                                color=giveaway.color
                            )
                            await message.edit(embed=embed, view=None)
                            await channel.send(f"Congrats {mentions}! You won **{giveaway.prize}**!")
                        else:
                            await message.edit(embed=discord.Embed(
                                title="🎉 Giveaway Ended!",
                                description="No entries received!",
                                color=giveaway.color
                            ), view=None)
                    except:
                        pass
                giveaway_manager.remove_giveaway(giveaway_id)
        await asyncio.sleep(60)


class GiveawayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bot.loop.create_task(check_giveaways(bot))

    @app_commands.command(name="setupgiveaway", description="Set the required role to manage giveaways")
    async def setupgiveaway(self, interaction: discord.Interaction, required_role: discord.Role):
        global REQUIRED_ROLE_ID
        REQUIRED_ROLE_ID = required_role.id
        await interaction.response.send_message(
            embed=discord.Embed(
                title="Setup Complete",
                description=f"Required role set to {required_role.mention}",
                color=discord.Color.green()
            ), ephemeral=True
        )

    @app_commands.command(name="creategiveaway", description="Create a giveaway")
    async def creategiveaway(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        prize: str,
        description: str,
        winners: int,
        duration: int,
        required_role: Optional[discord.Role] = None,
        min_account_age: Optional[int] = None,
        min_messages: Optional[int] = None,
        allowed_roles: Optional[str] = None,
        excluded_roles: Optional[str] = None,
        color: Optional[str] = None
    ):
        if not any(role.id == REQUIRED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message("You can't use this!", ephemeral=True)

        try:
            hex_color = int(color.strip('#'), 16) if color else 0x2F3136
        except:
            return await interaction.response.send_message("Invalid color!", ephemeral=True)

        end_time = datetime.utcnow() + timedelta(hours=duration)
        allowed_ids = [int(r.strip()) for r in allowed_roles.split(',')] if allowed_roles else []
        excluded_ids = [int(r.strip()) for r in excluded_roles.split(',')] if excluded_roles else []

        embed = discord.Embed(
            title="🎉 GIVEAWAY",
            description=f"**Prize:** {prize}\n{description}\n\n"
                        f"**Winners:** {winners}\n"
                        f"**Ends:** <t:{int(end_time.timestamp())}:R>\n\n"
                        "Click below to enter!",
            color=hex_color
        )
        if required_role:
            embed.add_field(name="Required Role", value=required_role.mention, inline=True)

        view = GiveawayView(Giveaway(
            message_id=0,
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
            allowed_roles=allowed_ids,
            excluded_roles=excluded_ids,
            color=hex_color
        ))

        message = await channel.send(embed=embed, view=view)
        view.giveaway.message_id = message.id
        giveaway_manager.add_giveaway(str(message.id), view.giveaway)

        await interaction.response.send_message(f"Giveaway created in {channel.mention}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
