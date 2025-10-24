from discord.ext import commands
import discord

INTRO_CHANNEL_NAME = "introductions"
ROLE_NAME = "write intro"

class IntroReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Simple confirmation in logs so we know the cog is active
        print(f"✅ IntroReactionRole loaded. Monitoring pinned message reactions in #{INTRO_CHANNEL_NAME}.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Ignore DMs
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        # Get member from payload or fetch as fallback
        member = payload.member
        if member is None:
            member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return

        # Ignore bot reactions
        if member.bot:
            return

        # Resolve channel
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except discord.HTTPException:
                return

        # Only act in the introductions channel (by name)
        if isinstance(channel, discord.abc.GuildChannel):
            if channel.name != INTRO_CHANNEL_NAME:
                return
        else:
            # Not a guild text channel
            return

        # Fetch the message and ensure it's pinned
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        if not message.pinned:
            return

        # Locate the role
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is None:
            print(f"⚠️ Role '{ROLE_NAME}' not found in guild '{guild.name}'.")
            return

        # Assign role if the member doesn't already have it
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Reacted to pinned intro message")
                print(f"✅ Gave '{ROLE_NAME}' to {member} for reacting to pinned intro message.")
            except discord.Forbidden:
                print("❌ Missing permissions to add roles.")
            except discord.HTTPException:
                print("❌ Failed to add role due to HTTP error.")

async def setup(bot: commands.Bot):
    await bot.add_cog(IntroReactionRole(bot))
