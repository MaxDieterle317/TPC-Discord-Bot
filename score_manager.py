import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional

class ScoreManager(commands.Cog):
    """
    Handles score-related slash commands (get_score and set_score).
    It interacts with the shared server_users.db file.
    """
    
    def __init__(self, bot):
        self.bot = bot
        # Use the same database file name as user_databse.py
        self.db_name = "server_users.db"
        # Since user_databse.py handles the creation, we just need the connection logic.

    # --- Helper Method to ensure user is in DB for new entries ---
    def ensure_user_exists(self, user_id: int, joined_at_iso: Optional[str] = None):
        """Inserts a user into the DB if they don't exist, using account creation date as a fallback."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                # INSERT OR IGNORE attempts to insert the data. 
                # If joined_at_iso is not provided (which happens when fetching via user object), 
                # we can use the current time or a placeholder, but using INSERT OR IGNORE is safest.
                # Note: We rely on the on_message listener in UserDatabase to populate 'first_joined' accurately.
                cur.execute("""
                    INSERT OR IGNORE INTO users (ID, first_joined)
                    VALUES (?, ?)
                """, (user_id, joined_at_iso or 'Unknown'))
                con.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error ensuring user {user_id} exists in ScoreManager: {e}")
            return False

    # --- Slash Command: /get_score ---
    @app_commands.command(name="get_score", description="Retrieves the current score for a specified user.")
    @app_commands.describe(user='The member whose score you want to check.')
    async def get_score_command(self, interaction: discord.Interaction, user: Union[discord.Member, discord.User]):
        await interaction.response.defer(ephemeral=False)
        
        user_id = user.id
        
        # Ensure the user exists in the database first, using their creation date as fallback for 'first_joined'
        self.ensure_user_exists(user_id, user.created_at.isoformat())

        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("SELECT score FROM users WHERE ID = ?", (user_id,))
                result = cur.fetchone()

                if result:
                    score = result[0]
                    await interaction.followup.send(
                        f"🎉 **{user.display_name}**'s current score is **{score}**.", 
                        ephemeral=False
                    )
                else:
                    # Should be covered by ensure_user_exists, but acts as a safeguard
                    await interaction.followup.send(
                        f"⚠️ Could not find a score entry for **{user.display_name}**. Score is likely 0.", 
                        ephemeral=False
                    )

        except Exception as e:
            print(f"Error in /get_score for user {user_id}: {e}")
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
        
        user_id = user.id

        # Ensure the user exists in the database first
        self.ensure_user_exists(user_id, user.created_at.isoformat())

        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                
                # Directly set the score
                cur.execute("""
                    UPDATE users
                    SET score = ?
                    WHERE ID = ?
                """, (new_score, user_id))
                
                con.commit()

                if cur.rowcount > 0:
                    await interaction.followup.send(
                        f"✅ Successfully set **{user.display_name}**'s score to **{new_score}**.", 
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"❌ Failed to update score for **{user.display_name}**. User may not exist.", 
                        ephemeral=True
                    )
        
        except Exception as e:
            print(f"Error in /set_score for user {user_id}: {e}")
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