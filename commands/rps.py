import discord
from discord import app_commands
import random

CHOICES = ["rock", "paper", "scissors"]

@app_commands.command(name="rps", description="Play Rock Paper Scissors with the bot")
@app_commands.describe(choice="Your choice: rock, paper, or scissors")
@app_commands.choices(choice=[
    app_commands.Choice(name="rock", value="rock"),
    app_commands.Choice(name="paper", value="paper"),
    app_commands.Choice(name="scissors", value="scissors")
])
async def rps(interaction: discord.Interaction, choice: str):
    bot_choice = random.choice(CHOICES)
    
    # Determine winner
    if choice == bot_choice:
        result = "It's a tie! 🤝"
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = "You win! 🎉"
    else:
        result = "I win! 😎"
    
    embed = discord.Embed(
        title="Rock Paper Scissors",
        color=discord.Color.blue()
    )
    embed.add_field(name="Your Choice", value=f"`{choice}`", inline=True)
    embed.add_field(name="My Choice", value=f"`{bot_choice}`", inline=True)
    embed.add_field(name="Result", value=result, inline=False)
    
    await interaction.response.send_message(embed=embed) 