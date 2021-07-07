import discord
import decimal
import pytz
import re
import random
import requests
import asyncio
import collections
from discord.utils import get        
from math import floor
from datetime import datetime, timezone, timedelta 
from discord.ext import commands
from urllib.parse import urlparse 
from bfunc import numberEmojis, alphaEmojis, commandPrefix, left,right,back, db, callAPI, checkForChar, timeConversion, traceBack, tier_reward_dictionary, cp_bound_array, calculateTreasure, settingsRecord


def get_embed_length(embed):
    # embed would be the discord.Embed instance
    fields = [embed.title, embed.description, embed.footer.text, embed.author.name]

    fields.extend([field.name for field in embed.fields])
    fields.extend([field.value for field in embed.fields])

    total = ""
    for item in fields:
        
        # If we str(discord.Embed.Empty) we get 'Embed.Empty', when
        # we just want an empty string...
        total += str(item) if str(item) != 'Embed.Empty' else ''

    return(len(total))
    
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
async def paginate(ctx, bot, title, contents, msg=None, separator="\n", author = None, color= None, footer=""):
    
    # storage of the elements that will be displayed on a page
    entry_pages =[]
    
    # length of main title
    title_length = len(title)
    
    # sample worst case footer length
    footer_text_sample = len(f"{footer}\nPage 100 of 100")
    
    # go over each required content piece and split it into the different groups
    # currently different content elements are separated by page
    
    entry_list = []
    set_length = 0
    for name, text, new_page in contents:
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
            if new_page or (set_length + title_length + footer_text_sample >= 6000):
                new_page = False
                set_length = len(section_text) + len(subtitle)
                # add the page to the storage
                entry_pages.append(entry_list)
                # reset page tracker
                entry_list = []
            
            # add to page
            entry_list.append((subtitle, section_text))
            
            # increase parts
            parts += 1
            
        # add the page to the storage
        #entry_pages.append(entry_list)
        
    entry_pages.append(entry_list)
    # get page count
    pages = len(entry_pages)
    # create embed
    embed = discord.Embed()
    
    embed.title = title
    if author:
        embed.set_author(name=author, icon_url=author.avatar_url)
    if color:
        embed.color = color
    if footer:
        embed.set_footer(text=f"{footer}")
    # if no preexisting message exists create a new one
    if not msg:
        msg = await ctx.channel.send(msg, embed = embed)
    # check that only original user can use the menu
    def userCheck(r,u):
        sameMessage = False
        if msg.id == r.message.id:
            sameMessage = True
        return sameMessage and u == ctx.author and (r.emoji == left or r.emoji == right)
    page = 0
    #add the fields for the page
    for subtitle, section_text in entry_pages[page]:
        embed.add_field(name=subtitle, value=section_text, inline=False)
    if (pages>1):
        embed.set_footer(text=f"{footer}\nPage {page+1} of {pages}")
    await msg.edit(embed=embed) 
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
            for subtitle, section_text in entry_pages[page]:
                embed.add_field(name=subtitle, value=section_text, inline=False)
                
            if (pages>1):
                embed.set_footer(text=f"{footer}\nPage {page+1} of {pages}")
            await msg.edit(embed=embed) 
            await msg.clear_reactions()
                
    

