import requests
import discord
from discord.ext import commands, tasks
from discord import app_commands, Embed, Color, File
import random
import aiohttp
import json
from typing import Dict, List, Optional
import asyncio
import os
from datetime import datetime, timedelta
from io import BytesIO

REMINDERS_FILE = "reminders.json"
CHOICES = ["rock", "paper", "scissors"]
MEME_API_URL = "https://meme-api.com/gimme"
JOKE_API_URL = "https://icanhazdadjoke.com/"
HEADERS = {"Accept": "application/json"}
# Dictionary of countries and their codes
COUNTRIES = {
    "Afghanistan": "AF", "Albania": "AL", "Algeria": "DZ", "Andorra": "AD", "Angola": "AO",
    "Argentina": "AR", "Armenia": "AM", "Australia": "AU", "Austria": "AT", "Azerbaijan": "AZ",
    "Bahamas": "BS", "Bahrain": "BH", "Bangladesh": "BD", "Barbados": "BB", "Belarus": "BY",
    "Belgium": "BE", "Belize": "BZ", "Benin": "BJ", "Bhutan": "BT", "Bolivia": "BO",
    "Bosnia and Herzegovina": "BA", "Botswana": "BW", "Brazil": "BR", "Brunei": "BN", "Bulgaria": "BG",
    "Burkina Faso": "BF", "Burundi": "BI", "Cambodia": "KH", "Cameroon": "CM", "Canada": "CA",
    "Cape Verde": "CV", "Central African Republic": "CF", "Chad": "TD", "Chile": "CL", "China": "CN",
    "Colombia": "CO", "Comoros": "KM", "Congo": "CG", "Costa Rica": "CR", "Croatia": "HR",
    "Cuba": "CU", "Cyprus": "CY", "Czech Republic": "CZ", "Denmark": "DK", "Djibouti": "DJ",
    "Dominica": "DM", "Dominican Republic": "DO", "Ecuador": "EC", "Egypt": "EG", "El Salvador": "SV",
    "Equatorial Guinea": "GQ", "Eritrea": "ER", "Estonia": "EE", "Ethiopia": "ET", "Fiji": "FJ",
    "Finland": "FI", "France": "FR", "Gabon": "GA", "Gambia": "GM", "Georgia": "GE",
    "Germany": "DE", "Ghana": "GH", "Greece": "GR", "Grenada": "GD", "Guatemala": "GT",
    "Guinea": "GN", "Guinea-Bissau": "GW", "Guyana": "GY", "Haiti": "HT", "Honduras": "HN",
    "Hungary": "HU", "Iceland": "IS", "India": "IN", "Indonesia": "ID", "Iran": "IR",
    "Iraq": "IQ", "Ireland": "IE", "Italy": "IT", "Jamaica": "JM",
    "Japan": "JP", "Jordan": "JO", "Kazakhstan": "KZ", "Kenya": "KE", "Kiribati": "KI",
    "Kuwait": "KW", "Kyrgyzstan": "KG", "Laos": "LA", "Latvia": "LV", "Lebanon": "LB",
    "Lesotho": "LS", "Liberia": "LR", "Libya": "LY", "Liechtenstein": "LI", "Lithuania": "LT",
    "Luxembourg": "LU", "Madagascar": "MG", "Malawi": "MW", "Malaysia": "MY", "Maldives": "MV",
    "Mali": "ML", "Malta": "MT", "Marshall Islands": "MH", "Mauritania": "MR", "Mauritius": "MU",
    "Mexico": "MX", "Micronesia": "FM", "Moldova": "MD", "Monaco": "MC", "Mongolia": "MN",
    "Montenegro": "ME", "Morocco": "MA", "Mozambique": "MZ", "Myanmar": "MM", "Namibia": "NA",
    "Nauru": "NR", "Nepal": "NP", "Netherlands": "NL", "New Zealand": "NZ", "Nicaragua": "NI",
    "Niger": "NE", "Nigeria": "NG", "North Korea": "KP", "North Macedonia": "MK", "Norway": "NO",
    "Oman": "OM", "Pakistan": "PK", "Palau": "PW", "Palestine": "PS", "Panama": "PA",
    "Papua New Guinea": "PG", "Paraguay": "PY", "Peru": "PE", "Philippines": "PH", "Poland": "PL",
    "Portugal": "PT", "Qatar": "QA", "Romania": "RO", "Russia": "RU", "Rwanda": "RW",
    "Saint Kitts and Nevis": "KN", "Saint Lucia": "LC", "Saint Vincent and the Grenadines": "VC",
    "Samoa": "WS", "San Marino": "SM", "Sao Tome and Principe": "ST", "Saudi Arabia": "SA",
    "Senegal": "SN", "Serbia": "RS", "Seychelles": "SC", "Sierra Leone": "SL", "Singapore": "SG",
    "Slovakia": "SK", "Slovenia": "SI", "Solomon Islands": "SB", "Somalia": "SO", "South Africa": "ZA",
    "South Korea": "KR", "South Sudan": "SS", "Spain": "ES", "Sri Lanka": "LK", "Sudan": "SD",
    "Suriname": "SR", "Sweden": "SE", "Switzerland": "CH", "Syria": "SY", "Taiwan": "TW",
    "Tajikistan": "TJ", "Tanzania": "TZ", "Thailand": "TH", "Timor-Leste": "TL", "Togo": "TG",
    "Tonga": "TO", "Trinidad and Tobago": "TT", "Tunisia": "TN", "Turkey": "TR", "Turkmenistan": "TM",
    "Tuvalu": "TV", "Uganda": "UG", "Ukraine": "UA", "United Arab Emirates": "AE", "United Kingdom": "GB",
    "United States": "US", "Uruguay": "UY", "Uzbekistan": "UZ", "Vanuatu": "VU", "Vatican City": "VA",
    "Venezuela": "VE", "Vietnam": "VN", "Yemen": "YE", "Zambia": "ZM", "Zimbabwe": "ZW"
}

