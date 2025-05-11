import discord
from discord import app_commands
import random

FLAGS = {
    "🇺🇸": "United States",
    "🇬🇧": "United Kingdom",
    "🇫🇷": "France",
    "🇩🇪": "Germany",
    "🇮🇹": "Italy",
    "🇪🇸": "Spain",
    "🇯🇵": "Japan",
    "🇨🇦": "Canada",
    "🇦🇺": "Australia",
    "🇧🇷": "Brazil"
}

@app_commands.command(name="flagguess", description="Play a flag guessing game")
async def flagguess(interaction: discord.Interaction):
    flag = random.choice(list(FLAGS.keys()))
    country = FLAGS[flag]
    
    embed = discord.Embed(
        title="🎯 Flag Guessing Game",
        description=f"What country does this flag belong to?\n{flag}",
        color=discord.Color.blue()
    )
    
    await interaction.response.send_message(embed=embed) 