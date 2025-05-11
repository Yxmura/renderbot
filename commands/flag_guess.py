import discord
from discord import app_commands
import random
import aiohttp
import json
from typing import Dict, List, Optional

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

@app_commands.command(name="flagguess", description="Start a competitive flag guessing game!")
async def flagguess(interaction: discord.Interaction):
    game = FlagGame(interaction.channel)
    game.generate_round()
    
    embed = discord.Embed(
        title="🏳️ Flag Guessing Game",
        description="Guess the country of the flag shown below!",
        color=discord.Color.blue()
    )
    
    country_code = COUNTRIES[game.correct_answer]
    flag_url = f"https://flagcdn.com/w320/{country_code.lower()}.png"
    embed.set_image(url=flag_url)
    
    view = FlagGuessView(game)
    await interaction.response.send_message(embed=embed, view=view)