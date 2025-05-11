import discord
from discord import app_commands
import requests
import random

SUBREDDITS = ["memes", "dankmemes", "wholesomememes"]

@app_commands.command(name="meme", description="Get a random meme from Reddit")
async def meme(interaction: discord.Interaction):
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