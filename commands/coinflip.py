import discord
from discord import app_commands
import random

@app_commands.command(name="coinflip", description="Flip a coin - heads or tails")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    
    embed = discord.Embed(
        title="Coin Flip",
        description=f"The coin landed on: **{result}**",
        color=discord.Color.gold()
    )
    
    if result == "Heads":
        embed.set_thumbnail(url="https://i.ibb.co/Pv64WDjs/Chat-GPT-Image-May-10-2025-08-18-59-PM.png")
    else:
        embed.set_thumbnail(url="https://em-content.zobj.net/source/microsoft-teams/337/coin_1fa99.png")
    
    await interaction.response.send_message(embed=embed) 