class Reminder:
    def __init__(self, user_id: int, channel_id: int, message: str, end_time: datetime):
        self.user_id = user_id
        self.channel_id = channel_id
        self.message = message
        self.end_time = end_time

class ReminderManager:
    def __init__(self):
        self.reminders = {}
        self.load_reminders()

    def load_reminders(self):
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, 'r') as f:
                try:
                    data = json.load(f)
                    for reminder_id, reminder_data in data.items():
                        reminder_data['end_time'] = datetime.fromisoformat(reminder_data['end_time'])
                        self.reminders[reminder_id] = Reminder(**reminder_data)
                except json.JSONDecodeError:
                    self.reminders = {}

    def save_reminders(self):
        data = {
            reminder_id: {
                'user_id': reminder.user_id,
                'channel_id': reminder.channel_id,
                'message': reminder.message,
                'end_time': reminder.end_time.isoformat()
            }
            for reminder_id, reminder in self.reminders.items()
        }
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_reminder(self, reminder_id: str, reminder: Reminder):
        self.reminders[reminder_id] = reminder
        self.save_reminders()

    def remove_reminder(self, reminder_id: str):
        if reminder_id in self.reminders:
            del self.reminders[reminder_id]
            self.save_reminders()

reminder_manager = ReminderManager()

async def check_reminders(bot: commands.Bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        now = datetime.now()
        for reminder_id, reminder in list(reminder_manager.reminders.items()):
            if now >= reminder.end_time:
                channel = bot.get_channel(reminder.channel_id)
                if channel:
                    user = bot.get_user(reminder.user_id)
                    if user:
                        embed = Embed(
                            title="⏰ Reminder",
                            description=reminder.message,
                            color=Color.purple()
                        )
                        embed.set_footer(text=f"Reminder set by {user.name}")
                        await channel.send(f"{user.mention} Here's your reminder!", embed=embed)
                reminder_manager.remove_reminder(reminder_id)
        await asyncio.sleep(60)

class FlagGame:
    def __init__(self, channel: discord.TextChannel):
        self.channel = channel
        self.current_flag = None
        self.options = []
        self.correct_answer = None
        self.answered = False
        self.scores = {}
        self.active = True
        self.guessed_users = set()
        self.message = None # To store the game message for updating

    def generate_round(self):
        self.correct_answer = random.choice(list(COUNTRIES.keys()))

        wrong_options = random.sample(
            [country for country in COUNTRIES.keys() if country != self.correct_answer],
            4
        )

        self.options = [self.correct_answer] + wrong_options
        random.shuffle(self.options)
        self.answered = False
        self.guessed_users.clear()

class FlagGuessView(discord.ui.View):
    def __init__(self, game: FlagGame):
        super().__init__(timeout=30)
        self.game = game
        self.add_buttons()

    def add_buttons(self):
        for option in self.game.options:
            button = discord.ui.Button(
                label=option,
                style=discord.ButtonStyle.primary,
                custom_id=option
            )
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user.id in self.game.guessed_users:
            await interaction.response.send_message("❌ You've already guessed this round!", ephemeral=True)
            return

        self.game.guessed_users.add(interaction.user.id)

        if interaction.data["custom_id"] == self.game.correct_answer:
            self.game.answered = True
            user_id = interaction.user.id
            if user_id not in self.game.scores:
                self.game.scores[user_id] = 0
            self.game.scores[user_id] += 1

            await interaction.response.send_message(
                f"✅ Correct! {interaction.user.mention} got it right!\n"
                f"The flag was from {self.game.correct_answer}!"
            )
            # Generate a new round immediately after a correct answer
            await self.game.channel.send("**New Round!** Preparing the next flag...")
            self.game.generate_round()
            await self.send_new_round()

        else:
            await interaction.response.send_message("❌ Wrong answer! Try again!", ephemeral=True)

    async def on_timeout(self):
        if not self.game.answered:
            await self.game.channel.send(
                f"⏰ Time's up! The correct answer was {self.game.correct_answer}!"
            )
            # Generate a new round on timeout
            await self.game.channel.send("**New Round!** Preparing the next flag...")
            self.game.generate_round()
            await self.send_new_round()

    async def send_new_round(self):
        embed = Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of this flag:",
            color=Color.purple()
        )
        code = COUNTRIES[self.game.correct_answer].lower()
        embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")

        new_view = FlagGuessView(self.game)
        self.game.message = await self.game.channel.send(embed=embed, view=new_view)


