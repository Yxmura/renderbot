import requests
import discord
from discord.ext import commands
from discord import app_commands
import random
import aiohttp
import json
from typing import Dict, List, Optional
import asyncio
import os
from datetime import datetime, timedelta

REMINDERS_FILE = "reminders.json"
CHOICES = ["rock", "paper", "scissors"]
SUBREDDITS = ["memes", "dankmemes", "wholesomememes"]
JOKE_API_URL = "https://icanhazdadjoke.com/"
KISS_GIF_URL = f"https://api.otakugifs.xyz/gif?reaction=kiss&id={str(random.randint(1, 1000000))}".json()
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
        if self.game.answered:
            await interaction.response.send_message("This round is already over!", ephemeral=True)
            return

        if interaction.data["custom_id"] == self.game.correct_answer:
            self.game.answered = True
            user_id = interaction.user.id
            if user_id not in self.game.scores:
                self.game.scores[user_id] = 0
            self.game.scores[user_id] += 1

            scoreboard = discord.Embed(
                title="🏆 Scoreboard",
                color=discord.Color.green()
            )
            
            # Sort scores and get top 5
            sorted_scores = sorted(
                self.game.scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            for i, (user_id, score) in enumerate(sorted_scores, 1):
                user = interaction.guild.get_member(user_id)
                if user:
                    scoreboard.add_field(
                        name=f"{i}. {user.name}",
                        value=f"Score: {score}",
                        inline=False
                    )

            await interaction.response.send_message(
                f"✅ Correct! {interaction.user.mention} got it right!\n"
                f"The flag was from {self.game.correct_answer}!",
                embed=scoreboard
            )

            self.game.generate_round()
            new_view = FlagGuessView(self.game)
            await self.game.channel.send(
                f"**New Round!** Guess this flag:",
                view=new_view
            )
        else:
            await interaction.response.send_message("❌ Wrong answer! Try again!", ephemeral=True)

    async def on_timeout(self):
        if not self.game.answered:
            await self.game.channel.send(
                f"⏰ Time's up! The correct answer was {self.game.correct_answer}!"
            )
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
    async def dadjoke(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        try:
            response = requests.get(JOKE_API_URL, headers=HEADERS)
            if response.status_code == 200:
                joke = response.json().get("joke")
                await interaction.followup.send(joke)
            else:
                await interaction.followup.send("Sorry, I couldn't fetch a dad joke right now. Try again later.")
        except Exception as e:
            await interaction.followup.send(f"Error fetching joke: {e}")

    @commands.slash_command(name="remind", description="Set a reminder")
    @app_commands.describe(
        time="When to remind you (e.g., '1h', '30m', '1d')",
        message="What to remind you about"
    )
    async def remind(
        self,
        interaction: discord.Interaction,
        time: str,
        message: str
    ):
        try:
            # Parse time string
            unit = time[-1].lower()
            value = int(time[:-1])
            
            if unit == 's':
                delta = timedelta(seconds=value)
            elif unit == 'm':
                delta = timedelta(minutes=value)
            elif unit == 'h':
                delta = timedelta(hours=value)
            elif unit == 'd':
                delta = timedelta(days=value)
            else:
                await interaction.response.send_message(
                    "Invalid time format! Use 's' for seconds, 'm' for minutes, 'h' for hours, or 'd' for days.",
                    ephemeral=True
                )
                return

            end_time = datetime.now() + delta
            
            reminder = Reminder(
                user_id=interaction.user.id,
                channel_id=interaction.channel_id,
                message=message,
                end_time=end_time
            )

            reminder_id = f"{interaction.user.id}_{int(end_time.timestamp())}"
            reminder_manager.add_reminder(reminder_id, reminder)

            embed = discord.Embed(
                title="⏰ Reminder Set",
                description=f"I'll remind you about:\n{message}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Time",
                value=f"<t:{int(end_time.timestamp())}:R>",
                inline=True
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except ValueError:
            await interaction.response.send_message(
                "Invalid time format! Please use a number followed by 's', 'm', 'h', or 'd'.",
                ephemeral=True
            )

    @commands.slash_command(name="kiss", description="Kiss someone in the server")
    @app_commands.describe(
        user="The user to kiss"
    )
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        if user.id == interaction.user.id:
            await interaction.response.send_message(
                "You can't kiss yourself!",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="💋 Kiss",
            description=f"{interaction.user.mention} kissed {user.mention}!",
            color=discord.Color.pink()
        )

        kiss_gif = KISS_GIF_URL['url']
        embed.set_image(url=kiss_gif)

        # Send the embed with the kiss gif
        await interaction.response.send_message(
            f"{interaction.user.mention} {user.mention}",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True)
        )

    @commands.slash_command(name="coinflip", description="Flip a coin - heads or tails")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])

        embed = discord.Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=discord.Color.gold()
        )

        if result == "Heads":
            embed.set_thumbnail("https://i.ibb.co/gwM94r8/coin-heads.png")
        else:
            embed.set_thumbnail("https://i.ibb.co/ZTHtS5D/coin-tails.png")
        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="meme", description="Get a random meme from Reddit")
    async def meme(self, interaction: discord.Interaction):
        await interaction.response.defer()

        subreddit = random.choice(SUBREDDITS)
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=100"

        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code == 200:
                posts = response.json()['data']['children']
                valid_posts = [post for post in posts if not post['data']['is_video'] and not post['data']['over_18']]

                if valid_posts:
                    post = random.choice(valid_posts)
                    title = post['data']['title']
                    image_url = post['data']['url']

                    embed = discord.Embed(
                        title=title,
                        color=discord.Color.orange()
                    )
                    embed.set_image(url=image_url)

                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("Couldn't find a suitable meme. Try again!")
            else:
                await interaction.followup.send("Failed to fetch meme. Try again later!")
        except Exception as e:
            await interaction.followup.send(f"Error fetching meme: {e}")

    @commands.slash_command(name="rps", description="Play Rock Paper Scissors with the bot")
    @app_commands.describe(choice="Your choice: rock, paper, or scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="rock", value="rock"),
        app_commands.Choice(name="paper", value="paper"),
        app_commands.Choice(name="scissors", value="scissors")
    ])
    async def rps(self, interaction: discord.Interaction, choice: str):
        bot_choice = random.choice(CHOICES)

        # Determine winner
        if choice == bot_choice:
            result = "It's a tie! 🤝"
        elif (choice == "rock" and bot_choice == "scissors") or \
             (choice == "paper" and bot_choice == "rock") or \
             (choice == "scissors" and bot_choice == "paper"):
            result = "You win! 🎉"
        else:
            result = "I win! 😎"

        embed = discord.Embed(
            title="Rock Paper Scissors",
            color=discord.Color.purple()
        )
        embed.add_field(name="Your Choice", value=f"`{choice}`", inline=True)
        embed.add_field(name="My Choice", value=f"`{bot_choice}`", inline=True)
        embed.add_field(name="Result", value=result, inline=False)

        await interaction.response.send_message(embed=embed)

    @commands.slash_command(name="flagguess", description="Start a competitive flag guessing game!")
    async def flagguess(self, interaction: discord.Interaction):
        game = FlagGame(interaction.channel)
        game.generate_round()
        
        embed = discord.Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of the flag shown below!",
            color=discord.Color.purple()
        )
        
        country_code = COUNTRIES[game.correct_answer]
        flag_url = f"https://flagcdn.com/w320/{country_code.lower()}.png"
        embed.set_image(url=flag_url)
        
        view = FlagGuessView(game)
        await interaction.response.send_message(embed=embed, view=view)
        
async def setup(bot):
    await bot.add_cog(FunCommands(bot))