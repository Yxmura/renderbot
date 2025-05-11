import discord
from discord.ext import commands

# Replace these with your actual channel IDs
GOODBYE_CHANNEL_ID = 1367574829208699020  # Goodbye channel ID
WELCOME_CHANNEL_ID = None  # Set this to your welcome channel ID

class WelcomeGoodbyeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
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

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
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

# Setup function to add the cog to the bot
def setup(bot):
    bot.add_cog(WelcomeGoodbyeCog(bot))
