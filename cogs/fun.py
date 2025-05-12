import requests
import discord
from discord.ext import commands, tasks
from discord import app_commands, Embed, Color, File, ui
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
JOKE_API_URL = "https://icanhazdadjoke.com/"
HEADERS = {"Accept": "application/json"}
MEME_API_URL = "https://meme-api.com/gimme" # API for memes

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
    "Guinea": "GN", "Guinea-Bissau": "GW", "Guyana": "GUY", "Haiti": "HT", "Honduras": "HN",
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

# View for the "Play Again" button
class PlayAgainView(ui.View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=300) # Timeout after 5 minutes of inactivity
        self.cog = cog # Keep a reference to the cog to access the game state

    @ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.channel_id in self.cog.active_flag_game_channels:
             await interaction.response.send_message("A flag guessing game is already starting in this channel!", ephemeral=True)
             return

        # Stop this view to disable the button
        self.stop()
        try:
            await interaction.message.edit(view=None) # Remove the button from the previous message
        except:
            pass # Ignore if the message was deleted

        await interaction.response.send_message("Starting a new flag guessing game...")
        # Use a task to start the new game to avoid blocking the interaction
        asyncio.create_task(self.cog.start_new_flag_game(interaction.channel))


# Modified FlagGame for a single round with Play Again button
class FlagGame:
    def __init__(self, channel: discord.TextChannel, cog: commands.Cog):
        self.channel = channel
        self.cog = cog # Reference to the cog to access active_flag_game_channels
        self.current_flag = None
        self.options = []
        self.correct_answer = None
        self.answered = False
        self.message: Optional[discord.Message] = None # To store the game message

    def generate_round_data(self):
        self.correct_answer = random.choice(list(COUNTRIES.keys()))

        wrong_options = random.sample(
            [country for country in COUNTRIES.keys() if country != self.correct_answer],
            4
        )

        self.options = [self.correct_answer] + wrong_options
        random.shuffle(self.options)
        self.answered = False

    async def start_round(self, interaction: discord.Interaction):
        self.generate_round_data()

        embed = Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of this flag:",
            color=Color.purple()
        )
        code = COUNTRIES[self.correct_answer].lower()
        embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")

        view = FlagGuessView(self) # Pass the game instance to the view
        self.message = await interaction.response.send_message(embed=embed, view=view)

    async def end_round(self, message: str):
        if self.message:
            try:
                # Disable the view on the original game message
                await self.message.edit(view=None)

                # Send a separate message with the game result and the Play Again button
                await self.channel.send(message, view=PlayAgainView(self.cog))

            except Exception as e:
                print(f"Error ending flag game round or sending play again button: {e}")
            finally:
                # Remove the channel from active games when the round ends
                if self.channel.id in self.cog.active_flag_game_channels:
                    self.cog.active_flag_game_channels.remove(self.channel.id)


class FlagGuessView(ui.View):
    def __init__(self, game: FlagGame):
        super().__init__(timeout=30) # Set a timeout for the round
        self.game = game
        self.add_buttons()

    def add_buttons(self):
        for option in self.game.options:
            button = ui.Button(
                label=option,
                style=discord.ButtonStyle.primary,
                custom_id=option # Custom ID just needs to be unique within the view
            )
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        if self.game.answered: # Prevent multiple answers in a single-round game
            await interaction.response.send_message("This round has already ended.", ephemeral=True)
            return

        self.game.answered = True # Mark the round as answered

        if interaction.data["custom_id"] == self.game.correct_answer:
            result_message = (
                f"✅ Correct! {interaction.user.mention} got it right!\n"
                f"The flag was from **{self.game.correct_answer}**!\n"
                "Game Over!"
            )
            await interaction.response.send_message(
                f"✅ Correct! You got it!",
                ephemeral=True # Send ephemeral response to the user first
            )
            await self.game.end_round(result_message) # End the round and send the result
        else:
            result_message = (
                f"❌ Wrong answer! {interaction.user.mention} guessed incorrectly.\n"
                f"The correct answer was **{self.game.correct_answer}**.\n"
                "Game Over!"
            )
            await interaction.response.send_message(
                 f"❌ Wrong answer!",
                 ephemeral=True # Send ephemeral response to the user first
            )
            await self.game.end_round(result_message) # End the round and send the result

        self.stop() # Stop the view when an answer is received


    async def on_timeout(self):
        if not self.game.answered: # Only end if no one answered
            result_message = (
                f"⏰ Time's up! No one guessed in time.\n"
                f"The correct answer was **{self.game.correct_answer}**.\n"
                "Game Over!"
            )
            await self.game.end_round(result_message) # End the round and send the result

        self.stop() # Stop the view on timeout


class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()
        # Set to track channels with an active flag game
        self.active_flag_game_channels: set[int] = set()


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

        # Send the message with the pings and the embed
        await interaction.response.send_message(
            content=f"{interaction.user.mention} kisses {user.mention}!", # Pings the users outside the embed
            embed=embed
        )

    @app_commands.command(name="coinflip", description="Flip a coin - heads or tails")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        embed = Embed(
            title="🪙 Coin Flip",
            description=f"The coin landed on: **{result}**",
            color=Color.gold()
        ).set_thumbnail(
            url="https://i.ibb.co/gwM94r8/coin-heads.png" if result == "Heads"
            else "https://i.ibb.co/ZTHtS5D/coin-tails.png"
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

                    # Check if the API returned a meme
                    if not data or not data.get('url'):
                         await interaction.followup.send("Couldn't get meme data from the API.")
                         return

                    meme_title = data.get('title', 'No Title')
                    meme_image_url = data.get('url')

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
        if interaction.channel_id in self.active_flag_game_channels:
            await interaction.response.send_message("A flag guessing game is already active in this channel!", ephemeral=True)
            return

        self.active_flag_game_channels.add(interaction.channel_id)
        # Use a task to start the game to avoid blocking the interaction response immediately
        # Pass the interaction to the start_round method
        asyncio.create_task(self.start_new_flag_game_from_interaction(interaction))


    # Helper method to start a new flag game from an interaction
    async def start_new_flag_game_from_interaction(self, interaction: discord.Interaction):
        # Check if the interaction has already been responded to or deferred
        if not interaction.response.is_done():
            await interaction.response.defer() # Defer the interaction

        game = FlagGame(interaction.channel, self) # Pass the cog instance
        # Start the round using the original interaction
        await game.start_round(interaction)

    # Helper method to start a new flag game from the Play Again button
    async def start_new_flag_game_from_button(self, channel: discord.TextChannel):
        if channel.id in self.active_flag_game_channels:
             # This check should ideally prevent this, but for safety
             print(f"Attempted to start new game in channel {channel.id} but one is already active.")
             return

        self.active_flag_game_channels.add(channel.id)
        game = FlagGame(channel, self) # Pass the cog instance
        # Since there's no direct interaction to respond to from the button's follow-up,
        # we just generate round data and send a new message.
        game.generate_round_data()

        embed = Embed(
            title="🏳️ Flag Guessing Game",
            description="Guess the country of this flag:",
            color=Color.purple()
        )
        code = COUNTRIES[game.correct_answer].lower()
        embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")

        view = FlagGuessView(game)
        game.message = await channel.send(embed=embed, view=view)


# Setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(FunCommands(bot))
