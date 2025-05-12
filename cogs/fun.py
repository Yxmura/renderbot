from discord.ext import commands
import discord
from discord import Option
import requests
import random
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import os

REMINDERS_FILE = "reminders.json"
CHOICES = ["rock", "paper", "scissors"]
SUBREDDITS = ["memes", "dankmemes", "wholesomememes"]
JOKE_API_URL = "https://icanhazdadjoke.com/"
KISS_GIF_URL = "https://api.otakugifs.xyz/gif?reaction=kiss&id=" + str(random.randint(1, 1000000))
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
                data = json.load(f)
                for reminder_id, reminder_data in data.items():
                    reminder_data['end_time'] = datetime.fromisoformat(reminder_data['end_time'])
                    self.reminders[reminder_id] = Reminder(**reminder_data)

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

async def check_reminders(bot):
    while True:
        now = datetime.now()
        for reminder_id, reminder in list(reminder_manager.reminders.items()):
            if now >= reminder.end_time:
                channel = bot.get_channel(reminder.channel_id)
                if channel:
                    user = bot.get_user(reminder.user_id)
                    if user:
                        embed = discord.Embed(
                            title="⏰ Reminder",
                            description=reminder.message,
                            color=discord.Color.purple()
                        )
                        embed.set_footer(text=f"Reminder set by {user.name}")
                        await channel.send(f"{user.mention} Here's your reminder!", embed=embed)
                reminder_manager.remove_reminder(reminder_id)
        await asyncio.sleep(60)

class FlagGame:
    def __init__(self, channel):
        self.channel = channel
        self.current_flag = None
        self.options = []
        self.correct_answer = None
        self.answered = False
        self.scores = {}
        self.active = True
        self.guessed_users = set()

    def generate_round(self):
        self.correct_answer = random.choice(list(COUNTRIES.keys()))
        
        wrong_options = random.sample(
            [country for country in COUNTRIES.keys() if country != self.correct_answer],
            4
        )
        
        self.options = [self.correct_answer] + wrong_options
        random.shuffle(self.options)

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
                f"The flag was from {self.game.correct_answer}!",
            )
        else:
            await interaction.response.send_message("❌ Wrong answer! Try again!", ephemeral=True)

    async def on_timeout(self):
        if not self.game.answered:
            await self.game.channel.send(
                f"⏰ Time's up! The correct answer was {self.game.correct_answer}!"
            )
            self.game.guessed_users.clear()
            self.game.generate_round()
            new_view = FlagGuessView(self.game)
            await self.game.channel.send(
                f"**New Round!** Guess this flag:",
                view=new_view
            )

class FunCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name="joke", description="Get a terrible dad joke.")
    async def dadjoke(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        try:
            response = requests.get(JOKE_API_URL, headers=HEADERS)
            if response.status_code == 200:
                joke = response.json().get("joke")
                await ctx.respond(joke)
            else:
                await ctx.respond("Sorry, I couldn't fetch a dad joke right now.")
        except Exception as e:
            await ctx.respond(f"Error fetching joke: {e}")

    @commands.slash_command(name="remind", description="Set a reminder")
    async def remind(
        self,
        ctx: discord.ApplicationContext,
        time: Option(str, description="When to remind you (e.g., 1h, 30m, 1d)"),
        message: Option(str, description="What to remind you about")
    ):
        try:
            unit = time[-1].lower()
            value = int(time[:-1])
            delta = {'s': timedelta(seconds=value), 'm': timedelta(minutes=value),
                     'h': timedelta(hours=value), 'd': timedelta(days=value)}.get(unit)

            if not delta:
                await ctx.respond("Invalid time format! Use s, m, h, or d.", ephemeral=True)
                return

            end_time = datetime.now() + delta
            reminder = Reminder(ctx.user.id, ctx.channel.id, message, end_time)
            reminder_id = f"{ctx.user.id}_{int(end_time.timestamp())}"
            reminder_manager.add_reminder(reminder_id, reminder)

            embed = discord.Embed(
                title="⏰ Reminder Set",
                description=f"I'll remind you about:\n{message}",
                color=discord.Color.green()
            )
            embed.add_field(name="Time", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)

            await ctx.respond(embed=embed, ephemeral=True)
        except ValueError:
            await ctx.respond("Invalid time format!", ephemeral=True)

    @commands.slash_command(name="kiss", description="Kiss someone in the server")
    async def kiss(
        self,
        ctx: discord.ApplicationContext,
        user: Option(discord.Member, "The user to kiss")
    ):
        try:
            if user.id == ctx.user.id:
                await ctx.respond("You can't kiss yourself!", ephemeral=True)
                return

            embed = discord.Embed(
                title="💋 Kiss",
                description=f"{ctx.user.mention} kissed {user.mention}!",
                color=discord.Color.red()
            )
            embed.set_image(url=KISS_GIF_URL)
            await ctx.respond(f"{ctx.user.mention} {user.mention}", embed=embed)
        except Exception as e:
            await ctx.respond(f'an error occured: {e}')

    @commands.slash_command(name="coinflip", description="Flip a coin")
    async def coinflip(self, ctx: discord.ApplicationContext):
        result = random.choice(["Heads", "Tails"])
        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold()
        )
        img = "https://i.ibb.co/gwM94r8/coin-heads.png" if result == "Heads" else "https://i.ibb.co/ZTHtS5D/coin-tails.png"
        embed.set_image(url=img)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="meme", description="Get a random meme from Reddit")
    async def meme(self, ctx: discord.ApplicationContext):
        await ctx.defer()
        try:
            response = requests.get("https://meme-api.com/gimme")
            if response.status_code == 200:
                data = response.json()
                embed = discord.Embed(title=data["title"], url=data["postLink"], color=discord.Color.orange())
                embed.set_image(url=data["url"])
                await ctx.respond(embed=embed)
            else:
                await ctx.respond("❌ Failed to fetch meme.")
        except Exception as e:
            await ctx.respond(f"❌ Error fetching meme: {e}")

    @commands.slash_command(name="rps", description="Play Rock Paper Scissors")
    async def rps(
        self,
        ctx: discord.ApplicationContext,
        choice: Option(str, "Your choice", choices=["rock", "paper", "scissors"])
    ):
        bot_choice = random.choice(CHOICES)
        win_conditions = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
        if choice == bot_choice:
            result = "It's a tie! 🤝"
        elif win_conditions[choice] == bot_choice:
            result = "You win! 🎉"
        else:
            result = "I win! 😎"

        embed = discord.Embed(title="Rock Paper Scissors", color=discord.Color.purple())
        embed.add_field(name="Your Choice", value=f"`{choice}`", inline=True)
        embed.add_field(name="My Choice", value=f"`{bot_choice}`", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        await ctx.respond(embed=embed)

    @commands.slash_command(name="flagguess", description="Start a flag guessing game!")
    async def flagguess(self, ctx: discord.ApplicationContext):
        game = FlagGame(ctx.channel)
        game.generate_round()

        embed = discord.Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of the flag shown below!",
            color=discord.Color.purple()
        )
        flag_url = f"https://flagcdn.com/w320/{COUNTRIES[game.correct_answer].lower()}.png"
        embed.set_image(url=flag_url)

        view = FlagGuessView(game)
        await ctx.respond(embed=embed, view=view)
