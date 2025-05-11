import discord
from discord import app_commands
import aiohttp
import random

KISS_GIF_URL = "https://api.otakugifs.xyz/gif?reaction=kiss&id="+str(random.randint(1,1000000))

@app_commands.command(name="kiss", description="Kiss someone in the server")
@app_commands.describe(
    user="The user to kiss"
)
async def kiss(
    interaction: discord.Interaction,
    user: discord.Member
):
    if user.id == interaction.user.id:
        await interaction.response.send_message(
            "You can't kiss yourself!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="💋 Kiss",
        description=f"{interaction.user.mention} kissed {user.mention}!",
        color=discord.Color.pink()
    )
    
    kiss_gif = KISS_GIF_URL
    embed.set_image(url=kiss_gif)
    
    await interaction.response.send_message(
        f"{interaction.user.mention} {user.mention}",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(users=True)
    ) 