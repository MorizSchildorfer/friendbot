import discord
import random
import asyncio
import re
from cogs.view import AlphaView, ConfirmView, TestView, Report
from discord.utils import get      
from math import floor
from discord.ext import commands
from bfunc import settingsRecord, alphaEmojis, commandPrefix, db, left,right,back, traceBack, tier_reward_dictionary
import math

noodle_roles = {'Newdle': {'noodles': 1, 'creation_items': [0, 0, 0], 'creation_level_bonus': 1, 'dm_item_rewards': [1, 0, 0], 'player_item_rewards': [1, 1, 1], 'training': 0},
'Fresh Noodle': {'noodles': 3, 'creation_items': [1, 0, 0], 'creation_level_bonus': 2, 'dm_item_rewards': [1, 1, 0], 'player_item_rewards': [1, 2, 1], 'training': 0},
'Good Noodle': {'noodles': 10, 'creation_items': [1, 1, 0], 'creation_level_bonus': 3, 'dm_item_rewards': [1, 1, 1], 'player_item_rewards': [1, 2, 2], 'training': 1},
'Elite Noodle': {'noodles': 25, 'creation_items': [1, 1, 1], 'creation_level_bonus': 4, 'dm_item_rewards': [2, 1, 1], 'player_item_rewards': [2, 3, 2], 'training': 2},
'True Noodle': {'noodles': 45, 'creation_items': [2, 1, 1], 'creation_level_bonus': 5, 'dm_item_rewards': [2, 2, 1], 'player_item_rewards': [2, 3, 3], 'training': 3},
'Nice Noodle': {'noodles': 69, 'creation_items': [2, 2, 1], 'creation_level_bonus': 6, 'dm_item_rewards': [2, 2, 2], 'player_item_rewards': [2, 4, 3], 'training': 4},
'Ascended Noodle': {'noodles': 100, 'creation_items': [2, 2, 2], 'creation_level_bonus': 7, 'dm_item_rewards': [3, 2, 2], 'player_item_rewards': [3, 4, 4], 'training': 5},
'Immortal Noodle': {'noodles': 140, 'creation_items': [3, 2, 2], 'creation_level_bonus': 8, 'dm_item_rewards': [3, 3, 2], 'player_item_rewards': [3, 5, 4], 'training': 6},
'Eternal Noodle': {'noodles': 185, 'creation_items': [3, 3, 2], 'creation_level_bonus': 9, 'dm_item_rewards': [3, 3, 3], 'player_item_rewards': [3, 5, 5], 'training': 7},
'Infinity Noodle': {'noodles': 235, 'creation_items': [3, 3, 3], 'creation_level_bonus': 10, 'dm_item_rewards': [4, 3, 3], 'player_item_rewards': [4, 6, 5], 'training': 8},
'Beyond Noodle': {'noodles': 290, 'creation_items': [4, 3, 3], 'creation_level_bonus': 11, 'dm_item_rewards': [4, 4, 3], 'player_item_rewards': [4, 6, 6], 'training': 9},
'Transcendent Noodle': {'noodles': 350, 'creation_items': [4, 4, 3], 'creation_level_bonus': 12, 'dm_item_rewards': [4, 4, 4], 'player_item_rewards': [4, 7, 6], 'training': 10},
'Blazing Noodle': {'noodles': 420, 'creation_items': [4, 4, 4], 'creation_level_bonus': 13, 'dm_item_rewards': [5, 4, 4], 'player_item_rewards': [5, 7, 7], 'training': 11},
'Quantum Noodle': {'noodles': 500, 'creation_items': [5, 4, 4], 'creation_level_bonus': 14, 'dm_item_rewards': [5, 5, 4], 'player_item_rewards': [5, 8, 7], 'training': 12},
'Deific Noodle': {'noodles': 580, 'creation_items': [5, 5, 4], 'creation_level_bonus': 15, 'dm_item_rewards': [5, 5, 5], 'player_item_rewards': [5, 8, 8], 'training': 13},
'Infernal Noodle': {'noodles': 666, 'creation_items': [5, 5, 5], 'creation_level_bonus': 16, 'dm_item_rewards': [6, 5, 5], 'player_item_rewards': [6, 9, 8], 'training': 14},
'Lucky Noodle': {'noodles': 777, 'creation_items': [6, 5, 5], 'creation_level_bonus': 17, 'dm_item_rewards': [6, 6, 5], 'player_item_rewards': [6, 9, 9], 'training': 15},
'Millenium Noodle': {'noodles': 1000, 'creation_items': [6, 6, 5], 'creation_level_bonus': 18, 'dm_item_rewards': [6, 6, 6], 'player_item_rewards': [6, 10, 9], 'training': 16}}

