import discord
from discord import app_commands
import requests

JOKE_API_URL = "https://icanhazdadjoke.com/"
HEADERS = {"Accept": "application/json"}

@app_commands.command(name="joke", description="Get a terrible dad joke.")
async def dadjoke(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    try:
        response = requests.get(JOKE_API_URL, headers=HEADERS)
        if response.status_code == 200:
            joke = response.json().get("joke")
            await interaction.followup.send(joke)
        else:
            await interaction.followup.send("Sorry, I couldn't fetch a dad joke right now. Try again later.")
    except Exception as e:
        await interaction.followup.send(f"Error fetching joke: {e}") 