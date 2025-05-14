import discord
from discord import app_commands, Embed, Color, ui
from discord.ext import commands, tasks
import json
import os
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
from yt_dlp import YoutubeDL
import asyncio
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from googleapiclient.discovery import build
import re
from datetime import datetime

# Load environment variables (ensure these are also in your .env file)
# load_dotenv() # Consider loading dotenv once in main.py

YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")


# Initialize YouTube API client
if YOUTUBE_API_KEY:
    try:
        youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    except Exception as e:
        print(f"Error initializing YouTube API client: {e}")
        youtube_client = None
else:
    print("YOUTUBE_API_KEY not found in environment variables. YouTube commands will not work.")
    youtube_client = None


# Regex pattern for YouTube URLs (Keep if needed within this file's logic)
YOUTUBE_URL_PATTERN = r'(?:https?://)?(?:www\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'


class MusicCopyrightCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cache_file = 'video_cache.json'

        # Initialize Spotify client credentials manager
        try:
            # Check if keys are available before initializing
            if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
                self.spotify_client_credentials_manager = SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
                self.spotify = spotipy.Spotify(client_credentials_manager=self.spotify_client_credentials_manager)
            else:
                 print("Spotify client ID or secret not found in environment variables. Spotify commands will not work.")
                 self.spotify = None

        except Exception as e:
             print(f"Error initializing Spotify client: {e}")
             self.spotify = None


        # Load cached data from the file (if it exists)
        self.cached_info = self.load_cache()


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
         # Add persistent views for the getid command (if you have any saved ones)
         # This needs to be done here if you have persistent button views from getid
         # For simplicity in this example, we're adding dynamic views when the commands are used.
         # If you need persistence for these buttons across restarts, you would need to
         # load saved view data and use bot.add_view here.
         pass


    async def cog_unload(self):
         print("MusicCopyrightCog unloading...")
         # Save the cache when the cog is unloaded
         self.save_cache()


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
                    'album': track['album'].get('name', 'Unknown Album'), # Use .get for safety
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
        learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
        view.add_item(learn_copyright_button)

        # Add a button to fetch detailed video info if YouTube client is available and we have a valid URL
        if youtube_client and info.get('url'):
            match = re.search(YOUTUBE_URL_PATTERN, info['url'])
            if match:
                video_id = match.group(1)
                # Using a dynamic custom_id for potential persistence (though less critical here)
                fetch_details_button = ui.Button(label="Fetch Detailed Info", style=discord.ButtonStyle.primary, custom_id=f"fetch_youtube_{video_id}")
                # Pass the video_id to the actual handler method via lambda
                fetch_details_button.callback = lambda i: self.fetch_details_button_callback(i, video_id)
                view.add_item(fetch_details_button)


        if info['thumbnail']:
            embed.set_thumbnail(url=info['thumbnail'])

        return embed, view

    async def fetch_details_button_callback(self, interaction: discord.Interaction, video_id: str):
        await interaction.response.defer(ephemeral=True) # Defer ephemerally

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            # Use run_in_executor for the blocking call
            video_info = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_video_info_blocking(video_url))


            embed = Embed(
                title=video_info['title'],
                description=video_info['description'][:200] + "..." if len(video_info['description']) > 200 else video_info['description'],
                color=Color.red(),
                url=video_url
            )
            embed.set_author(name=video_info['channel_title'])
            # Format date for better readability
            try:
                publish_date = datetime.fromisoformat(video_info.get('publish_date', '').replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            except ValueError:
                 publish_date = video_info.get('publish_date', 'Unknown Date') # Use raw or default if parsing fails

            embed.add_field(name="Published on", value=publish_date, inline=True)
            embed.add_field(name="Views", value=f"{int(video_info.get('views', 0)):,}", inline=True)
            embed.add_field(name="Likes", value=f"{int(video_info.get('likes', 0)):,}", inline=True)
            embed.add_field(name="Comments", value=f"{int(video_info.get('comments', 0)):,}", inline=True)
            embed.add_field(name="Duration", value=self.format_duration(video_info.get('duration', 'PT0S')), inline=True) # Use get and default
            embed.add_field(name="Channel Subscribers", value=f"{int(video_info.get('channel_subscribers', 0)):,}", inline=True)
            embed.add_field(name="Total Videos", value=f"{int(video_info.get('channel_videos', 0)):,}", inline=True)

            if 'thumbnail' in video_info and video_info['thumbnail']:
                embed.set_thumbnail(url=video_info['thumbnail'])

            # Add button to get channel stats if channel ID is available
            view = ui.View() # Create a new view for these buttons
            if youtube_client and video_info.get('channel_id'):
                channel_id = video_info['channel_id']
                get_stats_button = ui.Button(label="Get Channel Stats", style=discord.ButtonStyle.primary, custom_id=f"get_channel_stats_{channel_id}")
                # Pass the channel_id to the callback
                get_stats_button.callback = lambda i: self.get_channel_stats_button_callback(i, channel_id)
                view.add_item(get_stats_button)

            # Add a button to learn about copyright
            learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
            view.add_item(learn_copyright_button)


            await interaction.followup.send(embed=embed, view=view, ephemeral=False) # Send non-ephemeral


        except Exception as e:
            error_message = f"An error occurred while fetching detailed info: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            print(f"Error in fetch_details_button_callback: {e}") # Log the error
            await interaction.followup.send(error_message, ephemeral=True)


    # This is a blocking helper method for fetching video details
    def get_video_info_blocking(self, video_url: str) -> Dict[str, Any]:
        if not youtube_client:
             raise Exception("YouTube API client is not initialized.")

        match = re.search(YOUTUBE_URL_PATTERN, video_url)
        if not match:
             raise Exception("Invalid YouTube video link.")
        video_id = match.group(1)

        try:
            video_request = youtube_client.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            # This is a blocking call
            video_response = video_request.execute()
        except Exception as e:
            print(f"Error executing YouTube videos list request: {e}")
            raise Exception("Error fetching video details from YouTube.") from e


        if not video_response or not video_response.get('items'):
            raise Exception("YouTube video not found or API returned no items.")

        video_data = video_response["items"][0]
        channel_id = video_data["snippet"].get("channelId")

        if not channel_id:
             raise Exception("Could not find channel ID for the video.")

        try:
            channel_request = youtube_client.channels().list(
                part="snippet,statistics",
                id=channel_id
            )
            # This is a blocking call
            channel_response = channel_request.execute()
        except Exception as e:
             print(f"Error executing YouTube channels list request: {e}")
             # Proceed even if channel data fetching fails, mark relevant fields as unavailable
             channel_response = {'items': []} # Provide a fallback structure

        channel_data = channel_response["items"][0] if channel_response.get('items') else {}

        thumbnail = video_data["snippet"].get("thumbnails", {}).get("high", {}).get("url") # Use .get for safety

        return {
            "title": video_data["snippet"].get("title", "Unknown Title"),
            "description": video_data["snippet"].get("description", "No description provided."),
            "channel_title": video_data["snippet"].get("channelTitle", "Unknown Channel"),
            "channel_id": channel_id, # Include channel ID
            "publish_date": video_data["snippet"].get("publishedAt", "Unknown Date"),
            "views": video_data["statistics"].get("viewCount", "0"),
            "likes": video_data["statistics"].get("likeCount", "0"),
            "comments": video_data["statistics"].get("commentCount", "0"),
            "duration": video_data["contentDetails"].get("duration", "PT0S"), # Default to PT0S if missing
            "channel_subscribers": channel_data.get("statistics", {}).get("subscriberCount", "N/A"), # Use .get safely
            "channel_videos": channel_data.get("statistics", {}).get("videoCount", "N/A"), # Use .get safely
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
            try:
                hours = int(hours_str)
            except ValueError:
                 pass # Ignore if hours part is not a valid int
        if 'M' in duration:
            minutes_str, duration = duration.split('M')
            try:
                minutes = int(minutes_str)
            except ValueError:
                 pass # Ignore if minutes part is not a valid int
        if 'S' in duration:
            seconds_str = duration.replace('S', '')
            try:
                # Handle potential floating point seconds if API returns them
                seconds = int(float(seconds_str))
            except ValueError:
                 pass # Ignore if seconds part is not a valid number

        parts = []
        if hours > 0:
            parts.append(f"{hours}") # No leading zero for hours

        parts.append(f"{minutes:02d}")
        parts.append(f"{seconds:02d}")

        # Ensure at least minutes:seconds format
        if len(parts) == 1: # Only seconds (shouldn't happen with 02d formatting but for safety)
             return f"00:00:{parts[0]}"
        elif len(parts) == 2: # Minutes and seconds (and hours if exists)
             return ":".join(parts)
        elif len(parts) == 3: # Hours, minutes, seconds
             return ":".join(parts)
        else:
             return "Invalid Duration" # Fallback for unexpected parsing

    @app_commands.command(name='youtubestats', description='Get detailed statistics for a YouTube channel.')
    @app_commands.describe(channel_id='The ID of the YouTube channel')
    async def youtube_stats(self, interaction: discord.Interaction, channel_id: str):
        await interaction.response.defer() # Defer the interaction

        if not youtube_client:
             await interaction.followup.send("YouTube API client is not initialized. Please check the bot's configuration.")
             return

        try:
            # Use run_in_executor for the blocking calls
            stats = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_channel_details_blocking(channel_id))
            latest_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_latest_video_blocking(channel_id))
            top_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_top_video_blocking(channel_id))

            if stats:
                embed = Embed(
                    title=f"{stats.get('title', 'Unknown')} - YouTube Channel Stats",
                    description=stats.get('description', 'No description'),
                    color=Color.red()
                )
                if stats.get("profile_pic"):
                    embed.set_thumbnail(url=stats["profile_pic"])
                if stats.get("banner_url"):
                    embed.set_image(url=stats["banner_url"])

                embed.add_field(name="Subscribers", value=f"{int(stats.get('subscribers', 0)):,}", inline=True)
                embed.add_field(name="Total Views", value=f"{int(stats.get('views', 0)):,}", inline=True)
                embed.add_field(name="Total Videos", value=f"{int(stats.get('videos', 0)):,}", inline=True)
                embed.add_field(name="Channel Created", value=stats.get('created_at', 'Unknown Date'), inline=True)

                if latest_video:
                    embed.add_field(
                        name="Latest Video",
                        value=f"[{latest_video.get('title', 'Unknown Title')}](https://www.youtube.com/watch?v={latest_video.get('video_id', '')})" if latest_video.get('video_id') else latest_video.get('title', 'Unknown Title'),
                        inline=False
                    )
                if top_video:
                    embed.add_field(
                        name="Top Video",
                        value=f"[{top_video.get('title', 'Unknown Title')}](https://www.youtube.com/watch?v={top_video.get('video_id', '')})" if top_video.get('video_id') else top_video.get('title', 'Unknown Title'),
                        inline=False
                    )

                # Add a button to learn about copyright
                view = ui.View()
                learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
                view.add_item(learn_copyright_button)

                await interaction.followup.send(embed=embed, view=view)

            else:
                await interaction.followup.send("Channel not found for the provided ID!")

        except Exception as e:
            error_message = f"An error occurred: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            print(f"Error in youtube_stats: {e}") # Log the error
            await interaction.followup.send(error_message)

    # These helper methods were blocking and need to be called within run_in_executor
    def get_channel_details_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        try:
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
        except Exception as e:
             print(f"Error fetching channel details (blocking): {e}")
             return None

    def get_latest_video_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        try:
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
                        "title": video["snippet"].get("title", "Unknown Title"),
                        "video_id": video["id"].get("videoId"),
                        "published_at": video["snippet"].get("publishedAt", "Unknown Date")
                    }
            return None
        except Exception as e:
             print(f"Error fetching latest video (blocking): {e}")
             return None


    def get_top_video_blocking(self, channel_id: str) -> Optional[Dict[str, Any]]:
        if not youtube_client: return None
        try:
            # The YouTube Data API does not have a direct "order by viewCount" for search results
            # This search order is approximate and might not find the absolute top video.
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
                         "title": video["snippet"].get("title", "Unknown Title"),
                         "video_id": video["id"].get("videoId")
                     }
            return None
        except Exception as e:
             print(f"Error fetching top video (blocking): {e}")
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
            # Note: forHandle is the correct parameter for modern handles
            request_handle = youtube_client.channels().list(
                part="id,snippet",
                forHandle=handle
            )
            response_handle = await asyncio.get_event_loop().run_in_executor(None, request_handle.execute)

            if response_handle and response_handle.get("items"):
                channel_id = response_handle["items"][0].get("id")
                channel_name = response_handle["items"][0].get("snippet", {}).get("title")
            else:
                # If not found by handle, try searching
                search_request = youtube_client.search().list(
                    part="id,snippet",
                    q=query, # Use the original query for search
                    type="channel",
                    maxResults=1
                )
                search_response = await asyncio.get_event_loop().run_in_executor(None, search_request.execute)

                if search_response and search_response.get("items"):
                    channel_id = search_response["items"][0].get("id", {}).get("channelId")
                    channel_name = search_response["items"][0].get("snippet", {}).get("title")
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
            # Pass the channel_id to the callback
            get_stats_button.callback = lambda i: self.get_channel_stats_button_callback(i, channel_id)
            view.add_item(get_stats_button)

            # Add a button to learn about copyright
            learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
            view.add_item(learn_copyright_button)

            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(error_message or "Could not fetch channel information.")


    async def get_channel_stats_button_callback(self, interaction: discord.Interaction, channel_id: str):
        await interaction.response.defer(ephemeral=True) # Defer ephemerally

        if not youtube_client:
             await interaction.followup.send("YouTube API client is not initialized. Please check the bot's configuration.")
             return

        try:
            # Use run_in_executor for the blocking calls
            stats = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_channel_details_blocking(channel_id))
            latest_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_latest_video_blocking(channel_id))
            top_video = await asyncio.get_event_loop().run_in_executor(None, lambda: self.get_top_video_blocking(channel_id))


            if stats:
                embed = Embed(
                    title=f"{stats.get('title', 'Unknown')} - YouTube Channel Stats",
                    description=stats.get('description', 'No description'),
                    color=Color.red()
                )
                if stats.get("profile_pic"):
                    embed.set_thumbnail(url=stats["profile_pic"])
                if stats.get("banner_url"):
                    embed.set_image(url=stats["banner_url"])

                embed.add_field(name="Subscribers", value=f"{int(stats.get('subscribers', 0)):,}", inline=True)
                embed.add_field(name="Total Views", value=f"{int(stats.get('views', 0)):,}", inline=True)
                embed.add_field(name="Total Videos", value=f"{int(stats.get('videos', 0)):,}", inline=True)
                embed.add_field(name="Channel Created", value=stats.get('created_at', 'Unknown Date'), inline=True)

                if latest_video:
                    embed.add_field(
                        name="Latest Video",
                        value=f"[{latest_video.get('title', 'Unknown Title')}](https://www.youtube.com/watch?v={latest_video.get('video_id', '')})" if latest_video.get('video_id') else latest_video.get('title', 'Unknown Title'),
                        inline=False
                    )
                if top_video:
                    embed.add_field(
                        name="Top Video",
                        value=f"[{top_video.get('title', 'Unknown Title')}](https://www.youtube.com/watch?v={top_video.get('video_id', '')})" if top_video.get('video_id') else top_video.get('title', 'Unknown Title'),
                        inline=False
                    )

                # Add a button to learn about copyright
                view = ui.View()
                learn_copyright_button = ui.Button(style=discord.ButtonStyle.link, label="Learn About Copyright", url="https://gappa-web.pages.dev/wiki/wiki")
                view.add_item(learn_copyright_button)

                await interaction.followup.send(embed=embed, view=view, ephemeral=False) # Send non-ephemeral

            else:
                await interaction.followup.send("Channel statistics not found for the provided ID.", ephemeral=True)

        except Exception as e:
            error_message = f"An error occurred while fetching channel stats: {str(e)}"
            if "quota" in str(e).lower():
                 error_message = "YouTube API quota exceeded. Please try again later."
            print(f"Error in get_channel_stats_button_callback: {e}") # Log the error
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
            # Check against server's file size limit
            # If interaction.guild is None (e.g., DM), use a default limit
            filesize_limit = interaction.guild.filesize_limit if interaction.guild else 8 * 1024 * 1024 # Default 8MB


            if file_size > filesize_limit:
                 await interaction.followup.send(f"The extracted audio file is too large ({file_size / (1024*1024):.2f} MB). Discord file size limit is {filesize_limit / (1024*1024):.2f} MB.")
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


# Setup function for the MusicCopyrightCog
async def setup(bot: commands.Bot):
    print("MusicCopyrightCog setup called")
    await bot.add_cog(MusicCopyrightCog(bot))
    print("MusicCopyrightCog setup finished")

# --- END: Music Copyright Cog and its Setup ---


