from datetime import datetime
import discord
from discord import Embed, Color, app_commands
from discord.ext import commands
import json
import os

WELCOME_GOODBYE_CHANNEL_ID: 1367574829208699020

class WelcomeGoodbyeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config() # Load configuration on cog initialization

    def load_config(self):
        global WELCOME_GOODBYE_CHANNEL_ID
        # Load the channel ID from a persistent config file if it exists
        if os.path.exists("welcomer_config.json"):
            with open("welcomer_config.json", "r") as f:
                try:
                    config_data = json.load(f)
                    WELCOME_GOODBYE_CHANNEL_ID = config_data.get("channel_id")
                except json.JSONDecodeError:
                     print("Error loading welcomer_config.json. Using default/None value for WELCOME_GOODBYE_CHANNEL_ID.")
                     WELCOME_GOODBYE_CHANNEL_ID = None
        else:
             # Create a default config file if it doesn't exist
             self.save_config()

    def save_config(self):
         config_data = {
             "channel_id": WELCOME_GOODBYE_CHANNEL_ID
         }
         with open("welcomer_config.json", "w") as f:
             json.dump(config_data, f, indent=4)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if WELCOME_GOODBYE_CHANNEL_ID:
            channel = member.guild.get_channel(WELCOME_GOODBYE_CHANNEL_ID)
            if channel:
                embed = Embed(
                    title=f"Welcome to {member.guild.name}!", # Dynamic title
                    description=f"🎉 Say hello to our newest member, {member.mention}! We're happy to have you here.",
                    color=Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                # Optional: Add a field with server member count
                embed.add_field(
                    name="Total Members",
                    value=f"{member.guild.member_count}",
                    inline=True
                )
                embed.set_footer(text=f"User ID: {member.id}")
                embed.timestamp = datetime.now() # Add a timestamp

                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if WELCOME_GOODBYE_CHANNEL_ID:
            channel = member.guild.get_channel(WELCOME_GOODBYE_CHANNEL_ID)
            if channel:
                embed = Embed(
                    title=f"Goodbye!", # Simple goodbye title
                    description=f"😔 {member.mention} has left the server.",
                    color=Color.red()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                 # Optional: Add a field with remaining server member count
                embed.add_field(
                    name="Remaining Members",
                    value=f"{member.guild.member_count}",
                    inline=True
                )
                embed.set_footer(text=f"User ID: {member.id}")
                embed.timestamp = datetime.now() # Add a timestamp

                await channel.send(embed=embed)

    @app_commands.command(name="setwelcomerchannel", description="Set the channel for welcome and goodbye messages")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel for welcome and goodbye messages"
    )
    async def setwelcomerchannel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel
    ):
        global WELCOME_GOODBYE_CHANNEL_ID
        WELCOME_GOODBYE_CHANNEL_ID = channel.id
        self.save_config()

        embed = Embed(
            title="🎉 Welcomer Channel Set",
            description=f"Welcome and goodbye messages will now be sent to {channel.mention}.",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeGoodbyeCog(bot))
