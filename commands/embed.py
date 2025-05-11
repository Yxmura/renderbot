import discord
from discord import app_commands

REQUIRED_ROLE_ID = 1317607057687576696

@app_commands.command(
    name="embed",
    description="Create a custom embed message (Requires a specific role)"
)
@app_commands.describe(
    channel="The channel to send the embed in",
    title="The title of the embed",
    description="The main text of the embed",
    color="The color of the embed (hex code)",
    footer="The footer text of the embed"
)
async def create_embed(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    description: str,
    color: str = "0000FF",
    footer: str = None
):
    if not any(role.id == REQUIRED_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message(
            "You do not have the required role to use this command.",
            ephemeral=True
        )
        return

    try:
        color_int = int(color.replace("#", ""), 16)
        embed = discord.Embed(
            title=title,
            description=description,
            color=color_int
        )
        if footer:
            embed.set_footer(text=footer)
        await channel.send(embed=embed)
        await interaction.response.send_message(
            f"Embed sent to {channel.mention}!",
            ephemeral=True
        )
    except ValueError:
        await interaction.response.send_message(
            "Invalid color code! Please use a valid hex color code (e.g., 'FF0000' for red).",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"An error occurred: {e}",
            ephemeral=True
        )

@create_embed.error
async def create_embed_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You need the 'Manage Server' permission to use this command!", ephemeral=True)
    else:
        await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True) 