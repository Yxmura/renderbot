import discord
from discord import app_commands, Embed, Color, ui
from discord.ext import commands, tasks
import json
import os
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv # Keep dotenv here for config loading
import asyncio # Import asyncio


# Load environment variables specific to utilities if needed (or keep it in main)
# load_dotenv()

# This should ideally be loaded from a config file or database on startup
# For simplicity in this example, we'll use a global variable for now
# This global is specific to the Utilities cog's config
UTILITIES_REQUIRED_ROLE_ID: Optional[int] = 1317607057687576696 # Keeping the original value

# View for pagination (can be in a separate shared file if used by other cogs)
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
        try:
            await interaction.response.defer() # Defer to avoid interaction failed
            self.current_index -= 1
            self.update_buttons()
            await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)
        except Exception as e:
            print(f"Error in HelpPaginatorView go_previous: {e}")
            # Consider sending an ephemeral error message to the user

    async def go_next(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer() # Defer to avoid interaction failed
            self.current_index += 1
            self.update_buttons()
            await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)
        except Exception as e:
            print(f"Error in HelpPaginatorView go_next: {e}")
            # Consider sending an ephemeral error message to the user

    async def jump_to_page(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer() # Defer to avoid interaction failed
            selected_page_index = int(interaction.data['values'][0])
            self.current_index = selected_page_index
            self.update_buttons()
            await interaction.edit_original_response(embed=self.embeds[self.current_index], view=self)
        except Exception as e:
            print(f"Error in HelpPaginatorView jump_to_page: {e}")
            # Consider sending an ephemeral error message to the user


    async def on_timeout(self):
        print("HelpPaginatorView timed out.")
        if self.message:
            try:
                await self.message.edit(view=None) # Remove buttons on timeout
            except:
                pass # Ignore if message was deleted


class Utilities(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("Utilities __init__ called") # Debug print
        try:
            self.load_config() # Load configuration on cog initialization
            # Store categorized commands
            self.categorized_commands: Dict[str, List[app_commands.AppCommand]] = {}
            print("Utilities __init__ finished successfully.") # Debug print
        except Exception as e:
            print(f"Error during Utilities __init__: {e}")
            # Consider raising the exception to see it fail explicitly in main
            # raise e


    def load_config(self):
        print("Utilities load_config called.") # Debug print
        global UTILITIES_REQUIRED_ROLE_ID
        try:
            # Load the required role ID from a persistent config file if it exists
            if os.path.exists("utilities_config.json"):
                with open("utilities_config.json", "r") as f:
                    config_data = json.load(f)
                    # Only update if the key exists in the config file
                    if 'required_role_id' in config_data:
                         # Attempt to cast to int, handle potential errors
                         try:
                             loaded_role_id = config_data.get("required_role_id")
                             if loaded_role_id is not None:
                                 UTILITIES_REQUIRED_ROLE_ID = int(loaded_role_id)
                             else:
                                 UTILITIES_REQUIRED_ROLE_ID = None # Explicitly set to None if the value is None
                         except (ValueError, TypeError):
                             print("Invalid value for required_role_id in config. Using default.")
                             UTILITIES_REQUIRED_ROLE_ID = 1317607057687576696 # Reset to default if invalid

            print("Utilities load_config finished.") # Debug print
        except (FileNotFoundError, json.JSONDecodeError) as e:
             print(f"Error loading utilities_config.json: {e}. Using default value for REQUIRED_ROLE_ID.")
             UTILITIES_REQUIRED_ROLE_ID = 1317607057687576696 # Ensure default is set on error
        except Exception as e:
             print(f"Unexpected error in Utilities load_config: {e}")
             # Consider raising if this error should prevent the cog from loading


    def save_config(self):
         print("Utilities save_config called.") # Debug print
         try:
             config_data = {
                 "required_role_id": UTILITIES_REQUIRED_ROLE_ID
             }
             with open("utilities_config.json", "w") as f:
                 json.dump(config_data, f, indent=4)
             print("Utilities save_config finished.") # Debug print
         except Exception as e:
             print(f"Error saving utilities_config.json: {e}")


    @commands.Cog.listener()
    async def on_ready(self):
        print("UtilitiesCog ready listener called.") # Debug print
        # Categorize commands when the bot is ready
        # Delay categorization slightly to ensure other cogs are loaded
        # Increased delay as command fetching might take a bit after sync
        await asyncio.sleep(5)
        print("UtilitiesCog ready listener after sleep, calling categorize_commands.") # Debug print
        await self.categorize_commands()
        print("UtilitiesCog ready listener finished.") # Debug print


    async def categorize_commands(self):
        """Categorizes slash commands by their cog."""
        print("categorize_commands called.") # Debug print
        await self.bot.wait_until_ready() # Ensure bot is ready and commands are synced
        self.categorized_commands.clear() # Clear previous categorization

        print("Fetching commands for categorization...")
        try:
            # Fetch global commands
            global_commands = await self.bot.tree.fetch_commands(guild=None)
            print(f"Fetched {len(global_commands)} global commands.")

            # Fetch guild commands for all connected guilds
            all_commands = list(global_commands) # Start with global commands
            # Note: Fetching guild commands for *all* guilds on every ready might be slow
            # if the bot is in many guilds. Consider optimizing if necessary.
            for guild in self.bot.guilds:
                 try:
                     guild_commands = await self.bot.tree.fetch_commands(guild=guild)
                     print(f"Fetched {len(guild_commands)} guild commands for guild {guild.id}.")
                     all_commands.extend(guild_commands)
                 except Exception as e:
                     print(f"Error fetching guild commands for guild {guild.id}: {e}")


            # Use a set to avoid duplicate commands if a command is both global and guild-synced (less common)
            seen_command_identifiers = set()
            unique_commands = []
            for command in all_commands:
                # Using a combination of name, guild_id, and potentially description for uniqueness
                cmd_identifier = (command.name, command.guild_id, command.description)
                if cmd_identifier not in seen_command_identifiers:
                    unique_commands.append(command)
                    seen_command_identifiers.add(cmd_identifier)


            for command in unique_commands:
                cog_name = "No Cog" # Default category
                # Find the cog instance the command belongs to
                if command.binding is not None:
                     try:
                         # command.binding is the cog instance itself when using bot.add_cog(Cog(bot))
                         cog_instance = command.binding
                         if cog_instance:
                             cog_name = type(cog_instance).__name__
                     except AttributeError:
                         # Handle cases where binding might not be the cog instance
                         pass
                     except Exception as e:
                         print(f"Error identifying cog for command {command.name}: {e}")


                if cog_name not in self.categorized_commands:
                    self.categorized_commands[cog_name] = []
                self.categorized_commands[cog_name].append(command)

            print("Commands categorized.")
            # Print categorized commands for verification
            for cog, cmds in self.categorized_commands.items():
                 print(f"  {cog}: {[cmd.name for cmd in cmds]}")

        except Exception as e:
            print(f"Error during command categorization: {e}")


    @app_commands.command(name="ping", description="Check the bot's latency")
    async def ping(self, interaction: discord.Interaction):
        try:
            latency = round(self.bot.latency * 1000)

            embed = Embed(
                title="🏓 Pong!",
                description=f"Bot Latency: **{latency}ms**",
                color=Color.purple()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
             print(f"Error in ping command: {e}")
             try:
                 await interaction.response.send_message("An error occurred while fetching latency.", ephemeral=True)
             except:
                 pass


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
        try:
            if interaction.guild is None:
                 await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
                 return

            # Check if the user has the required role
            if UTILITIES_REQUIRED_ROLE_ID is not None:
                required_role = interaction.guild.get_role(UTILITIES_REQUIRED_ROLE_ID)
                if required_role and required_role not in interaction.user.roles:
                    await interaction.response.send_message(
                        f"You do not have the {required_role.name} role to use this command.",
                        ephemeral=True
                    )
                    return
            elif UTILITIES_REQUIRED_ROLE_ID is None and interaction.user.guild_permissions.administrator:
                 # Allow administrators to use if no required role is set
                 pass
            elif UTILITIES_REQUIRED_ROLE_ID is None:
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
                print(f"Error sending embed message: {e}")
                await interaction.response.send_message(
                    f"❌ An error occurred while sending the embed: {e}",
                    ephemeral=True
                )
        except Exception as e:
            print(f"Error in embed command: {e}")
            try:
                 await interaction.response.send_message("An unexpected error occurred with the embed command.", ephemeral=True)
            except:
                 pass


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
        try:
            global UTILITIES_REQUIRED_ROLE_ID
            UTILITIES_REQUIRED_ROLE_ID = required_role.id
            self.save_config()

            embed = Embed(
                title="🛠️ Utilities Role Set",
                description=f"The role required to use utility commands is now: {required_role.mention}",
                color=Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
             print(f"Error in setutilitiesrole command: {e}")
             try:
                  await interaction.response.send_message("An error occurred while setting the utilities role.", ephemeral=True)
             except:
                  pass


    @app_commands.command(name="help", description="Get a list of all available commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer() # Defer the interaction as command loading can take time

        try:
            # Ensure commands are categorized
            if not self.categorized_commands:
                print("Categorized commands not populated, attempting categorization from help command.") # Debug print
                await self.categorize_commands()
            else:
                 print("Using cached categorized commands for help command.") # Debug print


            if not self.categorized_commands:
                await interaction.followup.send("Could not load commands for the help menu. Please try again later.", ephemeral=True)
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
                await interaction.followup.send("No commands found to display in help.", ephemeral=True)
                return

            # Send the first embed with the paginator view
            view = HelpPaginatorView(embeds, 0)
            # The interaction was deferred, so use followup.send
            view.message = await interaction.followup.send(embed=embeds[0], view=view)

        except Exception as e:
            print(f"Error in help command: {e}")
            try:
                 await interaction.followup.send("An unexpected error occurred while generating the help menu.", ephemeral=True)
            except:
                 pass


# Setup function for the Utilities cog
async def setup(bot: commands.Bot):
    print("Utilities cog setup called from file.") # Debug print
    try:
        await bot.add_cog(Utilities(bot))
        print("Utilities cog setup finished successfully.") # Debug print
    except Exception as e:
        print(f"Error adding Utilities cog: {e}")
        # Consider re-raising the exception if this should be a fatal error
        # raise e