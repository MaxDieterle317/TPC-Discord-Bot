import sqlite3
import discord
import io # Required to send data as a file without saving it to disk
from discord import app_commands # Required for Slash Commands
from discord.ext import commands
from typing import Optional, Union

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
    def ensure_user_exists(self, user_id: int, joined_at_iso: str):
        """Inserts a user into the DB if they don't exist."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                # INSERT OR IGNORE attempts to insert the data. If the ID exists, it ignores the operation.
                cur.execute("""
                    INSERT OR IGNORE INTO users (ID, first_joined)
                    VALUES (?, ?)
                """, (user_id, joined_at_iso))
                con.commit()
                # Returns True if a new row was inserted, False otherwise.
                return cur.rowcount > 0
        except Exception as e:
            print(f"Error ensuring user {user_id} exists: {e}")
            return False

    # --- New Interface Functions ---

    def get_user_score(self, user_id: int) -> Optional[int]:
        """Fetches the score for a specific user ID."""
        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("SELECT score FROM users WHERE ID = ?", (user_id,))
                result = cur.fetchone()
                # result will be (score,) or None
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting score for user {user_id}: {e}")
            return None

    def update_user_score(self, user_id: int, amount: int) -> Optional[int]:
        """
        Increases or decreases a user's score by the specified amount.
        Returns the new score or None on failure.
        """
        # 1. Ensure the user is in the database before attempting an update
        # You'll need to pass the joined_at information from your calling function if you use this. 
        # For simplicity here, we'll assume the user is managed by the on_message listener.
        # In a real scenario, you'd call 'ensure_user_exists' with proper data.

        try:
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                
                # Perform the update
                cur.execute("""
                    UPDATE users
                    SET score = score + ?
                    WHERE ID = ?
                """, (amount, user_id))
                
                con.commit()

                if cur.rowcount == 0:
                    # If no row was updated, the user might not exist.
                    # You might want to handle insertion logic here or ensure it happens elsewhere.
                    return None

                # 2. Retrieve the new score immediately after the update
                cur.execute("SELECT score FROM users WHERE ID = ?", (user_id,))
                new_score = cur.fetchone()
                
                return new_score[0] if new_score else None
        
        except Exception as e:
            print(f"Error updating score for user {user_id}: {e}")
            return None
        
    def add_user(self, user_id: int) -> Optional[int]:
        """Adds a new user to the database with default values."""

        try: 
            with sqlite3.connect(self.db_name) as con:
                cur = con.cursor()
                cur.execute("""
                    INSERT INTO users (ID, first_joined)
                    VALUES (?, ?)
                """, (user_id, discord.utils.utcnow().isoformat()))
                con.commit()
                return cur.lastrowid
        except Exception as e:
            print(f"Error adding user {user_id}: {e}")
            return None

    # --- Slash Command to export database ---
    @app_commands.command(name="export_db", description="Exports the internal user database file (Admin Only).")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def export_db_command(self, interaction: discord.Interaction):
        # Defer the response ephemerally, as file operations can take a moment
        await interaction.response.defer(ephemeral=True) 

        try:
            # Create a discord.File object from the existing database file
            db_file = discord.File(self.db_name)
            
            # Send the file back to the user as an ephemeral message
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
                con.row_factory = sqlite3.Row # Allows accessing columns by name
                cur = con.cursor()
                cur.execute("SELECT * FROM users")
                rows = cur.fetchall()

                if not rows:
                    await interaction.followup.send("⚠️ The user database is currently empty.", ephemeral=True)
                    return

                # Get column headers
                headers = [col[0] for col in cur.description]
                
                # Format data into a readable string (e.g., CSV or fixed-width)
                data_output = []
                data_output.append(",".join(headers)) # CSV header
                
                for row in rows:
                    # Convert all row elements to string for output
                    row_data = [str(row[header]) for header in headers]
                    data_output.append(",".join(row_data))

                output_content = "\n".join(data_output)
                
                # Check Discord's message content limit (2000 characters)
                if len(output_content) < 1900:
                    # Send as a formatted message if short enough
                    await interaction.followup.send(
                        "📊 **User Database Snapshot**:\n"
                        f"```csv\n{output_content}```",
                        ephemeral=True
                    )
                else:
                    # Send as a file if too long
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
    
    # --- Listener ---

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        user_id = message.author.id
        # Note: message.author.created_at is the user's account creation date, 
        # not when they joined the guild. Consider using message.author.joined_at if available.
        created_at_utc = message.author.created_at.isoformat()

        try:
            with sqlite3.connect(self.db_name) as con:
                self.add_user(user_id)

        except Exception as e:
            print(f"Database operation error for user {user_id}: {e}")

async def setup(bot):
    await bot.add_cog(UserDatabase(bot))