def admin_or_owner():
    async def predicate(ctx):
        output = ctx.message.author.id in [220742049631174656, 203948352973438995] or (get(ctx.message.guild.roles, name = "A d m i n") in ctx.message.author.roles)
        return  output
    return commands.check(predicate)

def uwuize(text):
    vowels = ['a','e','i','o','u']
    faces = ['rawr XD', 'OwO', 'owo', 'UwU', 'uwu']
    uwuMessage = text.replace('r', 'w')
    uwuMessage = uwuMessage.replace('l', 'w')
    uwuMessage = uwuMessage.replace('ove', 'uv')
    uwuMessage = uwuMessage.replace('. ', '!')
    uwuMessage = uwuMessage.replace(' th', ' d')
    uwuMessage = uwuMessage.replace('th', 'f')
    uwuMessage = uwuMessage.replace('mom', 'yeshh')

    for v in vowels:
      uwuMessage = uwuMessage.replace('n'+ v, 'ny'+v)

    i = 0
    while i < len(uwuMessage):
        if uwuMessage[i] == '!':
            randomFace = random.choice(faces)
            if i == len(uwuMessage):
                uwuMessage = uwuMessage + ' ' + randomFace
                break
            else:
              uwuList = list(uwuMessage)
              uwuList.insert(i+1, " " + randomFace)
              uwuMessage = ''.join(uwuList)
              i += len(randomFace)
        i += 1
    return uwuMessage
       
def noodleBarrier(noodlesBefore, noodlesAfter):
    noodleCongrats = ""
    for name, data in noodle_roles:
        noodles = data['noodles']
        if noodles > noodlesBefore and noodles < noodleAfter:
            noodleCongrats = f"Congratulations! You have reached {name}!"
    return noodleCongrats
    
def findNoodleData(noodles):
    noodle_name = "Newdle"
    for name, data in noodle_roles.items():
        if data['noodles'] > noodles:
            break
        noodle_name = name
    return noodle_name, noodle_roles[noodle_name]
    
def findNoodleDataFromRoles(roles):
    search_result = list([(r.name, noodle_roles[r.name], r) for r in roles if r.name in noodle_roles])
    if not search_result:
        return (None, None, None)
    return search_result[0]
       
async def noodleCheck(ctx, dmID):
    guild = ctx.guild
    dmUser = ctx.guild.get_member(int(dmID))
    if dmUser:
        dmEntry = db.users.find_one({"User ID" : str(dmID)})
        noodles = dmEntry["Noodles"]
        noodleString = ""
        noodle_name, noodle_data, _ =  findNoodleDataFromRoles(dmUser.roles)
        # for the relevant noodle role cut-off check if the user would now qualify for the role and if they do not have it and remove the old role
        next_name, next_data = findNoodleData(noodles)
        if noodle_name != next_name:
            noodleRole = get(guild.roles, name = next_name)
            await dmUser.add_roles(noodleRole, reason=f"Hosted {noodles} sessions. This user has {next_data['noodles']}+ Noodles.")
            if noodle_name != None:
                await dmUser.remove_roles(get(guild.roles, name = noodle_name))

async def confirm(msg, author):
    view = ConfirmView(author)
    msg = await msg.edit(view = view)
    await view.wait()
    await msg.edit(view = None)
    return view.state

