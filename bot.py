import asyncio
import traceback
from discord.ext import commands, tasks
from os import listdir
from os.path import isfile, join
from itertools import cycle
import aiohttp
from random import sample
from bfunc import *
from cogs.util import uwuize

cogs_dir = "cogs"

# Files to check for server differences: logs, timer, misc

# Things that can change
# ~ Server roles.
# ~ Quest Board.
# ~ Session Logs.
# ~ Campaign Board.
# ~ Applications.
# ~ Game Rooms (including timers).
# ~ General Rooms (excluding timers).
# ~ Suggestions.
# ~ General Reports.
# ~ Staff Reports.

if __name__ == '__main__':
    pass


bot.remove_command('help')
@bot.event
async def on_command_error(ctx,error):
    msg = None
    
    if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
        await ctx.channel.send("There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command. ")
        #bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
        ctx.command.reset_cooldown(ctx)
        return
    
    elif ctx.cog is not None and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
        return
        
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

    elif isinstance(error, commands.CommandNotFound):
        if (ctx.invoked_with.isnumeric()):
            await ctx.channel.send(f'{sample(liner_dic["Money"], 1)[0]}'.replace("<cashmoney>", f"${ctx.invoked_with}").replace("<user>", ctx.author.display_name))
        else:
            await ctx.channel.send(f'Sorry, the command **`{commandPrefix}{ctx.invoked_with}`** is not valid, please try again!')
        return 
    else:
        ctx.command.reset_cooldown(ctx)
        await traceBack(ctx,error)
    print(ctx.invoked_with)
    print(error)


bot.run(token)