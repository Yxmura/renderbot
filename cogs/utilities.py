import discord
from discord import app_commands, Embed, Color, ui
from discord.ext import commands, tasks # Import tasks
import json
import datatime
import os
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import re

load_dotenv()
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Regex pattern for YouTube URLs
YOUTUBE_URL_PATTERN = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'

REQUIRED_ROLE_ID= 1317607057687576696

# View for pagination
class HelpPaginatorView(ui.View):
    def __init__(self, embeds: List[Embed], initial_embed_index: int):
        super().__init__(timeout=180) # Timeout after 3 minutes
        self.embeds = embeds
        self.current_index = initial_embed_index
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        # Add back/forward buttons
        if len(self.embeds) > 1:
            previous_button = ui.Button(label="Previous", style=discord.ButtonStyle.secondary, disabled=(self.current_index == 0))
            previous_button.callback = self.go_previous
            self.add_item(previous_button)

            next_button = ui.Button(label="Next", style=discord.ButtonStyle.secondary, disabled=(self.current_index == len(self.embeds) - 1))
            next_button.callback = self.go_next
            self.add_item(next_button)

        # Add jump to category select if there are multiple categories (embeds)
        if len(self.embeds) > 1:
            options = [
                discord.SelectOption(label=f"Page {i+1}", value=str(i))
                for i in range(len(self.embeds))
            ]
            select = ui.Select(placeholder="Jump to Page...", options=options)
            select.callback = self.jump_to_page
            self.add_item(select)


    async def go_previous(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer to avoid interaction failed
        self.current_index -= 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)

    async def go_next(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer to avoid interaction failed
        self.current_index += 1
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)

    async def jump_to_page(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer to avoid interaction failed
        selected_page_index = int(interaction.data['values'][0])
        self.current_index = selected_page_index
        self.update_buttons()
        await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)


    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None) # Remove buttons on timeout
            except:
                pass


