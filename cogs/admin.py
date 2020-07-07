import discord
import asyncio
import requests
import re
from discord.utils import get        
from discord.ext import commands

def admin_or_owner():
    async def predicate(ctx):
        
        role = get(ctx.message.guild.roles, name = "Admin")
        output = (role in ctx.message.author.roles) or ctx.message.author.id in [220742049631174656, 203948352973438995]
        return  output
    return commands.check(predicate)

class Admin(commands.Cog, name="A d m i n"):
    def __init__ (self, bot):
        self.bot = bot
    
    #this function allows you to specify a channel and message and have the bot react with a given emote
    #Not tested with emotes the bot might not have access to
    @commands.group()
    @admin_or_owner()
    async def react(self, ctx, channel: int, msg: int, emote: str):
        ch = ctx.guild.get_channel(channel)
        message = await ch.fetch_message(msg)
        await message.add_reaction(emote)
        await ctx.message.delete()
    
    @commands.group()
    @admin_or_owner()
    async def reload(self, ctx, cog: str):
        
        try:
            self.bot.reload_extension('cogs.'+cog)
            print(f"{cog} has been reloaded")
        except commands.ExtensionNotLoaded as e:
            try:
                self.bot.load_extension("cogs." + cog)
                print(f"{cog} has been added")
            except (discord.ClientException, ModuleNotFoundError):
                print(f'Failed to load extension {extension}.')
                traceback.print_exc()
        except Exception as e:
            print(e)


def setup(bot):
    bot.add_cog(Admin(bot))
