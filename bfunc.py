import discord
import gspread
import decimal
import math
import os
import time
import traceback
# import json
import requests
from discord.ext import commands
import asyncio
from oauth2client.service_account import ServiceAccountCredentials
from pymongo import MongoClient
import re

from pymongo import UpdateOne

from secret import *

intents = discord.Intents.default()
intents.members = True


def timeConversion (time,hmformat=False):
        hours = time//3600
        time = time - 3600*hours
        minutes = time//60
        if hmformat is False:
            return ('%d Hours %d Minutes' %(hours,minutes))
        else:
            return ('%dh%dm' %(hours,minutes))
        
		
# def getTiers (tiers):
#     getTierArray = []
#     for i in range(len(tiers)):
#         if tiers[i] != "":
#             getTierArray.append(i)
#     getTierArray.append(len(sheet.row_values(3)) + 1)

#     return getTierArray

async def traceBack (ctx,error,silent=False):
    ctx.command.reset_cooldown(ctx)
    etype = type(error)
    trace = error.__traceback__

    # the verbosity is how large of a traceback to make
    # more specifically, it's the amount of levels up the traceback goes from the exception source
    #verbosity = -6

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


def calculateTreasure(level, charcp, tier, seconds, death=False, gameID="", guildDouble=False, playerDouble=False, dmDouble=False, gold_modifier = 100):
    # calculate the CP gained during the game
    cp = ((seconds) // 1800) / 2
    cp_multiplier = 1 + guildDouble + playerDouble + dmDouble
       
        
    crossTier = None
    
    # calculate the CP with the bonuses included
    cp *= cp_multiplier
    
    gainedCP = cp
    
    #######role = role.lower()
    
    tier = 5
    # calculate the tier of the rewards
    if level < 5:
        tier = 1
    elif level < 11:
        tier = 2
    elif level < 17:
        tier = 3
    elif level < 20:
        tier = 4
        
    #unreasonably large number as a cap
    cpThreshHoldArray = [16, 16+60, 16+60+60, 16+60+60+30, 90000000]
    # calculate how far into the current level CP the character is after the game
    leftCP = charcp
    gp= 0
    tp = {}
    charLevel = level
    while(cp>0):
        
        # Level 20 characters haves access to exclusive items
        # create a string representing which tier the character is in in order to create/manipulate the appropriate TP entry in the DB
        tierTP = f"T{tier} TP"
        # the level of the character
        
        levelCP = (((charLevel-5) * 10) + 16)
        if charLevel < 5:
            levelCP = ((charLevel -1) * 4)
            charLevel = 5
        elif charLevel < 11:
            charLevel = 11
        elif charLevel < 17:
            charLevel = 17
        elif charLevel < 20:
            charLevel = 20
            
        if levelCP + leftCP + cp > cpThreshHoldArray[tier-1]:
            consideredCP = cpThreshHoldArray[tier-1] - (levelCP + leftCP)
            leftCP = 0
        else:
            consideredCP = cp
        cp -=  consideredCP
        tp[tierTP] = consideredCP * tier_reward_dictionary[tier-1][1]
        gp += consideredCP * tier_reward_dictionary[tier-1][0]
        tier += 1
    gp = math.ceil(gold_modifier * gp/100)
    return [gainedCP, tp, int(gp)]
    
    
"""
The purpose of this function is to do a general call to the database
apiEmbed -> the embed element that the calling function will be using
apiEmbedmsg -> the message that will contain apiEmbed
table -> the table in the database that should be searched in, most common tables are RIT, MIT and SHOP
query -> the word which will be searched for in the "Name" property of elements, adjustments were made so that also a special property "Grouped" also gets searched
"""
async def callAPI(ctx, apiEmbed="", apiEmbedmsg=None, table=None, query=None, tier=5, exact=False, filter_rit=True):
    
    #channel and author of the original message creating this call
    channel = ctx.channel
    author = ctx.author
    
    #do nothing if no table is given
    if table is None:
       return None, apiEmbed, apiEmbedmsg

    collection = db[table]
    
    #get the entire table if no query is given
    if query is None:
        return list(collection.find()), apiEmbed, apiEmbedmsg

    #if the query has no text, return nothing
    if query.strip() == "":
        return None, apiEmbed, apiEmbedmsg

    #restructure the query to be more regEx friendly
  
    
    invalidChars = ["[", "]", "?", '"', "\\", "*", "$", "{", "}", "^", ">", "<", "|"]

    for i in invalidChars:
        if i in query:
            await channel.send(f":warning: Please do not use `{i}` in your query. Revise your query and retry the command.\n")
            return None, apiEmbed, apiEmbedmsg
         
    query = query.strip()
    query = query.replace('(', '\\(')
    query = query.replace(')', '\\)')
    query = query.replace('+', '\\+')
    query = query.replace('.', '\\.')
    query_data =  {"$regex": query,
                    #make the check case-insensitively
                    "$options": "i"
                  }
    if exact:
        query_data["$regex"] = f'^{query_data["$regex"]}$'
        
    #search through the table for an element were the Name or Grouped property contain the query
    if table == "spells":
        filterDic = {"Name": query_data}
    else:
        filterDic = {"$or": [
                            {
                              "Name": query_data
                            },
                            {
                              "Grouped": query_data
                            }
                        ]
                    } 
    if table == "rit" or table == "mit":
        filterDic['Tier'] = {'$lt':tier+1}
    
     
    # Here lies MSchildorfer's dignity. He copy and pasted with abandon and wondered why
    #  collection.find(collection.find(filterDic)) does not work for he could not read
    # https://cdn.discordapp.com/attachments/663504216135958558/735695855667118080/New_Project_-_2020-07-22T231158.186.png
    records = list(collection.find(filterDic))
    
    #turn the query into a regex expression
    r = re.compile(query, re.IGNORECASE)
    #restore the original query
    query = query.replace("\\", "")
    #sort elements by either the name, or the first element of the name list in case it is a list
    def sortingEntryAndList(elem):
        if(isinstance(elem['Name'],list)): 
            return elem['Name'][0] 
        else:  
            return elem['Name']
    
    #create collections to track needed changes to the records
    remove_grouper = [] #track all elements that need to be removes since they act as representative for a group of items
    faux_entries = [] #collection of temporary items that will act as database elements during the call
    
    #for every search result check if it contains a group and create entries for each group element if it does
    for entry in records:
        # if the element is part of a group
        if("Grouped" in entry):
            # remove it later
            remove_grouper.append(entry)
            # check if the query is more specific about a group element
            newlist = list(filter(r.search, entry['Name']))
            """
            if the every element has been filtered out because of the code above then we know from the fact 
            that this was found in the search that the Grouper field had to have been matched, 
            indicating that the entire group needs to be listed
            """
            if(newlist == list()):
                newlist = entry['Name']
            # for every group element that needs to be considered, create a new element with just the name adjusted
            for name in newlist:
                #copy the Group entry to get all relevant information about the item
                faux_entry = entry.copy()
                #change the name from the list to the specific element.
                faux_entry["Name"]= name
                #add it to the tracker
                faux_entries.append(faux_entry)
    # remove all group representatives
    for group_to_remove in remove_grouper:
        records.remove(group_to_remove)
    #append the new entries
    records += faux_entries
    if filter_rit and table == "rit":
        # get all minor reward item results
        all_minors = list([record["Name"] for record in filter(lambda record: record["Minor/Major"]== "Minor", records)])
        records = filter(lambda record: record["Minor/Major"]!= "Major" or record["Name"] not in all_minors, records)

    
    #sort all items alphabetically 
    records = sorted(records, key = sortingEntryAndList)    
    #if no elements are left, return nothing
    if records == list():
        return None, apiEmbed, apiEmbedmsg
    else:
        # if theres an exact match return
        # if 'Name' in records[0]:
            # print([r['Name'].lower() for r in records])
            # for r in records:
                # if query.lower() == r['Name'].lower():
                    # return r, apiEmbed, apiEmbedmsg
    
        #create a string to provide information about the items to the user
        infoString = ""
        if (len(records) > 1):
            #sort items by tier if the magic item tables were requested
            if table == 'mit' or table == 'rit':
                records = sorted(records, key = lambda i : i ['Tier'])
            queryLimit = 15
            #limit items to queryLimit
            for i in range(0, min(len(records), queryLimit)):
                if table == 'mit':
                    infoString += f"{alphaEmojis[i]}: {records[i]['Name']} (Tier {records[i]['Tier']}): **{records[i]['TP']} TP**\n"
                elif table == 'rit':
                    infoString += f"{alphaEmojis[i]}: {records[i]['Name']} (Tier {records[i]['Tier']} {records[i]['Minor/Major']})\n"
                # base spell scroll db entry should not be searched
                elif table == 'shop' and records[i]['Type'] == "Spell Scroll":
                    pass
                else:
                    infoString += f"{alphaEmojis[i]}: {records[i]['Name']}\n"
            #check if the response from the user matches the limits
            def apiEmbedCheck(r, u):
                sameMessage = False
                if apiEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((r.emoji in alphaEmojis[:min(len(records), queryLimit)]) or (str(r.emoji) == '❌')) and u == author and sameMessage
            #inform the user of the current information and ask for their selection of an item
            apiEmbed.add_field(name=f"There seems to be multiple results for \"**{query}**\"! Please choose the correct one.\nThe maximum number of results shown is {queryLimit}. If the result you are looking for is not here, please react with ❌ and be more specific.", value=infoString, inline=False)
            if not apiEmbedmsg or apiEmbedmsg == "Fail":
                apiEmbedmsg = await channel.send(embed=apiEmbed)
            else:
                await apiEmbedmsg.edit(embed=apiEmbed)
            # if len(records) <= 5:
                # for i in range(0, len(records)):
                    # await apiEmbedmsg.add_reaction(alphaEmojis[i])
                
            await apiEmbedmsg.add_reaction('❌')

            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
            except asyncio.TimeoutError:
                #stop if no response was given within the timeframe and reenable the command
                await apiEmbedmsg.delete()
                await channel.send('Timed out! Try using the command again.')
                ctx.command.reset_cooldown(ctx)
                return None, apiEmbed, "Fail"
            else:
                #stop if the cancel emoji was given and reenable the command
                if tReaction.emoji == '❌':
                    await apiEmbedmsg.edit(embed=None, content=f"Command cancelled. Try using the command again.")
                    await apiEmbedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, apiEmbed, "Fail"
            apiEmbed.clear_fields()
            #return the selected item indexed by the emoji given by the user
            await apiEmbedmsg.clear_reactions()
            return records[alphaEmojis.index(tReaction.emoji)], apiEmbed, apiEmbedmsg

        else:
            #if only 1 item was left, simply return it
            return records[0], apiEmbed, apiEmbedmsg

async def checkForChar(ctx, char, charEmbed="", authorOverride=None,  mod=False, customError=False, authorCheck=None):
    channel = ctx.channel
    author = ctx.author
    guild = ctx.guild
    if authorOverride != None:
        author = authorOverride
        mod=False
    search_author = author
    if authorCheck != None:
        search_author = authorCheck
        mod=False
    playersCollection = db.players

    query = char.strip()
    query = query.replace('(', '\\(')
    query = query.replace(')', '\\)')
    query = query.replace('.', '\\.')
    if mod == True:
        charRecords = list(playersCollection.find({"Name": {"$regex": query, '$options': 'i' }})) 
    else:
        charRecords = list(playersCollection.find({"User ID": str(search_author.id), "Name": {"$regex": query, '$options': 'i' }}))

    if charRecords == list():
        if not mod and not customError:
            await channel.send(content=f'I was not able to find your character named "**{char}**". Please check your spelling and try again.')
        ctx.command.reset_cooldown(ctx)
        return None, None

    else:
        if len(charRecords) > 1:
            infoString = ""
            charRecords = sorted(list(charRecords), key = lambda i : i ['Name'])
            for i in range(0, min(len(charRecords), 9)):
                infoString += f"{alphaEmojis[i]}: {charRecords[i]['Name']} ({guild.get_member(int(charRecords[i]['User ID']))})\n"
            
            def infoCharEmbedcheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((r.emoji in alphaEmojis[:min(len(charRecords), 9)]) or (str(r.emoji) == '❌')) and u == author and sameMessage

            charEmbed.add_field(name=f"There seems to be multiple results for \"`{char}`\"! Please choose the correct character. If you do not see your character here, please react with ❌ and be more specific with your query.", value=infoString, inline=False)
            charEmbedmsg = await channel.send(embed=charEmbed)
            await charEmbedmsg.add_reaction('❌')

            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=infoCharEmbedcheck, timeout=60)
            except asyncio.TimeoutError:
                await charEmbedmsg.delete()
                await channel.send('Character information timed out! Try using the command again.')
                ctx.command.reset_cooldown(ctx)
                return None, None
            else:
                if tReaction.emoji == '❌':
                    await charEmbedmsg.edit(embed=None, content=f"Character information cancelled. Try again using the same command!")
                    await charEmbedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, None
            charEmbed.clear_fields()
            await charEmbedmsg.clear_reactions()
            return charRecords[alphaEmojis.index(tReaction.emoji[0])], charEmbedmsg

    return charRecords[0], None

