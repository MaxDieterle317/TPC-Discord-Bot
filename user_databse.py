import sqlite3
import discord
import io
from discord import app_commands
from discord.ext import commands
from typing import Optional, Union

# Define custom events arguments before the class
# These are simple classes to hold the event data cleanly
class UserScoreUpdateEvent:
    def __init__(self, user_id: int, old_value: int, new_value: int):
        self.user_id = user_id
        self.old_value = old_value
        self.new_value = new_value

class UserWarningsUpdateEvent:
    def __init__(self, user_id: int, old_value: int, new_value: int):
        self.user_id = user_id
        self.old_value = old_value
        self.new_value = new_value

class UserDatabase(commands.Cog):
    """Handles user data storage and updates using SQLite."""
    
    def __init__(self, bot):
        self.bot = bot
        self.db_name = "server_users.db"
        self.initialize_db()

    def initialize_db(self):
        """Creates the SQLite table if it does not exist."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        ID INTEGER PRIMARY KEY,
                        first_joined TEXT,
                        score INTEGER DEFAULT 0,
                        warnings_activity INTEGER DEFAULT 0
                    )
                """)
                con.commit()
            print(f"Database '{self.db_name}' initialized successfully.")
        except Exception as e:
            print(f"Error initializing database: {e}")

# --- Helper Method to ensure user is in DB ---
    def check_user_exists(self, user_id: int) -> bool:
        """Checks if a user exists in the DB without inserting."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("""
                    SELECT 1 FROM users WHERE ID = ?
                """, (user_id,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"Error checking if user {user_id} exists: {e}")
            return False

    # --- New Interface Functions (Getters) ---

    def get_user_score(self, user_id: int) -> Optional[int]:
        """Fetches the score for a specific user ID."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("SELECT score FROM users WHERE ID = ?", (user_id,))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting score for user {user_id}: {e}")
            return None

    def get_user_warning(self, user_id: int) -> Optional[int]:
        """Fetches the warnings count for a specific user ID."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("SELECT warnings_activity FROM users WHERE ID = ?", (user_id,))
                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting warnings for user {user_id}: {e}")
            return None
            
    # --- Internal Update Helper (New) ---
    def _execute_update_and_fetch_new_value(self, user_id: int, amount: int, column: str, event_type: str) -> Optional[int]:
        """
        Generic helper to update a column, fetch the new value, and dispatch an event.
        Returns the new value or None on failure/no-update.
        """
        try:
            # 1. Fetch the current (old) value before the update
            old_value = self.get_user_score(user_id) if column == 'score' else self.get_user_warning(user_id)
            if old_value is None:
                return None # User doesn't exist or error fetching old value

            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                
                # Perform the update
                # Note: The SQL injection risk is low here since `column` is controlled by the class methods
                # but in a real-world application, dynamic SQL execution should use safe placeholders/whitelisting.
                cur.execute(f"""
                    UPDATE users
                    SET {column} = {column} + ?
                    WHERE ID = ?
                """, (amount, user_id))
                
                con.commit()

                if cur.rowcount == 0:
                    return None # No row was updated

                # 2. Retrieve the new value immediately after the update
                cur.execute(f"SELECT {column} FROM users WHERE ID = ?", (user_id,))
                new_value = cur.fetchone()
                new_value = new_value[0] if new_value else None

                # 3. Dispatch the custom event (Listeners)
                if new_value is not None:
                    if event_type == 'score':
                        # Dispatch the on_user_score_update event
                        # The bot.dispatch method is how discord.py listeners are notified.
                        self.bot.dispatch('user_score_update', UserScoreUpdateEvent(user_id, old_value, new_value))
                    elif event_type == 'warnings':
                        # Dispatch the on_user_warnings_update event
                        self.bot.dispatch('user_warnings_update', UserWarningsUpdateEvent(user_id, old_value, new_value))

                return new_value
        
        except Exception as e:
            print(f"Error updating {column} for user {user_id}: {e}")
            return None


    def update_user_score(self, user_id: int, amount: int) -> Optional[int]:
        """
        Increases or decreases a user's score by the specified amount.
        Returns the new score or None on failure.
        """
        # Note: Caller must ensure user exists (or handle the None return)
        return self._execute_update_and_fetch_new_value(user_id, amount, 'score', 'score')
        

    def update_user_warnings(self, user_id: int, amount: int) -> Optional[int]:
        """
        Increases or decreases a user's warnings by the specified amount.
        Returns the new warnings count or None on failure.
        """
        return self._execute_update_and_fetch_new_value(user_id, amount, 'warnings_activity', 'warnings')
        
    def add_new_user(self, user_id: int, joined_at_iso: str):
        """Inserts a user into the DB if they don't exist."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT OR IGNORE INTO users (ID, first_joined)
                    VALUES (?, ?)
                """, (user_id, joined_at_iso))
                con.commit()
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error ensuring user {user_id} exists: {e}")
            return False

    # --- Slash Command to export database ---
    @app_commands.command(name="export_db", description="Exports the internal user database file (Admin Only).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def export_db_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) 

        try:
            db_file = discord.File(self.db_name)
            await interaction.followup.send("✅ Here is the database file:", file=db_file, ephemeral=True)
        except FileNotFoundError:
            await interaction.followup.send("❌ Error: Database file not found.", ephemeral=True)
        except Exception as e:
            print(f"Error exporting database: {e}")
            await interaction.followup.send(f"❌ An unexpected error occurred: {e}", ephemeral=True)
    # ----------------------------------------

    # --- NEW Slash Command to view database contents ---
    @app_commands.command(name="view_db", description="Displays all user data from the database (Admin Only).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def view_db_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            with sqlite3.connect(self.db_name) as con:
                con.row_factory = sqlite3.Row
                cur = con.cursor()
                cur.execute("SELECT * FROM users")
                rows = cur.fetchall()

                if not rows:
                    await interaction.followup.send("⚠️ The user database is currently empty.", ephemeral=True)
                    return

                headers = [col[0] for col in cur.description]
                data_output = []
                data_output.append(",".join(headers))
                
                for row in rows:
                    row_data = [str(row[header]) for header in headers]
                    data_output.append(",".join(row_data))

                output_content = "\n".join(data_output)
                
                if len(output_content) < 1900:
                    await interaction.followup.send(
                        "📊 **User Database Snapshot**:\n"
                        f"```csv\n{output_content}```",
                        ephemeral=True
                    )
                else:
                    data_file = discord.File(
                        io.BytesIO(output_content.encode('utf-8')),
                        filename="user_database_snapshot.csv"
                    )
                    await interaction.followup.send(
                        "✅ The database snapshot is too large to display directly, here it is as a file:",
                        file=data_file,
                        ephemeral=True
                    )

        except Exception as e:
            print(f"Error viewing database: {e}")
            await interaction.followup.send(f"❌ An unexpected error occurred while fetching data: {e}", ephemeral=True)

    # ----------------------------------------
    

async def setup(bot):
    await bot.add_cog(UserDatabase(bot))