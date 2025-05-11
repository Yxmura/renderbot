import discord
from discord.ext import commands
from discord import app_commands

class Hello(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.tree.add_command(self.hello)

    @app_commands.command(name="hello", description="Greet the user with a hello message")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Hello, {interaction.user.mention}! 👋')

async def setup(bot):
    await bot.add_cog(Hello(bot))
