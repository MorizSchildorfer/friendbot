import discord
import asyncio 
from discord.ext import commands
from bfunc import traceBack, commandPrefix

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
            commandParent = ctx.command.parent
            if commandParent is None:
                commandParent = ''
            else:
                commandParent = commandParent.name + " "

            if error.retry_after == float('inf'):
                await ctx.channel.send(f"Sorry, the command **`{commandPrefix}{commandParent}{ctx.invoked_with}`** is already in progress, please complete the command before trying again.")
            else:
                await ctx.channel.send(f"Sorry, the command **`{commandPrefix}{commandParent}{ctx.invoked_with}`** is on cooldown for you! Try the command in the next " + "{:.1f}seconds".format(error.retry_after))
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

Your suggestion will be sent to the Admins and Mods where it will be reviewed on a rolling basis, or at the next Mod Meeting.

Feel free to discuss your suggestion with others in the relevant general chats. Or if you would prefer to talk about it during office hours or town hall, please don't hesitate to reach out.

Please copy-paste the following template and reply to me with your filled out template:

Thank you and have a good day!

```$suggestion

Your suggestion here.```
"""
        await ctx.channel.send(content=text)
        
    @commands.command()
    @is_private_channel()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    async def report(self, ctx, *, response = ""):
        response = response.strip()
        if not response:
            text = f"""This report is by default anonymous, you may add your discord ID at the end
The report should follow the following format:
```
$report
- Who are you reporting?
- When did it happen?
- Where did it happen? (In a game, in gen chat or other)
- Describe the incident in as much detail as possible.
- [optional] @yourself (to not be anonymous)
- [optional] attach files (via links. you can send them as a separate message [not $report] and right click copy link)
```
    """
            await ctx.channel.send(content=text)
            return
            
        msg = ctx.message
        await ctx.channel.send(content='Thanks! Your suggestion has been submitted and will be reviewed by the Admin and Mod teams.')
            
        # suggestion channel
        channelID = 390727227899248651
        channel = self.bot.get_channel(channelID)
        files =None
        if msg.attachments:
            files =[]
            for att in msg.attachments:
                files.append(await att.to_file())
        botMsg = await channel.send(f"<@&382052033987084288> Incoming Report", 
                        files= files)
                        
        embed = discord.Embed()
        embed.description = response
        await botMsg.edit(content=f"<@&382052033987084288> Incoming Report", embed=embed)
                
async def setup(bot):
    await bot.add_cog(Suggestions(bot))
