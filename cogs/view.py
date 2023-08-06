
import discord
import asyncio
from discord.utils import get        
from discord.ext import commands
from bfunc import traceBack, alphaEmojis


# Define a simple View that gives us a counter button
class AlphaButton(discord.ui.Button):
    
    def __init__(self, pos: int, emoji):
        super().__init__(style=discord.ButtonStyle.secondary, emoji=emoji)
        self.pos = pos
        self.value = emoji
    
    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AlphaView = self.view
        if interaction.user != view.author:
            return
        view.state = self.pos
        await interaction.response.defer()
        view.stop()

class CancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.danger, emoji='✖️')
    
    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AlphaView = self.view
        if interaction.user != view.author:
            return
        view.state = -1
        view.stop()       
class ConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.success, emoji='✅')
    
    # This function is called whenever this particular button is pressed
    # This is part of the "meat" of the game logic
    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: AlphaView = self.view
        if interaction.user != view.author:
            return
        view.state = 1
        view.stop()  
class AlphaView(discord.ui.View):
    
    def __init__(self, count: int, author, emojies, cancel=False):
        super().__init__()
        self.author = author
        self.state = None
        for i in range(0, count):
            self.add_item(AlphaButton(i, emojies[i%len(emojies)]))
        if cancel:
            self.add_item(CancelButton())
class ConfirmView(discord.ui.View):
    def __init__(self, author):
        super().__init__()
        self.author = author
        self.state = None
        self.add_item(ConfirmButton())
        self.add_item(CancelButton())

class Views(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    
                
async def setup(bot):
    await bot.add_cog(Views(bot))