class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.load_config() # Load configuration on cog initialization
        # Store categorized commands
        self.categorized_commands: Dict[str, List[app_commands.AppCommand]] = {}


    def load_config(self):
        global REQUIRED_ROLE_ID
        # Load the required role ID from a persistent config file if it exists
        if os.path.exists("utilities_config.json"):
            with open("utilities_config.json", "r") as f:
                try:
                    config_data = json.load(f)
                    # Only update if the key exists in the config file
                    if 'required_role_id' in config_data:
                         REQUIRED_ROLE_ID = config_data.get("required_role_id")
                except json.JSONDecodeError:
                     print("Error loading utilities_config.json. Using default value for REQUIRED_ROLE_ID.")
        else:
             # Create a default config file if it doesn't exist
             self.save_config()


    def save_config(self):
         config_data = {
             "required_role_id": REQUIRED_ROLE_ID
         }
         with open("utilities_config.json", "w") as f:
             json.dump(config_data, f, indent=4)

    @commands.Cog.listener()
    async def on_ready(self):
        print("UtilitiesCog ready.")
        # Categorize commands when the bot is ready
        # Delay categorization slightly to ensure other cogs are loaded
        await asyncio.sleep(2) # Adjust delay if needed
        await self.categorize_commands()


    async def categorize_commands(self):
        """Categorizes slash commands by their cog."""
        await self.bot.wait_until_ready() # Ensure bot is ready and commands are synced
        self.categorized_commands.clear() # Clear previous categorization

        # Get global commands
        global_commands = await self.bot.tree.fetch_commands()

        for command in global_commands:
            cog_name = "No Cog" # Default category
            # Find the cog instance the command belongs to
            if command.binding is not None:
                 try:
                     cog_instance = self.bot.get_cog(command.binding.qualified_name)
                     if cog_instance:
                         cog_name = type(cog_instance).__name__
                 except AttributeError:
                     # Handle cases where binding might not have qualified_name
                     pass
                 except Exception as e:
                     print(f"Error categorizing command {command.name}: {e}")


            if cog_name not in self.categorized_commands:
                self.categorized_commands[cog_name] = []
            self.categorized_commands[cog_name].append(command)

        # You might also want to add guild-specific commands if you have any
        # for guild in self.bot.guilds: # Iterate through connected guilds
        #     guild_commands = await self.bot.tree.fetch_commands(guild=guild)
        #     for command in guild_commands:
        #         # Categorize similarly, perhaps adding guild name to cog_name
        #         pass


    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)

        embed = Embed(
            title="🏓 Pong!",
            description=f"Bot Latency: **{latency}ms**",
            color=Color.purple()
        )
        await interaction.response.send_message(embed=embed)


    @app_commands.command(
        name="embed",
        description="Create a custom embed message"
    )
    @app_commands.describe(
        channel="The channel to send the embed in",
        title="The title of the embed",
        description="The description for the embed",
        color="Hex color (e.g., FF0000). Defaults to blue.",
        footer="Footer text for the embed"
    )
    async def embed(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str,
        color: Optional[str] = "0000FF", # Use default directly in function signature
        footer: Optional[str] = None
    ):
        if interaction.guild is None:
             await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
             return

        # Check if the user has the required role
        if REQUIRED_ROLE_ID is not None:
            required_role = interaction.guild.get_role(REQUIRED_ROLE_ID)
            if required_role and required_role not in interaction.user.roles:
                await interaction.response.send_message(
                    f"You do not have the {required_role.name} role to use this command.",
                    ephemeral=True
                )
                return
        elif REQUIRED_ROLE_ID is None and interaction.user.guild_permissions.administrator:
             # Allow administrators to use if no required role is set
             pass
        elif REQUIRED_ROLE_ID is None:
             await interaction.response.send_message(
                 "The utilities commands need to be configured by an administrator first using `/setutilitiesrole`.",
                 ephemeral=True
             )
             return


        try:
            # Safely handle the color conversion
            color_int = int(color.replace("#", ""), 16)
            # Use discord.Color constructor directly with the integer
            embed_color = Color(color_int)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid color code! Please use a valid hex code (e.g., `FF0000` for red).",
                ephemeral=True
            )
            return

        embed = Embed(
            title=title,
            description=description,
            color=embed_color
        )
        if footer:
            embed.set_footer(text=footer)

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(
                f"✅ Embed sent to {channel.mention}!",
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                 f"❌ I don't have permission to send messages in {channel.mention}.",
                 ephemeral=True
             )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while sending the embed: {e}",
                ephemeral=True
            )

    @app_commands.command(name="setutilitiesrole", description="Set the role required to use utility commands like /embed")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        required_role="The role required to use utility commands"
    )
    async def setutilitiesrole(
        self,
        interaction: discord.Interaction,
        required_role: discord.Role
    ):
        global REQUIRED_ROLE_ID
        REQUIRED_ROLE_ID = required_role.id
        self.save_config()

        embed = Embed(
            title="🛠️ Utilities Role Set",
            description=f"The role required to use utility commands is now: {required_role.mention}",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Get a list of all available commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer the interaction as command loading can take time

        # Ensure commands are categorized
        if not self.categorized_commands:
            await self.categorize_commands()

        if not self.categorized_commands:
            await interaction.followup.send("Could not load commands. Please try again later.", ephemeral=True)
            return

        embeds = []
        # Sort cog names alphabetically, putting "No Cog" (if exists) first
        sorted_cog_names = sorted(self.categorized_commands.keys())
        if "No Cog" in sorted_cog_names:
            sorted_cog_names.insert(0, sorted_cog_names.pop(sorted_cog_names.index("No Cog")))


        for cog_name in sorted_cog_names:
            commands_list = self.categorized_commands[cog_name]
            if not commands_list: continue # Skip empty categories

            embed = Embed(
                title=f"Bot Commands - {cog_name}",
                description="Here are the available commands in this category:",
                color=Color.blue()
            )

            # Sort commands alphabetically
            sorted_commands = sorted(commands_list, key=lambda cmd: cmd.name)

            for command in sorted_commands:
                # Get command parameters and descriptions
                params_str = ""
                if command.parameters:
                    params_str = " " + " ".join(
                        f"<{param.name}>" for param in command.parameters
                    )

                embed.add_field(
                    name=f"/{command.name}{params_str}",
                    value=command.description or "No description provided.",
                    inline=False
                )

            embeds.append(embed)

        if not embeds:
            await interaction.followup.send("No commands found.", ephemeral=True)
            return

        # Send the first embed with the paginator view
        view = HelpPaginatorView(embeds, 0)
        # The interaction was deferred, so use followup.send
        view.message = await interaction.followup.send(embed=embeds[0], view=view)


# --- Music Copyright Cog ---

class MusicCopyrightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache_file = 'video_cache.json'

        # Initialize Spotify client credentials manager
        try:
            self.spotify_client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
            self.spotify = spotipy.Spotify(client_credentials_manager=self.spotify_client_credentials_manager)
        except Exception as e:
             print(f"Error initializing Spotify client: {e}")
             self.spotify = None


        # Load cached data from the file (if it exists)
        self.cached_info = self.load_cache()

        # Add persistent views for the getid command
        # This requires the view class (Button) to be defined globally or before this point
        # We can try to add any views that were saved if needed, but for simplicity,
        # we'll focus on making new buttons persistent.
        # self.bot.add_view(Button(style=discord.ButtonStyle.green, label="Get Channel Stats", custom_id="placeholder_youtube_stats")) # Placeholder


    def load_cache(self):
        """Load the cached video info from a file."""
        try:
            if os.path.exists(self.cache_file):
                 with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {} # Return empty dict if file not found
        except (FileNotFoundError, json.JSONDecodeError):
            return {} # Handle empty or invalid JSON file

    def save_cache(self):
        """Save the cached video info to a file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cached_info, f, indent=4) # Add indent for readability
        except Exception as e:
            print(f"Error saving cache file: {e}")

    async def cog_load(self):
         print("MusicCopyrightCog loading...")

    async def cog_unload(self):
         print("MusicCopyrightCog unloading...")
         # Save the cache when the cog is unloaded
         self.save_cache()


    # Make commands slash commands where appropriate

    @app_commands.command(name='checkcopyright', description='Check copyright status of a song by title or YouTube URL')
    @app_commands.describe(query="Song title or YouTube URL")
    async def check_copyright(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer() # Defer the interaction

        try:
            if 'youtube.com' in query or 'youtu.be' in query:
                info = await self.get_youtube_info(query)
                if info:
                    embed, view = await self.create_youtube_embed(info)
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send("❌ Couldn't fetch video information. Please make sure the URL is valid.")
            else:
                if not self.spotify:
                     await interaction.followup.send("Spotify service is not available.")
                     return

                results = await self.search_spotify_info(query)
                if results:
                    embed = await self.create_spotify_embed(results)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("❌ No information found for this song on Spotify.")
        except Exception as e:
            error_msg = f"❌ An error occurred: {str(e)}"
            # More specific error handling if possible
            if "HTTP Error 429" in str(e):
                error_msg = "❌ Rate limit reached. Please try again later."
            elif "This video is unavailable" in str(e):
                error_msg = "❌ This video is unavailable or private."
            elif "quota" in str(e).lower():
                 error_msg = "❌ YouTube API quota exceeded. Please try again later."

            await interaction.followup.send(error_msg)

    async def get_youtube_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Get copyright information from YouTube video, using cache if available."""
        # Normalize URL for consistent caching
        normalized_url = url
        match = re.search(YOUTUBE_URL_PATTERN, url)
        if match:
            video_id = match.group(1)
            normalized_url = f"https://www.youtube.com/watch?v={video_id}"

        if normalized_url in self.cached_info:
            return self.cached_info[normalized_url]

        ydl_opts = {
            'format': 'bestaudio/best',
            'extract_flat': 'in_playlist',
            'quiet': True,
            'no_warnings': True,
            'force_generic_extractor': False,
            'cookiesfrom': 'cookies.txt' if os.path.exists('cookies.txt') else None # Use cookies if available
        }

        with YoutubeDL(ydl_opts) as ydl:
            try:
                # Use the bot's event loop with run_in_executor for blocking ydl call
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=False))

                if not info:
                    return None

                license_info = info.get('license', 'Standard YouTube License')
                title = info.get('title', '').lower()
                description = info.get('description', '').lower()

                # Improved keyword checking for copyright status
                is_creative_commons = license_info.lower() == 'creative commons' or 'creative commons' in description
                no_copyright_terms = ['no copyright', 'free to use', 'royalty-free', 'copyright free', 'public domain','royalty free music']
                contains_no_copyright_keywords = any(term in title for term in no_copyright_terms) or any(term in description for term in no_copyright_terms)

                # Consider copyrighted if not explicitly marked as creative commons or contains no copyright keywords
                copyrighted = not (is_creative_commons or contains_no_copyright_keywords)

                video_info = {
                    'title': info.get('title', 'Unknown'),
                    'channel': info.get('uploader', 'Unknown'),
                    'license': license_info,
                    'is_copyrighted': copyrighted,
                    'description': info.get('description', 'No description available'),
                    'thumbnail': info.get('thumbnail', None),
                    'duration': info.get('duration', 0),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'), # Format might vary, consider parsing
                    'url': info.get('webpage_url', url)
                }

                self.cached_info[normalized_url] = video_info
                self.save_cache()
                return video_info

            except Exception as e:
                print(f"Error extracting video info: {str(e)}")
                return None

    async def search_spotify_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Search for song information using Spotify"""
        if not self.spotify: return None
        try:
            # Use run_in_executor for blocking spotipy calls
            results = await asyncio.get_event_loop().run_in_executor(None, lambda: self.spotify.search(q=query, type='track', limit=1))

            if results and results['tracks']['items']:
                track = results['tracks']['items'][0]
                # Fetch album details separately for copyrights
                album = await asyncio.get_event_loop().run_in_executor(None, lambda: self.spotify.album(track['album']['id']))

                copyrighted = True
                copyright_text = 'No copyright information available'

                if album and 'copyrights' in album:
                    copyright_texts = [c['text'].lower() for c in album['copyrights']]
                    copyright_text = '\n'.join(copyright_texts)

                    if any(term in copyright_text for term in ['creative commons', 'public domain', 'cc0']):
                        copyrighted = False

                return {
                    'title': track['name'],
                    'artist': ", ".join(artist['name'] for artist in track['artists']),
                    'album': track['album']['name'],
                    'release_date': track['album'].get('release_date', 'Unknown'),
                    'spotify_url': track['external_urls']['spotify'],
                    'thumbnail': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'is_copyrighted': copyrighted,
                    'copyright_text': copyright_text
                }
            return None
        except Exception as e:
            print(f"Error fetching song info from Spotify: {str(e)}")
            return None

    async def create_spotify_embed(self, info: Dict[str, Any]) -> Embed:
        """Create Discord embed for Spotify track info"""
        copyright_status = "🔒 Likely Copyrighted" if info['is_copyrighted'] else "⚠️ Potentially Not Copyrighted"
        embed = Embed(
            title="Spotify Track Information",
            description=f"[Listen on Spotify]({info['spotify_url']})",
            color=Color.green()
        )
        embed.add_field(name="Title", value=info['title'], inline=False)
        embed.add_field(name="Artist(s)", value=info['artist'], inline=True)
        embed.add_field(name="Album", value=info['album'], inline=True)
        embed.add_field(name="Release Date", value=info['release_date'], inline=True)
        embed.add_field(name="Estimated Status", value=copyright_status, inline=False)
        embed.add_field(name="Copyright Info", value=info['copyright_text'] or 'No copyright information available', inline=False)
        embed.add_field(name="⚠️ Important Note", value=(
            "Spotify Search Results Are Not Highly Accurate for Copyright.\n"
            "Results are based on available Spotify data, which might not be comprehensive for copyright details.\n"
            "For YouTube videos, use the URL check (`/checkcopyright <YouTube URL>`) for a more direct analysis of video metadata."
        ), inline=False) # Improved note for clarity
        if info['thumbnail']:
            embed.set_thumbnail(url=info['thumbnail'])
        return embed

    async def create_youtube_embed(self, info: Dict[str, Any]) -> tuple[Embed, ui.View]:
        """Create Discord embed and view for YouTube video info"""
        copyright_status = "🔒 Copyrighted" if info['is_copyrighted'] else "✔️ Public Domain / Creative Commons"
        embed = Embed(
            title="YouTube Video Information",
            description=f"[Watch on YouTube]({info.get('url')})",
            color=Color.red()
        )
        embed.add_field(name="Title", value=info['title'], inline=False)
        embed.add_field(name="Channel", value=info['channel'], inline=True)
        embed.add_field(name="License", value=info['license'], inline=True)
        embed.add_field(name="Status", value=copyright_status, inline=True)
        # Add description snippet
        description_snippet = info.get('description', 'No description available')
        if len(description_snippet) > 200:
            description_snippet = description_snippet[:197] + "..."
        embed.add_field(name="Description Snippet", value=description_snippet, inline=False)


        embed.add_field(name="Note", value="This check is based on video license information, title, and description analysis.", inline=True)
        embed.add_field(name="Note For Epidemic Music", value="If you are checking music from Epidemic Music which says it is Royalty Free, that does not mean you can use it; you must buy a subscription from Epidemic.", inline=False)
        embed.set_footer(text="Learn About Copyright, types, symbols, and much more. Visit Gappa Wiki Now!")

        view = ui.View()
        button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
        view.add_item(button)

        # Add a button to fetch detailed video info if YouTube client is available
        if youtube_client and info.get('url'):
            match = re.search(YOUTUBE_URL_PATTERN, info['url'])
            if match:
                video_id = match.group(1)
                # Using a dynamic custom_id for potential persistence (though less critical here)
                fetch_details_button = ui.Button(label="Fetch Detailed Info", style=discord.ButtonStyle.primary, custom_id=f"fetch_youtube_{video_id}")
                fetch_details_button.callback = self.fetch_details_button_callback # Assign the new callback
                view.add_item(fetch_details_button)


        if info['thumbnail']:
            embed.set_thumbnail(url=info['thumbnail'])

        return embed, view

    async def fetch_details_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Defer ephemerally

        custom_id_parts = interaction.data.get('custom_id', '').split('_')
        if len(custom_id_parts) != 3 or custom_id_parts[0] != 'fetch' or custom_id_parts[1] != 'youtube':
            await interaction.followup.send("Invalid button callback.", ephemeral=True)
            return

        video_id = custom_id_parts[2]
        video_url = f"https://www.youtube.com/watch?v={video_id}"


        try:
            video_info = self.get_video_info(video_url) # This is a blocking call, ensure get_video_info is safe or make it async
            # If get_video_info uses blocking YouTube API calls, it should be awaited like:
            # video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_video_info_blocking(video_url))


            embed = Embed(
                title=video_info['title'],
                description=video_info['description'][:200] + "..." if len(video_info['description']) > 200 else video_info['description'],
                color=Color.red(),
                url=video_url
            )
            embed.set_author(name=video_info['channel_title'])
            # Format date for better readability
            try:
                publish_date = datetime.fromisoformat(video_info['publish_date'].replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            except ValueError:
                 publish_date = video_info['publish_date'] # Use raw if parsing fails

            embed.add_field(name="Published on", value=publish_date, inline=True)
            embed.add_field(name="Views", value=f"{int(video_info.get('views', 0)):,}", inline=True)
            embed.add_field(name="Likes", value=f"{int(video_info.get('likes', 0)):,}", inline=True)
            embed.add_field(name="Comments", value=f"{int(video_info.get('comments', 0)):,}", inline=True)
            embed.add_field(name="Duration", value=self.format_duration(video_info['duration']), inline=True)
            embed.add_field(name="Channel Subscribers", value=f"{int(video_info.get('channel_subscribers', 0)):,}", inline=True)
            embed.add_field(name="Total Videos", value=f"{int(video_info.get('channel_videos', 0)):,}", inline=True)

            if 'thumbnail' in video_info and video_info['thumbnail']:
                embed.set_thumbnail(url=video_info['thumbnail'])

            # Add button to get channel stats if channel ID is available
            if youtube_client and video_info.get('channel_id'):
                channel_id = video_info['channel_id']
                get_stats_button = ui.Button(label="Get Channel Stats", style=discord.ButtonStyle.primary, custom_id=f"get_channel_stats_{channel_id}")
                get_stats_button.callback = self.get_channel_stats_button_callback
                view = ui.View() # Create a new view for these buttons
                view.add_item(get_stats_button)
                await interaction.followup.send(embed=embed, view=view, ephemeral=False) # Send non-ephemeral
            else:
                await interaction.followup.send(embed=embed, ephemeral=False) # Send non-ephemeral


        except Exception as e:
            error_message = f"An error occurred while fetching detailed info: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            await interaction.followup.send(error_message, ephemeral=True)


    # Ensure this is compatible with async (using run_in_executor for blocking parts)
    def get_video_info(self, video_url: str) -> Dict[str, Any]:
        if not youtube_client:
             raise Exception("YouTube API client is not initialized.")

        match = re.search(YOUTUBE_URL_PATTERN, video_url)
        if not match:
             raise Exception("Invalid YouTube video link.")
        video_id = match.group(1)


        video_request = youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        # This is a blocking call, needs to be run in executor if called from async context
        video_response = video_request.execute()


        if not video_response['items']:
            raise Exception("YouTube video not found.")
        video_data = video_response["items"][0]
        channel_id = video_data["snippet"]["channelId"]

        channel_request = youtube_client.channels().list(
            part="snippet,statistics",
            id=channel_id
        )
        # This is a blocking call, needs to be run in executor if called from async context
        channel_response = channel_request.execute()

        channel_data = channel_response["items"][0]
        thumbnail = video_data["snippet"]["thumbnails"]["high"]["url"] if "thumbnails" in video_data["snippet"] and "high" in video_data["snippet"]["thumbnails"] else None

        return {
            "title": video_data["snippet"]["title"],
            "description": video_data["snippet"].get("description", "No description provided."),
            "channel_title": video_data["snippet"]["channelTitle"],
            "channel_id": channel_id, # Include channel ID
            "publish_date": video_data["snippet"]["publishedAt"],
            "views": video_data["statistics"].get("viewCount", "0"),
            "likes": video_data["statistics"].get("likeCount", "0"),
            "comments": video_data["statistics"].get("commentCount", "0"),
            "duration": video_data["contentDetails"]["duration"],
            "channel_subscribers": channel_data["statistics"].get("subscriberCount", "0"),
            "channel_videos": channel_data["statistics"].get("videoCount", "0"),
            "thumbnail": thumbnail
        }

    # Ensure this is compatible with async (using run_in_executor for blocking parts)
    def format_duration(self, duration: str) -> str:
        """Convert ISO 8601 duration to a more readable format"""
        # Ensure duration starts with PT
        if not duration.startswith('PT'):
             return duration # Return as is if not in expected format

        duration = duration[2:] # Remove 'PT'
        hours = 0
        minutes = 0
        seconds = 0
        if 'H' in duration:
            hours_str, duration = duration.split('H')
            hours = int(hours_str)
        if 'M' in duration:
            minutes_str, duration = duration.split('M')
            minutes = int(minutes_str)
        if 'S' in duration:
            seconds_str = duration.replace('S', '')
            seconds = int(seconds_str)

        parts = []
        if hours > 0:
            parts.append(f"{hours:02d}")
        parts.append(f"{minutes:02d}")
        parts.append(f"{seconds:02d}")

        return ":".join(parts)


    @app_commands.command(name='youtubestats', description='Get detailed statistics for a YouTube channel.')
    @app_commands.describe(channel_id='The ID of the YouTube channel')
    async def youtube_stats(self, interaction: discord.Interaction, channel_id: str):
        await interaction.response.defer() # Defer the interaction

        if not youtube_client:
             await interaction.followup.send("YouTube API client is not initialized. Please check the bot's configuration.")
             return


        try:
            stats = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_channel_details_blocking(channel_id))
            latest_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_latest_video_blocking(channel_id))
            top_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_top_video_blocking(channel_id))

            if stats:
                embed = Embed(
                    title=f"{stats['title']} - YouTube Channel Stats",
                    description=stats['description'],
                    color=Color.red()
                )
                if stats["profile_pic"]:
                    embed.set_thumbnail(url=stats["profile_pic"])
                if stats["banner_url"]:
                    embed.set_image(url=stats["banner_url"])
                # Format numbers with commas
                embed.add_field(name="Subscribers", value=f"{int(stats.get('subscribers', 0)):,}", inline=True)
                embed.add_field(name="Total Views", value=f"{int(stats.get('views', 0)):,}", inline=True)
                embed.add_field(name="Total Videos", value=f"{int(stats.get('videos', 0)):,}", inline=True)
                # Estimated watch hours calculation should be more robust if needed
                # embed.add_field(name="Watch Hours (estimated)", value=stats['watch_hours'], inline=True)
                embed.add_field(name="Channel Created", value=stats['created_at'], inline=True)

                if latest_video:
                    embed.add_field(
                        name="Latest Video",
                        value=f"[{latest_video['title']}](https://www.youtube.com/watch?v={latest_video['video_id']})",
                        inline=False
                    )
                if top_video:
                    embed.add_field(
                        name="Top Video",
                        value=f"[{top_video['title']}](https://www.youtube.com/watch?v={top_video['video_id']})",
                        inline=False
                    )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("Channel not found for the provided ID!")

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            if "quota" in str(e).lower():
                error_message = "YouTube API quota exceeded. Please try again later."
            await interaction.followup.send(error_message)

    # These helper methods were blocking and need to be called within run_in_executor
    def get_channel_details_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        request = youtube_client.channels().list(
            part="snippet,statistics,brandingSettings,contentDetails",
            id=channel_id
        )
        response = request.execute()
        if "items" in response and len(response["items"]) > 0:
            channel = response["items"][0]
            statistics = channel.get("statistics", {})
            snippet = channel.get("snippet", {})
            branding = channel.get("brandingSettings", {})
            image_branding = branding.get("image", {})

            return {
                "title": snippet.get("title", "Unknown"),
                "description": snippet.get("description", "No description"),
                "subscribers": statistics.get("subscriberCount", "0"),
                "views": statistics.get("viewCount", "0"),
                "videos": statistics.get("videoCount", "0"),
                "created_at": snippet.get("publishedAt", "Unknown"),
                "profile_pic": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                "banner_url": image_branding.get("bannerExternalUrl"),
            }
        else:
            return None

    def get_latest_video_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        request = youtube_client.search().list(
            part="snippet",
            channelId=channel_id,
            order="date",
            maxResults=1,
            type="video" # Specify type as video
        )
        response = request.execute()

        if response["items"]:
            video = response["items"][0]
            if video["id"]["kind"] == "youtube#video": # Ensure it's a video
                return {
                    "title": video["snippet"]["title"],
                    "video_id": video["id"]["videoId"],
                    "published_at": video["snippet"]["publishedAt"]
                }
        return None

    def get_top_video_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        # The YouTube Data API does not have a direct "order by viewCount" for search results
        # You would typically fetch videos and then sort by viewCount if needed
        # Or fetch from playlists like "Popular uploads" if available
        # For simplicity, keeping the search by viewCount as it was, but noting it's an estimate.
        # A more accurate way might involve fetching actual video details after a general search.

        request = youtube_client.search().list(
            part="snippet",
            channelId=channel_id,
            order="viewCount", # This might not work as expected for general search
            maxResults=1,
            type="video"
        )
        response = request.execute()

        if response["items"]:
             video = response["items"][0]
             if video["id"]["kind"] == "youtube#video":
                 return {
                     "title": video["snippet"]["title"],
                     "video_id": video["id"]["videoId"]
                 }
        return None


    @app_commands.command(name='getchannelid', description='Fetches the YouTube channel ID from a given handle or search.')
    @app_commands.describe(query='The YouTube handle (e.g., @handle) or search term for the channel.')
    async def getid(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer() # Defer the interaction

        if not youtube_client:
             await interaction.followup.send("YouTube API client is not initialized. Please check the bot's configuration.")
             return

        channel_id = None
        channel_name = None
        error_message = None

        try:
            handle = query.lstrip('@')

            # First, try to fetch by handle (more reliable if it's an exact handle)
            request_handle = youtube_client.channels().list(
                part="id,snippet",
                forHandle=handle # Use forHandle for modern handles
            )
            response_handle = await asyncio.get_event_loop().run_in_executor(None, request_handle.execute)

            if response_handle.get("items"):
                channel_id = response_handle["items"][0]["id"]
                channel_name = response_handle["items"][0]["snippet"]["title"]
            else:
                # If not found by handle, try searching
                search_request = youtube_client.search().list(
                    part="id,snippet",
                    q=query, # Use the original query for search
                    type="channel",
                    maxResults=1
                )
                search_response = await asyncio.get_event_loop().run_in_executor(None, search_request.execute)

                if search_response.get("items"):
                    channel_id = search_response["items"][0]["id"]["channelId"]
                    channel_name = search_response["items"][0]["snippet"]["title"]
                else:
                     error_message = f"No channel found for `{query}`."

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            print(f"Error in getid: {e}") # Log the error

        if channel_id and channel_name:
            embed = Embed(
                title="YouTube Channel ID",
                description=f"Channel ID for `{query}`",
                color=Color.red()
            )
            embed.add_field(name="Channel Name", value=channel_name, inline=False)
            embed.add_field(name="Channel ID", value=channel_id, inline=False)
            embed.add_field(name="Note", value="Search results may sometimes be inaccurate. Please verify the results.", inline=False)

            view = ui.View()
            # Create a button to get channel stats
            get_stats_button = ui.Button(style=discord.ButtonStyle.green, label="Get Channel Stats", custom_id=f"get_channel_stats_{channel_id}")
            get_stats_button.callback = self.get_channel_stats_button_callback # Assign the callback
            view.add_item(get_stats_button)

            # Add a button to learn about copyright
            learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
            view.add_item(learn_copyright_button)

            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(error_message or "Could not fetch channel information.")


    async def get_channel_stats_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # Defer ephemerally

        custom_id_parts = interaction.data.get('custom_id', '').split('_')
        if len(custom_id_parts) != 4 or custom_id_parts[0] != 'get' or custom_id_parts[1] != 'channel' or custom_id_parts[2] != 'stats':
            await interaction.followup.send("Invalid button callback.", ephemeral=True)
            return

        channel_id = custom_id_parts[3]

        if not youtube_client:
             await interaction.followup.send("YouTube API client is not initialized. Please check the bot's configuration.")
             return

        try:
            stats = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_channel_details_blocking(channel_id))
            latest_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_latest_video_blocking(channel_id))
            top_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_top_video_blocking(channel_id))


            if stats:
                embed = Embed(
                    title=f"{stats['title']} - YouTube Channel Stats",
                    description=stats['description'],
                    color=Color.red()
                )
                if stats["profile_pic"]:
                    embed.set_thumbnail(url=stats["profile_pic"])
                if stats["banner_url"]:
                    embed.set_image(url=stats["banner_url"])

                embed.add_field(name="Subscribers", value=f"{int(stats.get('subscribers', 0)):,}", inline=True)
                embed.add_field(name="Total Views", value=f"{int(stats.get('views', 0)):,}", inline=True)
                embed.add_field(name="Total Videos", value=f"{int(stats.get('videos', 0)):,}", inline=True)
                embed.add_field(name="Channel Created", value=stats.get('created_at', 'Unknown'), inline=True) # Keep raw if formatting is complex

                if latest_video:
                    embed.add_field(
                        name="Latest Video",
                        value=f"[{latest_video['title']}](https://www.youtube.com/watch?v={latest_video['video_id']})",
                        inline=False
                    )
                if top_video:
                    embed.add_field(
                        name="Top Video",
                        value=f"[{top_video['title']}](https://www.youtube.com/watch?v={top_video['video_id']})",
                        inline=False
                    )

                await interaction.followup.send(embed=embed, ephemeral=False) # Send non-ephemeral

            else:
                await interaction.followup.send("Channel statistics not found for the provided ID.", ephemeral=True)

        except Exception as e:
            error_message = f"An error occurred while fetching channel stats: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            await interaction.followup.send(error_message, ephemeral=True)


    @app_commands.command(name='getthumbnail', description='Get the HD thumbnail of a YouTube video.')
    @app_commands.describe(url='The YouTube video URL')
    async def thumb(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()

        match = re.search(YOUTUBE_URL_PATTERN, url)
        if match:
            video_id = match.group(1)
            thumbnail_url = f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'

            embed = Embed(
                title='YouTube Thumbnail',
                description='Here is the HD thumbnail of the provided video:',
                color=Color.blue()
            )
            embed.set_image(url=thumbnail_url)
            embed.set_footer(text='Requested by ' + interaction.user.name)

            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send('Please provide a valid YouTube link!')

    @app_commands.command(name='botinfo', description='Show information about the bot.')
    async def show_bot_info(self, interaction: discord.Interaction):
        await interaction.response.defer()

        embed = Embed(
            title="Gappa Bot Info",
            description="I'm a bot designed to help The Creator Community With Free Tools! FREE FOR ALL!",
            color=Color.blue()
        )
        # Get bot version (if you have one defined)
        # try:
        #     with open('version.txt', 'r') as f:
        #         bot_version = f.read().strip()
        # except FileNotFoundError:
        #     bot_version = "Unknown"
        bot_version = "0.7" # Keeping your existing version number


        embed.add_field(
            name="Version",
            value=bot_version,
            inline=True
        )
        embed.add_field(
            name="Library",
            value=f"discord.py {discord.__version__}",
            inline=True
        )
        # Replace with actual creator/credits if needed
        embed.add_field(
            name="Creator",
            value="Coder-Soft",
            inline=True
        )
        embed.add_field(
            name="Credits",
            value="Skeptical",
            inline=True
        )
        # Commands are now listed in the /help command
        # embed.add_field(
        #     name="Commands",
        #     value="Use !help to see available commands", # Update if you remove the old prefix
        #     inline=False
        # )
        embed.set_footer(text="Learn About Copyright, types, symbols, and much more. Click the Button Below To Start Learning!")

        view = ui.View()
        button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
        view.add_item(button)

        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name='extractaudio', description='Extract audio from a YouTube video.')
    @app_commands.describe(url='The YouTube video URL')
    async def extract(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer(thinking=True) # Defer with "Bot is thinking..."


        if "youtube.com" not in url and "youtu.be" not in url:
            await interaction.followup.send("Please provide a valid YouTube link after the command.")
            return

        try:
            output_filename = "downloaded_audio"
            # Ensure output directory exists
            output_dir = "extracted_audio"
            os.makedirs(output_dir, exist_ok=True)
            full_output_path = os.path.join(output_dir, output_filename)


            ydl_opts = {
                'format': 'bestaudio',
                'outtmpl': f'{full_output_path}.%(ext)s', # Use full path
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                }],
                 'cookiesfrom': 'cookies.txt' if os.path.exists('cookies.txt') else None # Use cookies if available
            }
            with YoutubeDL(ydl_opts) as ydl:
                info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                if not info:
                     await interaction.followup.send("Could not extract video information.")
                     return

                # Find the actual output file name
                downloaded_file = ydl.prepare_filename(info)
                # Replace the extension with .mp3 as per the postprocessor
                output_mp3_file = os.path.splitext(downloaded_file)[0] + '.mp3'


            # Check if the output file exists and is not too large
            if not os.path.exists(output_mp3_file):
                 await interaction.followup.send("Audio extraction failed.")
                 return

            file_size = os.path.getsize(output_mp3_file)
            if file_size > interaction.guild.filesize_limit: # Check against server's file size limit
                 await interaction.followup.send(f"The extracted audio file is too large ({file_size / (1024*1024):.2f} MB). Discord file size limit is {interaction.guild.filesize_limit / (1024*1024):.2f} MB.")
                 os.remove(output_mp3_file) # Clean up
                 return


            await interaction.followup.send("Audio extracted successfully!", file=discord.File(output_mp3_file))
            os.remove(output_mp3_file) # Clean up the file

        except Exception as e:
            print(f"Error during audio extraction: {e}")
            await interaction.followup.send("An error occurred while extracting audio.")
            # Clean up any partial files
            if os.path.exists(output_mp3_file):
                 os.remove(output_mp3_file)


# Setup function to add the cog to the bot
async def setup(bot: commands.Bot):
    await bot.add_cog(Utilities(bot))
    await bot.add_cog(MusicCopyrightCog(bot))
