import discord
from discord import app_commands

@app_commands.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Here are all available commands:",
        color=discord.Color.blue()
    )
    
    commands = [
        ("🎮 Games", "/rps, /flagguess"),
        ("😄 Fun", "/joke, /meme, /kiss"),
        ("⚙️ Utility", "/ping, /remind, /create_embed"),
        ("🎉 Features", "/giveaway, /poll, /birthday"),
        ("👥 Roles", "/createrolemenu, /deleterolemenu")
    ]
    
    for category, cmds in commands:
        embed.add_field(name=category, value=cmds, inline=False)
    
    await interaction.response.send_message(embed=embed) 