async def texttest(msg, author):
    view = Report()
    msg = await msg.edit(view = view)
    await view.wait()
    await msg.edit(view = None)
    return view.value

async def disambiguate(options, msg, author, cancel=True, emojies = alphaEmojis):
    view = AlphaView(options, author, emojies, cancel)
    msg = await msg.edit(view = view)
    await view.wait()
    await msg.edit(view = None)
    return view.state

def timeConversion (time,hmformat=False):
    hours = time//3600
    time = time - 3600*hours
    minutes = time//60
    if hmformat is False:
        return ('%d Hours %d Minutes' %(hours,minutes))
    else:
        return ('%dh%dm' %(hours,minutes))

"""
Paginate is a function that given a list of text contents turns them into an embed menu system displaying them while creating pagination when required
ctx -> command call context
bot -> bot object which is being interacted with
title -> title for the embed object
contents -> a list of tuples of the form (Section Title, Section Text, New Page?)
    Section Title is what the field title will be
    Section Text is the value for the field and is split if it exceeds the field size limit
    New Page? is a boolean that indicates if a new page should be created for this section
msg -> The message which will contain the embed, if none is given a new message will be created
separator -> text element by which the section texts will be split if they overflow, defaults to "\n"
author -> author of the embed, if one is given the author and profile image will be set
color -> color for the embed, if one is given the embed will use that color
footer -> custom footer message, is added to page text
"""    
async def paginate(ctx, bot, title, contents, msg=None, separator="\n", author = None, color= None, content="", footer=""):
    
    # storage of the elements that will be displayed on a page
    entry_pages =[]
    
    # length of main title
    title_length = len(title)
    
    # sample worst case footer length
    footer_text_sample = len(f"{footer}\nPage 100 of 100")
    
    # go over each required content piece and split it into the different groups
    # currently different content elements are separated by page
    def unwrap_tuple(name, text, new_page=False, inline=False):
        return name, text, new_page, inline
    
    entry_list = []
    set_length = 0
    for data_tuple in contents:
        name, text, new_page, inline = unwrap_tuple(*data_tuple)
        
        # how many parts are there for this section
        parts = 1
        
        # storage of entries for a single page
        name_length = len(name)
        length = len(text)
        
        # separate the text into different line sections until the full text has been split
        while(length>0):
            
            if length>1000:
                # get everything to the limit
                section_text = text[:1000]
                # ensure that we do not separate mid sentence by splitting at the separator
                section_text = section_text.rsplit(separator, 1)[0]
                # then update the text to everything past what we took for the section text
                text = text[len(section_text)+len(separator):]
                # update our length running tally
                length -= len(section_text)+len(separator)
            else:
                section_text = text
                length = 0
            # track the text length for the page 
            # if there was only one section then do not add a page count
            subtitle = f"{name}"
            if length>0 or parts>1:
                subtitle = f"{name} - p. {parts}"
            
            set_length += len(section_text) + len(subtitle)
            # check if the content would exceed the page limit    
            if (new_page or 
                len(entry_list) > 24 or
                (set_length + title_length + footer_text_sample >= 6000)):
                new_page = False
                set_length = len(section_text) + len(subtitle)
                # add the page to the storage
                entry_pages.append(entry_list)
                # reset page tracker
                entry_list = []
            
            # add to page
            entry_list.append((subtitle, section_text, inline))
            
            # increase parts
            parts += 1
            
        # add the page to the storage
        
    entry_pages.append(entry_list)
    # get page count
    pages = len(entry_pages)
    # create embed
    embed = discord.Embed()
    
    embed.title = title
    if author:
        embed.set_author(name=author, icon_url=author.display_avatar)
    if color:
        embed.color = color
    if footer:
        embed.set_footer(text=f"{footer}")
    # check that only original user can use the menu
    def userCheck(r,u):
        sameMessage = False
        if msg.id == r.message.id:
            sameMessage = True
        return sameMessage and u == ctx.author and (r.emoji == left or r.emoji == right)
    page = 0
    #add the fields for the page
    for subtitle, section_text, inline in entry_pages[page]:
        embed.add_field(name=subtitle, value=section_text, inline=inline)
    if (pages>1):
        embed.set_footer(text=f"{footer}\nPage {page+1} of {pages}")
    # if no preexisting message exists create a new one
    if not msg:
        msg = await ctx.channel.send("", embed = embed)
    else:
        await msg.edit(content= content, embed=embed) 
    await msg.clear_reactions()
    while pages>1:
        #add navigation
        await msg.add_reaction(left) 
        await msg.add_reaction(right)
        
        # wait for interaction
        try:
            hReact, hUser = await bot.wait_for("reaction_add", check=userCheck, timeout=30.0)
        # end if no reaction was given in time
        except asyncio.TimeoutError:
            await msg.edit(content=f"Your user menu has timed out! I'll leave this page open for you. If you need to cycle through the menu again then use the same command!")
            await msg.clear_reactions()
            await msg.add_reaction('💤')
            return
        else:
            # clear the page
            embed.clear_fields()
            
            # update page based on navigation
            if hReact.emoji == left:
                page -= 1
                if page < 0:
                    page = (pages -1)
            elif hReact.emoji == right:
                page += 1
                if page > (pages -1 ):
                    page = 0
            
            #add the fields for the page
            for subtitle, section_text, inline in entry_pages[page]:
                embed.add_field(name=subtitle, value=section_text, inline=inline)
                
            if (pages>1):
                embed.set_footer(text=f"{footer}\nPage {page+1} of {pages}")
            await msg.edit(embed=embed) 
            await msg.clear_reactions()

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
        #create a string to provide information about the items to the user
        infoString = ""
        if (len(records) > 1):
            #sort items by tier if the magic item tables were requested
            if table == 'mit' or table == 'rit':
                records = sorted(records, key = lambda i : i ['Tier'])
            queryLimit = 20
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
            apiEmbed.description =f"**There seems to be multiple results for `\"{query}\"`! Please choose the correct one.\nThe maximum number of results shown is {queryLimit}. If the result you are looking for is not here, please react with ❌ and be more specific.**\n\n{infoString}"
            #inform the user of the current information and ask for their selection of an item
            #apiEmbed.add_field(name=f"There seems to be multiple results for \"**{query}**\"! Please choose the correct one.\nThe maximum number of results shown is {queryLimit}. If the result you are looking for is not here, please react with ❌ and be more specific.", value=infoString, inline=False)
            if not apiEmbedmsg or apiEmbedmsg == "Fail":
                apiEmbedmsg = await channel.send(embed=apiEmbed)
            else:
                await apiEmbedmsg.edit(embed=apiEmbed)
            choice = await disambiguate(min(len(records), queryLimit), apiEmbedmsg, author)
            
            if choice is None or choice == -1:
                await apiEmbedmsg.edit(embed=None, content=f"Command cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None, apiEmbed, "Fail"
            apiEmbed.clear_fields()
            return records[choice], apiEmbed, apiEmbedmsg

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
    query = query.replace('+', '\\+')
    query_data =  {"$regex": query,
                    "$options": "i"
                  }
    filterDic = {"$or": [
                            {
                              "Name": query_data
                            },
                            {
                              "Nickname": query_data
                            }
                        ]
                    } 
    if mod == True:
        charRecords = list(playersCollection.find(filterDic)) 
    else:
        filterDic["User ID"] = str(search_author.id)
        charRecords = list(playersCollection.find(filterDic))

    if charRecords == list():
        if not mod and not customError:
            await channel.send(content=f'I was not able to find your character named "**{char}**". Please check your spelling and try again.')
        ctx.command.reset_cooldown(ctx)
        return None, None

    else:
        if len(charRecords) > 1:
            infoString = ""
            
            charRecords = sorted(list(charRecords), key = lambda i : i ['Name'])
            for i in range(0, min(len(charRecords), 20)):
                infoString += f"{alphaEmojis[i]}: {charRecords[i]['Name']} ({guild.get_member(int(charRecords[i]['User ID']))})\n"
            
            
            charEmbed.add_field(name=f"There seems to be multiple results for \"`{char}`\"! Please choose the correct character. If you do not see your character here, please react with ❌ and be more specific with your query.", value=infoString, inline=False)
            charEmbedmsg = await channel.send(embed=charEmbed)
            choice = await disambiguate(min(len(charRecords), 20), charEmbedmsg, author)
            
            if choice is None or choice == -1:
                await charEmbedmsg.edit(embed=None, content=f"Character information cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None, None
            charEmbed.clear_fields()
            return charRecords[choice], charEmbedmsg

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
            for i in range(0, min(len(guildRecords), 20)):
                infoString += f"{alphaEmojis[i]}: {guildRecords[i]['Name']}\n"
            
            guildEmbed.add_field(name=f"There seems to be multiple results for \"`{name}`\"! Please choose the correct guild. If you do not see your guild here, please react with ❌ and be more specific with your query.", value=infoString, inline=False)
            guildEmbedmsg = await channel.send(embed=guildEmbed)
            choice = await disambiguate(min(len(guildRecords), 20), guildEmbedmsg, author)
            
            if choice is None or choice == -1:
                await guildEmbedmsg.edit(embed=None, content=f"Command cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None, None
            guildEmbed.clear_fields()
            return guildRecords[choice], guildEmbedmsg

    return guildRecords[0], None

def calculateTreasure(level, charcp, seconds, guildDouble=False, playerDouble=False, dmDouble=False, bonusDouble=False, tierBonus=False, gold_modifier = 100, tierOneDouble=False):
    # calculate the CP gained during the game
    cp = ((seconds) // 900) / 4
    cp_multiplier = 1 + guildDouble + playerDouble + dmDouble + bonusDouble + tierBonus + tierOneDouble
       
        
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
    levelCP = (((charLevel-5) * 10) + 16)
    if charLevel < 5:
        levelCP = ((charLevel -1) * 4)
    while(cp>0):
        
        # Level 20 characters haves access to exclusive items
        # create a string representing which tier the character is in in order to create/manipulate the appropriate TP entry in the DB
        tierTP = f"T{tier} TP"
            
        if levelCP + leftCP + cp > cpThreshHoldArray[tier-1]:
            consideredCP = cpThreshHoldArray[tier-1] - (levelCP + leftCP)
            leftCP -= min(leftCP, cpThreshHoldArray[tier-1]-levelCP)
            levelCP = cpThreshHoldArray[tier-1]
        else:
            consideredCP = cp
        if consideredCP > 0:
            cp -=  consideredCP
            tp[tierTP] = consideredCP * tier_reward_dictionary[tier-1][1]
            gp += consideredCP * tier_reward_dictionary[tier-1][0]
        tier += 1
    if gold_modifier!=100:
        gp = min(gp, math.ceil(gold_modifier * gp/100))
    return [gainedCP, tp, gp]


async def spell_item_search(ctx, search_parameter, item_type, charEmbed, charEmbedmsg, msg=""):    
    spellItem = search_parameter.lower().replace(item_type.lower(), "").replace('(', '').replace(')', '')
    sRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'spells', spellItem) 
    
    spell_item_name = ""
    if not sRecord :
        msg += f'''**{search_parameter}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Reward Item Table, what tier it is, and your spelling.'''
        
    elif sRecord["Level"]==0:
        search_parameter = item_type +" (Cantrip)"
        spell_item_name = f"{item_type} ({sRecord['Name']})"
    else:
        ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(floor(n/10)%10!=1)*(n%10<4)*n%10::4])
        # change the query to be an accurate representation
        search_parameter = f"{item_type} ({ordinal(sRecord['Level'])} Level)"
        spell_item_name = f"{item_type} ({sRecord['Name']})"
    return search_parameter, spell_item_name, charEmbed, charEmbedmsg, msg

class Util(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    

async def setup(bot):
    await bot.add_cog(Util(bot))