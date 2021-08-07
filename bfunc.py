import discord
from discord.ext import commands
from pymongo import MongoClient
from secret import *

intents = discord.Intents.default()
intents.members = True



currentTimers = []

gameCategory = ["🎲 game rooms", "🐉 campaigns", "mod friends"]
roleArray = ['New', 'Junior', 'Journey', 'Elite', 'True', 'Ascended', '']
noodleRoleArray = ['Good Noodle', 'Elite Noodle', 'True Noodle', 'Ascended Noodle', 'Immortal Noodle', 'Eternal Noodle']
commandPrefix = '$'
timezoneVar = 'US/Eastern'

tier_reward_dictionary = [[50, 0.5], [100, 0.5], [150, 1], [200, 1], [200, 1]]

cp_bound_array = [[4, "4"], [10, "10"], [10, "10"], [10, "10"], [9999999999, "∞"]]


left = '\N{BLACK LEFT-POINTING TRIANGLE}'
right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
back = '\N{LEFTWARDS ARROW WITH HOOK}'

alphaEmojis = ['🇦','🇧','🇨','🇩','🇪','🇫','🇬','🇭','🇮','🇯','🇰',
'🇱','🇲','🇳','🇴','🇵','🇶','🇷','🇸','🇹','🇺','🇻','🇼','🇽','🇾','🇿']

statuses = [f'D&D Friends | {commandPrefix}help', "We're all friends here!", f"See a bug? tell @MSchildorfer!", "Practicing social distancing!", "Wearing a mask!", "Being a good boio.", "Vibing", "Hippity Hoppity", "These Logs Are My Property"]
discordClient = discord.Client()
bot = commands.Bot(command_prefix=commandPrefix, case_insensitive=True, intents = intents)

connection = MongoClient(mongoConnection, ssl=True) 
db = connection.dnd

settings = db.settings

global settingsRecord
settingsRecord = list(settings.find())[0]
# get all entries of the relevant DB and extract the Text field and compile as a list and assign to the dic
liner_dic = {"Find" : list([line["Text"] for line in db.liners_find.find()]),
             "Meme" : list([line["Text"] for line in db.liners_meme.find()]),
             "Craft" : list([line["Text"] for line in db.liners_craft.find()])}

