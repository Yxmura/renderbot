import discord
from discord import app_commands, Embed, Color
from discord.ext import commands
import json
import os
from typing import Optional

REQUIRED_ROLE_ID: 1317607057687576696

class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config() # Load configuration on cog initialization

    def load_config(self):
        global REQUIRED_ROLE_ID
        # Load the required role ID from a persistent config file if it exists
        if os.path.exists("utilities_config.json"):
            with open("utilities_config.json", "r") as f:
                try:
                    config_data = json.load(f)
                    REQUIRED_ROLE_ID = config_data.get("required_role_id")
                except json.JSONDecodeError:
                     print("Error loading utilities_config.json. Using default/None value for REQUIRED_ROLE_ID.")
                     REQUIRED_ROLE_ID = None
        else:
             # Create a default config file if it doesn't exist
             self.save_config()


    def save_config(self):
         config_data = {
             "required_role_id": REQUIRED_ROLE_ID
         }
         with open("utilities_config.json", "w") as f:
             json.dump(config_data, f, indent=4)


    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        # No need to defer for a simple latency check unless you anticipate very high latency
        # or more complex operations in the future.
        # await interaction.response.defer()

        latency = round(self.bot.latency * 1000)

        embed = Embed(
            title="🏓 Pong!",
            description=f"Bot Latency: **{latency}ms**",
            color=Color.purple()
        )
        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="embed",
        description="Create a custom embed message"
    )
    @app_commands.describe(
        channel="The channel to send the embed in",
        title="The title of the embed",
        description="The description for the embed",
        color="Hex color (e.g., FF0000). Defaults to blue.",
        footer="Footer text for the embed"
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        color: Optional[str] = "0000FF", # Use default directly in function signature
        footer: Optional[str] = None
    ):
        if interaction.guild is None:
             await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
             return

        # Check if the user has the required role
        if REQUIRED_ROLE_ID is not None:
            required_role = interaction.guild.get_role(REQUIRED_ROLE_ID)
            if required_role not in interaction.user.roles:
                await interaction.response.send_message(
                    f"You do not have the {required_role.name} role to use this command.",
                    ephemeral=True
                )
                return
        elif REQUIRED_ROLE_ID is None and interaction.user.guild_permissions.administrator:
             # Allow administrators to use if no required role is set
             pass
        elif REQUIRED_ROLE_ID is None:
             await interaction.response.send_message(
                 "The utilities commands need to be configured by an administrator first.",
                 ephemeral=True
             )
             return


        try:
            # Safely handle the color conversion
            color_int = int(color.replace("#", ""), 16)
            # Use discord.Color constructor directly with the integer
            embed_color = Color(color_int)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid color code! Please use a valid hex code (e.g., `FF0000` for red).",
                ephemeral=True
            )
            return

        embed = Embed(
            title=title,
            description=description,
            color=embed_color
        )
        if footer:
            embed.set_footer(text=footer)

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Embed sent to {channel.mention}!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                 f"❌ I don't have permission to send messages in {channel.mention}.",
                 ephemeral=True
             )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while sending the embed: {e}",
                ephemeral=True
            )

    @app_commands.command(name="setutilitiesrole", description="Set the role required to use utility commands like /embed")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        required_role="The role required to use utility commands"
    )
    async def setutilitiesrole(
        self,
        interaction: discord.Interaction,
        required_role: discord.Role
    ):
        global REQUIRED_ROLE_ID
        REQUIRED_ROLE_ID = required_role.id
        self.save_config()

        embed = Embed(
            title="🛠️ Utilities Role Set",
            description=f"The role required to use utility commands is now: {required_role.mention}",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
