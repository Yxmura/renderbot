import discord
from discord import app_commands

@app_commands.command(name="help", description="Shows all available commands and their descriptions")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="CutieBot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    
    commands = [
        ("/hello", "Greet the user with a hello message"),
        ("/pingstaff", "Ping tomato 10 times"),
        ("/joke", "Get a terrible dad joke"),
        ("/rps", "Play Rock Paper Scissors with the bot"),
        ("/meme", "Get a random meme"),
        ("/embed", "Create a custom embed message (Server Management Only)"),
        ("/coinflip", "Flip a coin - heads or tails"),
        ("/fact", "Get a random interesting fact"),
        ("/ping", "Check the bot's latency"),
        ("/help", "Shows this help message")
    ]
    
    for name, description in commands:
        embed.add_field(name=name, value=description, inline=False)
    
    await interaction.response.send_message(embed=embed) 