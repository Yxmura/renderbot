import discord
from discord import app_commands

@app_commands.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    latency = round(interaction.client.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: **{latency}ms**",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed) 