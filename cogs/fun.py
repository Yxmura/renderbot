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
# Define SUBREDDITS here if you want to use them for the new meme API
SUBREDDITS = ["memes", "dankmemes", "wholesomememes", "funny"]
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

# View for the "Play Again" button for Flag Game
class FlagGamePlayAgainView(ui.View):
    def __init__(self, cog: commands.Cog):
        super().__init__(timeout=300) # Timeout after 5 minutes of inactivity
        self.cog = cog # Keep a reference to the cog to access the game state

    @ui.button(label="Play Again", style=discord.ButtonStyle.green)
    async def play_again_button(self, interaction: discord.Interaction, button: ui.Button):
        # Defer the interaction immediately
        await interaction.response.defer()

        if interaction.channel_id in self.cog.active_flag_game_channels:
             await interaction.followup.send("A flag guessing game is already active in this channel!", ephemeral=True)
             return

        # Stop this view to disable the button
        self.stop()
        try:
            # Try to remove the button from the message it was on
            await interaction.message.edit(view=None)
        except:
            pass # Ignore if the message was deleted

        # Use a task to start the new game to avoid blocking the interaction
        asyncio.create_task(self.cog.start_new_flag_game_from_button(interaction.channel))

# FlagGame for a single round with Play Again button
class FlagGame:
    def __init__(self, channel: discord.TextChannel, cog: "FunCommands"): # Use forward reference
        self.channel = channel
        self.cog = cog # Reference to the cog to access active_flag_game_channels
        self.current_flag = None
        self.options = []
        self.correct_answer = None
        self.answered = False
        self.message: Optional[discord.Message] = None # To store the game message

    def generate_round_data(self):
        self.correct_answer = random.choice(list(COUNTRIES.keys()))

        # Ensure we get 4 unique wrong options
        wrong_options = random.sample(
            [country for country in COUNTRIES.keys() if country != self.correct_answer],
            min(4, len(COUNTRIES) - 1) # Ensure we don't ask for more options than available
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
        code = COUNTRIES.get(self.correct_answer, "").lower() # Use .get for safety
        if code:
            embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")
        else:
            embed.description += "\n\n*(Could not load flag image)*"


        view = FlagGuessView(self) # Pass the game instance to the view
        self.message = await interaction.followup.send(embed=embed, view=view) # Use followup.send after deferring

    async def end_round(self, message_content: str):
        if self.message:
            try:
                # Disable the view on the original game message
                await self.message.edit(view=None)

                # Send a separate message with the game result and the Play Again button
                await self.channel.send(content=message_content, view=FlagGamePlayAgainView(self.cog))

            except Exception as e:
                print(f"Error ending flag game round or sending play again button: {e}")
            finally:
                # Remove the channel from active games when the round ends
                if self.channel.id in self.cog.active_flag_game_channels:
                    self.cog.active_flag_game_channels.remove(self.channel.id)
                # Ensure the game object can be garbage collected
                del self.cog.active_flag_game_channels[self.channel.id] # Use del


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
        # Defer the interaction to prevent timeout issues during processing
        await interaction.response.defer()

        if self.game.answered: # Prevent multiple answers in a single-round game
            await interaction.followup.send("This round has already ended.", ephemeral=True)
            return

        self.game.answered = True # Mark the round as answered

        if interaction.data["custom_id"] == self.game.correct_answer:
            result_message = (
                f"✅ Correct! {interaction.user.mention} got it right!\n"
                f"The flag was from **{self.game.correct_answer}**!\n"
                "Game Over!"
            )
            await interaction.followup.send(
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
            await interaction.followup.send(
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

class RPSGame:
    def __init__(self, player1: discord.Member, player2: Optional[discord.Member], channel: discord.TextChannel, cog: "FunCommands"):
        self.player1 = player1
        self.player2 = player2 # None if playing against bot
        self.channel = channel
        self.cog = cog # Reference to the cog to manage active games
        self.round = 1
        self.player1_score = 0
        self.player2_score = 0 # Bot score is always 0
        self.player1_choice: Optional[str] = None
        self.player2_choice: Optional[str] = None
        self.message: Optional[discord.Message] = None # Message with the buttons
        self.active = True
        self.choices_made_this_round: set[int] = set() # To track who has chosen in the current round

    async def start_game(self, interaction: discord.Interaction):
        self.cog.active_rps_games[self.channel.id] = self # Mark game as active
        await interaction.followup.send("Starting Rock Paper Scissors!", ephemeral=True) # Use followup
        await self.send_round_message()

    async def send_round_message(self):
        if not self.active: return # Don't send if game is inactive

        self.choices_made_this_round.clear() # Clear choices for the new round
        self.player1_choice = None
        self.player2_choice = None

        embed = Embed(
            title=f"🪨📄✂️ Rock Paper Scissors - Round {self.round}/3",
            description=f"Choose your move!\n"
                        f"{self.player1.display_name}: {self.player1_score}\n"
                        f"{self.player2.display_name if self.player2 else 'Bot'}: {self.player2_score}",
            color=Color.blue()
        )
        view = RPSChoiceView(self)
        if self.message:
            try:
                # Edit the previous message if it exists
                self.message = await self.message.edit(embed=embed, view=view)
            except:
                 self.message = await self.channel.send(embed=embed, view=view) # Send new if edit fails
        else:
            self.message = await self.channel.send(embed=embed, view=view)

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        if not self.active: return # Don't handle if game is inactive

        player_id = interaction.user.id

        if player_id == self.player1.id:
            if self.player1_choice is not None:
                 await interaction.response.send_message("You have already made your choice for this round!", ephemeral=True)
                 return
            self.player1_choice = choice
            self.choices_made_this_round.add(player_id)
            await interaction.response.send_message(f"You chose {choice}!", ephemeral=True)
        elif self.player2 and player_id == self.player2.id:
             if self.player2_choice is not None:
                 await interaction.response.send_message("You have already made your choice for this round!", ephemeral=True)
                 return
             self.player2_choice = choice
             self.choices_made_this_round.add(player_id)
             await interaction.response.send_message(f"You chose {choice}!", ephemeral=True)
        else:
            await interaction.response.send_message("You are not a participant in this game!", ephemeral=True)
            return

        await self.check_round_completion()

    async def check_round_completion(self):
        required_choices = 2 if self.player2 else 1 # 2 players or 1 player vs bot
        if len(self.choices_made_this_round) == required_choices:
            await self.resolve_round()

    async def resolve_round(self):
        if not self.active: return # Don't resolve if game is inactive

        # If against bot, bot makes a random choice now that the player has chosen
        if self.player2 is None:
            self.player2_choice = random.choice(CHOICES)

        result = "It's a tie! 🤝"
        winner_mention = None

        if self.player1_choice == self.player2_choice:
            result = "It's a tie! 🤝"
        elif (self.player1_choice == "rock" and self.player2_choice == "scissors") or \
             (self.player1_choice == "paper" and self.player2_choice == "rock") or \
             (self.player1_choice == "scissors" and self.player2_choice == "paper"):
            result = f"{self.player1.display_name} wins this round! 🎉"
            self.player1_score += 1
            winner_mention = self.player1.mention
        else:
            player2_name = self.player2.display_name if self.player2 else 'Bot'
            result = f"{player2_name} wins this round! 😎"
            if self.player2:
                 self.player2_score += 1
                 winner_mention = self.player2.mention
            # No winner_mention for bot

        round_embed = Embed(
            title=f"Round {self.round} Results",
            description=f"{self.player1.display_name}: {self.player1_choice.capitalize()}\n"
                        f"{self.player2.display_name if self.player2 else 'Bot'}: {self.player2_choice.capitalize()}\n"
                        f"{result}",
            color=Color.orange()
        )
        await self.channel.send(embed=round_embed)

        self.round += 1

        if self.round <= 3:
            await self.send_round_message()
        else:
            await self.end_game()

    async def on_timeout(self):
        if self.active: # Only end if the game is still active
             self.active = False # Mark as inactive on timeout
             if self.message:
                 try:
                     await self.message.edit(view=None) # Disable buttons
                 except:
                     pass # Ignore if message was deleted

             timeout_message = "Round timed out!"

             # Determine winner based on score if timeout happens after some rounds
             if self.round > 1:
                 if self.player1_score > self.player2_score:
                     timeout_message += f"\n{self.player1.display_name} wins the game!"
                 elif self.player2_score > self.player1_score:
                     timeout_message += f"\n{self.player2.display_name if self.player2 else 'Bot'} wins the game!"
                 else:
                     timeout_message += "\nThe game is a tie!"

             else: # Timeout in the first round
                  timeout_message = "Rock Paper Scissors game timed out before the first round could complete."


             await self.channel.send(timeout_message)

             if self.channel.id in self.cog.active_rps_games:
                 del self.cog.active_rps_games[self.channel.id] # Mark game as inactive

        self.stop() # Stop this view


class RPSChoiceView(ui.View):
    def __init__(self, game: RPSGame):
        super().__init__(timeout=30) # Timeout for each round
        self.game = game

        for choice in CHOICES:
            button = ui.Button(label=choice.capitalize(), style=discord.ButtonStyle.primary, custom_id=choice)
            button.callback = self.button_callback
            self.add_item(button)

    async def button_callback(self, interaction: discord.Interaction):
        # Defer the interaction
        await interaction.response.defer()

        if not self.game.active:
             await interaction.followup.send("This game has ended.", ephemeral=True)
             return

        # Check if the user is one of the players
        if interaction.user.id != self.game.player1.id and (self.game.player2 is None or interaction.user.id != self.game.player2.id):
             await interaction.followup.send("You are not a participant in this game!", ephemeral=True)
             return

        choice = interaction.data['custom_id']

        await self.game.handle_choice(interaction, choice)


    async def on_timeout(self):
        if self.game.active: # Only handle timeout if game is active
            await self.game.on_timeout() # Call the game's timeout handler
        self.stop() # Stop this view


# View for accepting/declining an RPS challenge
class RPSChallengeView(ui.View):
    def __init__(self, challenger: discord.Member, challenged: discord.Member, cog: "FunCommands"):
        super().__init__(timeout=60) # Timeout for accepting the challenge
        self.challenger = challenger
        self.challenged = challenged
        self.cog = cog # Reference to the cog

    @ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept_challenge(self, interaction: discord.Interaction, button: ui.Button):
        # Defer the interaction
        await interaction.response.defer()

        if interaction.user.id != self.challenged.id:
             await interaction.followup.send("This challenge is not for you!", ephemeral=True)
             return

        if interaction.channel.id in self.cog.active_rps_games and self.cog.active_rps_games[interaction.channel.id].active:
             await interaction.followup.send("A Rock Paper Scissors game is already active in this channel!", ephemeral=True)
             await interaction.message.edit(view=None) # Remove challenge buttons
             self.stop()
             return

        await interaction.followup.send("Challenge accepted! Starting the game...", ephemeral=True)
        try:
            await interaction.message.edit(view=None) # Remove challenge buttons
        except:
            pass # Ignore if message was deleted

        game = RPSGame(self.challenger, self.challenged, interaction.channel, self.cog)
        await game.start_game(interaction) # Use the original interaction for followup

        self.stop() # Stop this view

    @ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline_challenge(self, interaction: discord.Interaction, button: ui.Button):
        # Defer the interaction
        await interaction.response.defer()

        if interaction.user.id != self.challenged.id:
             await interaction.followup.send("This challenge is not for you!", ephemeral=True)
             return

        await interaction.followup.send("Challenge declined.", ephemeral=False)
        try:
             await interaction.message.edit(view=None) # Remove challenge buttons
        except:
            pass # Ignore if message was deleted

        self.stop() # Stop this view

    async def on_timeout(self):
        # Edit the message to show it timed out
        try:
            await self.message.edit(content="RPS challenge timed out.", view=None)
        except:
            pass # Ignore if message was deleted

# Add after Chunk 3

# New Fun Feature: Cat/Dog pictures
class AnimalView(ui.View):
    def __init__(self, animal_type: str, cog: "FunCommands"):
        super().__init__(timeout=60) # Timeout for the view
        self.animal_type = animal_type
        self.cog = cog # Reference to the cog to access aiohttp session

        refresh_button = ui.Button(label=f"More {animal_type.capitalize()}", style=discord.ButtonStyle.primary)
        refresh_button.callback = self.refresh_callback
        self.add_item(refresh_button)

    async def refresh_callback(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer the interaction
        try:
            if self.animal_type == "cat":
                url = "https://api.thecatapi.com/v1/images/search"
            elif self.animal_type == "dog":
                url = "https://api.thedogapi.com/v1/images/search"
            else:
                await interaction.followup.send("Invalid animal type.", ephemeral=True)
                return

            async with aiohttp.ClientSession() as session: # Use a new session for simplicity here
                 async with session.get(url) as resp:
                     if resp.status != 200:
                         await interaction.followup.send(f"Couldn't fetch a {self.animal_type} picture right now.", ephemeral=True)
                         return
                     data = await resp.json()
                     if not data or not data[0].get('url'):
                         await interaction.followup.send(f"Couldn't get {self.animal_type} picture data.", ephemeral=True)
                         return

                     image_url = data[0]['url']

                     embed = Embed(title=f"Random {self.animal_type.capitalize()}!", color=Color.blue())
                     embed.set_image(url=image_url)

                     await interaction.edit_original_response(embed=embed, view=self) # Edit the original message

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None) # Disable the button on timeout
            except:
                pass # Ignore if message was deleted

# Add after all imports and other class definitions (Reminder, FlagGame, RPSGame, Views)

class FunCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_reminders.start()
        # Set to track channels with an active flag game
        self.active_flag_game_channels: set[int] = set()
        self.active_rps_games: Dict[int, RPSGame] = {}
        # Add aiohttp session to the cog for reuse
        self.session: Optional[aiohttp.ClientSession] = None


    async def cog_load(self):
        print("FunCog loading...")
        self.session = aiohttp.ClientSession()

    async def cog_unload(self):
        print("FunCog unloading...")
        self.check_reminders.cancel()
        # Close the aiohttp session
        if self.session:
            await self.session.close()
        # Attempt to end active games gracefully
        for game in list(self.active_rps_games.values()):
             await game.end_game()
        # Flag game ends automatically after one round or timeout

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
            async with self.session.get(JOKE_API_URL, headers=HEADERS) as resp: # Use the cog's session
                if resp.status != 200:
                    await interaction.followup.send("Sorry, I couldn't fetch a dad joke right now.")
                    return
                data = await resp.json()
                joke = data.get("joke")
                await interaction.followup.send(joke)
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

        async with self.session.get("https://api.otakugifs.xyz/gif?reaction=kiss") as resp: # Use the cog's session
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
            api_url = MEME_API_URL

            async with self.session.get(api_url) as resp: # Use the cog's session
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
                meme_subreddit = data.get('subreddit', 'Unknown Subreddit') # Get subreddit if available


                embed = Embed(title=meme_title, color=Color.orange())
                embed.set_image(url=meme_image_url)
                if meme_subreddit != 'Unknown Subreddit':
                    embed.set_footer(text=f"From r/{meme_subreddit}")


                await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"Failed to fetch meme: {e}")

    @app_commands.command(name="rps", description="Play Rock Paper Scissors against the bot or another user.")
    @app_commands.describe(opponent="The user you want to play against (leave blank for bot)")
    async def rps(self, interaction: discord.Interaction, opponent: Optional[discord.Member] = None):
        if interaction.channel_id in self.active_rps_games and self.active_rps_games[interaction.channel_id].active:
             await interaction.response.send_message("A Rock Paper Scissors game is already active in this channel!", ephemeral=True)
             return

        player1 = interaction.user
        player2 = opponent

        if player2 and player2.bot:
             await interaction.response.send_message("You can't play against a bot opponent.", ephemeral=True)
             return

        if player2 and player1.id == player2.id:
             await interaction.response.send_message("You can't play against yourself!", ephemeral=True)
             return

        # Defer the interaction early
        await interaction.response.defer()

        # If against another user, require their confirmation
        if player2:
            confirmation_view = RPSChallengeView(player1, player2, self)
            # Send the challenge message as a followup
            await interaction.followup.send(f"{player2.mention}, {player1.mention} wants to play Rock Paper Scissors against you! Do you accept?", view=confirmation_view)
        else:
            # Start bot game directly
            game = RPSGame(player1, None, interaction.channel, self)
            # Start the game using the original interaction (which was deferred)
            await game.start_game(interaction)


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
        code = COUNTRIES.get(game.correct_answer, "").lower()
        if code:
            embed.set_image(url=f"https://flagcdn.com/w320/{code}.png")
        else:
             embed.description += "\n\n*(Could not load flag image)*"


        view = FlagGuessView(game)
        game.message = await channel.send(embed=embed, view=view)

    @app_commands.command(name="8ball", description="Ask the Magic 8-Ball a question.")
    @app_commands.describe(question="The question you want to ask the 8-Ball")
    async def eightball(self, interaction: discord.Interaction, question: str):
        responses = [
            "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes, definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
            "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Cannot predict now.",
            "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful.", "Better not tell you now.", "Ask again later." # Added missing responses
        ]
        answer = random.choice(responses)

        embed = Embed(
            title="🎱 Magic 8-Ball",
            description=f"**Question:** {question}\n**Answer:** {answer}",
            color=Color.dark_purple()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dice", description="Roll one or more dice.")
    @app_commands.describe(
        number_of_dice="The number of dice to roll (default is 1, max 6)",
        sides="The number of sides on each die (default is 6, max 100)"
    )
    async def dice(
        self,
        interaction: discord.Interaction,
        number_of_dice: app_commands.Range[int, 1, 6] = 1,
        sides: app_commands.Range[int, 1, 100] = 6
    ):
        if number_of_dice < 1 or sides < 1:
            await interaction.response.send_message("Please provide valid numbers for dice and sides.", ephemeral=True)
            return

        results = [random.randint(1, sides) for _ in range(number_of_dice)]
        total = sum(results)

        embed = Embed(
            title="🎲 Dice Roll",
            description=f"Rolling {number_of_dice}d{sides}...",
            color=Color.blue()
        )
        embed.add_field(name="Results", value=", ".join(map(str, results)))
        embed.add_field(name="Total", value=total, inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cat", description="Get a random cat picture!")
    async def cat(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            url = "https://api.thecatapi.com/v1/images/search"
            async with self.session.get(url) as resp: # Use the cog's session
                if resp.status != 200:
                    await interaction.followup.send("Couldn't fetch a cat picture right now.")
                    return
                data = await resp.json()
                if not data or not data[0].get('url'):
                    await interaction.followup.send("Couldn't get cat picture data.")
                    return

                image_url = data[0]['url']

                embed = Embed(title="Random Cat!", color=Color.blue())
                embed.set_image(url=image_url)

                await interaction.followup.send(embed=embed, view=AnimalView("cat", self)) # Add the view

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)

    @app_commands.command(name="dog", description="Get a random dog picture!")
    async def dog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            url = "https://api.thedogapi.com/v1/images/search"
            async with self.session.get(url) as resp: # Use the cog's session
                if resp.status != 200:
                    await interaction.followup.send("Couldn't fetch a dog picture right now.")
                    return
                data = await resp.json()
                if not data or not data[0].get('url'):
                    await interaction.followup.send("Couldn't get dog picture data.")
                    return

                image_url = data[0]['url']

                embed = Embed(title="Random Dog!", color=Color.blue())
                embed.set_image(url=image_url)

                await interaction.followup.send(embed=embed, view=AnimalView("dog", self)) # Add the view

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)