async def checkForGuild(ctx, name, guildEmbed="" ):
    channel = ctx.channel
    author = ctx.author
    guild = ctx.guild

    name = name.strip()

    collection = db.guilds
    guildRecords = list(collection.find({"Name": {"$regex": name, '$options': 'i' }}))


    if guildRecords == list():
        await channel.send(content=f'I was not able to find a guild named "**{name}**". Please check your spelling and try again.')
        ctx.command.reset_cooldown(ctx)
        return None, None
    else:
        if len(guildRecords) > 1:
            infoString = ""
            guildRecords = sorted(list(guildRecords), key = lambda i : i ['Name'])
            for i in range(0, min(len(guildRecords), 9)):
                infoString += f"{alphaEmojis[i]}: {guildRecords[i]['Name']}\n"
            
            def infoCharEmbedcheck(r, u):
                sameMessage = False
                if guildEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((r.emoji in alphaEmojis[:min(len(guildRecords), 9)]) or (str(r.emoji) == '❌')) and u == author and sameMessage

            guildEmbed.add_field(name=f"There seems to be multiple results for \"`{name}`\"! Please choose the correct character. If you do not see your character here, please react with ❌ and be more specific with your query.", value=infoString, inline=False)
            guildEmbedmsg = await channel.send(embed=guildEmbed)
            await guildEmbedmsg.add_reaction('❌')

            try:
                tReaction, tUser = await bot.wait_for("reaction_add", check=infoCharEmbedcheck, timeout=60)
            except asyncio.TimeoutError:
                await guildEmbedmsg.delete()
                await channel.send('Guild command timed out! Try again using the same command!')
                ctx.command.reset_cooldown(ctx)
                return None, None
            else:
                if tReaction.emoji == '❌':
                    await guildEmbedmsg.edit(embed=None, content=f"Guild command cancelled. Try again using the same command!")
                    await guildEmbedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None, None
            guildEmbed.clear_fields()
            await guildEmbedmsg.clear_reactions()
            return guildRecords[alphaEmojis.index(tReaction.emoji[0])], guildEmbedmsg

    return guildRecords[0], None

        
