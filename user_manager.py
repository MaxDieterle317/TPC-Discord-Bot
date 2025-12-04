import sqlite3
import discord
from discord import app_commands
from discord.ext import commands
from typing import Union, Optional
from datetime import datetime, timezone, timedelta 
# Import the custom event classes to use for type hinting/structure
from user_databse import UserScoreUpdateEvent, UserWarningsUpdateEvent


class UserManager(commands.Cog):
    """
    Using user_dtabase.py's database to manage user data. 
    And tracks Score and Warnings.
    """

    PROTECTED_ROLE_ID = 1446241806680461505  # Replace with the actual protected role ID

    def __init__(self, bot):
        self.bot = bot
        self.db_name = "server_users.db"
    
    def get_user_db_cog(self):
        """Helper to safely retrieve the UserDatabase cog instance."""
        user_db = self.bot.get_cog('UserDatabase')
        if not user_db:
            print("❌ Error: UserDatabase cog not found/loaded.")
        return user_db
    
    
    def get_account_age(self, member: Optional[Union[discord.Member, discord.User]] = None) -> Optional[timedelta]:
        """Calculates the age of a Discord account."""
        if member is None:
            return None

        creation_date = member.created_at
        account_age_td = datetime.now(timezone.utc) - creation_date
        return account_age_td
    
    # --- Custom Event Listeners (The "Listeners" for DB changes) ---
    
    # Listener for the 'user_score_update' event
    @commands.Cog.listener()
    async def on_user_score_update(self, event: UserScoreUpdateEvent):
        """Prints a notification when a user's score is updated."""
        user = self.bot.get_user(event.user_id) or await self.bot.fetch_user(event.user_id)
        user_display = str(user) if user else f"ID: {event.user_id}"

        print(f"🔔 **SCORE UPDATED** for User: **{user_display}**")
        print(f"   - Old Score: {event.old_value}")
        print(f"   - New Score: **{event.new_value}**")
        print("-" * 30)

        

    # Listener for the 'user_warnings_update' event
    @commands.Cog.listener()
    async def on_user_warnings_update(self, event: UserWarningsUpdateEvent):
        """Prints a notification when a user's warnings count is updated."""
        user = self.bot.get_user(event.user_id) or await self.bot.fetch_user(event.user_id)
        user_display = str(user) if user else f"ID: {event.user_id}"
        kick_reason = f"User reached {event.new_value} warnings. Automatic kick enforced."

        print(f"⚠️ **WARNINGS UPDATED** for User: **{user_display}**")
        print(f"   - Old Warnings: {event.old_value}")
        print(f"   - New Warnings: **{event.new_value}**")
        print("-" * 30)

        if(event.new_value >= 3):
            print(f"‼️ User {user_display} has reached 3 warnings! Consider Kicking them.")
         # Check for the kick threshold (5 or more warnings)
        if event.new_value >= 5:
            print(f"🔥 KICK THRESHOLD REACHED: Attempting to kick user {user_display}...")
            
            # Kicking requires a discord.Member object and guild context.
            # We must iterate over all guilds the bot is in to find the member.
            member_to_kick = None
            for guild in self.bot.guilds:
                member = guild.get_member(event.user_id)
                if member:
                    member_to_kick = member
                    break
            
            # Check for the kick threshold (5 or more warnings)
        if event.new_value >= 5:
            print(f"🔥 KICK THRESHOLD REACHED: Attempting to kick user {user_display}...")
            
            # Kicking requires a discord.Member object and guild context.
            member_to_kick = None
            for guild in self.bot.guilds:
                member = guild.get_member(event.user_id)
                if member:
                    member_to_kick = member
                    break
            
            if event.new_value >= 5:
                print(f"🔥 KICK THRESHOLD REACHED: Attempting to kick user {user_display}...")
                
                # Kicking requires a discord.Member object and guild context.
                member_to_kick = None
                for guild in self.bot.guilds:
                    member = guild.get_member(event.user_id)
                    if member:
                        member_to_kick = member
                        break
                
                if member_to_kick:
                    
                    # --- NEW/UPDATED: Check if the member is protected ---
                    perms = member_to_kick.guild_permissions
                    
                    # Check for the specific role ID
                    is_protected_by_role = any(role.id == PROTECTED_ROLE_ID for role in member_to_kick.roles)

                    should_skip = False
                    skip_reason = ""

                    # 1. Check for general Moderator/Admin Permissions
                    if perms.administrator or perms.kick_members or perms.ban_members or perms.manage_guild:
                        skip_reason = "admin/moderator permissions"
                        should_skip = True
                    # 2. Check for the Specific Protected Role ID
                    elif is_protected_by_role:
                        skip_reason = f"protected role ID {PROTECTED_ROLE_ID}"
                        should_skip = True
                    
                    
                    if should_skip:
                        print(f"🛑 SKIPPED KICK: User {user_display} is protected by {skip_reason} in {member_to_kick.guild.name}.")
                        return
                    # --- END UPDATED CHECK ---
                    
                    try:
                        # Check bot's permissions to ensure it can kick
                        if member_to_kick.guild.me.guild_permissions.kick_members:
                            # Attempt to kick the user
                            await member_to_kick.kick(reason=kick_reason)
                            print(f"✅ Successfully KICKED user {user_display} from {member_to_kick.guild.name}.")
                        else:
                            print(f"❌ Cannot kick {user_display}: Bot lacks 'Kick Members' permission in {member_to_kick.guild.name}.")
                    except discord.Forbidden:
                        print(f"❌ Cannot kick {user_display}: Bot lacks permissions (Forbidden error).")
                    except discord.HTTPException as e:
                        print(f"❌ Failed to kick {user_display} due to HTTP error: {e}")
                else:
                    print(f"⚠️ Could not find user {user_display} as a member in any shared guild. Cannot kick.")

    # -------------------------------------------------------------


    def new_member_process(self, member: Union[discord.Member, discord.User]):
        """Process a new member joining the server or sending a message."""
        user_db = self.get_user_db_cog()
        if not user_db:
            print(f"❌ Cannot process user {member.id}: UserDatabase cog not loaded.")
            return
        
        try:
            # Check if user exists. If not, add them.
            if not user_db.check_user_exists(member.id):
                joined_at_iso = member.joined_at.isoformat() if isinstance(member, discord.Member) and member.joined_at else datetime.now(timezone.utc).isoformat()
                user_db.add_new_user(member.id, joined_at_iso)
                
                # Initial score update - this will dispatch the custom event!
                user_db.update_user_score(member.id, 25)
                
                account_age = self.get_account_age(member)
                
                # Initial warning/score logic - this will dispatch the custom event!
                if account_age and account_age.total_seconds() < 600:
                    user_db.update_user_warnings(member.id, 25)
                    print(f"⚠️ User {member.id} is new (age < 10min), applied 25 warnings.")
                else:
                    user_db.update_user_score(member.id, 100)
                    print(f"✅ User {member.id} is established, applied 100 score.")

            # else: print(f"ℹ️ User {member.id} already exists in database.") # Optional: keep log minimal
        except Exception as e:
            print(f"Error processing user {member.id}: {e}")


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event listener to add a user to the database when they join the server."""
        self.new_member_process(member)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return
        
        # Only process for new members who might not be in the DB yet
        self.new_member_process(message.author)


    # --- Slash Command to export database ---
    @app_commands.command(name="add_protected_role", description="Add a role to be protected from automatic kicks.")
    @app_commands.describe(role='The role to be protected from automatic kicks.')
    async def add_protected_role(self, interaction: discord.Interaction, role: discord.Role):
        await interaction.response.defer(ephemeral=True)

        # Here you would implement the logic to store this role ID in a persistent way
        # For simplicity, we'll just set it in the cog instance variable
        self.PROTECTED_ROLE_ID = role.id

        await interaction.followup.send(f"✅ Role **{role.name}** (ID: {role.id}) has been added to the protected roles list.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserManager(bot))