from discord.ext import commands
import discord

class RoleManager(commands.Cog):
    def init(self, bot):
        self.bot = bot

    def get_role(self, guild, role_name):
        return discord.utils.get(guild.roles, name = role_name)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Event: A new member joins the server.
        Purpose: Assign them the 'Base (PNM)' role for the server.
        """

        #assign the role to a value
        base_role = self._get_role(member.guild, "Base")

        #assign the role to new members
        if base_role: #role is on the server
            await member.add_roles(base_role)
            print(f"assigned base role to {member.name}")
        else: #is not on server
            print("base role is not present on this server (please create a role named 'Base' in order for the bot to work)")

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Event: A message is sent in the server.
        Purpose: Promote users from 'Base' to 'Member' when they post in #introductions.
        """

        #ignore messages sent by bots
        if message.author.bot:
            return
        
        #was a message sent in intro
        if message.channel.name == "introductions":

            base_role = self._get_role(message.guild, "Base")  #get base & member
            member_role = self._get_role(message.guild, "Member")

            #does user have base role & is member role available
            if base_role in message.author.roles:
                if member_role: #delete base role, add member
                    await message.author.remove_roles(base_role)
                    await message.author.add_roles(member_role)
                    print(f"promoted {message.author.name} from Base to Member")
                else: 
                    print("Member role is not present on this server (please create a role named 'Member' for this to work!!)")

async def setup(bot):
    await bot.add_cog(RoleManager(bot))

    #TEST THESE NEXT MEETING !!!