def refreshKey (timeStarted):
    if (time.time() - timeStarted > 60 * 59):
            gClient.login()
            print("Sucessfully refreshed OAuth")
            global refreshTime
            refreshTime = time.time()
    return

# use creds to create a client to interact with the Google Drive API
# gSecret = {
#   "type": "service_account",
#   "project_id": "magic-item-table",
#   "private_key_id": os.environ['PKEY_ID'],
#   "private_key": os.environ['PKEY'],
#   "client_email": os.environ['CEMAIL'],
#   "client_id": os.environ['C_ID'],
#   "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#   "token_uri": "https://oauth2.googleapis.com/token",
#   "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#   "client_x509_cert_url": os.environ['C_CERT']
# }

# scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
# creds = ServiceAccountCredentials.from_json_keyfile_dict(gSecret, scope)

# gClient = gspread.authorize(creds)
# refreshTime = time.time()

# Find a workbook by name and open the first sheet
# Make sure you use the right name here.
# sheet = gClient.open("Magic Items Document").sheet1
# ritSheet = gClient.open("Magic Items Document").get_worksheet(1)
# charDatabase = gClient.open("Character Database").worksheet("Character Database")
# refListSheet = gClient.open("Character Database").worksheet("Reference Lists")


# sheet = gClient.open("Magic Item Table").sheet1
# ritSheet = gClient.open("Reward Item Table").sheet1

