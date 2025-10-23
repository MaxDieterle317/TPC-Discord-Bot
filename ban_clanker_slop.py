from discord.ext import commands
import discord
import asyncio

async def load_extensions(): #loads and runs BanFilter class
    await bot.load_extension('ban_clanker_slop') 

asyncio.run(load_extensions())

class BanFilter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #keyword list to indicate slop
        self.banned_keywords = ["free", "cheap", "discord support"]

        #minimum account age (in minutes) required for a user to post without being banned
        self.min_account_age = 10

    @commands.Cog.listener()
    async def on_message(self, message): #ignore messages from the bot itself and server admins
        if message.author == self.bot.user or isinstance(message.author, discord.User):
            return
        
        #how old is the users account?
        #(in minutes, subtracts current UTC time by the exact time the poster account has been created)
        account_age = (discord.utils.utcnow() - message.author.created_at).total_seconds() / 60 

        #if an account is too young? banned!
        if account_age < self.min_account_age:
            await message.channel.send(
                f"{message.author.mention} banned: account too new",
                delete_after=5
            )
            await message.author.ban(reason="Account too new, clanker.")
            return
        
        #check if the message contains any keywords
        if any(keyword in message.content.lower() for keyword in self.banned_keywords):
            await message.channel.send(
                f"{message.author.mention} banned: slop keyword detected",
                delete_after = 5 
            )
            await message.author.ban(reason="Slop posting, clanker")
            return

#allows the bot to load the Cog
async def setup(bot):
    await bot.add_cog(BanFilter(bot))

    #TEST THESE NEXT MEETING !!!