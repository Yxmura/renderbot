import discord
from discord.ext import commands
import asyncio
import os

# Your bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Optional: replace with your guild ID for faster slash command updates during testing
TEST_GUILD_ID = 1317605088558190602  # Set this to an integer like 123456789012345678 if you want fast syncing

async def setup_commands():
    commands_dir = "./commands"
    if os.path.exists(commands_dir):
        for filename in os.listdir(commands_dir):
            if filename.endswith(".py") and not filename.startswith("_") and filename != "__init__.py":
                try:
                    await bot.load_extension(f"commands.{filename[:-3]}")
                    print(f"Loaded cog: commands.{filename[:-3]}")
                except Exception as e:
                    print(f"Failed to load cog commands.{filename[:-3]}: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")

    await setup_commands()  # This must run AFTER bot is ready

    try:
        if TEST_GUILD_ID:
            synced = await bot.tree.sync(guild=discord.Object(id=TEST_GUILD_ID))
            print(f"Synced {len(synced)} command(s) to test guild.")
        else:
            synced = await bot.tree.sync()
            print(f"Synced {len(synced)} global command(s).")
    except Exception as e:
        print(f"Command sync failed: {e}")
        
    # Start background tasks
    asyncio.create_task(check_birthdays(bot))
    asyncio.create_task(check_giveaways(bot))
    asyncio.create_task(check_reminders(bot))
    asyncio.create_task(check_polls(bot))

# Dummy implementations (replace these with your actual logic)
async def check_birthdays(bot): pass
async def check_giveaways(bot): pass
async def check_reminders(bot): pass
async def check_polls(bot): pass

# Run the bot
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)
