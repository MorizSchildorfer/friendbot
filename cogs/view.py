
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
class TestView(discord.ui.View):
    def __init__(self, author):
        super().__init__()
        
        self.add_item(discord.ui.TextInput(label="Text"))
        
class Report(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=86400)
        self.value = None
     
    @discord.ui.button(label="Report", style=discord.ButtonStyle.red)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(Feedback()) # 
class Feedback(discord.ui.Modal, title='Feedback'):
    # Our modal classes MUST subclass `discord.ui.Modal`,
    # but the title can be whatever you want.

    # This will be a short input, where the user can enter their name
    # It will also have a placeholder, as denoted by the `placeholder` kwarg.
    # By default, it is required and is a short-style input which is exactly
    # what we want.
    name = discord.ui.TextInput(
        label='Name',
        placeholder='Your name here...',
    )

    # This is a longer, paragraph style input, where user can submit feedback
    # Unlike the name, it is not required. If filled out, however, it will
    # only accept a maximum of 300 characters, as denoted by the
    # `max_length=300` kwarg.
    feedback = discord.ui.TextInput(
        label='What do you think of this new feature?',
        style=discord.TextStyle.long,
        placeholder='Type your feedback here...',
        required=False,
        max_length=300,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Thanks for your feedback, {self.name.value}!', ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)
class Views(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    
                
async def setup(bot):
    await bot.add_cog(Views(bot))

