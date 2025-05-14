import discord
from discord.ext import commands
import os
import json

try:
    # Load config
    with open("config.json", mode="r") as config_file:
        config = json.load(config_file)
    GUILD_ID = config["guild_id"]
except Exception as e:
    print(f"Error loading config.json: {e}")
    GUILD_ID = 0  # Replace with your guild ID if needed

class SyncCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="sync", help="Manually sync slash commands (Owner only)")
    @commands.is_owner()
    async def sync(self, ctx):
        """Manually sync application commands"""
        try:
            print(f"Manual sync triggered by {ctx.author}")
            guild = discord.Object(id=GUILD_ID)
            
            # First, try guild-specific sync
            synced = await self.bot.tree.sync(guild=guild)
            await ctx.send(f"✅ Synced {len(synced)} guild commands to {GUILD_ID}")
            print(f"Synced {len(synced)} guild commands: {[cmd.name for cmd in synced]}")
            
            # Then try global sync
            global_synced = await self.bot.tree.sync()
            await ctx.send(f"✅ Synced {len(global_synced)} global commands")
            print(f"Synced {len(global_synced)} global commands: {[cmd.name for cmd in global_synced]}")
            
        except Exception as e:
            await ctx.send(f"❌ Error syncing commands: {e}")
            print(f"Error in sync command: {e}")
            import traceback
            traceback.print_exc()

async def setup(bot):
    await bot.add_cog(SyncCommands(bot))