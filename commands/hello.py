import discord
from discord import app_commands

@app_commands.command(name="hello", description="Greet the user with a hello message")
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f'Hello, {interaction.user.mention}! 👋') 