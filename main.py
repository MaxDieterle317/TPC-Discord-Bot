import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# Command to delete a specific number of messages
@bot.command()
@commands.has_permissions(manage_messages=True)  # only users with manage_messages can call this
async def clear(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)  # +1 to include the command message
    await ctx.send(f"🗑️ Deleted {amount} messages.", delete_after=5)  # auto-deletes confirmation

# Run the bot with the token from .env
bot.run(TOKEN)
