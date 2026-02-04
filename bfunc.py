import discord
import decimal
import math
import os
import time
import traceback
from discord.ext import commands, tasks
from os import listdir
from os.path import isfile, join
import asyncio
from pymongo import MongoClient
import re

from itertools import cycle

from pymongo import UpdateOne

from secret import *

cogs_dir = "cogs"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

async def traceBack (ctx,error,silent=False):
    ctx.command.reset_cooldown(ctx)
    etype = type(error)
    trace = error.__traceback__

    # 'traceback' is the stdlib module, `import traceback`.
    lines = traceback.format_exception(etype,error, trace)

    # format_exception returns a list with line breaks embedded in the lines, so let's just stitch the elements together
    traceback_text = ''.join(lines) +f"\n{ctx.message.author.mention}"

    dorfer = bot.get_user(203948352973438995)

    if not silent:
        length = len(traceback_text)
        while(length>1994):
            x = traceback_text[:1994]
            x = x.rsplit("\n", 1)[0]
            await dorfer.send(content=f"```{x}```")
            traceback_text = traceback_text[len(x):]
            length -= len(x)
        await dorfer.send(content=f"```{traceback_text}```")
        await ctx.channel.send(f"Uh oh, looks like this is some unknown error I have ran into. {dorfer.mention} has been notified.")
    raise error

def refreshKey (timeStarted):
    if (time.time() - timeStarted > 60 * 59):
            gClient.login()
            print("Sucessfully refreshed OAuth")
            global refreshTime
            refreshTime = time.time()
    return

# token = os.environ['TOKEN']
currentTimers = {}

gameCategory = ["🎲 game rooms", "🐉 campaigns", "mod friends"]
roleArray = ['New', 'Junior', 'Journey', 'Elite', 'True', 'Ascended', '']
commandPrefix = '$'
timezoneVar = 'US/Eastern'

cp_bound_array = [[4, "4"], [10, "10"], [10, "10"], [10, "10"], [9999999999, "∞"]]

left = '\N{BLACK LEFT-POINTING TRIANGLE}'
right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
back = '\N{LEFTWARDS ARROW WITH HOOK}'

numberEmojis = ['0️⃣', '1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣']

alphaEmojis = ['🇦','🇧','🇨','🇩','🇪','🇫','🇬','🇭','🇮','🇯','🇰',
'🇱','🇲','🇳','🇴','🇵','🇶','🇷','🇸','🇹','🇺','🇻','🇼','🇽','🇾','🇿']

statuses = [f'D&D Friends | {commandPrefix}help', "We're all friends here!", f"See a bug? tell @MSchildorfer!", "Practicing social distancing!", "Wearing a mask!", "Being a good boio.", "Vibing", "Hippity Hoppity", "These Logs Are My Property", "UwU", "Morbin", "Angy", "O.O", "ABOUT TO LOG ALL OVER YOU"]
discordClient = discord.Client(intents = intents)
@tasks.loop(minutes=10)
async def change_status():
    await bot.wait_until_ready()
    statusLoop = cycle(statuses)
    while not bot.is_closed():
        current_status = next(statusLoop)
        await bot.change_presence(activity=discord.Activity(name=current_status, type=discord.ActivityType.watching))
        await asyncio.sleep(5)

class FriendBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commandPrefix, case_insensitive=True, intents = intents)

    async def setup_hook(self):
        change_status.start()
        for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
            try:
                print(extension)
                await bot.load_extension(cogs_dir + "." + extension)
            except (discord.ClientException, ModuleNotFoundError):
                print(f'Failed to load extension {extension}.')
                traceback.print_exc()

    async def close(self):
        await super().close()
        #await self.session.close()


    async def on_ready(self):
        print('We have logged in as ' + self.user.name)

bot = FriendBot()
connection = MongoClient(mongoConnection, ssl=True) 
db = connection.dnd

settings = db.settings

global settingsRecord
settingsRecord = list(settings.find())[0]
# get all entries of the relevant DB and extract the Text field and compile as a list and assign to the dic
liner_dic = {"Find" : list([line["Text"] for line in db.liners_find.find()]),
             "Meme" : list([line["Text"] for line in db.liners_meme.find()]),
             "Craft" : list([line["Text"] for line in db.liners_craft.find()]),
             "Money" : list([line["Text"] for line in db.liners_money.find()])}
