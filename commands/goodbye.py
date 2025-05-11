import discord
from discord.ext import commands

GOODBYE_CHANNEL_ID = None  # Set this to your goodbye channel ID

def setup(bot: commands.Bot):
    @bot.event
    async def on_member_remove(member: discord.Member):
        if GOODBYE_CHANNEL_ID:
            channel = member.guild.get_channel(GOODBYE_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="👋 Goodbye!",
                    description=f"{member.mention} has left the server.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed) 