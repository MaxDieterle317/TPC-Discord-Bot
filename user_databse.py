import sqlite3
import discord
import io # Required to send data as a file without saving it to disk
from discord import app_commands # Required for Slash Commands
from discord.ext import commands


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
                cur = con.cursor()
                
                # Using INSERT OR IGNORE is a modern SQL trick to avoid the extra SELECT check
                # It tries to insert; if ID exists, it does nothing.
                cur.execute("""
                    INSERT OR IGNORE INTO users (ID, first_joined)
                    VALUES (?, ?)
                """, (user_id, created_at_utc))
                
                # If you want to know if it was actually added, you can check cursor.rowcount
                if cur.rowcount > 0:
                    print(f"User {user_id} added to database.")
                    con.commit()

        except Exception as e:
            print(f"Database operation error for user {user_id}: {e}")

async def setup(bot):
    await bot.add_cog(UserDatabase(bot))