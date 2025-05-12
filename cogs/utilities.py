import discord
from discord.ext import commands

REQUIRED_ROLE_ID = 1317607057687576696

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="ping", description="Check the bot's latency")
    async def ping(self, ctx: discord.ApplicationContext):
        latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot Latency: **{latency}ms**",
            color=discord.Color.purple()
        )
        await ctx.respond(embed=embed)

    @discord.slash_command(
        name="embed",
        description="Create a custom embed message (Requires a specific role)"
    )
    async def embed(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.Option(discord.TextChannel, "Channel to send the embed in"),
        title: discord.Option(str, "Title of the embed"),
        description: discord.Option(str, "Description for the embed"),
        color: discord.Option(str, "Hex color (e.g., FF0000)", default="0000FF"),
        footer: discord.Option(str, "Footer text", default=None)
    ):
        # Check if the user has the required role
        if not any(role.id == REQUIRED_ROLE_ID for role in ctx.user.roles):
            await ctx.respond(
                "You do not have the required role to use this command.",
                ephemeral=True
            )
            return

        try:
            color_int = int(color.replace("#", ""), 16)
            embed = discord.Embed(
                title=title,
                description=description,
                color=color_int
            )
            if footer:
                embed.set_footer(text=footer)

            await channel.send(embed=embed)
            await ctx.respond(
                f"✅ Embed sent to {channel.mention}!",
                ephemeral=True
            )

        except ValueError:
            await ctx.respond(
                "❌ Invalid color code! Please use a valid hex code (e.g., `FF0000` for red).",
                ephemeral=True
            )

        except Exception as e:
            await ctx.respond(
                f"❌ An error occurred: {e}",
                ephemeral=True
            )
