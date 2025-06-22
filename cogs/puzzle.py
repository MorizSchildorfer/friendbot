import discord
import asyncio
import requests
import re
from discord.utils import get        
from discord.ext import commands
from bfunc import db, commandPrefix, traceBack, alphaEmojis
from cogs.util import disambiguate
import traceback as traces
from functools import reduce


class Node():
    def __init__ (self, latch_node = None, input_node = None, out_connections = []):
        self.out_connections = out_connections
        self.input_node = input_node
        self.latch_node = latch_node
        self.value = False
    
    def update(self):
        if not self.latch_node.get_value() or self.input_node.get_value() == self.value:
            return
        self.value = self.input_node.get_value()
        for connection in self.out_connections:
            connection.update()
    
    def get_value(self):
        return self.value
        
        
class Negation():
    def __init__ (self, input_node = None, out_connections = []):
        self.out_connections = out_connections
        self.input_node = input_node
        self.value = input_node and not input_node.get_value()
    
    def update(self):
        if self.input_node.get_value() != self.value:
            return
        self.value = not self.input_node.get_value()
        for connection in self.out_connections:
            connection.update()
    
    def get_value(self):
        return self.value
        
class Or():
    def __init__ (self, input_nodes = [], out_connections = []):
        self.out_connections = out_connections
        self.input_nodes = input_nodes
        self.value = reduce(lambda soFar, n: soFar or n.get_value(), [False] + input_nodes)
    
    def update(self):
        temp = reduce(lambda soFar, n: soFar or n.get_value(), [False] + self.input_nodes)
        if temp == self.value:
            return
        self.value = temp
        for connection in self.out_connections:
            connection.update()
    
    def get_value(self):
        return self.value
        
class Button():
    def __init__ (self, out_connections = []):
        self.out_connections = out_connections
        self.value = False
    
    def toggle(self):
        self.value = not self.get_value()
        for connection in self.out_connections:
            connection.update()
    
    def get_value(self):
        return self.value

class Puzzle(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command **`{commandPrefix}{ctx.invoked_with}`** requires an additional keyword to the command or is invalid, please try again!')
            return
            
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
            return
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'charName':
                msg = "You're missing your character name in the command. "
            elif error.param.name == "mItem":
                msg = "You're missing the item you want to acquire in the command. "
            elif error.param.name == "tierNum":
                msg = "You're missing the tier for the TP you want to abandon. "
        elif isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "The amount you want to acquire must be a number. "
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):

             return
           
        ctx.command.reset_cooldown(ctx)
        await traceBack(ctx,error)
    
    def is_private_channel():
        async def predicate(ctx):
            return ctx.channel.type == discord.ChannelType.private
        return commands.check(predicate)
        
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_private_channel()
    @commands.command()
    async def puzzle(self, ctx):
        channel = ctx.channel
        author = ctx.author
        pEmbed = discord.Embed()
        
        button1 = Button()
        button2 = Button()
        button3 = Button()
        latch1 = Node(button1, button2)
        latch2 = Node(button2, button3)
        latch3 = Node(button3, button1)
        or1 = Or([button1, button2, button3])
        neg1 = Negation(button2)
        neg2 = Negation(latch3)
        neg3 = Negation(or1)
        button1.out_connections = [latch1, latch3, or1]
        button2.out_connections = [latch1, latch2, neg1, or1]
        button3.out_connections = [latch2, latch3, or1]
        latch3.out_connections = [neg2]
        or1.out_connections = [neg3]
        buttons = [button1, button2, button3]
        outputs = [latch1, latch2, neg2, neg1, neg3]
        emotes = [":red_circle:", ":green_circle:"]
        b = "  ".join([emotes[x.get_value()] for x in buttons])
        l = "  ".join([emotes[x.get_value()] for x in outputs])
        blank_space = "  ".join([":black_circle:"]*len(outputs))
        def puzzle_text():
            flavor_text = "Mighty adventurer, you have arrived at a giant gate blocking your path. At its foot is a magical mechanism to unlock it. There seem to be 3 buttons you can press and 5 sigils that light up. Can you open this mighty gate?"
            
            return f"{flavor_text}\n\n:black_circle: {b} :black_circle:\n{blank_space}\n{l}"
        pEmbed.title = "Dorfer's Magic Puzzle"
        pEmbed.description = puzzle_text()
        pmsg = await channel.send(embed=pEmbed)
        
        active = True
        count = 0
        while active:
            choice = await disambiguate(len(buttons), pmsg, author)
            if choice is None or choice == -1:
                break
            count += 1
            buttons[choice].toggle()
            b = " ".join([emotes[x.get_value()] for x in buttons])
            l = " ".join([emotes[x.get_value()] for x in outputs])
            pEmbed.description = puzzle_text()
            await pmsg.edit(embed=pEmbed)
            if all([x.get_value() for x in outputs]):
                pEmbed.description = f":black_circle: {b} :black_circle:\n{blank_space}\n{l}\n\nYou have released the seal on the door with {count} presses! By either luck or skill you may pass."
                await pmsg.edit(embed=pEmbed)
                break
        self.bot.get_command('puzzle').reset_cooldown(ctx)
        
async def setup(bot):
    await bot.add_cog(Puzzle(bot))