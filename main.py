import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv() 
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN is None:
    raise ValueError("Please set the DISCORD_TOKEN environment variable.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True # needed for ban functionality

bot = commands.Bot(command_prefix="!", intents=intents)

#when bot is activated, classes are loaded
@bot.event
async def setup_hook():
    #await bot.load_extension('ban_clanker_slop')
    #print("✅ BanFilter cog loaded")
    #await bot.load_extension('role_reaction')
    #print("✅ IntroReactionRole cog loaded")
    await bot.load_extension('user_databse')
    print("✅ user_databse cog loaded")
    await bot.load_extension('score_manager')
    print("✅ score_manager cog loaded")
    await bot.load_extension('user_manager')
    print("✅ user_manager cog loaded")


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    # --- ADDED: Sync slash commands on startup ---
    await bot.tree.sync()
    print("✅ Slash commands synced.")
    # ---------------------------------------------

# Command to delete a specific number of messages
@bot.command()
@commands.has_permissions(manage_messages=True)  # only users with manage_messages can call this
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
    await ctx.send(f"🗑️ Deleted {amount} messages.", delete_after=5)  # auto-deletes confirmation

# Run the bot with the token from .env
bot.run(TOKEN)