# token = os.environ['TOKEN']
currentTimers = {}

gameCategory = ["🎲 game rooms", "🐉 campaigns", "mod friends"]
roleArray = ['New', 'Junior', 'Journey', 'Elite', 'True', 'Ascended', '']
noodleRoleArray = ['Good Noodle', 'Elite Noodle', 'True Noodle', 'Ascended Noodle', 'Immortal Noodle', 'Eternal Noodle']
# tierArray = getTiers(sheet.row_values(2))
# tpArray = sheet.row_values(3)
commandPrefix = '$'
timezoneVar = 'US/Eastern'

# ritTierArray = getTiers(ritSheet.row_values(2))
# ritSubArray = ritSheet.row_values(3)

tier_reward_dictionary = [[50, 0.5], [100, 0.5], [150, 1], [200, 1], [200, 1]]

cp_bound_array = [[4, "4"], [10, "10"], [10, "10"], [10, "10"], [9999999999, "∞"]]
# settingsRecord = {"QB List" : {781021043778781195 : 382025597041246210, 728476108940640297 : 259732415319244800},
                    # "Role Channel List" : {777046003832193034 : 382025597041246210, 781360717101400084 : 259732415319244800},
                    # 382025597041246210: 
                    # {"Sessions" : 737076677238063125, "QB" : 781021043778781195, 
                        # "CB" : 382027251618938880,
                        # "Player Logs" : 788158884329422848 ,
                        # "Game Rooms" : 575798293913796619, 
                        # "Guild Rooms" :452704598440804375,
                        # "Campaign Rooms" : 698784680488730666, 
                        # "Messages" : {777051070110498846: "Roll20", 777051209299132456: "Foundry"},
                        # "Emotes" : {"Roll20" : "<:roll20:777767592684421130>" , "Foundry": "<:foundry:777767632471719956>"}}, 
                  # 259732415319244800 : 
                    # {"Sessions" : 728456783466725427, "QB" : 728476108940640297, 
                        # "CB" : 781360342483075113,
                        # "Player Logs" : 728729922205647019 ,
                        # "Game Rooms" : 728456686024523810, 
                        # "Guild Rooms" : 734586911901089832,
                        # "Campaign Rooms" : 734276389322096700, 
                        # "Messages" : {781360780162760765: "Roll20", 781360787854852106: "Foundry"},
                        # "Emotes" : {"Roll20" : "<:adorabat:733763021008273588>" , "Foundry": "🗡️"}}}


