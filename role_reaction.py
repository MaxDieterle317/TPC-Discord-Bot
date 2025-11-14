from discord.ext import commands
import discord

INTRO_CHANNEL_NAME = "introductions"
ROLE_NAME = "reacted to intro"

class IntroReactionRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        #confirm the cog is active
        print(f"IntroReactionRole loaded. Monitoring pinned message reactions in #{INTRO_CHANNEL_NAME}.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        #get memeber from payload 
        member = payload.member
        if member is None:
            member = guild.get_member(payload.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(payload.user_id)
            except discord.HTTPException:
                return

        #ignore bots 
        if member.bot:
            return

        #ensure the channel is there
        channel = self.bot.get_channel(payload.channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except discord.HTTPException:
                return

        #only check the introductions channel
        if isinstance(channel, discord.abc.GuildChannel):
            if channel.name != INTRO_CHANNEL_NAME:
                return
        else:
            #not a channel
            return

        #find the pinned message
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.HTTPException:
            return

        if not message.pinned:
            return

        #locate the member role 
        role = discord.utils.get(guild.roles, name=ROLE_NAME)
        if role is None:
            print(f"Role '{ROLE_NAME}' not found in guild '{guild.name}'.")
            return

        #assign the role
        if role not in member.roles:
            try:
                await member.add_roles(role, reason="Reacted to pinned intro message")
                print(f"Gave '{ROLE_NAME}' to {member} for reacting to pinned intro message.")
            except discord.Forbidden:
                print("Missing permissions to add roles.")
            except discord.HTTPException:
                print("Failed to add role due to HTTP error.")

async def setup(bot: commands.Bot):
    await bot.add_cog(IntroReactionRole(bot))
