import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = None  # Set this to your welcome channel ID

def setup(bot: commands.Bot):
    @bot.event
    async def on_member_join(member: discord.Member):
        if WELCOME_CHANNEL_ID:
            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=f"{member.mention} has joined the server!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed) 