# Quest Buffs - 2x Rewards, 2x Items, Recruitment Drive
questBuffsDict = {'2xRewards': [20, "2x CP,TP, and gp"], 
"2xItems - Small": [5,"+ 1 Tier 1 Minor Non-Consumable Reward"], 
"2xItems - Medium": [10, "+ 1 Same Tier or Lower Reward"], 
"2xItems - Large": [15,"Both of the above + 1 Tier 1 Minor Non-Consumable Reward"], 
"RD - Small":[4,"Small Guild Upgrade"], 
"RD - Medium": [6,"Small and Medium Upgrades"], 
"RD - Large": [9,"Small, Medium, and Large Upgrades"], 
"RD - All": [13, " All Guild Upgrades"]}
questBuffsArray = list(questBuffsDict.keys())

left = '\N{BLACK LEFT-POINTING TRIANGLE}'
right = '\N{BLACK RIGHT-POINTING TRIANGLE}'
back = '\N{LEFTWARDS ARROW WITH HOOK}'

numberEmojisMobile = ['1⃣','2⃣','3⃣','4⃣','5⃣','6⃣','7⃣','8⃣','9⃣']
numberEmojis = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','0️⃣']

alphaEmojis = ['🇦','🇧','🇨','🇩','🇪','🇫','🇬','🇭','🇮','🇯','🇰',
'🇱','🇲','🇳','🇴','🇵','🇶','🇷','🇸','🇹','🇺','🇻','🇼','🇽','🇾','🇿']

statuses = [f'D&D Friends | {commandPrefix}help', "We're all friends here!", f"See a bug? tell @MSchildorfer!", "Practicing social distancing!", "Wearing a mask!", "Being a good boio.", "Vibing", "Hippity Hoppity", "These Logs Are My Property", "UwU"]
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
             "Craft" : list([line["Text"] for line in db.liners_craft.find()]),
             "Money" : list([line["Text"] for line in db.liners_money.find()])}


# API_URL = ('https://api.airtable.com/v0/appF4hiT6A0ISAhUu/'+ 'races')
# # API_URL += '?offset=' + 'itr4Z54rnNABYW8jj/recr2ss2DkyF4Q84X' 
# r = requests.get(API_URL, headers=headers)
# r = r.json()['records']
# playersCollection = db.races
# addList = []
# for i in r:
#     print(i['fields'])
#     addList.append(i['fields'])

# playersCollection.insert_many(addList)

# collection = db['mit']
# cl = list(collection.find({"Name": {"$regex": 'Vicious.*\+1$', '$options': 'i' }}))
# cData = list(map(lambda item: UpdateOne({'_id': item['_id']}, {'$set': {'TP':12, 'GP':5280 } }, upsert=True), cl))
# collection.bulk_write(cData)

# records = list(collection.find({"Modifiers": {"$regex": '', '$options': 'i' }}))


# i = 0
# for r in sorted(records, key = lambda i: i['Name']) :
#     print(r['Name'])
#     i+=1

# print (i)

# # delete
# collection.remove(({"Modifiers": {"$regex": '', '$options': 'i' }}))