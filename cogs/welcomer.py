import discord
from discord.ext import commands

# Replace these with your actual channel IDs
CHANNEL_ID = 1367574829208699020  # Goodbye channel ID

class WelcomeGoodbyeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if CHANNEL_ID:
            channel = member.guild.get_channel(CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="👋 Welcome!",
                    description=f"{member.mention} has joined the server!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if CHANNEL_ID:
            channel = member.guild.get_channel(CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    title="👋 Goodbye!",
                    description=f"{member.mention} has left the server.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

# Setup function to add the cog to the bot
async def setup(bot):
    bot.add_cog(WelcomeGoodbyeCog(bot))
