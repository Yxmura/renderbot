import discord
from discord import app_commands

@app_commands.command(name="setup", description="Setup server configuration")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚙️ Server Setup",
        description="Use the following commands to set up different features:",
        color=discord.Color.blue()
    )
    
    setup_commands = [
        ("🎂 Birthday System", "/setup_birthdays"),
        ("🎫 Ticket System", "/setup_tickets"),
        ("🎉 Giveaway System", "/setupgiveaway"),
        ("📊 Poll System", "/setuppoll")
    ]
    
    for feature, command in setup_commands:
        embed.add_field(name=feature, value=command, inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True) 