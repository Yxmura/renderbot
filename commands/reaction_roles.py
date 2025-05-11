import discord
from discord import app_commands
import json
import os
from typing import List, Optional
from discord.ext import commands

ROLE_MENUS_FILE = "role_menus.json"
REQUIRED_ROLE_ID = 1317607057687576696

class RoleMenu:
    def __init__(self, message_id: int, channel_id: int, guild_id: int, menu_type: str, roles: dict):
        self.message_id = message_id
        self.channel_id = channel_id
        self.guild_id = guild_id
        self.menu_type = menu_type
        self.roles = roles

class RoleMenuManager:
    def __init__(self):
        self.menus = {}
        self.load_menus()

    def load_menus(self):
        if os.path.exists(ROLE_MENUS_FILE):
            with open(ROLE_MENUS_FILE, 'r') as f:
                data = json.load(f)
                for menu_id, menu_data in data.items():
                    self.menus[menu_id] = RoleMenu(
                        menu_data['message_id'],
                        menu_data['channel_id'],
                        menu_data['guild_id'],
                        menu_data['menu_type'],
                        menu_data['roles']
                    )

    def save_menus(self):
        data = {
            menu_id: {
                'message_id': menu.message_id,
                'channel_id': menu.channel_id,
                'guild_id': menu.guild_id,
                'menu_type': menu.menu_type,
                'roles': menu.roles
            }
            for menu_id, menu in self.menus.items()
        }
        with open(ROLE_MENUS_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def add_menu(self, menu_id: str, menu: RoleMenu):
        self.menus[menu_id] = menu
        self.save_menus()

    def get_menu(self, menu_id: str) -> Optional[RoleMenu]:
        return self.menus.get(menu_id)

    def remove_menu(self, menu_id: str):
        if menu_id in self.menus:
            del self.menus[menu_id]
            self.save_menus()

role_manager = RoleMenuManager()

class RoleSelect(discord.ui.Select):
    def __init__(self, roles: dict):
        options = [
            discord.SelectOption(
                label=role_name,
                description=f"Get the {role_name} role",
                value=str(role_id)
            )
            for role_name, role_id in roles.items()
        ]
        super().__init__(
            placeholder="Select your roles...",
            min_values=0,
            max_values=len(roles),
            options=options
        )
        self.roles = roles

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        # Remove roles that were unselected
        for role_id in self.roles.values():
            role = guild.get_role(int(role_id))
            if role and role in member.roles and str(role_id) not in self.values:
                await member.remove_roles(role)

        # Add newly selected roles
        for role_id in self.values:
            role = guild.get_role(int(role_id))
            if role and role not in member.roles:
                await member.add_roles(role)

        await interaction.response.send_message(
            "Your roles have been updated!",
            ephemeral=True
        )

class RoleButton(discord.ui.Button):
    def __init__(self, role_name: str, role_id: int):
        super().__init__(
            label=role_name,
            style=discord.ButtonStyle.primary,
            custom_id=str(role_id)
        )
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild
        role = guild.get_role(self.role_id)

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(
                f"Removed the {role.name} role!",
                ephemeral=True
            )
        else:
            await member.add_roles(role)
            await interaction.response.send_message(
                f"Added the {role.name} role!",
                ephemeral=True
            )

class RoleView(discord.ui.View):
    def __init__(self, roles: dict, menu_type: str):
        super().__init__(timeout=None)
        if menu_type == "dropdown":
            self.add_item(RoleSelect(roles))
        else:
            for role_name, role_id in roles.items():
                self.add_item(RoleButton(role_name, int(role_id)))

@app_commands.command(name="createrolemenu", description="Create a role selection menu")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    channel="The channel to send the role menu in",
    menu_type="The type of menu to create (dropdown or buttons)",
    title="The title of the embed",
    description="The description of the embed",
    color="The color of the embed (hex code)",
    roles="The roles to include (format: role1:role2:role3)",
    role_names="The display names for the roles (format: name1:name2:name3)"
)
async def createrolemenu(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    menu_type: str,
    title: str,
    description: str,
    color: str,
    roles: str,
    role_names: str
):
    # Role check
    if not any(role.id == REQUIRED_ROLE_ID for role in interaction.user.roles):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True
        )
        return

    if menu_type not in ["dropdown", "buttons"]:
        await interaction.response.send_message(
            "Invalid menu type! Choose either 'dropdown' or 'buttons'.",
            ephemeral=True
        )
        return

    try:
        color = int(color.strip('#'), 16)
    except ValueError:
        await interaction.response.send_message(
            "Invalid color code! Please provide a valid hex color code.",
            ephemeral=True
        )
        return

    role_ids = roles.split(':')
    role_display_names = role_names.split(':')

    if len(role_ids) != len(role_display_names):
        await interaction.response.send_message(
            "The number of roles and role names must match!",
            ephemeral=True
        )
        return

    roles_dict = {}
    for role_id, name in zip(role_ids, role_display_names):
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.response.send_message(
                f"Role with ID {role_id} not found!",
                ephemeral=True
            )
            return
        roles_dict[name] = role_id

    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color(color)
    )

    view = RoleView(roles_dict, menu_type)
    message = await channel.send(embed=embed, view=view)

    menu = RoleMenu(
        message.id,
        channel.id,
        interaction.guild_id,
        menu_type,
        roles_dict
    )
    role_manager.add_menu(str(message.id), menu)

    await interaction.response.send_message(
        "Role menu created successfully!",
        ephemeral=True
    )

@app_commands.command(name="deleterolemenu", description="Delete a role selection menu")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    message_id="The ID of the message containing the role menu"
)
async def deleterolemenu(
    interaction: discord.Interaction,
    message_id: str
):
    menu = role_manager.get_menu(message_id)
    if not menu:
        await interaction.response.send_message(
            "Role menu not found!",
            ephemeral=True
        )
        return

    try:
        channel = interaction.guild.get_channel(menu.channel_id)
        if channel:
            message = await channel.fetch_message(int(message_id))
            await message.delete()
    except:
        pass

    role_manager.remove_menu(message_id)
    await interaction.response.send_message(
        "Role menu deleted successfully!",
        ephemeral=True
    )

def setup(bot: commands.Bot):
    bot.add_cog(RoleMenu(bot))
