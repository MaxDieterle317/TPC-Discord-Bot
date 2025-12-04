import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional

class ScoreManager(commands.Cog):
    """
    Handles score-related slash commands (get_score and set_score) 
    by interacting with the UserDatabase cog's interface.
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Use the same database file name as user_databse.py (for context, though not used directly here)
        self.db_name = "server_users.db"
        
    def get_user_db_cog(self):
        """Helper to safely retrieve the UserDatabase cog instance."""
        # The cog name is the class name: UserDatabase
        user_db = self.bot.get_cog('UserDatabase')
        if not user_db:
            # Log an error if the database cog isn't loaded
            print("❌ Error: UserDatabase cog not found/loaded.")
        return user_db

    # --- Slash Command: /get_score ---
    @app_commands.command(name="get_score", description="Retrieves the current score for a specified user.")
    @app_commands.describe(user='The member whose score you want to check.')
    async def get_score_command(self, interaction: discord.Interaction, user: Union[discord.Member, discord.User]):
        await interaction.response.defer(ephemeral=False)
        
        user_db = self.get_user_db_cog()
        if not user_db:
            await interaction.followup.send("❌ Internal Error: Database handler is unavailable. Please ensure the 'user_databse' cog is loaded.", ephemeral=True)
            return

        user_id = user.id
        
        # 1. Use the UserDatabase's helper to ensure the user exists
        user_db.ensure_user_exists(user_id, user.created_at.isoformat())

        try:
            # 2. Use the UserDatabase interface method to get the score
            score = user_db.get_user_score(user_id) 

            if score is not None:
                await interaction.followup.send(
                    f"🎉 **{user.display_name}**'s current score is **{score}**.", 
                    ephemeral=False
                )
            else:
                # This should ideally be covered by ensure_user_exists, but handles edge cases
                await interaction.followup.send(
                    f"⚠️ Could not find a score entry for **{user.display_name}**. Score is likely 0.", 
                    ephemeral=False
                )

        except Exception as e:
            print(f"Error in /get_score via UserDatabase interface for user {user_id}: {e}")
            await interaction.followup.send(f"❌ An error occurred while fetching the score: {e}", ephemeral=True)


    # --- Slash Command: /set_score ---
    @app_commands.command(name="set_score", description="Sets the score for a specified user (Moderator Only).")
    @app_commands.checks.has_permissions(manage_guild=True) # Requires manage_guild permission
    @app_commands.describe(
        user='The member whose score you want to set.',
        new_score='The new value for the user\'s score.'
    )
    async def set_score_command(self, interaction: discord.Interaction, user: Union[discord.Member, discord.User], new_score: int):
        await interaction.response.defer(ephemeral=True)
        
        user_db = self.get_user_db_cog()
        if not user_db:
            await interaction.followup.send("❌ Internal Error: Database handler is unavailable. Please ensure the 'user_databse' cog is loaded.", ephemeral=True)
            return

        user_id = user.id

        # 1. Use the UserDatabase's helper to ensure the user exists
        user_db.ensure_user_exists(user_id, user.created_at.isoformat())

        try:
            # 2. Get the current score from the interface
            current_score = user_db.get_user_score(user_id)
            if current_score is None:
                # If the user was just added, score is 0
                current_score = 0 
                
            # 3. Calculate the difference (amount to add)
            # update_user_score adds the amount, so we calculate the delta: new_score = current_score + amount_to_add
            amount_to_add = new_score - current_score

            # 4. Use the UserDatabase interface method to apply the change
            updated_score = user_db.update_user_score(user_id, amount_to_add)
            
            if updated_score is not None and updated_score == new_score:
                await interaction.followup.send(
                    f"✅ Successfully set **{user.display_name}**'s score to **{new_score}**.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ Failed to update score for **{user.display_name}**. Database operation failed.", 
                    ephemeral=True
                )
        
        except Exception as e:
            print(f"Error in /set_score via UserDatabase interface for user {user_id}: {e}")
            await interaction.followup.send(f"❌ An error occurred while setting the score: {e}", ephemeral=True)

    # Error handling for permission checks
    @set_score_command.error
    async def set_score_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("⛔ You do not have permission to use the `/set_score` command. (Requires `Manage Server` permission)", ephemeral=True)
        else:
            print(f"Unhandled error in /set_score: {error}")
            # Ensure a response is sent if deferral hasn't occurred or if it's the first response
            if not interaction.response.is_done():
                 await interaction.response.send_message(f"❌ An unexpected error occurred: {error}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(ScoreManager(bot))