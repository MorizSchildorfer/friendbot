import discord
import asyncio 
from discord.ext import commands
from bfunc import traceBack

class Suggestions(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    
    async def cog_command_error(self, ctx, error):
        msg = None
        
        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your parameter types were off."
        
        elif isinstance(error, commands.CheckFailure):
            msg = ""
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "You missed a parameter"

        if msg:
            
            await ctx.channel.send(msg)
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             return

        # Whenever there's an error with the parameters that bot cannot deduce
        elif isinstance(error, commands.CommandInvokeError):
            msg = f'The command is not working correctly. Please try again and make sure the format is correct.'
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
            await traceBack(ctx,error, False)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
            
    def is_private_channel():
        async def predicate(ctx):
            return ctx.channel.type == discord.ChannelType.private
        return commands.check(predicate)
        
    @commands.command()
    @is_private_channel()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    async def suggestion(self, ctx, *, response):
        msg = ctx.message
        await ctx.channel.send(content='Thanks! Your suggestion has been submitted and will be reviewed by the Admin and Mod teams.')
            
        # suggestion channel
        channelID = 382031984471310336
        channel = self.bot.get_channel(channelID)
        files =None
        if msg.attachments:
            files =[]
            for att in msg.attachments:
                files.append(await att.to_file())
        botMsg = await channel.send(f"Incoming Suggestion by {ctx.message.author.mention}", 
                        files= files)
                        
        embed = discord.Embed()
        embed.description = response
        embed.set_author(name=msg.author, icon_url=msg.author.display_avatar)
        await botMsg.edit(content="", embed=embed)
        await botMsg.add_reaction('✅')
        await botMsg.add_reaction('❌')
            
    @commands.command()
    @is_private_channel()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    async def inbox(self, ctx):
        msg = ctx.message
         
            
        text = f"""Hello {msg.author.name}! 

Thank you for showing interest in improving the server. When submitting a suggestion, be as detailed as possible and include your reasoning for it. You can also include pictures and external links.

Your suggestion will be sent to the Admins and Mods where it will be reviewed on a rolling basis, or at the next Mod Meeting. Submitting a suggestion will generally have it discussed by the mod team but is not a guarantee of implementation. 

If you want to discuss your suggestion with others, feel free to talk about it in the `#general-dnd` or `#general-off-topic` channels on the server. Additionally, feel free to discuss suggestions during Town Hall events and Office Hours events.

If you wish to have a mod follow up with you once a decision is made, note so here, as well as if you wish to be credited if the idea is implemented on server.

Please copy-paste the following template and reply to me with your filled out template:

Thank you and have a good day! 
```$suggestion

Your suggestion here.```
"""
        await ctx.channel.send(content=text)
                
async def setup(bot):
    await bot.add_cog(Suggestions(bot))