class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()

    def cog_unload(self):
        self.check_reminders.cancel()

    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now = datetime.now()
        for reminder_id, reminder in list(reminder_manager.reminders.items()):
            if now >= reminder.end_time:
                channel = self.bot.get_channel(reminder.channel_id)
                if channel:
                    user = self.bot.get_user(reminder.user_id)
                    if user:
                        embed = Embed(
                            title="⏰ Reminder",
                            description=reminder.message,
                            color=Color.purple()
                        )
                        embed.set_footer(text=f"Reminder set by {user.name}")
                        await channel.send(f"{user.mention} Here's your reminder!", embed=embed)
                reminder_manager.remove_reminder(reminder_id)

    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="joke", description="Get a terrible dad joke.")
    async def dadjoke(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(JOKE_API_URL, headers=HEADERS) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        joke = data.get("joke")
                        await interaction.followup.send(joke)
                    else:
                        await interaction.followup.send("Sorry, I couldn't fetch a dad joke right now.")
        except Exception as e:
            await interaction.followup.send(f"Error fetching joke: {e}")

    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(
        time="When to remind you (e.g., '1h', '30m', '1d')",
        message="What to remind you about"
    )
    async def remind(self, interaction: discord.Interaction, time: str, message: str):
        try:
            unit = time[-1].lower()
            value = int(time[:-1])
            delta = {"s": timedelta(seconds=value), "m": timedelta(minutes=value),
                     "h": timedelta(hours=value), "d": timedelta(days=value)}.get(unit)

            if not delta:
                await interaction.response.send_message("Invalid format! Use s/m/h/d.", ephemeral=True)
                return

            end_time = datetime.now() + delta
            reminder = Reminder(interaction.user.id, interaction.channel_id, message, end_time)
            reminder_id = f"{interaction.user.id}_{int(end_time.timestamp())}"
            reminder_manager.add_reminder(reminder_id, reminder)

            embed = Embed(title="⏰ Reminder Set", description=message, color=Color.green())
            embed.add_field(name="Time", value=f"<t:{int(end_time.timestamp())}:R>")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError:
            await interaction.response.send_message("Invalid time value!", ephemeral=True)

    @app_commands.command(name="kiss", description="Kiss someone in the server")
    @app_commands.describe(user="The user to kiss")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == interaction.user.id:
            await interaction.response.send_message("You can't kiss yourself!", ephemeral=True)
            return

        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.otakugifs.xyz/gif?reaction=kiss") as resp:
                if resp.status != 200:
                    await interaction.response.send_message("Couldn't fetch a kiss gif!", ephemeral=True)
                    return
                gif_data = await resp.json()
                kiss_gif = gif_data['url']

        embed = Embed(
            title="💋 Kiss",
            description=f"{interaction.user.mention} kissed {user.mention}!",
            color=Color.pink()
        ).set_image(url=kiss_gif)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="coinflip", description="Flip a coin - heads or tails")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        embed = Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=Color.gold()
        ).set_thumbnail(
            url="https://i.ibb.co/zT4b26xW/Chat-GPT-Image-May-10-2025-08-18-59-PM.png" if result == "Heads"
            else "https://i.ibb.co/PvgwZbtJ/Pixel-Art-Golden-Star-Coin.png"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="meme", description="Get a random meme")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer the interaction

        try:
            async with aiohttp.ClientSession() as session:
                api_url = MEME_API_URL

                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Couldn't fetch a meme right now from the API.")
                        return

                    data = await resp.json()

                    if not data or not data.get('url'):
                         await interaction.followup.send("Couldn't get meme data from the API.")
                         return

                    meme_title = data.get('title', 'No Title')
                    meme_image_url = data.get('url')
                    meme_subreddit = data.get('subreddit', 'Unknown Subreddit')
                    meme_post_link = data.get('postLink')

                    embed = Embed(title=meme_title, color=Color.orange())
                    embed.set_image(url=meme_image_url)

                    await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Failed to fetch meme: {e}")

    @app_commands.command(name="rps", description="Play Rock Paper Scissors with the bot")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="rock", value="rock"),
        app_commands.Choice(name="paper", value="paper"),
        app_commands.Choice(name="scissors", value="scissors"),
    ])
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]):
        player_choice = choice.value
        bot_choice = random.choice(CHOICES)
        result = "It's a tie! 🤝" if player_choice == bot_choice else (
            "You win! 🎉" if (player_choice, bot_choice) in [("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")]
            else "I win! 😎"
        )

        embed = Embed(title="Rock Paper Scissors", color=Color.purple())
        embed.add_field(name="You", value=player_choice)
        embed.add_field(name="Me", value=bot_choice)
        embed.add_field(name="Result", value=result)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="flagguess", description="Start a flag guessing game")
    async def flagguess(self, interaction: discord.Interaction):
        game = FlagGame(interaction.channel)
        game.generate_round()

        embed = Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of this flag:",
            color=Color.purple()
        )
        code = COUNTRIES[game.correct_answer].lower()
        embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")

        view = FlagGuessView(game)
        game.message = await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))