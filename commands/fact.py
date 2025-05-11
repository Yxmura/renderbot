import discord
from discord import app_commands
import requests

FACT_API_URL = "https://uselessfacts.jsph.pl/api/v2/facts/random"

@app_commands.command(name="fact", description="Get a random interesting fact")
async def random_fact(interaction: discord.Interaction):
    await interaction.response.defer()
    
    try:
        response = requests.get(FACT_API_URL)
        if response.status_code == 200:
            fact_data = response.json()
            fact = fact_data['text']
            source = fact_data['source']
            
            embed = discord.Embed(
                title="Random Fact",
                description=fact,
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Source: {source}")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("Failed to fetch a fact. Try again later!")
    except Exception as e:
        await interaction.followup.send(f"Error fetching fact: {e}") 