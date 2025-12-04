import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional
from datetime import datetime, timezone, timedelta # Ensure timedelta is imported if you use type hints elsewhere



class UserManager(commands.Cog):
    """
    Using user_dtabase.py's database to manage user data. 
    And tracks Score and Warnings.
    """

    def __init__(self, bot):
        self.bot = bot
        self.db_name = "server_users.db"
        # Use the same database file name as user_databse.py
    
    def get_user_db_cog(self):
        """Helper to safely retrieve the UserDatabase cog instance."""
        # The cog name is the class name: UserDatabase
        user_db = self.bot.get_cog('UserDatabase')
        if not user_db:
            # Log an error if the database cog isn't loaded
            print("❌ Error: UserDatabase cog not found/loaded.")
        return user_db
    
    def get_account_age(self, member=None):
        # If no member is specified, handle the edge case
        if member is None:
            return None

        # Get the datetime object for account creation
        creation_date = member.created_at

        # Calculate the age difference (datetime.timedelta object)
        account_age_td = datetime.now(timezone.utc) - creation_date

        # Format the creation date string
        formatted_date = creation_date.strftime("%B %d, %Y at %I:%M %p UTC")

        # Return the creation date string and the raw timedelta object
        return account_age_td
    
    def new_member_process(self, member: discord.Member):
        """Process a new member joining the server."""
        user_db = self.get_user_db_cog()
        if not user_db:
            print(f"❌ Cannot add user {member.id} to DB: UserDatabase cog not loaded.")
            return
        
        try:
            # Use the UserDatabase's helper to ensure the user exists
            inserted = user_db.check_user_exists(member.id)
            if not inserted:
                user_db.add_new_user(member.id, member.joined_at.isoformat())
                user_db.update_user_score(member.id, 25)
                account_age = self.get_account_age(member)
                if(account_age.total_seconds() < 600):
                    user_db.update_user_warnings(member.id, 25)
                else:
                    user_db.update_user_score(member.id, 100)
                    
                print(f"ℹ️ User {member.id} account created on {account_age}, age: {account_age.days} days.")
            else:
                print(f"ℹ️ User {member.id} already exists in database on join.")
        except Exception as e:
            print(f"Error adding user {member.id} on join: {e}")


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event listener to add a user to the database when they join the server."""
        user_db = self.get_user_db_cog()
        if not user_db:
            print(f"❌ Cannot add user {member.id} to DB: UserDatabase cog not loaded.")
            return
        
        try:
            self.new_member_process(member)
        except Exception as e:
            print(f"Error adding user {member.id} on join: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        user_db = self.get_user_db_cog()
        if not user_db:
            print(f"❌ Cannot add user {message.author.id} to DB: UserDatabase cog not loaded.")
            return
        try:
            # Use the UserDatabase's helper to ensure the user exists
            self.new_member_process(message.author)
        except Exception as e:
            print(f"Error adding user {message.author.id} on join: {e}")

async def setup(bot):
    await bot.add_cog(UserManager(bot))