class Character(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        
        # Reserved for regex, lets not use these for character names please
        self.invalidChars = ["[", "]", "?", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]
        
    def is_log_channel():
        async def predicate(ctx):
            return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
        return commands.check(predicate)
   
    def is_log_channel_or_game():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Game Rooms"])
        return commands.check(predicate) 
        
    def stats_special():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"] or
                    ctx.channel.id == 564994370416410624)
        return commands.check(predicate) 
        
    @commands.group(aliases=['rf'], case_insensitive=True)
    async def reflavor(self, ctx):	
        pass
    
    
    async def cog_command_error(self, ctx, error):
        msg = None
        
        
        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your stats and level need to be numbers. "
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):

             return
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'char':
                msg = ":warning: You're missing the character name in the command.\n"
            elif error.param.name == 'new_flavor':
                msg = ":warning: You're missing the new race/class/background in the command.\n"
            elif error.param.name == "name":
                msg = ":warning: You're missing the name for the character you want to create or respec.\n"
            elif error.param.name == "newname":
                msg = ":warning: You're missing a new name for the character you want to respec.\n"
            elif error.param.name == "level":
                msg = ":warning: You're missing a level for the character you want to create.\n"
            elif error.param.name == "race":
                msg = ":warning: You're missing a race for the character you want to create.\n"
            elif error.param.name == "character_class":
                msg = ":warning: You're missing a class for the character you want to create.\n"
            elif error.param.name == 'background':
                msg = ":warning: You're missing a background for the character you want to create.\n"
            elif error.param.name == 'statsStr' or  error.param.name == 'statsDex' or error.param.name == 'statsCon' or error.param.name == 'statsInt' or error.param.name == 'statsWis' or error.param.name == 'statsCha':
                msg = ":warning: You're missing a stat (STR, DEX, CON, INT, WIS, or CHA) for the character you want to create.\n"
            elif error.param.name == 'url':
                msg = ":warning: You're missing a URL to add an image to your character's information window.\n"
            elif error.param.name == 'magic_item':
                msg = ":warning: You're missing a magic item to attune to, or unattune from, your character.\n"

            msg += "**Note: if this error seems incorrect, something else may be incorrect.**\n\n"

        if msg:
            if ctx.command.name == "create":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}create "name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```\n'
            elif ctx.command.name == "respec":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}respec "name" "new name" "race" "class" "background" STR DEX CON INT WIS CHA```\n'
            elif ctx.command.name == "retire":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}retire "character name"```\n'
            elif ctx.command.name == "reflavor":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}reflavor race/class/background "character name"```\n'
            elif ctx.command.name == "death":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}death "character name"```\n'
            elif ctx.command.name == "inventory":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}inventory "character name"```\n'
            elif ctx.command.name == "info":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}info "character name"```\n'
            elif ctx.command.name == "image":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}image "character name" "URL"```\n'
            elif ctx.command.name == "levelup":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}levelup "character name"```\n'
            elif ctx.command.name == "attune":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}attune "character name" "magic item"```\n'
            elif ctx.command.name == "unattune":
                msg += f'Please follow this format:\n```yaml\n{commandPrefix}unattune "character name" "magic item"```\n'
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
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

    @commands.command()
    @commands.cooldown(1, 60, type=commands.BucketType.user)
    @is_log_channel()
    async def printRaces(self, ctx):
        try:
            items = list(db.races.find(
               {},
            ))
            raceEmbed = discord.Embed()
            raceEmbed.title = f"All Valid Races:\n"
            
            items.sort(key = lambda x: x["Name"])
            character = ""
            out_strings = []
            collector_string = ""
            for race in items:
                race = race["Name"]
                if race[0] == character:
                    collector_string += f"{race}\n"
                else:
                    if collector_string:
                        out_strings.append(collector_string)
                    collector_string = f"{race}\n"
                    character = race[0]
            if collector_string:
                out_strings.append(collector_string)
            for i in out_strings:
                raceEmbed.add_field(name=i[0], value= i, inline = True)
            await ctx.channel.send(embed=raceEmbed)
    
        except Exception as e:
            traceback.print_exc()   
    @is_log_channel()
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.command()
    async def create(self,ctx, name, level: int, race, character_class, background, statsStr : int, statsDex :int, statsCon:int, statsInt:int, statsWis:int, statsCha :int, consumes="", campaignName = "", timeTransfer = None):
        name = name.strip()
        characterCog = self.bot.get_cog('Character')
        roleCreationDict = {
            'Journeyfriend':[3],
            'Elite Friend':[3],
            'True Friend':[3],
            'Ascended Friend':[3],
            'Good Noodle':[4],
            'Elite Noodle':[4,5],
            'True Noodle':[4,5,6],
            'Ascended Noodle':[4,5,6,7],
            'Immortal Noodle':[4,5,6,7,8],
            'Eternal Noodle':[4,5,6,7,8,9]
        }
        roles = [r.name for r in ctx.author.roles]
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        charEmbed = discord.Embed ()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        charEmbedmsg = None
        statNames = ['STR','DEX','CON','INT','WIS','CHA']

        charDict = {
          'User ID': str(author.id),
          'Name': name,
          'Level': int(level),
          'HP': 0,
          'Class': character_class,
          'Background': background,
          'STR': int(statsStr),
          'DEX': int(statsDex),
          'CON': int(statsCon),
          'INT': int(statsInt),
          'WIS': int(statsWis),
          'CHA': int(statsCha),
          'Alignment': 'Unknown',
          'CP' : 0,
          'GP': 0,
          'Magic Items': {},
          'Consumables': [],
          'Feats': '',
          'Inventory': {},
          'Predecessor': {},
          'Games': 0,
          'Max Stats': {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
        }
        

        # Prevents name, level, race, class, background from being blank. Resets infinite cooldown and prompts
        if not name:
            await channel.send(content=":warning: The name of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not level:
            await channel.send(content=":warning: The level of your character cannot be blank! Please try again.\n")

            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not race:
            await channel.send(content=":warning: The race of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return

        if not character_class:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        
        if not background:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return


        lvl = int(level)
        # Provides an error message at the end. If there are more than one, it will join msg.
        msg = ""

        msg = self.name_check(name)

        if msg == "":
            query = name
            query = query.replace('(', '\\(')
            query = query.replace(')', '\\)')
            query = query.replace('.', '\\.')
            playersCollection = db.players
            userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' } }))

            if userRecords != list():
                msg += f":warning: You already have a character by the name of ***{name}***! Please use a different name.\n"
        
        # ██████╗░░█████╗░██╗░░░░░███████╗  ░░░░██╗  ██╗░░░░░███████╗██╗░░░██╗███████╗██╗░░░░░
        # ██╔══██╗██╔══██╗██║░░░░░██╔════╝  ░░░██╔╝  ██║░░░░░██╔════╝██║░░░██║██╔════╝██║░░░░░
        # ██████╔╝██║░░██║██║░░░░░█████╗░░  ░░██╔╝░  ██║░░░░░█████╗░░╚██╗░██╔╝█████╗░░██║░░░░░
        # ██╔══██╗██║░░██║██║░░░░░██╔══╝░░  ░██╔╝░░  ██║░░░░░██╔══╝░░░╚████╔╝░██╔══╝░░██║░░░░░
        # ██║░░██║╚█████╔╝███████╗███████╗  ██╔╝░░░  ███████╗███████╗░░╚██╔╝░░███████╗███████╗
        # ╚═╝░░╚═╝░╚════╝░╚══════╝╚══════╝  ╚═╝░░░░  ╚══════╝╚══════╝░░░╚═╝░░░╚══════╝╚══════╝

        # Check if level or roles are vaild
        # A set that filters valid levels depending on user's roles
        roleSet = [1]
        for d in roleCreationDict.keys():
            if d in roles:
                roleSet += roleCreationDict[d]

        roleSet = set(roleSet)

        # If roles are present, add base levels + 1 for extra levels for these special roles.
        if ("Nitro Booster" in roles):
            roleSet = roleSet.union(set(map(lambda x: x+1,roleSet.copy())))

        if ("Bean Friend" in roles):
            roleSet = roleSet.union(set(map(lambda x: x+1,roleSet.copy())))
            roleSet = roleSet.union(set(map(lambda x: x+1,roleSet.copy())))
          
        if lvl not in roleSet:
            msg += f":warning: You cannot create a character of **{lvl}**! You do not have the correct role!\n"
        
        x["Menge"]
        y[0]
        
        # Checks CP
        if lvl < 5:
            maxCP = 4
        else:
            maxCP = 10
        cp = 0
        cpTransfered = 0
        campaignTransferSuccess = False
        campaignKey = ""
        if campaignName:
            campaignChannels = ctx.message.channel_mentions
            
            userRecords = db.users.find_one({"User ID" : str(author.id)})
            campaignFind = False
            if not userRecords:
                msg += f":warning: I could not find you in the database!\n"
            elif "Campaigns" not in userRecords.keys():
                pass
            else:
                
                if len(campaignChannels) > 1 or campaignChannels == list():
                    for key in userRecords["Campaigns"].keys():
                        if campaignName.lower() in key.lower(): 
                            campaignFind = True
                            campaignKey = key
                            break
                    error_name = campaignName
                else:
                    for key in userRecords["Campaigns"].keys():
                        if key.lower().replace(",", "") == (campaignChannels[0].name.replace('-', ' ')):
                            campaignFind = True
                            campaignKey = key
                            break
                    
                    error_name = campaignChannels[0].mention
                if not campaignFind:
                    msg += f":warning: I could not find {error_name} in your records!\n"
                elif not timeTransfer:
                    msg += f":warning: I could not find a time amount in your command!\n"
                else:
                    def convert_to_seconds(s):
                        return int(s[:-1]) * seconds_per_unit[s[-1]]

                    seconds_per_unit = { "m": 60, "h": 3600 }
                    lowerTimeString = timeTransfer.lower()
                    l = list((re.findall('.*?[hm]', lowerTimeString)))
                    totalTime = 0
                    try:
                        for timeItem in l:
                            totalTime += convert_to_seconds(timeItem)
                    except Exception as e:
                        msg += f":warning: I could not find a number in your time amount!\n"
                        totalTime = 0
                        
                    if userRecords["Campaigns"][campaignKey]["Time"] < 3600*4 or totalTime > userRecords["Campaigns"][campaignKey]["Time"]:
                        msg += f":warning: You do not have enough hours to transfer from {campaignChannels[0].mention}!\n"
                    else:
                        cp = ((totalTime) // 1800) / 2
                        cpTransfered = cp
                        while(cp >= maxCP and lvl <20):
                            cp -= maxCP
                            lvl += 1
                            if lvl > 4:
                                maxCP = 10
                        campaignTransferSuccess = True
                        charDict["Level"] = lvl
                            
        charDict['CP'] = cp
        
        levelCP = (((lvl-5) * 10) + 16)
        if lvl < 5:
            levelCP = ((lvl -1) * 4)
        cp_tp_gp_array = calculateTreasure(1, 0, 1, (levelCP+cp)*3600)
        totalGP = cp_tp_gp_array[2]
        bankTP = cp_tp_gp_array[1
        
        tierNum = 5
        # calculate the tier of the rewards
        if lvl < 5:
            tierNum = 1
        elif lvl < 11:
            tierNum = 2
        elif lvl < 17:
            tierNum = 3
        elif lvl < 20:
            tierNum = 4
        
        # Stats - Point Buy
        if msg == "":
            msg = self.point_buy_check(self, ctx, statsStr, statDex, statsCon, statsInt, statsWis, statsCha)


        # ██████╗░███████╗░██╗░░░░░░░██╗░█████╗░██████╗░██████╗░  ██╗████████╗███████╗███╗░░░███╗░██████╗
        # ██╔══██╗██╔════╝░██║░░██╗░░██║██╔══██╗██╔══██╗██╔══██╗  ██║╚══██╔══╝██╔════╝████╗░████║██╔════╝
        # ██████╔╝█████╗░░░╚██╗████╗██╔╝███████║██████╔╝██║░░██║  ██║░░░██║░░░█████╗░░██╔████╔██║╚█████╗░
        # ██╔══██╗██╔══╝░░░░████╔═████║░██╔══██║██╔══██╗██║░░██║  ██║░░░██║░░░██╔══╝░░██║╚██╔╝██║░╚═══██╗
        # ██║░░██║███████╗░░╚██╔╝░╚██╔╝░██║░░██║██║░░██║██████╔╝  ██║░░░██║░░░███████╗██║░╚═╝░██║██████╔╝
        # ╚═╝░░╚═╝╚══════╝░░░╚═╝░░░╚═╝░░╚═╝░░╚═╝╚═╝░░╚═╝╚═════╝░  ╚═╝░░░╚═╝░░░╚══════╝╚═╝░░░░░╚═╝╚═════╝░
        # Reward Items
        if msg == "":
            rewardItems = consumes.strip().split(',')
            allRewardItemsString = []
            if rewardItems != ['']:
                for r in rewardItems:
                    if "spell scroll" in r.lower():
                        if "spell scroll" == r.lower().strip():
                            msg += f"""Please be more specific with the type of spell scroll which you're purchasing. You must format spell scrolls as follows: "Spell Scroll (spell name)".\n"""
                            break 
                            
                        spellItem = r.lower().replace("spell scroll", "").replace('(', '').replace(')', '')
                        sRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'spells', spellItem) 
                        
                        if not sRecord :
                            msg += f'''**{r}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Reward Item Table, what tier it is, and your spelling.'''
                            

                        else:
                            
                            ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(floor(n/10)%10!=1)*(n%10<4)*n%10::4])
                            # change the query to be an accurate representation
                            r = f"Spell Scroll ({ordinal(sRecord['Level'])} Level)"

                    reRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'rit',r, tier = tierNum, filter_rit = False) 

                    if charEmbedmsg == "Fail":
                        return
                    if not reRecord:
                        msg += f" {r} belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Reward Item Table, what tier it is, and your spelling.\n"
                        break
                    else:
                        
                        if 'spell scroll' in r.lower():
                            reRecord['Name'] = f"Spell Scroll ({sRecord['Name']})"
                        allRewardItemsString.append(reRecord)
                allRewardItemsString.sort(key=lambda x: x["Tier"])
                tier1CountMNC = 0
                tierRewards = [[], [], [], [], []]
                tierConsumableCounts = [0,0,0,0,0,0]
                if 'Good Noodle' in roles:
                    tierConsumableCounts[0] = 1
                elif 'Elite Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 1
                elif 'True Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[2] = 1
                elif 'Ascended Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 1
                    tierConsumableCounts[2] = 1
                elif 'Immortal Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 2
                    tierConsumableCounts[2] = 1
                elif 'Eternal Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 2
                    tierConsumableCounts[2] = 2

                if 'Nitro Booster' in roles:
                    tierConsumableCounts[0] += 2

                if 'Bean Friend' in roles:
                    tierConsumableCounts[0] += 2
                    tierConsumableCounts[tierNum] += 2
                startCounts = tierConsumableCounts.copy()
                startCounts[0] = 0
                startt1MNC = tierConsumableCounts[0]

                for item in allRewardItemsString:
                    
                    if item['Minor/Major'] == 'Minor' and item["Type"] == 'Magic Items':
                        item['Tier'] -= 1
                    i = item["Tier"]
                    while i < len(tierConsumableCounts):
                        if tierConsumableCounts[i] > 0 or i == len(tierConsumableCounts)-1:
                            tierConsumableCounts[i] -= 1
                            break
                        i += 1
                    
                    if item["Tier"] > tierNum:
                        msg += ":warning: One or more of these reward items cannot be acquired at Level " + str(lvl) + ".\n"
                        break
                        
                    elif item["Type"] == 'Consumables':
                        # for consumables we care about the charges
                        tracked_data = {key:value for key,value in item.items() if key in ["Name", "Charges"]}
                        tracked_data["Awarded"] = True
                        charDict['Consumables'].append(tracked_data)
                        
                    elif item["Type"] == 'Magic Items':
                        # for consumables we care if they are attunable
                        tracked_data = {key:value for key,value in item.items() if key in ["Attunement"]}
                        tracked_data["Awarded"] = True
                        
                        # to maintain parity we just give a default value
                        tracked_data["Item Spend"] = {"GP": 0}
                        charDict['Magic Items'][item["Name"]](tracked_data)
                        
                    else:
                        if r["Name"] in charDict['Inventory'].keys():
                            charDict['Inventory'][r['Name']]["Amount"] += 1
                            charDict['Inventory'][r['Name']]["Awarded"] += 1
                        else:
                            charDict['Inventory'][r['Name']] = {"Amount" : 1, "Awarded": 1}
                        


                if tier1CountMNC < 0 or any([count < 0 for count in tierConsumableCounts]):
                    msg += f":warning: You do not have the right roles for these reward items. You can only choose **{startt1MNC}** Tier 1 (Non-Consumable) item(s)"
                    z = 0
                    for amount in startCounts:
                        if amount > 0:
                            msg += f", and **{amount}** Tier {z} (or lower) item(s)"
                        z += 1
                    msg += "\n"
                      
        # ██████╗░░█████╗░░█████╗░███████╗░░░  ░█████╗░██╗░░░░░░█████╗░░██████╗░██████╗
        # ██╔══██╗██╔══██╗██╔══██╗██╔════╝░░░  ██╔══██╗██║░░░░░██╔══██╗██╔════╝██╔════╝
        # ██████╔╝███████║██║░░╚═╝█████╗░░░░░  ██║░░╚═╝██║░░░░░███████║╚█████╗░╚█████╗░
        # ██╔══██╗██╔══██║██║░░██╗██╔══╝░░██╗  ██║░░██╗██║░░░░░██╔══██║░╚═══██╗░╚═══██╗
        # ██║░░██║██║░░██║╚█████╔╝███████╗╚█║  ╚█████╔╝███████╗██║░░██║██████╔╝██████╔╝
        # ╚═╝░░╚═╝╚═╝░░╚═╝░╚════╝░╚══════╝░╚╝  ░╚════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚═════╝░
        # check race
        
        if msg == "":
            raceRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'races',race)
            if charEmbedmsg == "Fail":
                return
            if not raceRecord:
                msg += f'• {race} isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
            else:
                charDict['Race'] = raceRecord['Name']

        
        # Check Character's class
        msg, subclasses, classStat, charEmbed, charEmbedmsg = class_select_kernel(ctx, msg, lvl, charDict, classRecord, charEmbed, charEmbedmsg)
        
        if msg == "":
            if charEmbedmsg == "Fail":
                    return
            if not class_item_select_kernel(ctx, msg, charDict, character_class, classRecord, charEmbed, charEmbedmsg):
                return
            if not background_item_select_kernel(ctx, msg, charDict, background, charEmbed, charEmbedmsg):
                return
        
        # ░██████╗████████╗░█████╗░████████╗░██████╗░░░  ███████╗███████╗░█████╗░████████╗░██████╗
        # ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔════╝░░░  ██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝
        # ╚█████╗░░░░██║░░░███████║░░░██║░░░╚█████╗░░░░  █████╗░░█████╗░░███████║░░░██║░░░╚█████╗░
        # ░╚═══██╗░░░██║░░░██╔══██║░░░██║░░░░╚═══██╗██╗  ██╔══╝░░██╔══╝░░██╔══██║░░░██║░░░░╚═══██╗
        # ██████╔╝░░░██║░░░██║░░██║░░░██║░░░██████╔╝╚█║  ██║░░░░░███████╗██║░░██║░░░██║░░░██████╔╝
        # ╚═════╝░░░░╚═╝░░░╚═╝░░╚═╝░░░╚═╝░░░╚═════╝░░╚╝  ╚═╝░░░░░╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚═════╝░
        # Stats - Point Buy
        
        if msg == "":
            statsArray, charEmbedmsg = await characterCog.pointBuy(ctx, statsArray, raceRecord, charEmbed, charEmbedmsg)
            
            if not statsArray:
                return
            charDict["STR"] = statsArray[0]
            charDict["DEX"] = statsArray[1]
            charDict["CON"] = statsArray[2]
            charDict["INT"] = statsArray[3]
            charDict["WIS"] = statsArray[4]
            charDict["CHA"] = statsArray[5]
            
        #Stats - Feats
        if msg == "":
            msg, hpRecords, featsChosen = asi_select_kernel(ctx, msg, charDict, classRecord, raceRecord, charEmbed, charEmbedmsg)
            if not hpRecords:
                return
        
        maxStatStr = ""
        for sk in charDict['Max Stats'].keys():
            if charDict[sk] > charDict['Max Stats'][sk]:
                charDict[sk] = charDict['Max Stats'][sk]
        if hpRecords:
            charDict['HP'] = await characterCog.calcHP(ctx,hpRecords,charDict,lvl)
        error_msg = =f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```"
        if not await self.creation_confirm_kernel(ctx, error_msg, charDict, tierNum, charEmbed, charEmbedmsg):
            return
            
        statsCollection = db.stats
        statsRecord  = statsCollection.find_one({'Life': 1})

        for c in classStat:
            char = c.split('-')
            if char[0] in statsRecord['Class']:
                statsRecord['Class'][char[0]]['Count'] += 1
            else:
                statsRecord['Class'][char[0]] = {'Count': 1}

            if len(char) > 1:
                if char[1] in statsRecord['Class'][char[0]]:
                    statsRecord['Class'][char[0]][char[1]] += 1
                else:
                    statsRecord['Class'][char[0]][char[1]] = 1

        if charDict['Race'] in statsRecord['Race']:
            statsRecord['Race'][charDict['Race']] += 1
        else:
            statsRecord['Race'][charDict['Race']] = 1

        if charDict['Background'] in statsRecord['Background']:
            statsRecord['Background'][charDict['Background']] += 1
        else:
            statsRecord['Background'][charDict['Background']] = 1
                
        if featsChosen != "":
            feat_split = featsChosen.split(", ")
            for feat_key in feat_split:
                if not feat_key in statsRecord['Feats']:
                    statsRecord['Feats'][feat_key] = 1
                else:
                    statsRecord['Feats'][feat_key] += 1
        try:
            playersCollection.insert_one(charDict)
            if campaignTransferSuccess:
                target = f"Campaigns.{campaignKey}.Time"
                db.users.update_one({"User ID": str(author.id)}, {"$inc" : {target: -cpTransfered *3600}})
                await self.levelCheck(ctx, charDict["Level"], charDict["Name"])
            statsCollection.update_one({'Life':1}, {"$set": statsRecord}, upsert=True)
            
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            if charEmbedmsg:
                await charEmbedmsg.clear_reactions()
                await charEmbedmsg.edit(embed=charEmbed, content =f"Congratulations! :tada: You have created ***{charDict['Name']}***!")
            else: 
                charEmbedmsg = await channel.send(embed=charEmbed, content=f"Congratulations! You have created your ***{charDict['Name']}***!")

        self.bot.get_command('create').reset_cooldown(ctx)


    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command(aliases=['rs'])
    async def respec(self,ctx, name, newname, race, character_class, background, statsStr:int, statsDex:int, statsCon:int, statsInt:int, statsWis:int, statsCha:int):
        newname = newname.strip()
        characterCog = self.bot.get_cog('Character')
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        charEmbed = discord.Embed ()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

        statNames = ['STR','DEX','CON','INT','WIS','CHA']
        roles = [r.name for r in ctx.author.roles]
        charDict, charEmbedmsg = await checkForChar(ctx, name, charEmbed)

        if not charDict:
            return

        charRemoveKeyList = ['Predecessor','Image', 'T1 TP', 'T2 TP', 'T3 TP', 'T4 TP', 'T5 TP', 'Attuned', 'Spellbook', 'Guild', 'Guild Rank', 'Grouped']
        
        guild_name = ""
        
        if "Guild" in charDict:
            guild_name = charDict["Guild"]
        

        for c in charRemoveKeyList:
            if c in charDict:
                del charDict[c]
        name = charDict["Name"]
        charDict["Magic Items"] = {item : data for item, data in charDict["Magic Items"].items() if "Awarded" in data}
        charDict["Inventory"] = {item : data for item, data in charDict["Magic Items"].items() 
                                        if "Awarded" in data and data["Awarded"]>0}
        for data in charDict["Inventory"].values():
            data["Amount"] = data["Awarded"]
        
        charDict["Consumables"] = list(filter(lambda consum: "Awarded" in consum, charDict["Consumables"]))
            
        
        charID = charDict['_id']
        charDict['STR'] = int(statsStr)
        charDict['DEX'] = int(statsDex)
        charDict['CON'] = int(statsCon)
        charDict['INT'] = int(statsInt)
        charDict['WIS'] = int(statsWis)
        charDict['CHA'] = int(statsCha)
        charDict['GP'] = 0

        charDict['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}

        lvl = charDict['Level']
        msg = ""

        if 'Death' in charDict.keys():
            await channel.send(content=f"You cannot respec a dead character. Use the following command to decide their fate:\n```yaml\n$death \"{charRecords['Name']}\"```")
            return
        
        # level check
        if lvl > 4 and "Respecc" not in charDict:
            msg += "• Your character's level is way too high to respec.\n"
            await ctx.channel.send(msg)
            self.bot.get_command('respec').reset_cooldown(ctx) 
            return
        
        # Prevents name, level, race, class, background from being blank. Resets infinite cooldown and prompts
        if not newname:
            await channel.send(content=":warning: The new name of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return
        
        msg = self.name_check(newname)
        
        query = newname
        query = query.replace('(', '\\(')
        query = query.replace(')', '\\)')
        query = query.replace('.', '\\.')
        playersCollection = db.players
        userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' }}))

        if userRecords != list() and newname.lower() != name.lower():
            msg += f":warning: You already have a character by the name ***{newname}***. Please use a different name.\n"

        oldName = charDict['Name']
        charDict['Name'] = newname

        if not race:
            await channel.send(content=":warning: The race of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return

        if not character_class:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return
        
        if not background:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return


        
        extraCp = charDict['CP']
        charLevel = charDict['Level']
        if "Respecc" in charDict:
            maxCP = 10
            if charLevel < 5:
                maxCP = 4
            while(extraCp >= maxCP and charLevel <20):
                extraCp -= maxCP
                charLevel += 1
                if charLevel > 4:
                    maxCP = 10
            charDict["Level"] = charLevel
            charDict['CP'] = extraCp
            lvl = charLevel
        tierNum = 5
        # calculate the tier of the rewards
        if charLevel < 5:
            tierNum = 1
        elif charLevel < 11:
            tierNum = 2
        elif charLevel < 17:
            tierNum = 3
        elif charLevel < 20:
            tierNum = 4
        if extraCp > cp_bound_array[tierNum-1][0] and "Respecc" not in charDict:
            msg += f":warning: {oldName} needs to level up before they can respec into a new character!"
        
        levelCP = (((charLevel-5) * 10) + 16)
        if charLevel < 5:
            levelCP = ((charLevel -1) * 4)
            
        cp_tp_gp_array = calculateTreasure(1, 0, 1, (levelCP+extraCp)*3600)
        totalGP = cp_tp_gp_array[2]
        bankTP = cp_tp_gp_array[1]
        
        # Stats - Point Buy
        if msg == "":
            msg = self.point_buy_check

        
        # ██████╗░░█████╗░░█████╗░███████╗░░░  ░█████╗░██╗░░░░░░█████╗░░██████╗░██████╗
        # ██╔══██╗██╔══██╗██╔══██╗██╔════╝░░░  ██╔══██╗██║░░░░░██╔══██╗██╔════╝██╔════╝
        # ██████╔╝███████║██║░░╚═╝█████╗░░░░░  ██║░░╚═╝██║░░░░░███████║╚█████╗░╚█████╗░
        # ██╔══██╗██╔══██║██║░░██╗██╔══╝░░██╗  ██║░░██╗██║░░░░░██╔══██║░╚═══██╗░╚═══██╗
        # ██║░░██║██║░░██║╚█████╔╝███████╗╚█║  ╚█████╔╝███████╗██║░░██║██████╔╝██████╔╝
        # ╚═╝░░╚═╝╚═╝░░╚═╝░╚════╝░╚══════╝░╚╝  ░╚════╝░╚══════╝╚═╝░░╚═╝╚═════╝░╚═════╝░
        # check race
        rRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'races',race)
        if not rRecord:
            msg += f':warning: **{race}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        else:
            charDict['Race'] = rRecord['Name']
         
        # Check Character's class
        msg, subclasses, classStat, charEmbed, charEmbedmsg = class_select_kernel(ctx, msg, lvl, charDict, classRecord, charEmbed, charEmbedmsg)
        
        if msg == "":
            if charEmbedmsg == "Fail":
                    return
            if not class_item_select_kernel(ctx, msg, charDict, character_class, classRecord, charEmbed, charEmbedmsg):
                return
            if not background_item_select_kernel(ctx, msg, charDict, background, charEmbed, charEmbedmsg):
                return
        
        # ░██████╗████████╗░█████╗░████████╗░██████╗░░░  ███████╗███████╗░█████╗░████████╗░██████╗
        # ██╔════╝╚══██╔══╝██╔══██╗╚══██╔══╝██╔════╝░░░  ██╔════╝██╔════╝██╔══██╗╚══██╔══╝██╔════╝
        # ╚█████╗░░░░██║░░░███████║░░░██║░░░╚█████╗░░░░  █████╗░░█████╗░░███████║░░░██║░░░╚█████╗░
        # ░╚═══██╗░░░██║░░░██╔══██║░░░██║░░░░╚═══██╗██╗  ██╔══╝░░██╔══╝░░██╔══██║░░░██║░░░░╚═══██╗
        # ██████╔╝░░░██║░░░██║░░██║░░░██║░░░██████╔╝╚█║  ██║░░░░░███████╗██║░░██║░░░██║░░░██████╔╝
        # ╚═════╝░░░░╚═╝░░░╚═╝░░╚═╝░░░╚═╝░░░╚═════╝░░╚╝  ╚═╝░░░░░╚══════╝╚═╝░░╚═╝░░░╚═╝░░░╚═════╝░
        # Stats - Point Buy
        if msg == "":
            statsArray, charEmbedmsg = await characterCog.pointBuy(ctx, statsArray, rRecord, charEmbed, charEmbedmsg)

            
            if not statsArray:
                return
            charDict["STR"] = statsArray[0]
            charDict["DEX"] = statsArray[1]
            charDict["CON"] = statsArray[2]
            charDict["INT"] = statsArray[3]
            charDict["WIS"] = statsArray[4]
            charDict["CHA"] = statsArray[5]

        
        maxStatStr = ""
        for sk in charDict['Max Stats'].keys():
            if charDict[sk] > charDict['Max Stats'][sk]:
                charDict[sk] = charDict['Max Stats'][sk]
        if hpRecords:
            charDict['HP'] = await characterCog.calcHP(ctx,hpRecords,charDict,lvl)

        error_msg =  f"Character respec cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" \"new character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```"
        if not await self.creation_confirm_kernel(ctx, error_msg, charDict, tierNum, charEmbed, charEmbedmsg):
            return


        try:
            
            if len(guild_name)>0:
                guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": guild_name, '$options': 'i' }}))
                # If there is only one of user's character in the guild remove the role.
                if (len(guildAmount) <= 1):
                    await author.remove_roles(get(guild.roles, name = guild_name), reason=f" Respecced")

            if "Respecc" in charDict and charDict["Respecc"] == "Transfer":
                charDict["Inventory"].update(charDict["Transfer Set"]["Inventory"])
                charDict["Magic Items"] = charDict["Transfer Set"]["Magic Items"]
                charDict["Consumables"] = charDict["Transfer Set"]["Consumables"]
                del charDict["Transfer Set"]
                statsCollection = db.stats
                statsRecord  = statsCollection.find_one({'Life': 1})

                for c in classStat:
                    char = c.split('-')
                    if char[0] in statsRecord['Class']:
                        statsRecord['Class'][char[0]]['Count'] += 1
                    else:
                        statsRecord['Class'][char[0]] = {'Count': 1}

                    if len(char) > 1:
                        if char[1] in statsRecord['Class'][char[0]]:
                            statsRecord['Class'][char[0]][char[1]] += 1
                        else:
                            statsRecord['Class'][char[0]][char[1]] = 1

                if charDict['Race'] in statsRecord['Race']:
                    statsRecord['Race'][charDict['Race']] += 1
                else:
                    statsRecord['Race'][charDict['Race']] = 1

                if charDict['Background'] in statsRecord['Background']:
                    statsRecord['Background'][charDict['Background']] += 1
                else:
                    statsRecord['Background'][charDict['Background']] = 1
                if featsChosen != "":
                    feat_split = featsChosen.split(", ")
                    for feat_key in feat_split:
                        if not feat_key in statsRecord['Feats']:
                            statsRecord['Feats'][feat_key] = 1
                        else:
                            statsRecord['Feats'][feat_key] += 1
                statsCollection.update_one({'Life':1}, {"$set": statsRecord}, upsert=True)
                await self.levelCheck(ctx, charDict["Level"], charDict["Name"])
            # Extra to unset
            if "Respecc" in charDict:
                del charDict["Respecc"]
            charRemoveKeyList = {"Transfer Set" : 1, "Respecc" : 1, 'Image':1, 'Spellbook':1, 'Attuned':1, 'Guild':1, 'Guild Rank':1, 'Grouped':1}
            playersCollection.update_one({'_id': charID}, {"$set": charDict, "$unset": charRemoveKeyList }, upsert=True)
            
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            if charEmbedmsg:
                await charEmbedmsg.clear_reactions()
                await charEmbedmsg.edit(embed=charEmbed, content =f"Congratulations! You have respecced your character!")
            else: 
                charEmbedmsg = await channel.send(embed=charEmbed, content=f"Congratulations! You have respecced your character!")

        self.bot.get_command('respec').reset_cooldown(ctx)
    
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.command()
    async def bemine(self, ctx, char):
        channel = ctx.channel
        author = ctx.author
        shopEmbed = discord.Embed()
        
        # Check if character exists
        charRecords, shopEmbedmsg = await checkForChar(ctx, char, shopEmbed)

        if charRecords:
            
            outcomes = [("Ghost Pepper Chocolate", "Ghost Pepper Chocolate"), 
                    ("Wand of Smiles", "Wand of Smiles"), 
                    ("Promise Rings", "Band of Loyalty"), 
                    ("Arcanaloth's Music Box", "Arcanaloth's Music Box"), 
                    ("Talking Teddy Bear", "Talking Doll"), 
                    ("Crown of Blind Love", "Crown of the Forest"), 
                    ("Pipe of Remembrance", "Pipe of Remembrance"), 
                    ("Chocolate of Nourishment", "Bead of Nourishment"), 
                    ("Love Note Bird", "Paper Bird"), 
                    ("Perfume of Bewitching", "Perfume of Bewitching"), 
                    ("Philter of Love", "Philter of Love"), 
                    ("Swan Boat", "Quaal's Feather Token \\(Swan Boat\\)")]
            selection = random.randrange(len(outcomes)) 
            
            show_name, selected_item = outcomes[selection]
            amount = 0
            if "Event Token" in charRecords:
                amount = charRecords["Event Token"]
            if amount <= 0:
                shopEmbed.description = f"You would have received {show_name} ({selected_item})"
                shopEmbedmsg = await channel.send(embed=shopEmbed)
                ctx.command.reset_cooldown(ctx)
                return
            bRecord = db.rit.find_one({"Name" : {"$regex" : f"{selected_item}", "$options": "i"}}) 
            out_text = f"You reach into the gift box and find a(n) **{show_name} ({selected_item})**\n\n*{amount-1} rolls remaining*"
            if bRecord:
                
                if shopEmbedmsg:
                    await shopEmbedmsg.edit(embed=shopEmbed)
                else:
                    shopEmbedmsg = await channel.send(embed=shopEmbed)
                if bRecord["Type"] != "Inventory":
                    if charRecords[bRecord["Type"]]:
                        charRecords[bRecord["Type"]] += ', ' + selected_item
                    else:
                        charRecords[bRecord["Type"]] = selected_item
                else:
                    if bRecord['Name'] not in charRecords['Inventory']:
                        charRecords['Inventory'][f"{selected_item}"] = 1 
                    else:
                        charRecords['Inventory'][f"{selected_item}"] += 1 
                else:
                    if bRecord['Name'] not in charRecords['Inventory']:
                        charRecords['Inventory'][f"{selected_item}"] = {"Amount" : 1, "Awarded" : 1}
                    else:
                        charRecords['Inventory'][f"{selected_item}"]["Amount"] += 1 
                        if "Awarded" in charRecords['Inventory'][f"{selected_item}"]:
                            charRecords['Inventory'][f"{selected_item}"]["Awarded"] += 1 
                        else:
                            charRecords['Inventory'][f"{selected_item}"]["Awarded"] = 1 
                try:
                    playersCollection = db.players
                    playersCollection.update_one({'_id': charRecords['_id']}, {"$set": {bRecord["Type"]:charRecords[bRecord["Type"]]}, "$inc": {"Event Token": -1}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    shopEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    shopEmbed.description = out_text
                    await shopEmbedmsg.edit(embed=shopEmbed)

            else:
                try:
                    playersCollection = db.players
                    playersCollection.update_one({'_id': charRecords['_id']}, {"$inc": {f"Collectibles.{selected_item}": 1, "Event Token": -1}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    shopEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    shopEmbed.description = out_text
                    await channel.send(embed=shopEmbed)
                
        ctx.command.reset_cooldown(ctx)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def retire(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()
        charEmbedmsg = None

        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        def retireEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author
        if charDict:
            charID = charDict['_id']

            charEmbed.title = f"Are you sure you want to retire {charDict['Name']}?"
            charEmbed.description = "✅: Yes\n\n❌: Cancel"
            if not charEmbedmsg:
                charEmbedmsg = await channel.send(embed=charEmbed)
            else:
                await charEmbedmsg.edit(embed=charEmbed)

            await charEmbedmsg.add_reaction('✅')
            await charEmbedmsg.add_reaction('❌')
            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=retireEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await charEmbedmsg.delete()
                await channel.send(f'Retire cancelled. Try again using the same command:\n```yaml\n{commandPrefix}retire "character name"```')
                self.bot.get_command('retire').reset_cooldown(ctx)
                return
            else:
                await charEmbedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await charEmbedmsg.edit(embed=None, content=f'Retire cancelled. Try again using the same command:\n```yaml\n{commandPrefix}retire "character name"```')
                    await charEmbedmsg.clear_reactions()
                    self.bot.get_command('retire').reset_cooldown(ctx)
                    return
                elif tReaction.emoji == '✅':
                    charEmbed.clear_fields()
                    try:
                        playersCollection = db.players
                        
                        deadCollection = db.dead
                        usersCollection = db.users
                        if "Guild" in charDict:
                            guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": charDict['Guild'], '$options': 'i' }}))
                            # If there is only one of user's character in the guild remove the role.
                            if (len(guildAmount) <= 1):
                                await author.remove_roles(get(guild.roles, name = charDict['Guild']), reason=f"Left guild {charDict['Guild']}")

                         playersCollection.delete_one({'_id': charID})
                        
                        deadCollection.insert_one(charDict)
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try retiring your character again.")
                    else:
                        if charEmbedmsg:
                            await charEmbedmsg.clear_reactions()
                            await charEmbedmsg.edit(embed=None, content =f"Congratulations! You have retired ***{charDict['Name']}***. ")
                        else: 
                            charEmbedmsg = await channel.send(embed=None, content=f"Congratulations! You have retired ***{charDict['Name']}***.")

        self.bot.get_command('retire').reset_cooldown(ctx)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def death(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()
        charEmbedmsg = None
        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed)


        def retireEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        def deathEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '1️⃣') or (str(r.emoji) == '2️⃣') or (charDict['GP'] + deathDict["inc"]['GP']  >= gpNeeded and str(r.emoji) == '3️⃣') or (str(r.emoji) == '❌')) and u == author

        if charDict:
            if 'Death' not in charDict:
                await channel.send("Your character is not dead. You cannot use this command.")
                self.bot.get_command('death').reset_cooldown(ctx)
                return
            
            deathDict = charDict['Death']
            charID = charDict['_id']
            charLevel = charDict['Level']
            if charLevel < 5:
                gpNeeded = 100
                tierNum = 1
            elif charLevel < 11:
                gpNeeded = 500
                tierNum = 2
            elif charLevel < 17:
                gpNeeded = 750
                tierNum = 3
            elif charLevel < 21:
                gpNeeded = 1000
                tierNum = 4

            charEmbed.title = f"Character Death - {charDict['Name']}"
            charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

            if charDict['GP'] + deathDict["inc"]['GP'] < gpNeeded:
                charEmbed.description = f"Please choose between these three options for {charDict['Name']}:\n\n1️⃣: Death - Retires your character.\n2️⃣: Survival - Forfeit rewards and survive.\n3️⃣: ~~Revival~~ - You currently have {charDict['GP'] + deathDict['inc']['GP']} GP but need {gpNeeded} GP to be revived."
            else:
                charEmbed.description = f"Please choose between these three options for {charDict['Name']}:\n\n1️⃣: Death - Retires your character.\n2️⃣: Survival - Forfeit rewards and survive.\n3️⃣: Revival - Revives your character for {gpNeeded} GP."
            if not charEmbedmsg:
                charEmbedmsg = await channel.send(embed=charEmbed)
            else:
                await charEmbedmsg.edit(embed=charEmbed)

            await charEmbedmsg.add_reaction('1️⃣')
            await charEmbedmsg.add_reaction('2️⃣')
            if charDict['GP'] + deathDict["inc"]['GP']  >= gpNeeded:
                await charEmbedmsg.add_reaction('3️⃣')
            await charEmbedmsg.add_reaction('❌')
            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=deathEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await charEmbedmsg.delete()
                await channel.send(f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                self.bot.get_command('death').reset_cooldown(ctx)
                return
            else:
                await charEmbedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await charEmbedmsg.edit(embed=None, content=f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                    await charEmbedmsg.clear_reactions()
                    self.bot.get_command('death').reset_cooldown(ctx)

                    return
                elif tReaction.emoji == '1️⃣':
                    charEmbed.title = f"Are you sure you want to retire {charDict['Name']}?"
                    charEmbed.description = "✅: Yes\n\n❌: Cancel"
                    charEmbed.set_footer(text=charEmbed.Empty)
                    await charEmbedmsg.edit(embed=charEmbed)
                    await charEmbedmsg.add_reaction('✅')
                    await charEmbedmsg.add_reaction('❌')
                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=retireEmbedCheck , timeout=60)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                        self.bot.get_command('death').reset_cooldown(ctx)
                        return
                    else:
                        await charEmbedmsg.clear_reactions()
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name" "charactername"```')
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command('death').reset_cooldown(ctx)
                            return
                        elif tReaction.emoji == '✅':
                            charEmbed.clear_fields()
                            try:
                                playersCollection = db.players
                                deadCollection = db.dead
                                playersCollection.delete_one({'_id': charID})
                                guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": charDict['Guild'], '$options': 'i' }}))
                                # If there is only one of user's character in the guild remove the role.
                                if (len(guildAmount) <= 1):
                                    await author.remove_roles(get(guild.roles, name = charDict['Guild']), reason=f"Left guild {charDict['Guild']}")

                                usersCollection = db.users
                                
                                deadCollection.insert_one(charDict)
                                pass
                                
                            except Exception as e:
                                print ('MONGO ERROR: ' + str(e))
                                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try retiring your character again.")
                            else:
                                if charEmbedmsg:
                                    await charEmbedmsg.clear_reactions()
                                    await charEmbedmsg.edit(embed=None, content ="Congratulations! You have retired your character.")

                                else: 
                                    charEmbedmsg = await channel.send(embed=None, content="Congratulations! You have retired your character.")
                    
                elif tReaction.emoji == '2️⃣' or tReaction.emoji == '3️⃣':
                    charEmbed.clear_fields()
                    surviveString = f"Congratulations! ***{charDict['Name']}*** has survived and has forfeited their rewards."
                    data ={}
                    if tReaction.emoji == '3️⃣':
                        for d in charDict["Death"].keys():
                            data["$"+d] = charDict["Death"][d]
                        data["$inc"]["GP"] -= gpNeeded
                        surviveString = f"Congratulations! ***{charDict['Name']}*** has been revived and has kept their rewards!"
                    data["$unset"] = {"Death":1}
                    
                    try:
                        playersCollection = db.players
                        playersCollection.update_one({'_id': charID}, data)
                        
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the command again.")
                    else:
                        if charEmbedmsg:
                            await charEmbedmsg.clear_reactions()
                            await charEmbedmsg.edit(embed=None, content= surviveString)
                        else: 
                            charEmbedmsg = await channel.send(embed=None, content=surviveString)
        self.bot.get_command('death').reset_cooldown(ctx)


    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command(aliases=['bag','inv'])
    async def inventory(self,ctx, char, mod_override=""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        roleColors = {r.name:r.colour for r in guild.roles}
        charEmbed = discord.Embed()
        charEmbedmsg = None
        contents = []
        mod= False
        if mod_override:
            mod = "Mod Friend" in [role.name for role in author.roles]
        statusEmoji = ""
        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed, mod=mod)
        if charDict:
            footer = f"To view your character's info, type the following command: {commandPrefix}info {charDict['Name']}"
            charLevel = charDict['Level']
            if charLevel < 5:
                role = 1
                color = (roleColors['Junior Friend'])
            elif charLevel < 11:
                role = 2
                color = (roleColors['Journeyfriend'])
            elif charLevel < 17:
                role = 3
                color = (roleColors['Elite Friend'])
            elif charLevel < 21:
                role = 4
                color = (roleColors['True Friend'])

            # Show Spellbook in inventory
            if 'Spellbook' in charDict:
                spellBookString = ""
                for s in charDict['Spellbook']:
                    spellBookString += f"• {s['Name']} ({s['School']})\n" 
                contents.append(("Spellbook", spellBookString, False))
            if 'Ritual Book' in charDict:
                ritualBookString = ""
                for s in charDict['Ritual Book']:
                    ritualBookString += f"• {s['Name']} ({s['School']})\n" 
                contents.append(("Ritual Book", ritualBookString, False))

    
            # Show Consumables in inventory.
            consumesCount = {}
            for item in charDict['Consumables']]:
                consumable_text = item["Name"]
                if "Charges" in item:
                    consumable_text += f'[{item["Charges"]} Charges]'
                if consumable_text in consumesCount:
                    consumesCount[consumable_text] += 1
            
            consumesString = ""
            for k, v in consumesCount.items():
                if v == 1:
                    consumesString += f"• {k}\n"
                else:
                    consumesString += f"• {k} x{v}\n"

            if not consumesString:
                consumesString = "None"
                
            contents.append(("Consumables", consumesString, False))
            
            # Show Magic items in inventory.

            miString = ""
            miArray = 

            for name, item_data in miArray.items():
                modifiers = []
                if "Modifiers" in item_data:
                    modifiers = item_data["Modifiers"]
                if "Predecessor" in item_data:
                    upgrade_names = item_data["Names"]
                    stage = item_data["Stage"]
                if modifiers:
                    name = name + f" ({', '.join(modifiers)})"
                    
                miString += f"• {name}"
                if "Count" in v and v["Count"]>1:
                    miString += f" x{v['Count']}"
                miString += "\n"
                
            if not miString:
                miString = "None"
                
            contents.append((f"Magic Items", miString, False))

            charDictAuthor = guild.get_member(int(charDict['User ID']))
            
            if charDict['Inventory']:
                typeDict = {}
                invCollection = db.shop
                namingDict = {}
                searchList = []
                keys = charDict['Inventory'].keys()
                for dbEntry in keys:
                    searchTerm = dbEntry
                    if(searchTerm.startswith("Silvered ")):
                        searchTerm=searchTerm.replace("Silvered ", "", 1)
                    if(searchTerm.startswith("Adamantine ")):
                        searchTerm= searchTerm.replace("Adamantine ", "", 1)
                    if(searchTerm in namingDict):
                        namingDict[searchTerm].append(dbEntry)
                    else:
                        namingDict[searchTerm] = [dbEntry]
                    searchList.append(searchTerm)
                charInv = list(invCollection.find({"Name": {'$in': searchList}}))
                for i in charInv:
                    iType = i['Type'].split('(')
                    if len(iType) == 1:
                        iType.append("")
                    else:
                        iType[1] = '(' + iType[1]
                
                    iType[0] = iType[0].strip()

                    if isinstance(i['Name'], str):
                        for entry in namingDict[i['Name']]:
                            amt = charDict['Inventory'][entry]["Amount"]
                            if amt == 1:
                                amt = ""
                            else:
                                amt = f"x{amt}"
                            
                            if iType[0] not in typeDict:
                                typeDict[iType[0]] = [f"• {entry} {iType[1]} {amt}\n"]
                            else:
                                typeDict[iType[0]].append(f"• {entry} {iType[1]} {amt}\n")
                    else:
                        for k,v in charDict['Inventory'].items():
                            if k in i['Name']:
                                amt = v["Amount"]
                                if amt == 1:
                                    amt = ""
                                else:
                                    amt = f"x{amt}"
                                
                                if iType[0] not in typeDict:
                                    typeDict[iType[0]] = [f"• {k} {iType[1]} {amt}\n"]
                                else:
                                    typeDict[iType[0]].append(f"• {k} {iType[1]} {amt}\n")

                for k, v in typeDict.items():
                    v.sort()
                    vString = ''.join(v)
                    contents.append((f"{k}", vString, False))
                        

            if "Collectibles" in charDict:
                vString = ""
                for k, v in charDict["Collectibles"].items():
                    vString += f'• {k} x{v}\n'
                
                contents.append((f"Collectibles", vString, False))
            
            await paginate(ctx, self.bot, f"{charDict['Name']} (Lv {charLevel}): Inventory", contents, msg=charEmbedmsg, separator="\n", author = charDictAuthor, color= color, footer=footer)


            self.bot.get_command('inv').reset_cooldown(ctx)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command()
    async def user(self,ctx):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        search_author = author
        contents = []
        if len(ctx.message.mentions)>0 and "Mod Friend" in [role.name for role in author.roles]:
            search_author = ctx.message.mentions[0]
        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(search_author.id)})

        if not userRecords: 
            userRecords = {'User ID': str(search_author.id), 'Games' : 0}
            usersData = db.users.insert_one(userRecords)  
            await channel.send(f'A user profile has been created.') 
        playersCollection = db.players
        charRecords = list(playersCollection.find({"User ID": str(search_author.id)}))

        totalGamesPlayed = 0
        charString = ""
        charDictTiers = [[],[],[],[],[]]
        if charRecords:
            charRecords = sorted(charRecords, key=lambda k: k['Name']) 


            for c in charRecords:
                if c["Level"] < 5:
                    charDictTiers[0].append(c)
                elif c["Level"] < 11:
                    charDictTiers[1].append(c)
                elif c["Level"] < 17:
                    charDictTiers[2].append(c)
                elif c["Level"] < 20:
                    charDictTiers[3].append(c)
                else:
                    charDictTiers[4].append(c)


            for n in range(0,len(charDictTiers)):
                charString += f"\n———**Tier {n+1} Characters:**———\n"
                for charDict in charDictTiers[n]:
                    tempCharString = charString
                    char_race = charDict['Race']
                    char_class = charDict['Class']
                    if "Reflavor" in charDict:
                        rfarray = charDict['Reflavor']
                        if 'Race' in rfarray:
                            char_race = f"{rfarray['Race']} | {char_race}"
                        if 'Class' in rfarray:
                            char_class = f"{rfarray['Class']} | {char_class}"
                    charString += f"• **{charDict['Name']}**: Lv {charDict['Level']}, {char_race}, {char_class}\n"

                    if 'Guild' in charDict:
                        charString += f"---Guild: *{charDict['Guild']}*\n"

        else:
            charString = "None"


        if 'Games' in userRecords:
            totalGamesPlayed += userRecords['Games']
        if 'Double' in userRecords and userRecords["Double"]>0:
            
            contents.append((f"Double Reward", f"Your next **{userRecords['Double']}** games will have double rewards.", False))

        if "Guilds" in userRecords:
            guildNoodles = "• "
            guildNoodles += "\n• ".join(userRecords["Guilds"])
            
            contents.append((f"Guilds", f"You have created **{len(userRecords['Guilds'])}** guilds:\n {guildNoodles}", False))

        if "Campaigns" in userRecords:
            campaignString = ""
            for u, v in userRecords['Campaigns'].items():
                campaignString += f"• {(not v['Active'])*'~~'}{u}{(not v['Active'])*'~~'}: {v['Sessions']} sessions, {timeConversion(v['Time'])}\n"

            
            contents.append((f"Campaigns", campaignString, False))

        if 'Noodles' in userRecords:
            description = f"Total One-shots Played/Hosted: {totalGamesPlayed}\nNoodles: {userRecords['Noodles']}\n"
        else:
            description = f"Total One-shots Played/Hosted: {totalGamesPlayed}\nNoodles: 0 (Try hosting sessions to receive Noodles!)\n"
    
        description += f"Total Characters: {len(charRecords)}\nTier 1 Characters: {len(charDictTiers[0])}\nTier 2 Characters: {len(charDictTiers[1])}\nTier 3 Characters: {len(charDictTiers[2])}\nTier 4 Characters: {len(charDictTiers[3])}\nTier 5 Characters: {len(charDictTiers[4])}"

        contents.insert(0, (f"General Information",description, False))
        
        contents.append((f"Characters", charString, False))

        await paginate(ctx, self.bot, f"{search_author.display_name}" , contents, separator="\n", author = search_author)
   
            
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command()
    async def apply(self,ctx, char, cons="", mits=""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        roleColors = {r.name:r.colour for r in guild.roles}
        charEmbed = discord.Embed()
        charEmbedmsg = None

        statusEmoji = ""
        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed)
        if charDict:
            footer = f"Attuned magic items are bolded."
            if 'Image' in charDict:
                charEmbed.set_thumbnail(url=charDict['Image'])
            char_race = charDict['Race']
            char_class = charDict['Class']
            if "Reflavor" in charDict:
                rfdict = charDict['Reflavor']
                if 'Race' in rfdict and rfdict['Race'] != "":
                    char_race = f"{rfdict['Race']} | {char_race}"
                if 'Class' in rfdict and rfdict['Class'] != "":
                    char_class = f"{rfdict['Class']} | {char_class}"
            nick_string = ""
            if "Nickname" in charDict and charDict['Nickname'] != "":
                nick_string = f"Goes By: **{charDict['Nickname']}**\n"
            description = f"{nick_string}{char_race}\n{char_class}\n"
            
            charLevel = charDict['Level']
            if charLevel < 5:
                role = 1
                charEmbed.colour = (roleColors['Junior Friend'])
            elif charLevel < 11:
                role = 2
                charEmbed.colour = (roleColors['Journeyfriend'])
            elif charLevel < 17:
                role = 3
                charEmbed.colour = (roleColors['Elite Friend'])
            elif charLevel < 20:
                role = 4
                charEmbed.colour = (roleColors['True Friend'])
            else:
                role = 5
                charEmbed.colour = (roleColors['Ascended Friend'])

            cpSplit = charDict['CP']
            
            if 'Guild' in charDict:
                description += f"{charDict['Guild']}: Rank {charDict['Guild Rank']}"
            else:
                description += "No Guild"
            charDictAuthor = guild.get_member(int(charDict['User ID']))
            charEmbed.set_author(name=charDictAuthor, icon_url=charDictAuthor.avatar_url)
            charEmbed.description = description
            charEmbed.clear_fields()    
            charEmbed.title = f"{charDict['Name']} (Lv {charLevel}) - {charDict['CP']}/{cp_bound_array[role-1][1]} CP"
            
            
            notValidConsumables = ""
            consumesCount = {}
            for item in charDict['Consumables']]:
                consumable_text = item["Name"]
                if "Charges" in item:
                    consumable_text += f'[{item["Charges"]} Charges]'
                if consumable_text in consumesCount:
                    consumesCount[consumable_text] += 1
            if cons:
                consumablesList = list(map(lambda x: x.strip(), cons.split(',')))
                brought_consumables = {}
                
                consumableLength = 2 + (charDict["Level"]-1)//4
                if("Ioun Stone (Mastery)" in charDict['Magic Items']):
                    consumableLength += 1
                # block the command if more consumables than allowed (limit or available) are being registed
                if len(consumablesList) > consumableLength:
                    await channel.send(content=f'You are trying to bring in too many consumables (**{len(consumablesList)}/{consumableLength}**)! The limit for your character is **{consumableLength}**.')
                
                #loop over all consumable pairs and check if the listed consumables are in the inventory
        
                # consumablesList is the consumable list the player intends to bring
                # consumesCount are the consumables that the character has available.
                for item in consumablesList:
                    itemFound = False
                    for jk, jv in consumesCount.items():
                        if item.strip() != "" and item.lower().replace(" ", "").strip() in jk.lower().replace(" ", ""):
                            if jv > 0 :
                                consumesCount[jk] -= 1
                                if jk in brought_consumables:
                                    brought_consumables[jk] += 1
                                else:
                                    brought_consumables[jk] = 1
                                
                                itemFound = True
                                break

                    if not itemFound:
                        notValidConsumables += f"{item.strip()}, "
                        

                # if there were any invalid consumables, inform the user on which ones cause the issue
                if notValidConsumables:
                    notValidConsumables=f"The following consumables were not found in your character's inventory: {notValidConsumables}"
                    await channel.send(notValidConsumables[0:-2])
                    return
                    
                consumesCount = brought_consumables
            # Show Consumables in inventory.
            cPages = 1
            cPageStops = [0]

            consumesString = ""
            for k, v in consumesCount.items():
                if v == 1:
                    consumesString += f"• {k}\n"
                else:
                    consumesString += f"• {k} x{v}\n"

                if len(consumesString) > (768 * cPages):
                    cPageStops.append(len(consumesString))
                    cPages += 1
            
            cPageStops.append(len(consumesString))
            if not consumesString:
                consumesString = "None"
            if cPages > 1:
                for p in range(len(cPageStops)-1):
                    if(cPageStops[p+1] > cPageStops[p]):
                        charEmbed.add_field(name=f'Consumables - p. {p+1}', value=consumesString[cPageStops[p]:cPageStops[p+1]], inline=True)
            else:
                charEmbed.add_field(name='Consumables', value=consumesString, inline=True)

            # Show Magic items in inventory.
            mPages = 1
            mPageStops = [0]
            
            miString = ""
            miArray = charDict['Magic Items']
            notValidMagicItems = ""
            
            if mits:
                magic_item_list = list(map(lambda x: x.strip(), mits.split(',')))
                brought_mits = {}
                #loop over all magic item pairs and check if the listed consumables are in the inventory
        
                # magic_item_list is the magic item list the player intends to bring
                # miArray are the magic items that the character has available.
                for i in magic_item_list:
                    itemFound = False
                    for jk, jv in miArray.items():
                        if i.strip() != "" and i.lower().replace(" ", "").strip() in jk.lower().replace(" ", ""):
                            brought_mits[jk] = jv
                            itemFound = True
                            break

                    if not itemFound:
                        notValidMagicItems += f"{i.strip()}, "
                        

                # if there were any invalid consumables, inform the user on which ones cause the issue
                if notValidMagicItems:
                    notValidMagicItems=f"The following magic items were not found in your character's inventory: {notValidMagicItems}"
                    await channel.send(notValidMagicItems[0:-2])
                    return
                rit_db_entries = []
                miArray = brought_mits
            
            for name, item_data in miArray.items():
                    
                bolding = ""
                if "Attuned" in item_data and item_data["Attuned"]:
                    bolding = "**"
                    
                # mi was a non-con and not attuned and not requested
                if not mits and not bolding and "Count" in item_data:
                    continue
                modifiers = []
                if "Modifiers" in item_data:
                    modifiers = item_data["Modifiers"]
                if "Predecessor" in item_data:
                    upgrade_names = item_data["Names"]
                    stage = item_data["Stage"]
                    modifiers.insert(0, upgrade_names[stage])
                if modifiers:
                    name = name + f" ({', '.join(modifiers)})"
                
                miString += f"• {bolding}{name}{bolding}"
                if "Count" in item_data and item_data["Count"]>1:
                    miString += f" x{item_data['Count']}"
                miString += "\n"

                if len(miString) > (768 * mPages):
                    mPageStops.append(len(miString))
                    mPages += 1

            mPageStops.append(len(miString))
            if not miString:
                miString = "None"
            if mPages > 1:
                for p in range(len(mPageStops)-1):
                    if(mPageStops[p+1] > mPageStops[p]):
                        charEmbed.add_field(name=f'Magic Items - p. {p+1}', value=miString[mPageStops[p]:mPageStops[p+1]], inline=True)
            else:
                charEmbed.add_field(name='Magic Items', value=miString, inline=True)
            
            charEmbed.set_footer(text=footer)
                
            if not charEmbedmsg:
                charEmbedmsg = await ctx.channel.send(embed=charEmbed)
            else:
                await charEmbedmsg.edit(embed=charEmbed)
        
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command(aliases=['i', 'char'])
    async def info(self,ctx, char, mod_override = ""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        roleColors = {r.name:r.colour for r in guild.roles}
        charEmbed = discord.Embed()
        charEmbedmsg = None
        mod= False
        if mod_override:
            mod = "Mod Friend" in [role.name for role in author.roles]
        statusEmoji = ""
        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed, mod=mod)
        if charDict:
            footer = f"To view your character's inventory, type the following command: {commandPrefix}inv {charDict['Name']}"
            
            char_race = charDict['Race']
            char_class = charDict['Class']
            char_background = charDict['Background']
            if "Reflavor" in charDict:
                rfdict = charDict['Reflavor']
                if 'Race' in rfdict and rfdict['Race'] != "":
                    char_race = f"{rfdict['Race']} | {char_race}"
                if 'Class' in rfdict and rfdict['Class'] != "":
                    char_class = f"{rfdict['Class']} | {char_class}"
                if 'Background' in rfdict and rfdict['Background'] != "":
                    char_background = f"{rfdict['Background']} | {char_background}"
            nick_string = ""
            if "Nickname" in charDict and charDict['Nickname'] != "":
                nick_string = f"Goes By: **{charDict['Nickname']}**\n"
            alignment_string = "Alignment: Unknown\n"
            if "Alignment" in charDict and charDict['Alignment'] != "":
                alignment_string = f"Alignment: {charDict['Alignment']}\n"

            description = f"{nick_string}{char_race}\n{char_class}\n{char_background}\n{alignment_string}One-shots Played: {charDict['Games']}\n"
            if 'Proficiency' in charDict:
                description +=  f"• Extra Training: {charDict['Proficiency']}\n"
            if 'NoodleTraining' in charDict:
                description +=  f"• Noodle Training: {charDict['NoodleTraining']}\n"
            description += f":moneybag: {charDict['GP']} GP\n"
            charLevel = charDict['Level']
            if charLevel < 5:
                role = 1
                charEmbed.colour = (roleColors['Junior Friend'])
            elif charLevel < 11:
                role = 2
                charEmbed.colour = (roleColors['Journeyfriend'])
            elif charLevel < 17:
                role = 3
                charEmbed.colour = (roleColors['Elite Friend'])
            elif charLevel < 20:
                role = 4
                charEmbed.colour = (roleColors['True Friend'])
            else:
                role = 5
                charEmbed.colour = (roleColors['Ascended Friend'])

            cpSplit = charDict['CP']
            if charLevel < 20 and cpSplit >= cp_bound_array[role-1][0]:
                footer += f'\nYou need to level up! Use the following command before playing in another quest to do so: {commandPrefix}levelup {charDict["Name"]}'


            if charLevel == 4 or charLevel == 10 or charLevel == 16:
                footer += f'\nYou will no longer receive Tier {role} TP the next time you level up! Please plan accordingly.'

            if 'Death' in charDict:
                statusEmoji = "⚰️"
                description += f"{statusEmoji} Status: **DEAD** -  decide their fate with the following command: {commandPrefix}death" 
                charEmbed.colour = discord.Colour(0xbb0a1e)

            charDictAuthor = guild.get_member(int(charDict['User ID']))
            charEmbed.set_author(name=charDictAuthor, icon_url=charDictAuthor.avatar_url)
            charEmbed.description = description
            charEmbed.clear_fields()    
            charEmbed.title = f"{charDict['Name']} (Lv {charLevel}) - {charDict['CP']}/{cp_bound_array[role-1][1]} CP"
            tpString = ""
            for i in range (1,6):
                if f"T{i} TP" in charDict:
                    tpString += f"• Tier {i} TP: {charDict[f'T{i} TP']} \n" 
            if tpString:
                charEmbed.add_field(name='TP', value=f"{tpString}", inline=True)
            if 'Guild' in charDict:
                charEmbed.add_field(name='Guild', value=f"{charDict['Guild']}: Rank {charDict['Guild Rank']}", inline=True)
            charEmbed.add_field(name='Feats', value=charDict['Feats'], inline=False)

            if 'Free Spells' in charDict:
                fsString = ""
                fsIndex = 0
                for el in charDict['Free Spells']:
                    if el > 0:
                        fsString += f"Level {fsIndex+1}: {el} free spells\n"
                    fsIndex += 1

                if fsString:
                    charEmbed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)

            maxStatDict = charDict['Max Stats']

            for sk in charDict['Max Stats'].keys():
                if charDict[sk] > charDict['Max Stats'][sk]:
                    charDict[sk] = charDict['Max Stats'][sk]
            
            
            totalHPAdd = 0
            attuned_items_dic = {key : item_data for key, item_data in charRecords['Magic Items'].items() 
                                if "Attunement" in item_data and item_data["Attunement"]}
            
            # Check for stat increases in attuned magic items.
            if attuned_items_dic:
                    
                charEmbed.add_field(name='Attuned', value='\n• '.join(attuned_items_dic.keys()), inline=False)
                statBonusDict = { 'STR': 0 ,'DEX': 0,'CON': 0, 'INT': 0, 'WIS': 0,'CHA': 0}
                for key, attuned_item in attuned_items_dic.items():
                        if 'HP' in attuned_item:
                            totalHPAdd += attuned_item['HP']
                        statBonus = attuned_item['Stat Bonuses']
                        if '+' not in statBonus:
                            statSplit = statBonus.split(' ')
                            modStat = str(charDict[statSplit[0]]).replace(')', '').split(' (')[0]
                            if int(statSplit[1]) > int(modStat):
                                maxStatNum = statSplit[1]
                                if '(' in str(charDict[statSplit[0]]):
                                    maxStatNum = max(int(str((charDict[statSplit[0]])).replace(')', '').split(' (')[1]), int(statSplit[1]) )
                                charDict[statSplit[0]] = f"{modStat} ({maxStatNum})"

                        elif '+' in statBonus:
                            statSplit = statBonus.split(' +')
                            if 'MAX' in statSplit[0]:
                                maxStat = statSplit[0][:-3]
                                statSplit[0] = statSplit[0].replace(maxStat, "")
                                maxStat = maxStat.split(" ")
                                maxStatDict[statSplit[0]] += int(statSplit[1])

                            modStat = str(charDict[statSplit[0]])
                            modStat = modStat.split(' (')[0]
                            statBonusDict[statSplit[0]] += int(statSplit[1])
                            statName = charDict[statSplit[0]]
                            maxCalc = int(modStat) + int(statBonusDict[statSplit[0]]) > maxStatDict[statSplit[0]]

                            if maxCalc:
                                statBonusDict[statSplit[0]] = maxStatDict[statSplit[0]] - int(modStat)
                                
                            if statBonusDict[statSplit[0]] > 0: 
                                charDict[statSplit[0]] = f"{modStat} (+{statBonusDict[statSplit[0]]})" 
                            else:
                                charDict[statSplit[0]] = f"{modStat}" 

                # recalc CON
                if statBonusDict['CON'] != 0 or '(' in str(charDict['CON']):
                    trueConValue = charDict['CON']
                    conValue = charDict['CON'].replace(')', '').split('(')            

                    if len(conValue) > 1:
                        trueConValue = max(map(lambda x: int(x), conValue))

                    if '+' in conValue[1]:
                        trueConValue = int(conValue[1].replace('+', '')) + int(conValue[0])


                    charDict['HP'] -= ((int(conValue[0]) - 10) // 2) * charLevel
                    charDict['HP'] += ((int(trueConValue) - 10) // 2) * charLevel

            charDict['HP'] += totalHPAdd * charLevel

            charEmbed.add_field(name='Stats', value=f":heart: {charDict['HP']} Max HP\n• STR: {charDict['STR']} \n• DEX: {charDict['DEX']} \n• CON: {charDict['CON']} \n• INT: {charDict['INT']} \n• WIS: {charDict['WIS']} \n• CHA: {charDict['CHA']}", inline=False)
            
            charEmbed.set_footer(text=footer)

            if 'Image' in charDict:
                charEmbed.set_thumbnail(url=charDict['Image'])

            if not charEmbedmsg:
                charEmbedmsg = await ctx.channel.send(embed=charEmbed)
            else:
                await charEmbedmsg.edit(embed=charEmbed)

            self.bot.get_command('info').reset_cooldown(ctx)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command(aliases=['img'])
    @is_log_channel()
    async def image(self,ctx, char, url):

        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()

        character_record, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if character_record:
            charID = character_record['_id']
            data = {
                'Image': url
            }

            try:
                r = requests.head(url)
                if r.status_code != requests.codes.ok:
                    await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{commandPrefix}image "character name" URL```\n') 
                    return
            except:
                await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{commandPrefix}image "character name" URL```\n') 

                return
              
            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the image for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    async def reflavorKernel(self,ctx, char, rtype, new_flavor):
             
        if( len(new_flavor) > 20):
            await ctx.channel.send(content=f'The new {rtype.lower()} must be between 1 and 20 symbols.')
            return
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()

        character_record, charEmbedmsg = await checkForChar(ctx, char, charEmbed)
        if character_record:
            charID = character_record['_id']
            
            try:
                db.players.update_one({'_id': charID}, {"$set": {'Reflavor.'+rtype: new_flavor}})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try reflavoring your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the {rtype} for ***{character_record["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @reflavor.command()
    async def race(self,ctx, char, *, new_flavor=""):
        
        rtype = "Race"
        await self.reflavorKernel(ctx, char, rtype, new_flavor)
        
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @reflavor.command(aliases=['class'])
    async def classes(self,ctx, char, *, new_flavor=""):
        
        rtype = "Class"
        await self.reflavorKernel(ctx, char, rtype, new_flavor)
        
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @reflavor.command()
    async def background(self,ctx, char, *, new_flavor=""):
        
        rtype = "Background"
        await self.reflavorKernel(ctx, char, rtype, new_flavor)
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command()
    async def align(self,ctx, char, *, new_align):
        if( len(new_align) > 20 or len(new_align) <1):
            await ctx.channel.send(content=f'The new alignment must be between 1 and 20 symbols.')
            return

    
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()

        character_record, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if character_record:
            charID = character_record['_id']
            data = {
                'Alignment': new_align
            }

            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the alignment for ***{character_record["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['aka'])
    async def alias(self,ctx, char, new_name = ""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        msg = self.name_check(new_name)
        if msg:
            await channel.send(msg)
            return
            
        charEmbed = discord.Embed()

        character_record, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if character_record:
            charID = character_record['_id']
            data = {
                'Nickname': new_name
            }

            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the name for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
            
    def name_check(self, name):
        msg = ""
        # Name should be less then 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"


        for i in self.invalidChars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"

        return msg
    
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command(aliases=['lvl', 'lvlup', 'lv'])
    async def levelup(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        levelUpEmbed = discord.Embed ()
        characterCog = self.bot.get_cog('Character')
        character_record, levelUpEmbedmsg = await checkForChar(ctx, char, levelUpEmbed)
        charClassChoice = ""
        if character_record:
            charID = character_record['_id']
            charDict = {}
            charName = character_record['Name']
            charClass = character_record['Class']
            cpSplit= character_record['CP']
            charLevel = character_record['Level']
            charStats = {'STR':character_record['STR'], 
                        'DEX':character_record['DEX'], 
                        'CON':character_record['CON'], 
                        'INT':character_record['INT'], 
                        'WIS':character_record['WIS'], 
                        'CHA':character_record['CHA']}
            charHP = character_record['HP']
            charFeats = character_record['Feats']
            freeSpells = [0] * 9
            
            tierNum=5
            # calculate the tier of the rewards
            if charLevel < 5:
                tierNum = 1
            elif charLevel < 11:
                tierNum = 2
            elif charLevel < 17:
                tierNum = 3
            elif charLevel < 20:
                tierNum = 4
                
            if 'Free Spells' in character_record:
                freeSpells = character_record['Free Spells']

            if 'Death' in character_record.keys():
                await channel.send(f'You cannot level up a dead character. Use the following command to decide their fate:\n```yaml\n$death "{charRecords["Name"]}"```')
                self.bot.get_command('levelup').reset_cooldown(ctx)
                return

            if charLevel > 19:
                await channel.send(f"***{character_record['Name']}*** is level 20 and cannot level up anymore.")
                self.bot.get_command('levelup').reset_cooldown(ctx)
                return
                

            elif cpSplit < cp_bound_array[tierNum-1][0]:
                await channel.send(f'***{charName}*** is not ready to level up. They currently have **{cpSplit}/{cp_bound_array[tierNum-1][1]}** CP.')
                self.bot.get_command('levelup').reset_cooldown(ctx)
                return
            else:
                cRecords, levelUpEmbed, levelUpEmbedmsg = await callAPI(ctx, levelUpEmbed, levelUpEmbedmsg,'classes')
                classRecords = sorted(cRecords, key=lambda k: k['Name']) 
                leftCP = cpSplit - cp_bound_array[tierNum-1][0]
                newCharLevel = charLevel  + 1
                totalCP = leftCP
                subclasses = []
                class_name = charClass
                if '/' in charClass:
                    tempClassList = charClass.split(' / ')
                    for t in tempClassList:
                        temp = t.split(' ')
                        tempSub = ""
                        if '(' and ')' in t:
                            tempSub = t[t.find("(")+1:t.find(")")]
                        class_name = temp[0]
                        subclasses.append({'Name':class_name, 'Subclass':tempSub, 'Level':int(temp[1])})
                else:
                    tempSub = ""
                    if '(' and ')' in charClass:
                        tempSub = charClass[charClass.find("(")+1:charClass.find(")")]
                        class_name = charClass[0:charClass.find("(")].strip()
                    subclasses.append({'Name':class_name, 'Subclass':tempSub, 'Level':charLevel})

                for c in classRecords:
                    for s in subclasses:
                        if c['Name'] in s['Name']:
                            s['Hit Die Max'] = c['Hit Die Max']
                            s['Hit Die Average'] = c['Hit Die Average']
                            if "Spellcasting" in c:
                                s["Spellcasting"] = c["Spellcasting"]

                
                def multiclassEmbedCheck(r, u):
                        sameMessage = False
                        if levelUpEmbedmsg.id == r.message.id:
                            sameMessage = True
                        return sameMessage and ((str(r.emoji) == '✅' and multi_error == "") or (str(r.emoji) == '🚫') or (str(r.emoji) == '❌')) and u == author
                def alphaEmbedCheck(r, u):
                        sameMessage = False
                        if levelUpEmbedmsg.id == r.message.id:
                            sameMessage = True
                        return sameMessage and ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author


                levelUpEmbed.clear_fields()
                lvl = charLevel
                newLevel = charLevel + 1
                levelUpEmbed.title = f"{charName}: Level Up! {lvl} → {newLevel}"
                levelUpEmbed.description = f"{character_record['Race']}: {charClass}\n**STR**: {charStats['STR']} **DEX**: {charStats['DEX']} **CON**: {charStats['CON']} **INT**: {charStats['INT']} **WIS**: {charStats['WIS']} **CHA**: {charStats['CHA']}"
                chooseClassString = ""
                alphaIndex = 0
                classes = []
                lvlClass = charClass

                # Multiclass Requirements
                failMulticlassList = []
                baseClass = {'Name': ''}
                
                for cRecord in classRecords:
                    if cRecord['Name'] in charClass:
                        baseClass = cRecord

                    statReq = cRecord['Multiclass'].split(' ')
                    if cRecord['Multiclass'] != 'None':
                        if '/' not in cRecord['Multiclass'] and '+' not in cRecord['Multiclass']:
                            if int(character_record[statReq[0]]) < int(statReq[1]):
                                failMulticlassList.append(cRecord['Name'])
                                continue
                        elif '/' in cRecord['Multiclass']:
                            statReq[0] = statReq[0].split('/')
                            reqFufill = False
                            for s in statReq[0]:
                                if int(character_record[s]) >= int(statReq[1]):
                                    reqFufill = True
                            if not reqFufill:
                                failMulticlassList.append(cRecord['Name'])
                                continue

                        elif '+' in cRecord['Multiclass']:
                            statReq[0] = statReq[0].split('+')
                            reqFufill = True
                            for s in statReq[0]:
                                if int(character_record[s]) < int(statReq[1]):
                                    reqFufill = False
                                    break
                            if not reqFufill:
                                failMulticlassList.append(cRecord['Name'])
                                continue


                        if cRecord['Name'] not in failMulticlassList and cRecord['Name'] != baseClass['Name']:
                            chooseClassString += f"{alphaEmojis[alphaIndex]}: {cRecord['Name']}\n"
                            alphaIndex += 1
                            classes.append(cRecord['Name'])
                multi_error = ""
                # New Multiclass
                if baseClass['Name'] in failMulticlassList:
                    multi_error = f"You cannot multiclass right now because your base class, **{baseClass['Name']}**, requires at least **{baseClass['Multiclass']}**.\nCurrent stats: **STR**: {charStats['STR']} **DEX**: {charStats['DEX']} **CON**: {charStats['CON']} **INT**: {charStats['INT']} **WIS**: {charStats['WIS']} **CHA**: {charStats['CHA']}\n"
                elif chooseClassString == "":
                    multi_error = "There are no classes available to multiclass into. \n"
                    
                if multi_error != "":
                    levelUpEmbed.add_field(name=f"""~~Would you like to choose a new multiclass?~~\nPlease react with "No" to proceed.""", value=f'{multi_error}✅: ~~Yes~~\n\n🚫: No\n\n❌: Cancel')

                else:
                    levelUpEmbed.add_field(name="Would you like to choose a new multiclass?", value='✅: Yes\n\n🚫: No\n\n❌: Cancel')
                
                if not levelUpEmbedmsg:
                    levelUpEmbedmsg = await channel.send(embed=levelUpEmbed)
                else:
                    await levelUpEmbedmsg.edit(embed=levelUpEmbed)
                if multi_error == "":
                    await levelUpEmbedmsg.add_reaction('✅')
                await levelUpEmbedmsg.add_reaction('🚫')
                await levelUpEmbedmsg.add_reaction('❌')
                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=multiclassEmbedCheck, timeout=60)
                except asyncio.TimeoutError:
                    await levelUpEmbedmsg.delete()
                    await channel.send(f'Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup "character name"\n{commandPrefix}lvlup "character name"\n{commandPrefix}lvl "character name"\n{commandPrefix}lv "character name"```')
                    self.bot.get_command('levelup').reset_cooldown(ctx)
                    return
                else:
                    await levelUpEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await levelUpEmbedmsg.edit(embed=None, content=f"Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup \"character name\"\n{commandPrefix}lvlup \"character name\"\n{commandPrefix}lvl \"character name\"\n{commandPrefix}lv \"character name\"```")
                        await levelUpEmbedmsg.clear_reactions()
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return
                    elif tReaction.emoji == '✅':
                        levelUpEmbed.clear_fields()
                        
                        levelUpEmbed.add_field(name="Pick a new class that you would like to multiclass into.", value=chooseClassString)

                        await levelUpEmbedmsg.edit(embed=levelUpEmbed)
                        await levelUpEmbedmsg.add_reaction('❌')
                        try:
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                        except asyncio.TimeoutError:
                            await levelUpEmbedmsg.delete()
                            await channel.send(f'Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup "character name"\n{commandPrefix}lvlup "character name"\n{commandPrefix}lvl "character name"\n{commandPrefix}lv "character name"```')
                            self.bot.get_command('levelup').reset_cooldown(ctx)
                            return
                        else:
                            await levelUpEmbedmsg.clear_reactions()
                            if tReaction.emoji == '❌':
                                await levelUpEmbedmsg.edit(embed=None, content=f"Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup \"character name\"\n{commandPrefix}lvlup \"character name\"\n{commandPrefix}lvl \"character name\"\n{commandPrefix}lv \"character name\"```")
                                await levelUpEmbedmsg.clear_reactions()
                                self.bot.get_command('levelup').reset_cooldown(ctx)
                                return

                            if '/' not in charClass:
                                if '(' in charClass and ')' in charClass:
                                    charClass = charClass.replace('(', f"{lvl} (")
                                else:
                                    charClass += ' ' + str(lvl)
                                
                            charClassChoice = classes[alphaEmojis.index(tReaction.emoji)]
                            charClass += f' / {charClassChoice} 1'
                            lvlClass = charClassChoice
                            for c in classRecords:
                                if c['Name'] in charClassChoice:
                                    subclass_entry_add = {'Name': charClassChoice, 'Subclass': '', 'Level': 1, 'Hit Die Max': c['Hit Die Max'], 'Hit Die Average': c['Hit Die Average']}
                                    if "Spellcasting" in c:
                                        subclass_entry_add["Spellcasting"] = c["Spellcasting"]

                                    subclasses.append(subclass_entry_add)

                            if "Wizard" in charClassChoice:
                                freeSpells[0] += 6

                            levelUpEmbed.description = f"{character_record['Race']}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"
                            levelUpEmbed.clear_fields()
                    elif tReaction.emoji == '🚫':
                        if '/' not in charClass:
                            lvlClass = class_name
                            subclasses[0]['Level'] += 1
                            if 'Wizard' in charClass: 
                                fsLvl = (subclasses[0]['Level'] - 1) // 2
                                if fsLvl > 8:
                                    fsLvl = 8

                                freeSpells[fsLvl] += 2
                        else:
                            multiclassLevelString = ""
                            alphaIndex = 0
                            for sc in subclasses:
                                multiclassLevelString += f"{alphaEmojis[alphaIndex]}: {sc['Name']} Level {sc['Level']}\n"
                                alphaIndex += 1
                            levelUpEmbed.clear_fields()
                            levelUpEmbed.add_field(name=f"What class would you like to level up?", value=multiclassLevelString, inline=False)
                            await levelUpEmbedmsg.edit(embed=levelUpEmbed)
                            await levelUpEmbedmsg.add_reaction('❌')
                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                            except asyncio.TimeoutError:
                                await levelUpEmbedmsg.delete()
                                await channel.send(f'Level up timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                                self.bot.get_command('levelup').reset_cooldown(ctx)
                                return
                            else:
                                if tReaction.emoji == '❌':
                                    await levelUpEmbedmsg.edit(embed=None, content=f"Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup \"character name\"\n{commandPrefix}lvlup \"character name\"\n{commandPrefix}lvl \"character name\"\n{commandPrefix}lv \"character name\"```")
                                    await levelUpEmbedmsg.clear_reactions()
                                    self.bot.get_command('levelup').reset_cooldown(ctx)
                                    return
                            await levelUpEmbedmsg.clear_reactions()
                            levelUpEmbed.clear_fields()
                            choiceLevelClass = multiclassLevelString.split('\n')[alphaEmojis.index(tReaction.emoji)]

                            for s in subclasses:
                                if s['Name'] in choiceLevelClass:
                                    lvlClass = s['Name']
                                    s['Level'] += 1
                                    if 'Wizard' in s['Name']:
                                        fsLvl = (s['Level'] - 1) // 2
                                        if fsLvl > 8:
                                            fsLvl = 8
                                        freeSpells[fsLvl] += 2
                                    break

                            charClass = charClass.replace(f"{lvlClass} {subclasses[alphaEmojis.index(tReaction.emoji)]['Level'] - 1}", f"{lvlClass} {subclasses[alphaEmojis.index(tReaction.emoji)]['Level']}")
                            levelUpEmbed.description = f"{character_record['Race']}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"
                # Choosing a subclass
                subclassCheckClass = subclasses[[s['Name'] for s in subclasses].index(lvlClass)]

                for s in classRecords:
                    if s['Name'] == subclassCheckClass['Name'] and int(s['Subclass Level']) == subclassCheckClass['Level']:
                        subclassesList = s['Subclasses'].split(', ')
                        subclassChoice, levelUpEmbedmsg = await characterCog.chooseSubclass(ctx, subclassesList, s['Name'], levelUpEmbed, levelUpEmbedmsg) 
                        if not subclassChoice:
                            return
                        
                        if '/' not in charClass:
                            levelUpEmbed.description = levelUpEmbed.description.replace(s['Name'], f"{s['Name']} ({subclassChoice})") 
                            charClass = charClass.replace(s['Name'], f"{s['Name']} ({subclassChoice})" )
                        else:
                            levelUpEmbed.description = levelUpEmbed.description.replace(f"{s['Name']} {subclassCheckClass['Level']}", f"{s['Name']} {subclassCheckClass['Level']} ({subclassChoice})" ) 
                            charClass = charClass.replace(f"{s['Name']} {subclassCheckClass['Level']}", f"{s['Name']} {subclassCheckClass['Level']} ({subclassChoice})" )

                        for sub in subclasses:
                            if sub['Name'] == subclassCheckClass['Name']:
                                sub['Subclass'] = subclassChoice
                
                # Feat 
                featLevels = []
                for c in subclasses:
                    if (int(c['Level']) in (4,8,12,16,19) or ('Fighter' in c['Name'] and int(c['Level']) in (6,14)) or ('Rogue' in c['Name'] and int(c['Level']) == 10)) and lvlClass in c['Name']:
                        featLevels.append(int(c['Level']))
                
                statsFeats = {}
                
                charFeatsGained = ""
                charFeatsGainedStr = ""
                if featLevels != list():
                    featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, character_record['Race'], charClass, subclasses, featLevels, levelUpEmbed, levelUpEmbedmsg, character_record, charFeats)
                    if not featsChosen and not statsFeats and not charEmbedmsg:
                        return

                    charStats = statsFeats 
                    
                    if featsChosen != list():
                        charFeatsGained = featsChosen

                if charFeatsGained != "":
                    charFeatsGainedStr = f"Feats Gained: **{charFeatsGained}**"

                data = {
                      'Class': charClass,
                      'Level': int(newCharLevel),
                      'CP': totalCP,
                      'STR': int(charStats['STR']),
                      'DEX': int(charStats['DEX']),
                      'CON': int(charStats['CON']),
                      'INT': int(charStats['INT']),
                      'WIS': int(charStats['WIS']),
                      'CHA': int(charStats['CHA']),
                }
                if statsFeats and "Ritual Book" in statsFeats:
                    data["Ritual Book"] = statsFeats["Ritual Book"] 
                if 'Free Spells' in character_record:
                    if freeSpells != ([0] * 9):
                        data['Free Spells'] = freeSpells

                if charFeatsGained != "":
                    if character_record['Feats'] == 'None':
                        data['Feats'] = charFeatsGained
                        character_record['Feats'] = charFeatsGained
                    else:
                        data['Feats'] = charFeats + ", " + charFeatsGained
                        character_record['Feats'] = charFeats + ", " + charFeatsGained

                stats_increment = {"Class" : {}}
                
                if charFeatsGained != "":
                    stats_increment["Feats"]
                    feat_split = charFeatsGained.split(", ")
                    for feat_key in feat_split:
                        stats_increment["Feats"][feat_key] = 1

                            
                subclassCheckClass['Name'] = subclassCheckClass['Name'].split(' (')[0]
                if subclassCheckClass['Subclass'] != "" :
                    stats_increment['Class'] = {subclassCheckClass['Name'] : {subclassCheckClass['Subclass'] : 1}}}
                else:
                    stats_increment['Class'] = {subclassCheckClass['Name'] : {"Count" : 1}}}

                
                data['Max Stats'] = character_record['Max Stats']

                #Special stat bonuses (Barbarian cap / giant soul sorc)
                specialCollection = db.special
                specialRecords = list(specialCollection.find())
                specialStatStr = ""
                for s in specialRecords:
                    if 'Bonus Level' in s:
                        for c in subclasses:
                            if s['Bonus Level'] == c['Level'] and s['Name'] in f"{c['Name']} ({c['Subclass']})":
                                if 'MAX' in s['Stat Bonuses']:
                                    statSplit = s['Stat Bonuses'].split('MAX ')[1].split(', ')
                                    for stat in statSplit:
                                        maxSplit = stat.split(' +')
                                        data[maxSplit[0]] += int(maxSplit[1])
                                        charStats[maxSplit[0]] += int(maxSplit[1])
                                        data['Max Stats'][maxSplit[0]] += int(maxSplit[1]) 

                                    specialStatStr = f"Level {s['Bonus Level']} {c['Name']} stat bonus unlocked! {s['Stat Bonuses']}"


                maxStatStr = ""
                for sk in data['Max Stats'].keys():
                    if charStats[sk] > data['Max Stats'][sk]:
                        data[sk] = charStats[sk] = data['Max Stats'][sk]
                        if charFeatsGained != "":
                            maxStatStr += f"\n{character_record['Name']}'s {sk} will not increase because their maximum is {data['Max Stats'][sk]}."
                character_record["Class"] = data["Class"]
                character_record['CON'] = charStats['CON']
                charHP = await characterCog.calcHP(ctx, subclasses, character_record, int(newCharLevel))
                data['HP'] = charHP
                tierNum += int(newCharLevel in [5, 11, 17, 20])
                levelUpEmbed.title = f'{charName} has leveled up to {newCharLevel}!\nCurrent CP: {totalCP}/{cp_bound_array[tierNum-1][1]} CP'
                levelUpEmbed.description = f"{character_record['Race']} {charClass}\n**STR**: {charStats['STR']} **DEX**: {charStats['DEX']} **CON**: {charStats['CON']} **INT**: {charStats['INT']} **WIS**: {charStats['WIS']} **CHA**: {charStats['CHA']}" + f"\n{charFeatsGainedStr}{maxStatStr}\n{specialStatStr}"
                if charClassChoice != "":
                    levelUpEmbed.description += f"{charName} has multiclassed into **{charClassChoice}!**"
                levelUpEmbed.set_footer(text= levelUpEmbed.Empty)
                levelUpEmbed.clear_fields()

                def charCreateCheck(r, u):
                    sameMessage = False
                    if levelUpEmbedmsg.id == r.message.id:
                        sameMessage = True
                    return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

                if not levelUpEmbedmsg:
                   levelUpEmbedmsg = await channel.send(embed=levelUpEmbed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")
                else:
                    await levelUpEmbedmsg.edit(embed=levelUpEmbed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")

                await levelUpEmbedmsg.add_reaction('✅')
                await levelUpEmbedmsg.add_reaction('❌')
                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
                except asyncio.TimeoutError:
                    await levelUpEmbedmsg.delete()
                    await channel.send(f'Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup "character name"\n{commandPrefix}lvlup "character name"\n{commandPrefix}lvl "character name"\n{commandPrefix}lv "character name"```')
                    self.bot.get_command('levelup').reset_cooldown(ctx)
                    return
                else:
                    await levelUpEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await levelUpEmbedmsg.edit(embed=None, content=f"Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup \"character name\"\n{commandPrefix}lvlup \"character name\"\n{commandPrefix}lvl \"character name\"\n{commandPrefix}lv \"character name\"```")
                        await levelUpEmbedmsg.clear_reactions()
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return

                try:
                    playersCollection = db.players
                    playersCollection.update_one({'_id': charID}, {"$set": data})
                    
                    statsCollection = db.stats
                    statsCollection.update_one({'Life':1}, {"$inc": stats_increment}, upsert=True)
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")


                roleName = await self.levelCheck(ctx, newCharLevel, charName)
                levelUpEmbed.clear_fields()
                await levelUpEmbedmsg.edit(content=f":arrow_up:   __**L E V E L   U P!**__\n\n:warning:   **Don't forget to spend your TP!** Use one of the following commands to do so:\n```yaml\n$tp find \"{charName}\" \"magic item\"\n$tp craft \"{charName}\" \"magic item\"\n$tp meme \"{charName}\" \"magic item\"```", embed=levelUpEmbed)
                
                if roleName != "":
                    levelUpEmbed.title = f":tada: {roleName} role acquired! :tada:\n" + levelUpEmbed.title
                    await levelUpEmbedmsg.edit(embed=levelUpEmbed)
                    await levelUpEmbedmsg.add_reaction('🎉')
                    await levelUpEmbedmsg.add_reaction('🎊')
                    await levelUpEmbedmsg.add_reaction('🥳')
                    await levelUpEmbedmsg.add_reaction('🍾')
                    await levelUpEmbedmsg.add_reaction('🥂')

        self.bot.get_command('levelup').reset_cooldown(ctx)
    async def levelCheck(self, ctx, level, charName):
        author = ctx.author
        roles = [r.name for r in author.roles]
        guild = ctx.guild
        roleName = ""
        if not any([(x in roles) for x in ['Junior Friend', 'Journeyfriend', 'Elite Friend', 'True Friend', 'Ascended Friend']]) and 'D&D Friend' in roles and level > 1:
            roleName = 'Junior Friend' 
            levelRole = get(guild.roles, name = roleName)
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 2!")
        if 'Journeyfriend' not in roles and 'Junior Friend' in roles and level > 4:
            roleName = 'Journeyfriend' 
            roleRemoveStr = 'Junior Friend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 5!")
            await author.remove_roles(roleRemove)
        if 'Elite Friend' not in roles and 'Journeyfriend' in roles and level > 10:
            roleName = 'Elite Friend'
            roleRemoveStr = 'Journeyfriend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 11!")
            await author.remove_roles(roleRemove)
        if 'True Friend' not in roles and 'Elite Friend' in roles and level > 16:
            roleName = 'True Friend'
            roleRemoveStr = 'Elite Friend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 17!")
            await author.remove_roles(roleRemove)
        if 'Ascended Friend' not in roles and 'True Friend' in roles and level > 19:
            roleName = 'Ascended Friend'
            roleRemoveStr = 'True Friend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 20!")
            await author.remove_roles(roleRemove)
        return roleName
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['att'])
    async def attune(self,ctx, char, magic_item):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed ()
        charRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if charRecords:
            if 'Death' in charRecords:
                await channel.send(f"You cannot attune to items while your character is dead! Use the following command to decide their fate:\n```yaml\n$death \"{charRecords['Name']}\"```")
                return

            # Check number of items character can attune to. Artificer has exceptions.
            attuneLength = 3
            
            for multi in charRecords['Class'].split("/"):
                multi = multi.strip()
                multi_split = multi.split(" ")
                if multi_split[0] == 'Artificer':
                    class_level = charRecords["Level"]
                    if len(multi_split)>2:
                        try:
                            class_level = int(multi_split[1])
                        except Exception as e:
                            pass
                    if class_level >= 18:
                        attuneLength = 6
                    elif class_level >= 14:
                        attuneLength = 5
                    elif class_level >= 10:
                        attuneLength = 4
                        
            attuned = list([key for key, item_data in charRecords['Magic Items'].items() 
                                if "Attunement" in item_data and item_data["Attunement"])
            
            if len(attuned) >= attuneLength:
                await channel.send(f"The maximum number of magic items you can attune to is {attuneLength}! You cannot attune to any more items!")
                return


            charRecordMagicItems = list(charRecords['Magic Items'].keys())

            def apiEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:min(len(magic_item_list), 9)]) or (str(r.emoji) == '❌')) and u == author

            magic_item_list = []
            magic_item_string = ""
            numI = 0

            # Check if query is in character's Magic Item List. Limit is 8 to show if there are multiple matches.
            for key in charRecordMagicItems:
                if magic_item.lower() in key.lower():
                    if key not in attuned:
                        magic_item_list.append(key)
                        magic_item_string += f"{alphaEmojis[numI]} {key} \n"
                        numI += 1
                if numI > 8:
                    break

            # IF multiple matches, check which one the player meant.
            if (len(magic_item_list) > 1):
                charEmbed.add_field(name=f"There seems to be multiple results for **`{magic_item}`**, please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.", 
                value=magic_item_string, inline=False)
                if not charEmbedmsg:
                    charEmbedmsg = await channel.send(embed=charEmbed)
                else:
                    await charEmbedmsg.edit(embed=charEmbed)

                await charEmbedmsg.add_reaction('❌')

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
                except asyncio.TimeoutError:
                    await charEmbedmsg.delete()
                    await channel.send('Timed out! Try using the command again.')
                    ctx.command.reset_cooldown(ctx)
                    return None, charEmbed, charEmbedmsg
                else:
                    if tReaction.emoji == '❌':
                        await charEmbedmsg.edit(embed=None, content=f"Command cancelled. Try using the command again.")
                        await charEmbedmsg.clear_reactions()
                        ctx.command.reset_cooldown(ctx)
                        return None,charEmbed, charEmbedmsg
                charEmbed.clear_fields()
                await charEmbedmsg.clear_reactions()
                magic_item = magic_item_list[alphaEmojis.index(tReaction.emoji)]

            elif len(magic_item_list) == 1:
                magic_item = magic_item_list[0]
            else:
                await channel.send(f"`{magic_item}` isn't in {charRecords['Name']}'s inventory or already attuned. Please try the command again.")
                return

            magic_item_record = charRecords['Magic Items'][magic_item]
            # Check if they are already attuned to the item.
            if magic_item == 'Hammer of Thunderbolts':
                # statSplit = MAX STAT +X
                statSplit = magic_item_record['Stat Bonuses'].split(' +')
                maxSplit = statSplit[0].split(' ')

                #Increase stats from Hammer and add to max stats. 
                charRecords['Max Stats'][maxSplit[1]] += int(statSplit[1]) 

                if 'Belt of' not in charRecords['Magic Items'] and 'Gauntlets of Ogre Power' not in charRecords['Magic Items']:
                    await channel.send(f"`Hammer of Thunderbolts` requires you to have a `Belt of Giant Strength (any variety)` and `Gauntlets of Ogre Power` in your inventory in order to attune to it.")
                    return 

            if 'Attunement' in magic_item_record:
                magic_item_record['Attunement'] = True
            else:
                await channel.send(f"`{magic_item}` does not require attunement so there is no need to try to attune this item.")
                return
                        
            
            data = charRecords

            try:
                
                charID = charRecords['_id']
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await channel.send(f"You successfully attuned to **{magic_item_record['Name']}**!")

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['uatt', 'unatt'])
    async def unattune(self,ctx, char, magic_item):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed ()
        charRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if charRecords:
            if 'Death' in charRecords:
                await channel.send(f"You cannot unattune from items with a dead character. Use the following command to decide their fate:\n```yaml\n$death \"{charRecords['Name']}\"```")
                return
            
            attuned = list([key for key, item_data in charRecords['Magic Items'].items() 
                                if "Attunement" in item_data and item_data["Attunement"])
            
            charRecordMagicItems = list(charRecords['Magic Items'].keys())
            
            def apiEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:min(len(mList), 9)]) or (str(r.emoji) == '❌')) and u == author

            magic_item_list = []
            magic_item_string = ""
            numI = 0

            # Check if query is in character's Magic Item List. Limit is 8 to show if there are multiple matches.
            for key in attuned:
                if magic_item.lower() in key.lower():
                    magic_item_list.append(key)
                    magic_item_string += f"{alphaEmojis[numI]} {key} \n"
                    numI += 1
                    
                if numI > 8:
                    break

            if (len(magic_item_list) > 1):
                charEmbed.add_field(name=f"There seems to be multiple results for `{magic_item}`, please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.", 
                value=magic_item_string, inline=False)
                if not charEmbedmsg:
                    charEmbedmsg = await channel.send(embed=charEmbed)
                else:
                    await charEmbedmsg.edit(embed=charEmbed)

                await charEmbedmsg.add_reaction('❌')

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
                except asyncio.TimeoutError:
                    await charEmbedmsg.delete()
                    await channel.send('Timed out! Try using the command again.')
                    ctx.command.reset_cooldown(ctx)
                    return None, charEmbed, charEmbedmsg
                else:
                    if tReaction.emoji == '❌':
                        await charEmbedmsg.edit(embed=None, content=f"Command cancelled. Try using the command again.")
                        await charEmbedmsg.clear_reactions()
                        ctx.command.reset_cooldown(ctx)
                        return None,charEmbed, charEmbedmsg
                charEmbed.clear_fields()
                await charEmbedmsg.clear_reactions()
                magic_item = magic_item_list[alphaEmojis.index(tReaction.emoji)]

            elif len(magic_item_list) == 1:
                magic_item = magic_item_list[0]
            else:
                await channel.send(f'`{magic_item}` is not attuned.')
                return

            
            magic_item_record = charRecords['Magic Items'][magic_item]
            
            if magic_item_record['Name'] == 'Hammer of Thunderbolts':
                statSplit = magic_item_record['Stat Bonuses'].split(' +')
                maxSplit = statSplit[0].split(' ')
                if "MAX" in statSplit[0]:
                    charRecords['Max Stats'][maxSplit[1]] -= int(statSplit[1]) 
            

            try:
                magic_item_record["Attunement"] = False
                charID = charRecords['_id']
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": charRecords})
                
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await channel.send(f"You successfully unattuned from **{magic_item_record['Name']}**!")
                    

    

    async def calcHP (self, ctx, classes, charDict, lvl):
        # classes = sorted(classes, key = lambda i: i['Hit Die Max'],reverse=True) 
        totalHP = 0
        totalHP += classes[0]['Hit Die Max']
        currentLevel = 1
        charDict = charDict.copy()
        for c in classes:
            classLevel = int(c['Level'])
            while currentLevel < classLevel:
                totalHP += c['Hit Die Average']
                currentLevel += 1
            currentLevel = 0

        totalHP += ((int(charDict['CON']) - 10) // 2 ) * lvl
        
        specialCollection = db.special
        specialRecords = list(specialCollection.find())

        for s in specialRecords:
            if s['Type'] == "Race" or s['Type'] == "Feats" or s['Type'] == "Magic Items":
                
                if s['Name'] in charDict[s['Type']]:
                    if 'HP' in s:
                        if 'Half Level' in s:
                            totalHP += s['HP'] * floor(lvl/2)
                        else:
                            totalHP += s['HP'] * lvl
                            
            elif s['Type'] == "Class":
                for multi in charDict['Class'].split("/"):
                    multi = multi.strip()
                    multi_split = list(multi.split(" "))
                    class_level = lvl
                    class_name = multi_split[0]
                    if len(multi_split) > 2:
                        try:
                            class_level=int(multi_split.pop(1))
                        except Exception as e:
                            continue
                    class_name = " ".join(multi_split)
                        
                        
                    if class_name == s["Name"]:
                        
                        if 'HP' in s:
                            if 'Half Level' in s:
                                totalHP += s['HP'] * floor(class_level/2)
                            else:
                                totalHP += s['HP'] * class_level
                            
                             

        return totalHP

    async def pointBuy(self,ctx, statsArray, rRecord, charEmbed, charEmbedmsg):
        author = ctx.author
        channel = ctx.channel
        def anyCharEmbedcheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            if (r.emoji in uniqueReacts or r.emoji == '❌') and u == author:
                anyList[charEmbedmsg.id].add(r.emoji)
            return sameMessage and ((len(anyList[charEmbedmsg.id]) == anyCheck) or str(r.emoji) == '❌') and u == author

        def slashCharEmbedcheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:len(statSplit)]) or (str(r.emoji) == '❌')) and u == author

        if rRecord:
            statsBonus = rRecord['Modifiers'].replace(" ", "").split(',')
            uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
            allStatsArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
            
            for s in statsBonus:
                if '/' in s:
                    statSplit = s[:len(s)-2].replace(" ", "").split('/')
                    statSplitString = ""
                    for num in range(len(statSplit)):
                        statSplitString += f'{alphaEmojis[num]}: {statSplit[num]}\n'
                    try:
                        charEmbed.add_field(name=f"The {rRecord['Name']} race lets you choose between {s}. React [A-{alphaEmojis[len(statSplit)]}] below with the stat(s) you would like to choose.", value=statSplitString, inline=False)
                        if charEmbedmsg:
                            await charEmbedmsg.edit(embed=charEmbed)
                        else: 
                            charEmbedmsg = await channel.send(embed=charEmbed)
                        for num in range(0,len(statSplit)): await charEmbedmsg.add_reaction(alphaEmojis[num])
                        await charEmbedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=slashCharEmbedcheck, timeout=60)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                    else:
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}char {ctx.invoked_with}```")
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None
                    await charEmbedmsg.clear_reactions()
                    s = statSplit[alphaEmojis.index(tReaction.emoji)] + s[-2:]

                if 'STR' in s:
                    statsArray[0] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('STR')
                elif 'DEX' in s:
                    statsArray[1] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('DEX')
                elif 'CON' in s:
                    statsArray[2] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('CON')
                elif 'INT' in s:
                    statsArray[3] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('INT')
                elif 'WIS' in s:
                    statsArray[4] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('WIS')
                elif 'CHA' in s:
                    statsArray[5] += int(s[len(s)-1]) if s[len(s)-2] == "+" else int("-" + s[len(s)-1])
                    uniqueArray.remove('CHA')

                elif 'AOU' in s or 'ANY' in s:
                    try:
                        anyList = dict()
                        anyCheck = [int(charL) for charL in s if charL.isnumeric()][0]
                        anyAmount = int(s[len(s)-1])
                        anyList = {charEmbedmsg.id:set()}
                        uniqueStatStr = ""
                        uniqueReacts = []

                        if 'ANY' in s:
                            uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

                        for u in range(0,len(uniqueArray)):
                            uniqueStatStr += f'{alphaEmojis[u]}: {uniqueArray[u]}\n'
                            uniqueReacts.append(alphaEmojis[u])

                        charEmbed.add_field(name=f"The {rRecord['Name']} race lets you choose {anyCheck} extra stats to increase by {anyAmount}. React below with the stat(s) you would like to choose.", value=uniqueStatStr, inline=False)
                        if charEmbedmsg:
                            await charEmbedmsg.edit(embed=charEmbed)
                        else: 
                            charEmbedmsg = await channel.send(embed=charEmbed)
                        for num in range(0,len(uniqueArray)): await charEmbedmsg.add_reaction(alphaEmojis[num])
                        await charEmbedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=anyCharEmbedcheck, timeout=60)
                        
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Point buy timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None

                    else:
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f'Point buy cancelled out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None 
                        

                    charEmbed.clear_fields()
                    await charEmbedmsg.clear_reactions()
                    if 'AOU' in s:
                        for s in anyList[charEmbedmsg.id]:
                            statsArray[allStatsArray.index(uniqueArray.pop(alphaEmojis.index(tReaction.emoji)))] += anyAmount
                    else:

                        for s in anyList[charEmbedmsg.id]:
                            statsArray[(alphaEmojis.index(tReaction.emoji))] += anyAmount
            return statsArray, charEmbedmsg

    async def chooseSubclass(self, ctx, subclassesList, charClass, charEmbed, charEmbedmsg):
        author = ctx.author
        channel = ctx.channel
        def classEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

        try:
            subclassString = ""
            for num in range(len(subclassesList)):
                subclassString += f'{alphaEmojis[num]}: {subclassesList[num]}\n'

            charEmbed.clear_fields()
            charEmbed.add_field(name=f"The {charClass} class allows you to pick a subclass at this level. React to the choices below to select your subclass.", value=subclassString, inline=False)
            alphaIndex = len(subclassesList)
            if charEmbedmsg:
                await charEmbedmsg.edit(embed=charEmbed)
            else: 
                charEmbedmsg = await channel.send(embed=charEmbed)
            await charEmbedmsg.add_reaction('❌')
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=classEmbedCheck, timeout=60)
        except asyncio.TimeoutError:
            await charEmbedmsg.delete()
            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
            return None, None
        else:
            if tReaction.emoji == '❌':
                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await charEmbedmsg.clear_reactions()
                self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                return None, None
        await charEmbedmsg.clear_reactions()
        charEmbed.clear_fields()
        choiceIndex = alphaEmojis.index(tReaction.emoji)
        subclass = subclassesList[choiceIndex].strip()

        return subclass, charEmbedmsg

    async def chooseFeat(self, ctx, race, charClass, cRecord, featLevels, charEmbed,  charEmbedmsg, charStats, charFeats):
        statNames = ['STR','DEX','CON','INT','WIS','CHA']
        author = ctx.author
        channel = ctx.channel

        def featCharEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:2]) or (str(r.emoji) == '❌')) and u == author
        
        def asiCharEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:asiIndex]) or (str(r.emoji) == '❌')) and u == author


        featChoices = []
        featsPickedList = []
        featsChosen = ""
        featsCollection = db.feats
        
        spellcasting = False
        for f in featLevels:
            charEmbed.clear_fields()
            if f != 'Extra Feat':
                try:
                    charEmbed.add_field(name=f"Your level allows you to pick an Ability Score Improvement or a feat. Please react with 1 or 2 for your level {f} ASI/feat.", value=f"{alphaEmojis[0]}: Ability Score Improvement\n{alphaEmojis[1]}: Feat\n", inline=False)
                    if charEmbedmsg:
                        await charEmbedmsg.edit(embed=charEmbed)
                    else: 
                        charEmbedmsg = await channel.send(embed=charEmbed)
                    for num in range(0,2): await charEmbedmsg.add_reaction(alphaEmojis[num])
                    await charEmbedmsg.add_reaction('❌')
                    charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=featCharEmbedCheck, timeout=60)
                except asyncio.TimeoutError:
                    await charEmbedmsg.delete()
                    await channel.send(f'Feat selection timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                    self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                    return None, None, None
                else:
                    if tReaction.emoji == '❌':
                        await charEmbedmsg.edit(embed=None, content=f"Feat selection cancelled.  Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                        await charEmbedmsg.clear_reactions()
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None, None

                choice = alphaEmojis.index(tReaction.emoji)
                await charEmbedmsg.clear_reactions()

            else:
                choice = 1
            if choice == 0:
                charEmbed.clear_fields() 
                for num in range(0,2):
                    try:   
                        statsString = ""
                        asiString = ""
                        asiList = []
                        asiIndex = 0
                        for n in range(0,6):
                            if (int(charStats[statNames[n]]) + 1 <= charStats['Max Stats'][statNames[n]]):
                                statsString += f"{statNames[n]}: **{charStats[statNames[n]]}** "
                                asiString += f"{alphaEmojis[asiIndex]}: {statNames[n]}\n"
                                asiList.append(statNames[n])
                                asiIndex += 1
                            else:
                                statsString += f"{statNames[n]}: **{charStats[statNames[n]]}** (MAX) "

                        charEmbed.add_field(name=f"{statsString}\nReact to choose a stat for your ASI:", value=asiString, inline=False)
                        await charEmbedmsg.edit(embed=charEmbed)
                        for num in range(0,len(asiList)): 
                            await charEmbedmsg.add_reaction(alphaEmojis[num])
                        await charEmbedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=asiCharEmbedCheck, timeout=60)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None, None
                    else:
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None, None
                    asi = alphaEmojis.index(tReaction.emoji)

                    charStats[asiList[asi]] = int(charStats[asiList[asi]]) + 1
                    if ctx.invoked_with == "levelup":
                         charEmbed.description = f"{race}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"
                    charEmbed.clear_fields()
                    charEmbed.add_field(name=f"ASI First Stat", value=f"{alphaEmojis[asi]}: {asiList[asi]}", inline=False)
                    
                    await charEmbedmsg.clear_reactions()
            elif choice == 1:
                if featChoices == list():
                    fRecords, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'feats')
                    for feat in fRecords:
                        featList = []
                        meetsRestriction = False

                        if 'Feat Restriction' not in feat and 'Race Restriction' not in feat and 'Class Restriction' not in feat and 'Stat Restriction' not in feat and (feat['Name'] not in charFeats) and 'Race Unavailable' not in feat and 'Require Spellcasting' not in feat:
                            featChoices.append(feat)

                        else:
                            if 'Feat Restriction' in feat and feat["Name"] not in charFeats:
                                featsList = [x.strip() for x in feat['Feat Restriction'].split(', ')]

                                for f in featsList:
                                    if f in charFeats or f in featsChosen:
                                        meetsRestriction = True
                                        
                            if 'Race Restriction' in feat:
                                featsList = [x.strip() for x in feat['Race Restriction'].split(', ')]

                                for f in featsList:
                                    if f in race:
                                        meetsRestriction = True

                            if 'Race Unavailable' in feat:
                                if race not in feat['Race Unavailable']:
                                    meetsRestriction = True
                            if 'Class Restriction' in feat:
                                featsList = [x.strip() for x in feat['Class Restriction'].split(', ')]
                                for c in cRecord:
                                    if ctx.invoked_with.lower() == "create" or ctx.invoked_with.lower() == "respec":
                                        if c['Class']['Name'] in featsList or c['Subclass'] in featsList:
                                            meetsRestriction = True
                                    else:
                                        if c['Name'] in featsList or c['Subclass'] in featsList:
                                            meetsRestriction = True
                                            
                            if 'Stat Restriction' in feat:
                                s = feat['Stat Restriction']
                                statNumber = int(s[-2:])
                                if '/' in s:
                                    checkStat = s[:len(s)-2].replace(" ", "").split('/')
                                    statSplitString = ""
                                else:
                                    checkStat = [s[:len(s)-2].strip()]

                                for stat in checkStat:
                                    if int(charStats[stat]) >= statNumber:
                                        meetsRestriction = True


                            if "Require Spellcasting" in feat:
                                for c in cRecord:
                                    if "Class" in c:
                                        if "Spellcasting" in c["Class"]:
                                            if c["Class"]["Spellcasting"] == True or c["Class"]["Spellcasting"] in charClass:
                                                meetsRestriction = True
                                    else:
                                        if "Spellcasting" in c:
                                            if c["Spellcasting"] == True or c["Spellcasting"] in charClass:
                                                meetsRestriction = True
                                
                                
                                spellcastingFeats = list(featsCollection.find({"Spellcasting": True}))
                                for f in spellcastingFeats:
                                    if f["Name"] in charFeats:
                                         meetsRestriction = True

                            if meetsRestriction:
                                featChoices.append(feat)


                else:
                    # Whenever a feat that grants spellcasting gets picked.
                    if spellcasting == True:
                        spellcastingFeats = list(featsCollection.find({"Require Spellcasting": True}))
                        for f in spellcastingFeats:
                            featChoices.append(f)

                    featRestrictRecords = list(featsCollection.find({"Feat Restriction": {"$regex": featPicked["Name"], "$options": 'i' }}))
                    for f in featRestrictRecords:
                        if f not in featChoices:
                            featChoices.append(f)
                    featChoices.remove(featPicked)

                def featChoiceCheck(r, u):
                    sameMessage = False
                    if charEmbedmsg.id == r.message.id:
                        sameMessage = True
                    return sameMessage and u == author and (r.emoji == left or r.emoji == right or r.emoji == '❌' or r.emoji == back or r.emoji in alphaEmojis[:alphaIndex])

                page = 0
                perPage = 24
                numPages =((len(featChoices) - 1) // perPage) + 1
                featChoices = sorted(featChoices, key = lambda i: i['Name']) 

                while True:
                    charEmbed.clear_fields()  
                    if f == 'Extra Feat':
                        charEmbed.add_field(name=f"Your race allows you to choose a feat. Please choose your feat from the list below.", value=f"-", inline=False)
                    else:
                        charEmbed.add_field(name=f"Please choose your feat from the list below:", value=f"━━━━━━━━━━━━━━━━━━━━", inline=False)

                    pageStart = perPage*page
                    pageEnd = perPage * (page + 1)
                    alphaIndex = 0
                    for i in range(pageStart, pageEnd if pageEnd < (len(featChoices) - 1) else (len(featChoices)) ):
                        charEmbed.add_field(name=alphaEmojis[alphaIndex], value=featChoices[i]['Name'], inline=True)
                        alphaIndex+=1
                    charEmbed.set_footer(text= f"Page {page+1} of {numPages} -- use {left} or {right} to navigate or ❌ to cancel.")
                    await charEmbedmsg.edit(embed=charEmbed) 
                    await charEmbedmsg.add_reaction(left) 
                    await charEmbedmsg.add_reaction(right)
                    # await charEmbedmsg.add_reaction(back)
                    await charEmbedmsg.add_reaction('❌')

                    try:
                        react, user = await self.bot.wait_for("reaction_add", check=featChoiceCheck, timeout=90.0)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f"Character creation timed out!")
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None, None
                    else:
                        if react.emoji == left:
                            page -= 1
                            if page < 0:
                              page = numPages - 1
                        elif react.emoji == right:
                            page += 1
                            if page > numPages - 1: 
                              page = 0
                        elif react.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None, None
                        # elif react.emoji == back:
                        #     await charEmbedmsg.delete()
                        #     await ctx.reinvoke()
                        elif react.emoji in alphaEmojis:
                            await charEmbedmsg.clear_reactions()
                            break
                        charEmbed.clear_fields()
                        await charEmbedmsg.clear_reactions()
                
                featPicked = featChoices[(page * perPage) + alphaEmojis.index(react.emoji)]

                # If feat picked grants spellcasting
                if "Spellcasting" in featPicked:
                    spellcasting = True

                featsPickedList.append(featPicked)

                # Special Case of Picked Ritual Caster
                def ritualFeatEmbedcheck(r, u):
                    sameMessage = False
                    if charEmbedmsg.id == r.message.id:
                        sameMessage = True
                    return sameMessage and ((r.emoji in alphaEmojis[:6]) or (str(r.emoji) == '❌')) and u == author

                def ritualSpellEmbedCheck(r, u):
                    sameMessage = False
                    if charEmbedmsg.id == r.message.id:
                        sameMessage = True

                    if (r.emoji in alphaEmojis[:alphaIndex]) and u == author:
                        ritualChoiceList[charEmbedmsg.id].add(r.emoji)

                    return sameMessage and ((len(ritualChoiceList[charEmbedmsg.id]) == 2) or (str(r.emoji) == '❌')) and u == author

                if featPicked['Name'] == "Ritual Caster":
                    ritualClasses = ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]
                    charEmbed.clear_fields()
                    charEmbed.set_footer(text=charEmbed.Empty)
                    charEmbed.add_field(name="For the **Ritual Caster** feat, please pick the spellcasting class.", value=f"{alphaEmojis[0]}: Bard\n{alphaEmojis[1]}: Cleric\n{alphaEmojis[2]}: Druid\n{alphaEmojis[3]}: Sorcerer\n{alphaEmojis[4]}: Warlock\n{alphaEmojis[5]}: Wizard\n", inline=False)

                    try:
                        await charEmbedmsg.edit(embed=charEmbed)
                        await charEmbedmsg.add_reaction('❌')
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=ritualFeatEmbedcheck, timeout=60)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None, None
                    else:
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None, None
                    await charEmbedmsg.clear_reactions()

                    ritualClass = ritualClasses[alphaEmojis.index(tReaction.emoji)]
                    featPicked['Name'] = f"{featPicked['Name']} ({ritualClass})"
                    spellsCollection = db.spells
                    ritualSpellsList = list(spellsCollection.find({"$and": [{"Classes": {"$regex": ritualClass, '$options': 'i' }}, {"Ritual": True}, {"Level": 1}] }))

                    alphaIndex = 0
                    ritualSpellsString = ""
                    for r in ritualSpellsList:
                        ritualSpellsString += f"{alphaEmojis[alphaIndex]}: {r['Name']}\n"
                        alphaIndex += 1

                    charEmbed.set_field_at(0, name=f"For the **Ritual Caster** feat, please pick the spellcasting class.", value=f"{tReaction.emoji}: {ritualClass}", inline=False)
                    charEmbed.add_field(name=f"Please pick two {ritualClass} spells from this list to add to your ritual book.", value=ritualSpellsString, inline=False)
                    ritualChoiceList = {charEmbedmsg.id:set()}

                    charStats['Ritual Book'] = []
                    if len(ritualSpellsList) > 2:
                        try:
                            await charEmbedmsg.edit(embed=charEmbed)
                            await charEmbedmsg.add_reaction('❌')
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=ritualSpellEmbedCheck, timeout=60)
                        except asyncio.TimeoutError:
                            await charEmbedmsg.delete()
                            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None, None
                        else:
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                                return None, None, None
                        await charEmbedmsg.clear_reactions()
                        for r in ritualChoiceList[charEmbedmsg.id]:
                            rChoice = ritualSpellsList[alphaEmojis.index(r)]
                            charStats['Ritual Book'].append({'Name':rChoice['Name'], 'School':rChoice['School']})
                    else:
                        charStats['Ritual Book'].append({'Name':ritualSpellsList[0]['Name'], 'School':ritualSpellsList[0]['School']})
                        charStats['Ritual Book'].append({'Name':ritualSpellsList[1]['Name'], 'School':ritualSpellsList[1]['School']})
                    

                def slashFeatEmbedcheck(r, u):
                    sameMessage = False
                    if charEmbedmsg.id == r.message.id:
                        sameMessage = True
                    return sameMessage and ((r.emoji in alphaEmojis[:len(featBonusList)]) or (str(r.emoji) == '❌')) and u == author

                if 'Stat Bonuses' in featPicked:
                    featBonus = featPicked['Stat Bonuses']
                    if '/' in featBonus or 'ANY' in featBonus:
                        if '/' in featBonus:
                            featBonusList = featBonus[:len(featBonus) - 3].split('/')
                        elif 'ANY' in featBonus:
                            featBonusList = statNames
                        featBonusString = ""
                        for num in range(len(featBonusList)):
                            featBonusString += f'{alphaEmojis[num]}: {featBonusList[num]}\n'

                        try:
                            charEmbed.clear_fields()    
                            charEmbed.set_footer(text= charEmbed.Empty)
                            charEmbed.add_field(name=f"The {featPicked['Name']} feat lets you choose between {featBonus}. React with [1-{len(featBonusList)}] below with the stat(s) you would like to choose.", value=featBonusString, inline=False)
                            await charEmbedmsg.edit(embed=charEmbed)
                            for num in range(0,len(featBonusList)): await charEmbedmsg.add_reaction(alphaEmojis[num])
                            await charEmbedmsg.add_reaction('❌')
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=slashFeatEmbedcheck, timeout=60)
                        except asyncio.TimeoutError:
                            await charEmbedmsg.delete()
                            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                            return None, None, None
                        else:
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                                return None, None, None
                        await charEmbedmsg.clear_reactions()
                        charStats[featBonusList[alphaEmojis.index(tReaction.emoji)]] = int(charStats[featBonusList[alphaEmojis.index(tReaction.emoji)]]) + int(featBonus[-1:])
                            
                    else:
                        featBonusList = featBonus.split(', ')
                        for fb in featBonusList:
                            charStats[fb[:3]] =  int(charStats[fb[:3]]) + int(fb[-1:])

                if featsPickedList != list():
                    featsChosen = ', '.join(str(string['Name']) for string in featsPickedList)            

        if ctx.invoked_with == "levelup":
              charEmbed.description = f"{race}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"

        return featsChosen, charStats, charEmbedmsg        
    

    async def class_select_kernel(self, ctx, msg, lvl, charDict, classRecord, charEmbed, charEmbedmsg):
        channel= ctx. channel
        
        classStat = []
        classRecord = []
        totalLevel = 0
        multiLevel = 0
        broke = []
        # If there's a /, character is creating a multiclass character
        if '/' in character_class:
            multiclassList = character_class.replace(' ', '').split('/')
            # Iterates through the multiclass list 
            
            for multiclass_text in multiclassList:
                # Separate level and class
                multiLevel = re.search('\d+', multiclass_text)
                if not multiLevel:
                    msg += ":warning: You are missing the level for your multiclass class. Please check your format.\n"

                    break
                multiLevel = multiLevel.group()
                multiClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'classes',multiclass_text[:len(multiclass_text) - len(multiLevel)])
                if not multiClass:
                    classRecord = None
                    broke.append(multiclass_text[:len(multiclass_text) - len(multiLevel)])
                
                # Check for class duplicates (ex. Paladin 1 / Paladin 2 = Paladin 3)
                classDupe = False
                if(classRecord or classRecord==list()):
                    for class_data in classRecord:
                        if class_data['Class'] == multiClass:
                            class_data['Level'] = str(int(class_data['Level']) + int(multiLevel))
                            classDupe = True                    
                            break

                    if not classDupe:
                        classRecord.append({'Class': multiClass, 'Level':multiLevel})
                    totalLevel += int(multiLevel)

        else:
            singleClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'classes',character_class)
            if singleClass:
                classRecord.append({'Class':singleClass, 'Level':lvl, 'Subclass': 'None'})
            else:
                classRecord = None
                broke.append(character_class)

        charDict['Class'] = ""
        if not multiLevel and '/' in character_class:
            pass
        elif len(broke)>0:
            msg += f':warning: **{broke}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        elif totalLevel != lvl and len(classRecord) > 1:
            msg += ':warning: Your classes do not add up to the total level. Please double-check your multiclasses.\n'
        else:
            # Subclass
            for class_data in classRecord:
                class_data['Subclass'] = 'None'
                if int(m['Level']) < lvl:
                    className = f'{class_data["Class"]["Name"]} {class_data["Level"]}'
                else:
                    className = f'{class_data["Class"]["Name"]}'

                classStatName = f'{class_data["Class"]["Name"]}'

                if int(class_data['Class']['Subclass Level']) <= int(class_data['Level']) and msg == "":
                    subclassesList = class_data['Class']['Subclasses'].split(',')
                    subclass, charEmbedmsg = await characterCog.chooseSubclass(ctx, subclassesList, m['Class']['Name'], charEmbed, charEmbedmsg)
                    if not subclass:
                        return msg, subclasses, classStat, charEmbed, charEmbedmsg

                    class_data['Subclass'] = f'{className} ({subclass})' 
                    classStat.append(f'{classStatName}-{subclass}')


                    if charDict['Class'] == "": 
                        charDict['Class'] = f'{className} ({subclass})'
                    else:
                        charDict['Class'] += f' / {className} ({subclass})'
                else:
                    classStat.append(classStatName)
                    if charDict['Class'] == "": 
                        charDict['Class'] = className
                    else:
                        charDict['Class'] += f' / {className}'
                        
        charClass = charDict["Class"]
        subclasses = []
        if '/' in charClass:
            tempClassList = charClass.split(' / ')
            for t in tempClassList:
                temp = t.split(' ')
                tempSub = ""
                if '(' and ')' in t:
                    tempSub = t[t.find("(")+1:t.find(")")]

                subclasses.append({'Name':temp[0], 'Subclass':tempSub, 'Level':int(temp[1])})
        else:
            tempSub = ""
            if '(' and ')' in charClass:
                tempSub = charClass[charClass.find("(")+1:charClass.find(")")]
            subclasses.append({'Name':charClass, 'Subclass':tempSub, 'Level':lvl})
        #Special stat bonuses (Barbarian cap / giant soul sorc)
        specialCollection = db.special
        specialRecords = list(specialCollection.find())
        for special in specialRecords:
            if 'Bonus Level' in special:
                for subclass in subclasses:
                    if special['Bonus Level'] <= subclass['Level'] and special['Name'] in f"{subclass['Name']} ({subclass['Subclass']})":
                        if 'MAX' in special['Stat Bonuses']:
                            statSplit = special['Stat Bonuses'].split('MAX ')[1].split(', ')
                            for stat in statSplit:
                                maxSplit = stat.split(' +')
                                charDict[maxSplit[0]] += int(maxSplit[1])
                                charDict['Max Stats'][maxSplit[0]] += int(maxSplit[1]) 
        return msg, subclasses, classStat, charEmbed, charEmbedmsg
        
        
    async def class_item_select_kernel(self, ctx, msg, charDict, classRecord, charEmbed, charEmbedmsg):
        channel= ctx. channel
        # starting equipment
        def alphaEmbedCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

        if 'Starting Equipment' in classRecord[0]['Class'] and msg == "":
            startEquipmentLength = 0
            if not charEmbedmsg:
                charEmbedmsg = await channel.send(embed=charEmbed)
            else:
                await charEmbedmsg.edit(embed=charEmbed)

            for item in classRecord[0]['Class']['Starting Equipment']:
                seTotalString = ""
                alphaIndex = 0
                for seList in item:
                    seString = []
                    for elk, elv in seList.items():
                        if 'Pack' in elk:
                            seString.append(f"{elk} x1")
                        else:
                            seString.append(f"{elk} x{elv}")
                            
                    seTotalString += f"{alphaEmojis[alphaIndex]}: {', '.join(seString)}\n"
                    alphaIndex += 1

                await charEmbedmsg.clear_reactions()
                charEmbed.add_field(name=f"Starting Equipment: {startEquipmentLength+ 1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=seTotalString, inline=False)
                await charEmbedmsg.edit(embed=charEmbed)
                if len(item) > 1:
                    for num in range(0,alphaIndex): await charEmbedmsg.add_reaction(alphaEmojis[num])
                    await charEmbedmsg.add_reaction('❌')
                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                    except asyncio.TimeoutError:
                        await charEmbedmsg.delete()
                        await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                        return False
                    else:
                        if tReaction.emoji == '❌':
                            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                            await charEmbedmsg.clear_reactions()
                            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                            return False
                    startEquipmentItem = item[alphaEmojis.index(tReaction.emoji)]
                else:
                    startEquipmentItem = item[0]

                await charEmbedmsg.clear_reactions()

                seiString = ""
                for seik, seiv in startEquipmentItem.items():
                    seiString += f"{seik} x{seiv}\n"
                    if "Pack" in seik:
                        seiString = f"{seik}:\n"
                        for pk, pv in seiv.items():
                            charDict['Inventory'][pk]= {"Amount" : pv}
                            seiString += f"+ {pk} x{pv}\n"

                charEmbed.set_field_at(startEquipmentLength, 
                                        name=f"Starting Equipment: {startEquipmentLength + 1} of {len(cRecord[0]['Class']['Starting Equipment'])}", 
                                        value=seiString, inline=False)
                
                for k,v in startEquipmentItem.items():
                    if '[' in k and ']' in k:
                        iType = k.split('[')
                        invCollection = db.shop
                        if 'Instrument' in iType[1]:
                            charInv = list(invCollection.find({"Type": {'$all': [re.compile(f".*{iType[1].replace(']','')}.*")]}}))
                        else:
                            charInv = list(invCollection.find({"Type": {'$all': [re.compile(f".*{iType[0]}.*"),re.compile(f".*{iType[1].replace(']','')}.*")]}}))

                        charInv = sorted(charInv, key = lambda i: i['Name']) 

                        typeEquipmentList = []
                        for i in range (0,int(v)):
                            charInvString = f"Please choose from the choices below for {iType[0]} {i+1}:\n"
                            alphaIndex = 0
                            charInv = list(filter(lambda c: ('Yklwa' not in c['Name'] and 
                                                            'Light Repeating Crossbow' not in c['Name'] and 
                                                            'Double-Bladed Scimitar' not in c['Name'] and 
                                                            'Oversized Longbow' not in c['Name']), charInv))
                            for c in charInv:
                                charInvString += f"{alphaEmojis[alphaIndex]}: {c['Name']}\n"
                                alphaIndex += 1

                            charEmbed.set_field_at(startEquipmentLength, 
                                                    name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", 
                                                    value=charInvString, inline=False)
                            await charEmbedmsg.clear_reactions()
                            await charEmbedmsg.add_reaction('❌')
                            await charEmbedmsg.edit(embed=charEmbed)

                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                            except asyncio.TimeoutError:
                                await charEmbedmsg.delete()
                                await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                                self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                                return False
                            else:
                                if tReaction.emoji == '❌':
                                    await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                    await charEmbedmsg.clear_reactions()
                                    self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                                    return False
                            
                            typeEquipmentList.append(charInv[alphaEmojis.index(tReaction.emoji)]['Name'])
                        typeCount = collections.Counter(typeEquipmentList)
                        typeString = ""
                        for tk, tv in typeCount.items():
                            typeString += f"{tk} x{tv}\n"
                            if tk in charDict['Inventory']:
                                charDict['Inventory'][tk]["Amount"] += tv
                            else:
                                charDict['Inventory'][tk] = {"Amount" : tv}

                        charEmbed.set_field_at(startEquipmentLength, 
                                                name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", 
                                                value=seiString.replace(f"{k} x{v}\n", typeString), inline=False)

                    elif 'Pack' not in k:
                        
                        if k in charDict['Inventory']:
                            charDict['Inventory'][k]["Amount"] += v
                        else:
                            charDict['Inventory'][k] = {"Amount" : v}
                            {"Amount" : 1}
                startEquipmentLength += 1
            await charEmbedmsg.clear_reactions()
            charEmbed.clear_fields()
        return True
    async def background_item_select_kernel(self, ctx, msg, charDict, background, charEmbed, charEmbedmsg):  
        def backgroundTopItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndexTop]) or (str(r.emoji) == '❌')) and u == author and sameMessage

        def backgroundItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author and sameMessage

        backgroundRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'backgrounds',background)

        if charEmbedmsg == "Fail":
            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
            return False
        if not backgroundRecord:
            msg += f':warning: **{background}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        else:
            charDict['Background'] = backgroundRecord['Name']

            # Background items: goes through each background and give extra items for inventory.
            
            for equipment in backgroundRecord['Equipment']:
                beTopChoiceList = []
                beTopChoiceKeys = []
                alphaIndexTop = 0
                beTopChoiceString = ""
                for equipment_key, equipment_value in equipment.items():
                    if type(equipment_value) == dict:
                        beTopChoiceKeys.append(equipment_key)
                        beTopChoiceList.append(equipment_value)
                        beTopChoiceString += f"{alphaEmojis[alphaIndexTop]}: {equipment_key}\n"
                        alphaIndexTop += 1
                    else:
                        if equipment_key not in charDict['Inventory']:
                            charDict['Inventory'][equipment_key] = {"Amount" : int(equipment_value)}
                        else:
                            charDict['Inventory'][equipment_key]["Amount"] += int(equipment_value)

                if len(beTopChoiceList) > 0:
                    # Lets user pick between top choices (ex. Game set or Musical Instrument. Then a followup choice.)
                    if len(beTopChoiceList) > 1:
                        charEmbed.add_field(name=f"Your {backgroundRecord['Name']} background lets you choose one type.", value=beTopChoiceString, inline=False)
                        if not charEmbedmsg:
                            charEmbedmsg = await channel.send(embed=charEmbed)
                        else:
                            await charEmbedmsg.edit(embed=charEmbed)

                        await charEmbedmsg.add_reaction('❌')
                        try:
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=backgroundTopItemCheck , timeout=60)
                        except asyncio.TimeoutError:
                            await charEmbedmsg.delete()
                            await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                            return False
                        else:
                            await charEmbedmsg.clear_reactions()
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                                return False

                        beTopValues = beTopChoiceList[alphaEmojis.index(tReaction.emoji)]
                        beTopKey = beTopChoiceKeys[alphaEmojis.index(tReaction.emoji)]
                    elif len(beTopChoiceList) == 1:
                        beTopValues = beTopChoiceList[0]
                        beTopKey = beTopChoiceKeys[0]

                    beChoiceString = ""
                    alphaIndex = 0
                    beList = []

                    if 'Pack' in beTopKey:
                      for c in beTopValues:
                          if c not in charDict['Inventory']:
                              charDict['Inventory'][c] = {"Amount" : 1}
                          else:
                              charDict['Inventory'][c]["Amount"] += 1
                    else:
                        for c in beTopValues:
                            beChoiceString += f"{alphaEmojis[alphaIndex]}: {c}\n"
                            beList.append(c)
                            alphaIndex += 1

                        charEmbed.add_field(name=f"Your {backgroundRecord['Name']} background lets you choose one {beTopKey}.", value=beChoiceString, inline=False)
                        if not charEmbedmsg:
                            charEmbedmsg = await channel.send(embed=charEmbed)
                        else:
                            await charEmbedmsg.edit(embed=charEmbed)

                        await charEmbedmsg.add_reaction('❌')
                        try:
                            tReaction, tUser = await self.bot.wait_for("reaction_add", check=backgroundItemCheck , timeout=60)
                        except asyncio.TimeoutError:
                            await charEmbedmsg.delete()
                            await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                            return False
                        else:
                            await charEmbedmsg.clear_reactions()
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                                return False
                            beKey = beList[alphaEmojis.index(tReaction.emoji)]
                            if beKey not in charDict['Inventory']:
                                charDict['Inventory'][beKey] = {"Amount" : 1}
                            else:
                                charDict['Inventory'][beKey]["Amount"] += 1

                    charEmbed.clear_fields()
            
            charDict['GP'] = int(backgroundRecord['GP']) + totalGP
            return True
                
    async def asi_select_kernel(self, ctx, msg, charDict, character_class, classRecord, raceRecord, charEmbed, charEmbedmsg):
        featLevels = []
        featChoices = []
        featsChosen = []
        if "Feat" in rRecord:
            featLevels.append('Extra Feat')

        for c in cRecord:
            if int(c['Level']) > 3:
                featLevels.append(4)
            if 'Fighter' in c['Class']['Name'] and int(c['Level']) > 5:
                featLevels.append(6)
            if int(c['Level']) > 7:
                featLevels.append(8)
            if 'Rogue' in c['Class']['Name'] and int(c['Level']) > 9:
                featLevels.append(10)
            if int(c['Level']) > 11:
                featLevels.append(12)
            if 'Fighter' in c['Class']['Name'] and int(c['Level']) > 13:
                featLevels.append(14)
            if int(c['Level']) > 15:
                featLevels.append(16)
            if int(c['Level']) > 18:
                featLevels.append(19)
        featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, raceRecord['Name'], charDict['Class'], cRecord, featLevels, charEmbed, charEmbedmsg, charDict, "")

        if not featsChosen and not statsFeats and not charEmbedmsg:
            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
            return msg, None, None

        if featsChosen:
            charDict['Feats'] = featsChosen 
        else: 
            charDict['Feats'] = "" 
        

        #HP
        hpRecords = []
        for class_data in classRecord:
            # Wizards get 2 free spells per wizard level
            if class_data['Class']['Name'] == "Wizard":
                charDict['Free Spells'] = [6,0,0,0,0,0,0,0,0]
                fsIndex = 0
                for i in range (2, int(class_data['Level']) + 1 ):
                    if i % 2 != 0:
                        fsIndex += 1
                    charDict['Free Spells'][min(fsIndex, 8)] += 2

            hpRecords.append({'Level':class_data['Level'], 
                                'Subclass': class_data['Subclass'], 
                                'Name': class_data['Class']['Name'], 
                                'Hit Die Max': class_data['Class']['Hit Die Max'], 
                                'Hit Die Average':class_data['Class']['Hit Die Average']})

        # Multiclass Requirements
        if '/' in character_class and len(classRecord) > 1:
            for class_data in classRecord:
                reqFufillList = []
                statReq = class_data['Class']['Multiclass'].split(' ')
                if class_data['Class']['Multiclass'] != 'None':
                    if '/' not in class_data['Class']['Multiclass'] and '+' not in class_data['Class']['Multiclass']:
                        if int(charDict[statReq[0]]) < int(statReq[1]):
                            msg += f":warning: In order to multiclass to or from **{class_data['Class']['Name']}** you need at least **{class_data['Class']['Multiclass']}**. Your character only has **{statReq[0]} {charDict[statReq[0]]}**!\n"

                    elif '/' in class_data['Class']['Multiclass']:
                        statReq[0] = statReq[0].split('/')
                        reqFufill = False
                        for s in statReq[0]:
                            if int(charDict[s]) >= int(statReq[1]):
                              reqFufill = True
                            else:
                              reqFufillList.append(f"{s} {charDict[s]}")
                        if not reqFufill:
                            msg += f":warning: In order to multiclass to or from **{class_data['Class']['Name']}** you need at least **{class_data['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**!\n"

                    elif '+' in class_data['Class']['Multiclass']:
                        statReq[0] = statReq[0].split('+')
                        reqFufill = True
                        for s in statReq[0]:
                            if int(charDict[s]) < int(statReq[1]):
                              reqFufill = False
                              reqFufillList.append(f"{s} {charDict[s]}")
                        if not reqFufill:
                            msg += f":warning: In order to multiclass to or from **{class_data['Class']['Name']}** you need at least **{class_data['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**!\n"
    
        if msg:
            if charEmbedmsg and charEmbedmsg != "Fail":
                await charEmbedmsg.delete()
            elif charEmbedmsg == "Fail":
                msg = ":warning: You have either cancelled the command or a value was not found."
            await ctx.channel.send(f'There were error(s) when creating your character:\n{msg}')

            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
        return msg, hpRecords, featsChosen

    def point_buy_check(self, ctx, statsStr, statDex, statsCon, statsInt, statsWis, statsCha)
        statsArray = [int(statsStr), int(statDex), int(statsCon), 
                      int(statsInt), int(statsWis), int(statsCha)]
        
        totalPoints = 0
        for s in statsArray:
            if (13-s) < 0:
                totalPoints += ((s - 13) * 2) + 5
            else:
                totalPoints += (s - 8)
                
        if any([s < 8 for s in statsArray]):
            msg += f":warning: You have at least one stat below the minimum of 8.\n"
        if totalPoints != 27:
            msg += f":warning: Your stats do not add up to 27 using point buy ({totalPoints}/27). Remember that you must list your stats before applying racial modifiers! Please check your point allocation using this calculator: <https://chicken-dinner.com/5e/5e-point-buy.html>\n"
        return msg
        
    async def creation_confirm_kernel(self, ctx, error_msg, charDict, tierNum, charEmbed, charEmbedmsg)
       
        charEmbed.clear_fields()    
        charEmbed.title = f"{charDict['Name']} (Lv {charDict['Level']}): {charDict['CP']}/{cp_bound_array[tierNum-1][1]} CP"
        charEmbed.description = f"**Race**: {charDict['Race']}\n**Class**: {charDict['Class']}\n**Background**: {charDict['Background']}\n**Max HP**: {charDict['HP']}\n**GP**: {charDict['GP']} " + (campaignTransferSuccess * ("\n**Transfered from:** " + campaignKey))

        
        for key, amount in bankTP.items():
            if  amount > 0:
                charDict[key] = amount
                charEmbed.add_field(name=f':warning: Unused {key}:', value=amount, inline=True)
        
        if charDict['Magic Items']:
            charEmbed.add_field(name='Magic Items', value=", ".join(charDict['Magic Items'].keys()), inline=False)
        if charDict['Consumables']:
            charEmbed.add_field(name='Consumables', value=", ".join([item["Name"] for item in charDict['Consumables']]), inline=False)
        charEmbed.add_field(name='Feats', value=charDict['Feats'], inline=True)
        charEmbed.add_field(name='Stats', value=f"**STR**: {charDict['STR']} **DEX**: {charDict['DEX']} **CON**: {charDict['CON']} **INT**: {charDict['INT']} **WIS**: {charDict['WIS']} **CHA**: {charDict['CHA']}", inline=False)

        if 'Wizard' in charDict['Class']:
            charEmbed.add_field(name='Spellbook (Wizard)', value=f"At 1st level, you have a spellbook containing six 1st-level Wizard spells of your choice (+2 free spells for each wizard level). Please use the `{commandPrefix}shop copy` command." , inline=False)

            fsString = ""
            fsIndex = 0
            for el in charDict['Free Spells']:
                if el > 0:
                    fsString += f"Level {fsIndex+1}: {el} free spells\n"
                fsIndex += 1

            if fsString:
                charEmbed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)

        
        charDictInvString = ""
        if charDict['Inventory']:
            for k,v in charDict['Inventory'].items():
                charDictInvString += f"• {k} x{v['Amount']}\n"
            charEmbed.add_field(name='Starting Equipment', value=charDictInvString, inline=False)


        def charCreateCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        user_msg = f"**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish {ctx.invoked_with.lower()}ing your character.\n❌ to cancel."
        if not charEmbedmsg:
            charEmbedmsg = await channel.send(embed=charEmbed, content=user_msg)
        else:
            await charEmbedmsg.edit(embed=charEmbed, content=user_msg)

        await charEmbedmsg.add_reaction('✅')
        await charEmbedmsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
        except asyncio.TimeoutError:
            await charEmbedmsg.delete()
            await channel.send(error_msg)
            self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
            return False
        else:
            await charEmbedmsg.clear_reactions()
            if tReaction.emoji == '❌':
                await charEmbedmsg.edit(embed=None, content=error_msg)
                await charEmbedmsg.clear_reactions()
                self.bot.get_command(ctx.invoked_with.lower()).reset_cooldown(ctx)
                return False
        return True
def setup(bot):
    bot.add_cog(Character(bot))
