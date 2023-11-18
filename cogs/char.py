import discord
import decimal
import pytz
import re
import random
import requests
import asyncio
import io
import collections
from discord.utils import get        
from math import floor
from datetime import datetime, timezone, timedelta 
from discord.ext import commands
from urllib.parse import urlparse 
from bfunc import alphaEmojis, commandPrefix, left,right,back, db, traceBack, cp_bound_array, settingsRecord
from cogs.util import calculateTreasure, callAPI, checkForChar, paginate, disambiguate, timeConversion, uwuize, confirm
                
class Character(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        
    def is_log_channel():
        async def predicate(ctx):
            if ctx.channel.type == discord.ChannelType.private:
                return False
            return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
        return commands.check(predicate)
   
    def is_log_channel_or_game():
        async def predicate(ctx):
            if ctx.channel.type == discord.ChannelType.private:
                return False
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Game Rooms"])
        return commands.check(predicate) 
        
    def stats_special():
        async def predicate(ctx):
            if ctx.channel.type == discord.ChannelType.private:
                return False
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
            elif error.param.name == "cclass":
                msg = ":warning: You're missing a class for the character you want to create.\n"
            elif error.param.name == 'bg':
                msg = ":warning: You're missing a background for the character you want to create.\n"
            elif error.param.name == 'sStr' or  error.param.name == 'sDex' or error.param.name == 'sCon' or error.param.name == 'sInt' or error.param.name == 'sWis' or error.param.name == 'sCha':
                msg = ":warning: You're missing a stat (STR, DEX, CON, INT, WIS, or CHA) for the character you want to create.\n"
            elif error.param.name == 'url':
                msg = ":warning: You're missing a URL to add an image to your character's information window.\n"
            elif error.param.name == 'm':
                msg = ":warning: You're missing a magic item to attune to, or unattune from, your character.\n"
            elif error.param.name == 'timeTransfer':
                msg = ":warning: You're missing a time amount\n"
            else:
                msg = ":warning: You're missing a required argument"

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
            def group_sort(x):
                if "Grouped" in x:
                    return x["Grouped"]
                return x["Name"]
            items.sort(key = group_sort)
            character = ""
            out_strings = []
            collector_string = ""
            for race in items:
                if "Grouped" in race:
                    race = race["Grouped"]
                else:
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
    async def create(self,ctx, name, level: int, race, cclass, bg, sStr : int, sDex :int, sCon:int, sInt:int, sWis:int, sCha :int, consumes="", timeTransfer = None):
        name = name.strip()
        
        channel = ctx.channel
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

        if not cclass:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        
        if not bg:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        
        characterCog = self.bot.get_cog('Character')
        roleCreationDict = {
            'D&D Friend':[2],
            'Journeyfriend':[3],
            'Elite Friend':[3],
            'True Friend':[3],
            'Ascended Friend':[3],
            'Good Noodle':[4],
            'Elite Noodle':[4,5],
            'True Noodle':[4,5,6],
            'Ascended Noodle':[4,5,6,7],
            'Immortal Noodle':[4,5,6,7,8],
            'Eternal Noodle':[4,5,6,7,8,9],
            'Infinity Noodle':[4,5,6,7,8,9,10],
            'Beyond Noodle':[4,5,6,7,8,9,10,11]
        }
        roles = [r.name for r in ctx.author.roles]
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed ()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        charEmbedmsg = None
        statNames = ['STR','DEX','CON','INT','WIS','CHA']
        charDict = {
          'User ID': str(author.id),
          'Name': name,
          'Level': int(level),
          'HP': 0,
          'Class': cclass,
          'Background': bg,
          'STR': int(sStr),
          'DEX': int(sDex),
          'CON': int(sCon),
          'INT': int(sInt),
          'WIS': int(sWis),
          'CHA': int(sCha),
          'Alignment': 'Unknown',
          'CP' : 0,
          'GP': 0,
          'Magic Items': 'None',
          'Consumables': 'None',
          'Feats': 'None',
          'Inventory': {},
          'Predecessor': {},
          'Games': 0
        }

        lvl = int(level)
        # Provides an error message at the end. If there are more than one, it will join msg.
        msg = ""

        
        # Name should be less then 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"

        # Reserved for regex, lets not use these for character names please
        invalidChars = ["[", "]", "?", "“","”", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]

        for i in invalidChars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"


        if msg == "":
            query = name
            query = query.replace('(', '\\(')
            query = query.replace(')', '\\)')
            query = query.replace('.', '\\.')
            playersCollection = db.players
            userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' } }))

            if userRecords != list():
                msg += f":warning: You already have a character by the name of ***{name}***! Please use a different name.\n"
        
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
        
        # Checks CP
        if lvl < 5:
            maxCP = 4
        else:
            maxCP = 10
        cp = 0
        cpTransfered = 0
        time_transfer_success = False
        if timeTransfer:
            
            userRecords = db.users.find_one({"User ID" : str(author.id)})
            if not userRecords:
                msg += f":warning: I could not find you in the database!\n"
            elif "Time Bank" not in userRecords.keys():
                pass
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
                    
                if totalTime > userRecords["Time Bank"]:
                    msg += f":warning: You do not have enough hours to transfer!\n"
                else:
                    cp = ((totalTime) // 900) / 4
                    cpTransfered = cp
                    while(cp >= maxCP and lvl <20):
                        cp -= maxCP
                        lvl += 1
                        if lvl > 4:
                            maxCP = 10
                    time_transfer_success = True
                    charDict["Level"] = lvl
                            
        charDict['CP'] = cp
        
        levelCP = (((lvl-5) * 10) + 16)
        if lvl < 5:
            levelCP = ((lvl -1) * 4)
        cp_tp_gp_array = calculateTreasure(1, 0, (levelCP+cp)*3600)
        totalGP = cp_tp_gp_array[2]
        bankTP = []
        bankTP = cp_tp_gp_array[1]
        tpBank = [0,0,0,0,0]
        #grab the available TP of the character
        for x in range(1,6):
            if f'T{x} TP' in bankTP.keys():
                tpBank[x-1] = (float(bankTP[f'T{x} TP']))
        
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
            statsArray = [int(sStr), int(sDex), int(sCon), int(sInt), int(sWis), int(sCha)]
            
            totalPoints = 0
            for s in statsArray:
                if (13-s) < 0:
                    totalPoints += ((s - 13) * 2) + 5
                else:
                    totalPoints += (s - 8)
                    
            if any([s < 8 for s in statsArray]):
                msg += f":warning: You have at least one stat below the minimum of 8.\n"
            if any([s > 15 for s in statsArray]):
                msg += f":warning: You have at least one stat above the maximum of 15.\n"
            if totalPoints != 27:
                msg += f":warning: Your stats do not add up to 27 using point buy ({totalPoints}/27). Remember that you must list your stats before applying racial modifiers! Please check your point allocation using this calculator: <https://chicken-dinner.com/5e/5e-point-buy.html>\n"
            
        
        
        # Magic Item / TP
        # Check if magic items exist, and calculates the TP cost of each magic item.
        mItems = ""
        magicItems = mItems.strip().split(',')
        allMagicItemsString = []


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
                        
                        if 'spell scroll' in r.lower() and sRecord:
                            reRecord['Name'] = f"Spell Scroll ({sRecord['Name']})"
                        allRewardItemsString.append(reRecord)
                allRewardItemsString.sort(key=lambda x: x["Tier"])
                tier1CountMNC = 0
                rewardConsumables = []
                rewardMagics = []
                rewardInv = []
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
                elif 'Infinity Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 3
                    tierConsumableCounts[2] = 2
                elif 'Beyond Noodle' in roles:
                    tierConsumableCounts[0] = 1
                    tierConsumableCounts[1] = 3
                    tierConsumableCounts[2] = 3
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
                      rewardConsumables.append(item)
                    elif item["Type"] == 'Magic Items':
                      rewardMagics.append(item)
                    else:
                        rewardInv.append(item)


                if tier1CountMNC < 0 or any([count < 0 for count in tierConsumableCounts]):
                    msg += f":warning: You do not have the right roles for these reward items. You can only choose **{startt1MNC}** Tier 1 (Non-Consumable) item(s)"
                    z = 0
                    for amount in startCounts:
                        if amount > 0:
                            msg += f", and **{amount}** Tier {z} (or lower) item(s)"
                        z += 1
                    msg += "\n"
                else:
                    for r in rewardConsumables:
                        if charDict['Consumables'] != "None":
                            charDict['Consumables'] += ', ' + r['Name']
                        else:
                            charDict['Consumables'] = r['Name']
                    for r in rewardMagics:
                        if charDict['Magic Items'] != "None":
                            charDict['Magic Items'] += ', ' + r['Name']
                        else:
                            charDict['Magic Items'] = r['Name']
                    for r in rewardInv:
                        if r["Name"] in charDict['Inventory'].keys():
                            charDict['Inventory'][r['Name']] +=1
                        else:
                            charDict['Inventory'][r['Name']] =1
                      
        # check race
        
        if msg == "":
            rRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'races',race)
            if charEmbedmsg == "Fail":
                return
            if not rRecord:
                msg += f'• {race} isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
            else:
                charDict['Race'] = rRecord['Name']

        
        # Check Character's class
        classStat = []
        cRecord = []
        totalLevel = 0
        mLevel = 0
        broke = []
        # If there's a /, character is creating a multiclass character
        if '/' in cclass:
            multiclassList = cclass.replace(' ', '').split('/')
            # Iterates through the multiclass list 
            
            for m in multiclassList:
                # Separate level and class
                mLevel = re.search('\d+', m)
                if not mLevel:
                    msg += ":warning: You are missing the level for your multiclass class. Please check your format.\n"

                    break
                mLevel = mLevel.group()
                mClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'classes',m[:len(m) - len(mLevel)])
                if not mClass:
                    cRecord = None
                    broke.append(m[:len(m) - len(mLevel)])

                # Check for class duplicates (ex. Paladin 1 / Paladin 2 = Paladin 3)
                classDupe = False
                if(cRecord or cRecord==list()):
                    for c in cRecord:
                        if c['Class'] == mClass:
                            c['Level'] = str(int(c['Level']) + int(mLevel))
                            classDupe = True                    
                            break

                    if not classDupe:
                        cRecord.append({'Class': mClass, 'Level':mLevel})
                    totalLevel += int(mLevel)

        else:
            singleClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'classes',cclass)
            if singleClass:
                cRecord.append({'Class':singleClass, 'Level':lvl, 'Subclass': 'None'})
            else:
                cRecord = None
                broke.append(cclass)

        charDict['Class'] = ""
        if not mLevel and '/' in cclass:
            pass
        elif len(broke)>0:
            msg += f':warning: **{broke}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        elif totalLevel != lvl and len(cRecord) > 1:
            msg += ':warning: Your classes do not add up to the total level. Please double-check your multiclasses.\n'
        elif msg == "":
            #cRecord = sorted(cRecord, key = lambda i: i['Level'], reverse=True) 

            # starting equipment
            def alphaEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

            if 'Starting Equipment' in cRecord[0]['Class'] and msg == "":
                startEquipmentLength = 0
                if not charEmbedmsg:
                    charEmbedmsg = await channel.send(embed=charEmbed)
                elif charEmbedmsg == "Fail":
                    msg += ":warning: You have either cancelled the command or a value was not found."
                else:
                    await charEmbedmsg.edit(embed=charEmbed)

                for item in cRecord[0]['Class']['Starting Equipment']:
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
                            self.bot.get_command('create').reset_cooldown(ctx)
                            return 
                        else:
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command('create').reset_cooldown(ctx)
                                return 
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
                                charDict['Inventory'][pk] = pv
                                seiString += f"+ {pk} x{pv}\n"

                    charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength + 1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=seiString, inline=False)
                    
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
                                charInv = list(filter(lambda c: 'Yklwa' not in c['Name'] and 'Light Repeating Crossbow' not in c['Name'] and 'Double-Bladed Scimitar' not in c['Name'] and 'Oversized Longbow' not in c['Name'], charInv))
                                for c in charInv:
                                    charInvString += f"{alphaEmojis[alphaIndex]}: {c['Name']}\n"
                                    alphaIndex += 1

                                charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=charInvString, inline=False)
                                await charEmbedmsg.clear_reactions()
                                await charEmbedmsg.add_reaction('❌')
                                await charEmbedmsg.edit(embed=charEmbed)

                                try:
                                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                                except asyncio.TimeoutError:
                                    await charEmbedmsg.delete()
                                    await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                                    self.bot.get_command('create').reset_cooldown(ctx)
                                    return 
                                else:
                                    if tReaction.emoji == '❌':
                                        await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                        await charEmbedmsg.clear_reactions()
                                        self.bot.get_command('create').reset_cooldown(ctx)
                                        return 
                                
                                
                                p = 0
                                for a in charInv:
                                    p+=1
                                typeEquipmentList.append(charInv[alphaEmojis.index(tReaction.emoji)]['Name'])
                            typeCount = collections.Counter(typeEquipmentList)
                            typeString = ""
                            for tk, tv in typeCount.items():
                                if tk in charDict['Inventory']:
                                    charDict['Inventory'][tk] += tv
                                else:
                                    charDict['Inventory'][tk] = tv
                                
                                typeString += f"{tk} x{charDict['Inventory'][tk]}\n"

                            charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=seiString.replace(f"{k} x{v}\n", typeString), inline=False)

                        elif 'Pack' not in k:
                            
                            if k in charDict['Inventory']:
                                charDict['Inventory'][k] += v
                            else:
                                charDict['Inventory'][k] = v
                                
                    startEquipmentLength += 1
                await charEmbedmsg.clear_reactions()
                charEmbed.clear_fields()

            # Subclass
            for m in cRecord:
                m['Subclass'] = 'None'
                if int(m['Level']) < lvl:
                    className = f'{m["Class"]["Name"]} {m["Level"]}'
                else:
                    className = f'{m["Class"]["Name"]}'

                classStatName = f'{m["Class"]["Name"]}'

                if int(m['Class']['Subclass Level']) <= int(m['Level']) and msg == "":
                    subclassesList = m['Class']['Subclasses'].split(',')
                    subclass, charEmbedmsg = await characterCog.chooseSubclass(ctx, subclassesList, m['Class']['Name'], charEmbed, charEmbedmsg)
                    if not subclass:
                        return

                    m['Subclass'] = f'{className} ({subclass})' 
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
        # check bg and gp

        def bgTopItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndexTop]) or (str(r.emoji) == '❌')) and u == author and sameMessage

        def bgItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author and sameMessage


        if msg == "":
            bRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'backgrounds',bg)

            if charEmbedmsg == "Fail":
                self.bot.get_command('create').reset_cooldown(ctx)
                return
            if not bRecord:
                msg += f':warning: **{bg}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
            else:
                charDict['Background'] = bRecord['Name']

                # TODO: make function for inputing in inventory
                # Background items: goes through each background and give extra items for inventory.
                
                for e in bRecord['Equipment']:
                    beTopChoiceList = []
                    beTopChoiceKeys = []
                    alphaIndexTop = 0
                    beTopChoiceString = ""
                    for ek, ev in e.items():
                        if type(ev) == dict:
                            beTopChoiceKeys.append(ek)
                            beTopChoiceList.append(ev)
                            beTopChoiceString += f"{alphaEmojis[alphaIndexTop]}: {ek}\n"
                            alphaIndexTop += 1
                        else:
                            if charDict['Inventory'] == "None":
                                charDict['Inventory'] = {ek : int(ev)}
                            else:
                                if ek not in charDict['Inventory']:
                                    charDict['Inventory'][ek] = int(ev)
                                else:
                                    charDict['Inventory'][ek] += int(ev)

                    if len(beTopChoiceList) > 0:
                        # Lets user pick between top choices (ex. Game set or Musical Instrument. Then a followup choice.)
                        if len(beTopChoiceList) > 1:
                            charEmbed.add_field(name=f"Your {bRecord['Name']} background lets you choose one type.", value=beTopChoiceString, inline=False)
                            if not charEmbedmsg:
                                charEmbedmsg = await channel.send(embed=charEmbed)
                            else:
                                await charEmbedmsg.edit(embed=charEmbed)

                            await charEmbedmsg.add_reaction('❌')
                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=bgTopItemCheck , timeout=60)
                            except asyncio.TimeoutError:
                                await charEmbedmsg.delete()
                                await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                                self.bot.get_command('create').reset_cooldown(ctx)
                                return
                            else:
                                await charEmbedmsg.clear_reactions()
                                if tReaction.emoji == '❌':
                                    await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                    await charEmbedmsg.clear_reactions()
                                    self.bot.get_command('create').reset_cooldown(ctx)
                                    return

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
                              if charDict['Inventory'] == "None":
                                  charDict['Inventory'] = {c : 1}
                              else:
                                  if c not in charDict['Inventory']:
                                      charDict['Inventory'][c] = 1
                                  else:
                                      charDict['Inventory'][c] += 1
                        else:
                            for c in beTopValues:
                                beChoiceString += f"{alphaEmojis[alphaIndex]}: {c}\n"
                                beList.append(c)
                                alphaIndex += 1

                            charEmbed.add_field(name=f"Your {bRecord['Name']} background lets you choose one {beTopKey}.", value=beChoiceString, inline=False)
                            if not charEmbedmsg:
                                charEmbedmsg = await channel.send(embed=charEmbed)
                            else:
                                await charEmbedmsg.edit(embed=charEmbed)

                            await charEmbedmsg.add_reaction('❌')
                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=bgItemCheck , timeout=60)
                            except asyncio.TimeoutError:
                                await charEmbedmsg.delete()
                                await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                                self.bot.get_command('create').reset_cooldown(ctx)
                                return
                            else:
                                await charEmbedmsg.clear_reactions()
                                if tReaction.emoji == '❌':
                                    await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                                    await charEmbedmsg.clear_reactions()
                                    self.bot.get_command('create').reset_cooldown(ctx)
                                    return
                                beKey = beList[alphaEmojis.index(tReaction.emoji)]
                                if charDict['Inventory'] == "None":
                                    charDict['Inventory'] = {beKey : 1}
                                else:
                                    if beKey not in charDict['Inventory']:
                                        charDict['Inventory'][beKey] = 1
                                    else:
                                        charDict['Inventory'][beKey] += 1

                        charEmbed.clear_fields()
                
                charDict['GP'] = int(bRecord['GP']) + totalGP
        
        
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
        #Stats - Feats
        if msg == "":
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
            featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, rRecord['Name'], charDict['Class'], cRecord, featLevels, charEmbed, charEmbedmsg, charDict, "")

            if not featsChosen and not statsFeats and not charEmbedmsg:
                self.bot.get_command('create').reset_cooldown(ctx)
                return

            if featsChosen:
                charDict['Feats'] = featsChosen 
            else: 
                charDict['Feats'] = "None" 
            
            for key, value in statsFeats.items():
                charDict[key] = value

            #HP
            hpRecords = []
            for cc in cRecord:
                # Wizards get 2 free spells per wizard level
                if cc['Class']['Name'] == "Wizard":
                    charDict['Free Spells'] = [6,0,0,0,0,0,0,0,0]
                    fsIndex = 0
                    for i in range (2, int(cc['Level']) + 1 ):
                        if i % 2 != 0:
                            fsIndex += 1
                        charDict['Free Spells'][fsIndex] += 2

                hpRecords.append({'Level':cc['Level'], 'Subclass': cc['Subclass'], 'Name': cc['Class']['Name'], 'Hit Die Max': cc['Class']['Hit Die Max'], 'Hit Die Average':cc['Class']['Hit Die Average']})

            # Multiclass Requirements
            if '/' in cclass and len(cRecord) > 1:
                for m in cRecord:
                    reqFufillList = []
                    statReq = m['Class']['Multiclass'].split(' ')
                    if m['Class']['Multiclass'] != 'None':
                        if '/' not in m['Class']['Multiclass'] and '+' not in m['Class']['Multiclass']:
                            if int(charDict[statReq[0]]) < int(statReq[1]):
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{statReq[0]} {charDict[statReq[0]]}**!\n"

                        elif '/' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('/')
                            reqFufill = False
                            for s in statReq[0]:
                                if int(charDict[s]) >= int(statReq[1]):
                                  reqFufill = True
                                else:
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**!\n"

                        elif '+' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('+')
                            reqFufill = True
                            for s in statReq[0]:
                                if int(charDict[s]) < int(statReq[1]):
                                  reqFufill = False
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**!\n"
        
        if msg:
            if charEmbedmsg and charEmbedmsg != "Fail":
                await charEmbedmsg.delete()
            elif charEmbedmsg == "Fail":
                msg = ":warning: You have either cancelled the command or a value was not found."
            await ctx.channel.send(f'There were error(s) when creating your character:\n{msg}')

            self.bot.get_command('create').reset_cooldown(ctx)
            return 
        
        if 'Max Stats' not in charDict:
            charDict['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
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
        specialStatStr = ""
        for s in specialRecords:
            if 'Bonus Level' in s:
                for c in subclasses:
                    if s['Bonus Level'] <= c['Level'] and s['Name'] in f"{c['Name']} ({c['Subclass']})":
                        if 'MAX' in s['Stat Bonuses']:
                            statSplit = s['Stat Bonuses'].split('MAX ')[1].split(', ')
                            for stat in statSplit:
                                maxSplit = stat.split(' +')
                                charDict[maxSplit[0]] += int(maxSplit[1])
                                charDict['Max Stats'][maxSplit[0]] += int(maxSplit[1]) 

                            specialStatStr = f"Level {s['Bonus Level']} {c['Name']} stat bonus unlocked! {s['Stat Bonuses']}"


        maxStatStr = ""
        for sk in charDict['Max Stats'].keys():
            if charDict[sk] > charDict['Max Stats'][sk]:
                charDict[sk] = charDict['Max Stats'][sk]
        if hpRecords:
            charDict['HP'] = await characterCog.calcHP(ctx,hpRecords,charDict,lvl)
        
        
        
        charLevel = charDict['Level']
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
        charEmbed.clear_fields()    
        charEmbed.title = f"{charDict['Name']} (Lv {charDict['Level']}): {charDict['CP']}/{cp_bound_array[tierNum-1][1]} CP"
        charEmbed.description = f"**Race**: {charDict['Race']}\n**Class**: {charDict['Class']}\n**Background**: {charDict['Background']}\n**Max HP**: {charDict['HP']}\n**GP**: {charDict['GP']} " + (time_transfer_success * ("\n**Transfered**"))

        
        for x in range(1,6):
            if tpBank[x-1]>0:
              charDict[f'T{x} TP'] = tpBank[x-1]
              charEmbed.add_field(name=f':warning: Unused T{x} TP', value=charDict[f'T{x} TP'], inline=True)
        if charDict['Magic Items'] != 'None':
            charEmbed.add_field(name='Magic Items', value=charDict['Magic Items'], inline=False)
        if charDict['Consumables'] != 'None':
            charEmbed.add_field(name='Consumables', value=charDict['Consumables'], inline=False)
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
        if charDict['Inventory'] != "None":
            for k,v in charDict['Inventory'].items():
                charDictInvString += f"• {k} x{v}\n"
            charEmbed.add_field(name='Starting Equipment', value=charDictInvString, inline=False)


        def charCreateCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author


        charEmbed.set_footer(text= None)
        if not charEmbedmsg:
            charEmbedmsg = await channel.send(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")
        else:
            await charEmbedmsg.edit(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")

        await charEmbedmsg.add_reaction('✅')
        await charEmbedmsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
        except asyncio.TimeoutError:
            await charEmbedmsg.delete()
            await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command('create').reset_cooldown(ctx)
            return
        else:
            await charEmbedmsg.clear_reactions()
            if tReaction.emoji == '❌':
                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await charEmbedmsg.clear_reactions()
                self.bot.get_command('create').reset_cooldown(ctx)
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
            if time_transfer_success:
                db.users.update_one({"User ID": str(author.id)}, {"$inc" : {"Time Bank": -cpTransfered *3600}})
                await self.levelCheck(ctx, charDict["Level"], charDict["Name"])
            statsCollection.update_one({'Life':1}, {"$set": statsRecord}, upsert=True)
            
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            charEmbed.set_footer(text= None)
            if charEmbedmsg:
                await charEmbedmsg.clear_reactions()
                await charEmbedmsg.edit(embed=charEmbed, content =f"Congratulations! :tada: You have created ***{charDict['Name']}***!")
            else: 
                charEmbedmsg = await channel.send(embed=charEmbed, content=f"Congratulations! You have created your ***{charDict['Name']}***!")

        self.bot.get_command('create').reset_cooldown(ctx)


    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command(aliases=['rs'])
    async def respec(self,ctx, name, newname, race, cclass, bg, sStr:int, sDex:int, sCon:int, sInt:int, sWis:int, sCha:int):
        newname = newname.strip()
        characterCog = self.bot.get_cog('Character')
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        charEmbed = discord.Embed ()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

        statNames = ['STR','DEX','CON','INT','WIS','CHA']
        roles = [r.name for r in ctx.author.roles]
        charDict, charEmbedmsg = await checkForChar(ctx, name, charEmbed)

        if not charDict:
            return

        # Reset  values here
        charNoneKeyList = ['Magic Items', 'Inventory', 'Current Item', 'Consumables']

        charRemoveKeyList = ['Predecessor','Image', 'T1 TP', 'T2 TP', 'T3 TP', 'T4 TP', 'Attuned', 'Spellbook', 'Guild', 'Guild Rank', 'Grouped']
        
        guild_name = ""
        
        if "Guild" in charDict:
            guild_name = charDict["Guild"]
        
        m_save = charDict['Magic Items'].split(", ")
        # i_save = list(charDict['Inventory'].keys())
        check_list = m_save #+i_save
        
        searched_items = list(db.rit.find({"Name" : {"$in": check_list}}))
        searched_items_names = []
        
        for element in searched_items:
            if "Grouped" in element:
                searched_items_names += element["Name"]
            else:
                searched_items_names.append(element["Name"])
        
        m_saved_list = []
        for m_item in m_save:
            if m_item in searched_items_names:
                m_saved_list.append(m_item)
                
        # i_saved_list = []
        # for i_item in i_save:
            # if i_item in searched_items_names:
                # i_saved_list.append([i_item, charDict["Inventory"][i_item]])
        
        for c in charNoneKeyList:
            charDict[c] = "None"

        for c in charRemoveKeyList:
            if c in charDict:
                del charDict[c]
        name = charDict["Name"]
        charDict["Magic Items"] = ", ".join(m_saved_list) + ("None" * (len(m_saved_list) == 0))
        charDict["Inventory"] = {}
        
        # for i_item in i_saved_list:
            # charDict["Inventory"][i_item[0]] = i_item[1]
        charDict["Predecessor"]= {}
        
        charID = charDict['_id']
        charDict['STR'] = int(sStr)
        charDict['DEX'] = int(sDex)
        charDict['CON'] = int(sCon)
        charDict['INT'] = int(sInt)
        charDict['WIS'] = int(sWis)
        charDict['CHA'] = int(sCha)
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
        
        # new name should be less then 64 chars
        if len(newname) > 64:
            msg += ":warning: Your character's new name is too long! The limit is 64 characters.\n"
        # Reserved for regex, lets not use these for character names please
        invalidChars = ["[", "]", "?", "“","”", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]
        for i in invalidChars:
            if i in newname:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"


        # Prevents name, level, race, class, background from being blank. Resets infinite cooldown and prompts
        if not newname:
            await channel.send(content=":warning: The new name of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return
        
        
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

        if not cclass:
            await channel.send(content=":warning: The class of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return
        
        if not bg:
            await channel.send(content=":warning: The background of your character cannot be blank! Please try again.\n")
            self.bot.get_command('respec').reset_cooldown(ctx)
            return


        allMagicItemsString = []

        # Because we are respeccing we are also adding extra TP based on CP.
        # no needed to to bankTP2 now because limit is lvl 4 to respec
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
            
        cp_tp_gp_array = calculateTreasure(1, 0, (levelCP+extraCp)*3600)
        totalGP = cp_tp_gp_array[2]
        bankTP = cp_tp_gp_array[1]
        # Stats - Point Buy
        if msg == "":
            statsArray = [int(sStr), int(sDex), int(sCon), int(sInt), int(sWis), int(sCha)]
            
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
        classStat = []
        cRecord = []
        totalLevel = 0
        mLevel = 0
        broke = []
        # If there's a /, character is creating a multiclass character
        if '/' in cclass:
            multiclassList = cclass.replace(' ', '').split('/')
            # Iterates through the multiclass list 
            
            for m in multiclassList:
                # Separate level and class
                mLevel = re.search('\d+', m)
                if not mLevel:
                    msg += ":warning: You are missing the level for your multiclass class. Please check your format.\n"

                    break
                mLevel = mLevel.group()
                mClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'classes',m[:len(m) - len(mLevel)])
                if not mClass:
                    cRecord = None
                    broke.append(m[:len(m) - len(mLevel)])

                # Check for class duplicates (ex. Paladin 1 / Paladin 2 = Paladin 3)
                classDupe = False
                
                if(cRecord or cRecord==list()):
                    for c in cRecord:
                        if c['Class'] == mClass:
                            c['Level'] = str(int(c['Level']) + int(mLevel))
                            classDupe = True                    
                            break

                    if not classDupe:
                        cRecord.append({'Class': mClass, 'Level':mLevel})
                    totalLevel += int(mLevel)

        else:
            singleClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'classes',cclass)
            if singleClass:
                cRecord.append({'Class':singleClass, 'Level':lvl, 'Subclass': 'None'})
            else:
                cRecord = None
                broke.append(cclass)

        charDict['Class'] = ""
        if not mLevel and '/' in cclass:
            pass
        elif len(broke)>0:
            msg += f':warning: **{broke}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        
        elif len(broke)>0:
            msg += f':warning: **{broke}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
        elif totalLevel != lvl and len(cRecord) > 1:
            msg += ':warning: Your classes do not add up to the total level. Please double-check your multiclasses.\n'
        elif msg == "":

            # starting equipment
            def alphaEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author

            if 'Starting Equipment' in cRecord[0]['Class'] and msg == "":
                if charDict['Inventory'] == "None":
                    charDict['Inventory'] = {}
                startEquipmentLength = 0
                if not charEmbedmsg:
                    charEmbedmsg = await channel.send(embed=charEmbed)
                elif charEmbedmsg == "Fail":
                    msg += ":warning: You have either cancelled the command or a value was not found."
                else:
                    await charEmbedmsg.edit(embed=charEmbed)

                for item in cRecord[0]['Class']['Starting Equipment']:
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
                            await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}respec "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                            self.bot.get_command('respec').reset_cooldown(ctx)
                            return 
                        else:
                            if tReaction.emoji == '❌':
                                await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                                await charEmbedmsg.clear_reactions()
                                self.bot.get_command('respec').reset_cooldown(ctx)
                                return 
                                
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
                                charDict['Inventory'][pk] = pv
                                seiString += f"+ {pk} x{pv}\n"

                    charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength + 1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=seiString, inline=False)

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
                                
                                charInv = list(filter(lambda c: 'Yklwa' not in c['Name'] and 'Light Repeating Crossbow' not in c['Name'] and 'Double-Bladed Scimitar' not in c['Name'] and 'Oversized Longbow' not in c['Name'], charInv))
                                for c in charInv:
                                    charInvString += f"{alphaEmojis[alphaIndex]}: {c['Name']}\n"
                                    alphaIndex += 1

                                charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=charInvString, inline=False)
                                await charEmbedmsg.clear_reactions()
                                await charEmbedmsg.add_reaction('❌')
                                await charEmbedmsg.edit(embed=charEmbed)

                                try:
                                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=alphaEmbedCheck, timeout=60)
                                except asyncio.TimeoutError:
                                    await charEmbedmsg.delete()
                                    await channel.send(f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}respec "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                                    self.bot.get_command('respec').reset_cooldown(ctx)
                                    return 
                                else:
                                    if tReaction.emoji == '❌':
                                        await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                                        await charEmbedmsg.clear_reactions()
                                        self.bot.get_command('respec').reset_cooldown(ctx)
                                        return 
                                typeEquipmentList.append(charInv[alphaEmojis.index(tReaction.emoji)]['Name'])
                            typeCount = collections.Counter(typeEquipmentList)
                            typeString = ""
                            for tk, tv in typeCount.items():
                                typeString += f"{tk} x{tv}\n"
                                if tk in charDict['Inventory']:
                                    charDict['Inventory'][tk] += tv
                                else:
                                    charDict['Inventory'][tk] = tv

                            charEmbed.set_field_at(startEquipmentLength, name=f"Starting Equipment: {startEquipmentLength+1} of {len(cRecord[0]['Class']['Starting Equipment'])}", value=seiString.replace(f"{k} x{v}\n", typeString), inline=False)

                        elif 'Pack' not in k:
                            if k in charDict['Inventory']:
                                charDict['Inventory'][k] += v
                            else:
                                charDict['Inventory'][k] = v
                    startEquipmentLength += 1
                await charEmbedmsg.clear_reactions()
                charEmbed.clear_fields()

            # Subclass
            for m in cRecord:
                m['Subclass'] = 'None'
                if int(m['Level']) < lvl:
                    className = f'{m["Class"]["Name"]} {m["Level"]}'
                else:
                    className = f'{m["Class"]["Name"]}'

                classStatName = f'{m["Class"]["Name"]}'

                if int(m['Class']['Subclass Level']) <= int(m['Level']) and msg == "":
                    subclassesList = m['Class']['Subclasses'].split(',')
                    subclass, charEmbedmsg = await characterCog.chooseSubclass(ctx, subclassesList, m['Class']['Name'], charEmbed, charEmbedmsg)
                    if not subclass:
                        return

                    m['Subclass'] = f'{className} ({subclass})' 
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

        # check bg and gp

        def bgTopItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndexTop]) or (str(r.emoji) == '❌')) and u == author and sameMessage

        def bgItemCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return ((r.emoji in alphaEmojis[:alphaIndex]) or (str(r.emoji) == '❌')) and u == author and sameMessage


        if msg == "":
            bRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'backgrounds',bg)

            if charEmbedmsg == "Fail":
                self.bot.get_command('respec').reset_cooldown(ctx)
                return
            if not bRecord:
                msg += f':warning: **{bg}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n'
            else:
                charDict['Background'] = bRecord['Name']

                # TODO: make function for inputing in inventory
                # Background items: goes through each background and give extra items for inventory.
                
                for e in bRecord['Equipment']:
                    beTopChoiceList = []
                    beTopChoiceKeys = []
                    alphaIndexTop = 0
                    beTopChoiceString = ""
                    for ek, ev in e.items():
                        if type(ev) == dict:
                            beTopChoiceKeys.append(ek)
                            beTopChoiceList.append(ev)
                            beTopChoiceString += f"{alphaEmojis[alphaIndexTop]}: {ek}\n"
                            alphaIndexTop += 1
                        else:
                            if charDict['Inventory'] == "None":
                                charDict['Inventory'] = {ek : int(ev)}
                            else:
                                if ek not in charDict['Inventory']:
                                    charDict['Inventory'][ek] = int(ev)
                                else:
                                    charDict['Inventory'][ek] += int(ev)

                    if len(beTopChoiceList) > 0:
                        # Lets user pick between top choices (ex. Game set or Musical Instrument. Then a followup choice.)
                        if len(beTopChoiceList) > 1:
                            charEmbed.add_field(name=f"Your {bRecord['Name']} background lets you choose one type.", value=beTopChoiceString, inline=False)
                            if not charEmbedmsg:
                                charEmbedmsg = await channel.send(embed=charEmbed)
                            else:
                                await charEmbedmsg.edit(embed=charEmbed)

                            await charEmbedmsg.add_reaction('❌')
                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=bgTopItemCheck , timeout=60)
                            except asyncio.TimeoutError:
                                await charEmbedmsg.delete()
                                await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec "character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
                                self.bot.get_command('respec').reset_cooldown(ctx)
                                return
                            else:
                                await charEmbedmsg.clear_reactions()
                                if tReaction.emoji == '❌':
                                    await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                                    await charEmbedmsg.clear_reactions()
                                    self.bot.get_command('respec').reset_cooldown(ctx)
                                    return

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
                              if charDict['Inventory'] == "None":
                                  charDict['Inventory'] = {c : 1}
                              else:
                                  if c not in charDict['Inventory']:
                                      charDict['Inventory'][c] = 1
                                  else:
                                      charDict['Inventory'][c] += 1
                        else:
                            for c in beTopValues:
                                beChoiceString += f"{alphaEmojis[alphaIndex]}: {c}\n"
                                beList.append(c)
                                alphaIndex += 1

                            charEmbed.add_field(name=f"Your {bRecord['Name']} background lets you choose one {beTopKey}.", value=beChoiceString, inline=False)
                            if not charEmbedmsg:
                                charEmbedmsg = await channel.send(embed=charEmbed)
                            else:
                                await charEmbedmsg.edit(embed=charEmbed)

                            await charEmbedmsg.add_reaction('❌')
                            try:
                                tReaction, tUser = await self.bot.wait_for("reaction_add", check=bgItemCheck , timeout=60)
                            except asyncio.TimeoutError:
                                await charEmbedmsg.delete()
                                await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec "character name" level "race" "class" "background" STR DEX CON INT WIS CHA"```')
                                self.bot.get_command('respec').reset_cooldown(ctx)
                                return
                            else:
                                await charEmbedmsg.clear_reactions()
                                if tReaction.emoji == '❌':
                                    await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                                    await charEmbedmsg.clear_reactions()
                                    self.bot.get_command('respec').reset_cooldown(ctx)
                                    return
                                beKey = beList[alphaEmojis.index(tReaction.emoji)]
                                if charDict['Inventory'] == "None":
                                    charDict['Inventory'] = {beKey : 1}
                                else:
                                    if beKey not in charDict['Inventory']:
                                        charDict['Inventory'][beKey] = 1
                                    else:
                                        charDict['Inventory'][beKey] += 1

                        charEmbed.clear_fields()
                
                charDict['GP'] = int(bRecord['GP']) + totalGP
        
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

        #Stats - Feats
        if msg == "":
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

            featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, rRecord['Name'], charDict['Class'], cRecord, featLevels, charEmbed, charEmbedmsg, charDict, "")

            if not featsChosen and not statsFeats and not charEmbedmsg:
                return

            if featsChosen:
                charDict['Feats'] = featsChosen 
            else: 
                charDict['Feats'] = "None" 
            
            for key, value in statsFeats.items():
                charDict[key] = value


            #HP
            hpRecords = []
            for cc in cRecord:
                # Wizards get 2 free spells per wizard level
                if cc['Class']['Name'] == "Wizard":
                    charDict['Free Spells'] = [6,0,0,0,0,0,0,0,0]
                    fsIndex = 0
                    for i in range (2, int(cc['Level']) + 1 ):
                        if i % 2 != 0:
                            fsIndex += 1
                        charDict['Free Spells'][min(fsIndex, 8)] += 2
                hpRecords.append({'Level':cc['Level'], 'Subclass': cc['Subclass'], 'Name': cc['Class']['Name'], 'Hit Die Max': cc['Class']['Hit Die Max'], 'Hit Die Average':cc['Class']['Hit Die Average']})
                
            
            # Multiclass Requirements
            if '/' in cclass and len(cRecord) > 1:
                for m in cRecord:
                    reqFufillList = []
                    statReq = m['Class']['Multiclass'].split(' ')
                    if m['Class']['Multiclass'] != 'None':
                        if '/' not in m['Class']['Multiclass'] and '+' not in m['Class']['Multiclass']:
                            if int(charDict[statReq[0]]) < int(statReq[1]):
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{statReq[0]} {charDict[statReq[0]]}**\n"

                        elif '/' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('/')
                            reqFufill = False
                            for s in statReq[0]:
                                if int(charDict[s]) >= int(statReq[1]):
                                  reqFufill = True
                                else:
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**\n"

                        elif '+' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('+')
                            reqFufill = True
                            for s in statReq[0]:
                                if int(charDict[s]) < int(statReq[1]):
                                  reqFufill = False
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**\n"


        if msg:
            if charEmbedmsg and charEmbedmsg != "Fail":
                await charEmbedmsg.delete()
            elif charEmbedmsg == "Fail":
                msg = ":warning: You have either cancelled the command or a value was not found."
            await ctx.channel.send(f'There were error(s) when creating your character:\n{msg}')

            self.bot.get_command('respec').reset_cooldown(ctx)
            return 
        
        if 'Max Stats' not in charDict:
            charDict['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
        
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
            subclasses.append({'Name':charClass, 'Subclass':tempSub, 'Level':charLevel})
        #Special stat bonuses (Barbarian cap / giant soul sorc)
        specialCollection = db.special
        specialRecords = list(specialCollection.find())
        specialStatStr = ""
        for s in specialRecords:
            if 'Bonus Level' in s:
                for c in subclasses:
                    if s['Bonus Level'] <= c['Level'] and s['Name'] in f"{c['Name']} ({c['Subclass']})":
                        if 'MAX' in s['Stat Bonuses']:
                            statSplit = s['Stat Bonuses'].split('MAX ')[1].split(', ')
                            for stat in statSplit:
                                maxSplit = stat.split(' +')
                                charDict[maxSplit[0]] += int(maxSplit[1])
                                charDict['Max Stats'][maxSplit[0]] += int(maxSplit[1]) 

                            specialStatStr = f"Level {s['Bonus Level']} {c['Name']} stat bonus unlocked! {s['Stat Bonuses']}"


        maxStatStr = ""
        for sk in charDict['Max Stats'].keys():
            if charDict[sk] > charDict['Max Stats'][sk]:
                charDict[sk] = charDict['Max Stats'][sk]
        if hpRecords:
            charDict['HP'] = await characterCog.calcHP(ctx,hpRecords,charDict,lvl)

        
        charEmbed.clear_fields()    
        charEmbed.title = f"{charDict['Name']} (Lv {charDict['Level']}): {charDict['CP']}/{cp_bound_array[tierNum-1][1]} CP"
        charEmbed.description = f"**Race**: {charDict['Race']}\n**Class**: {charDict['Class']}\n**Background**: {charDict['Background']}\n**Max HP**: {charDict['HP']}\n**GP**: {charDict['GP']} "

        
        for key, amount in bankTP.items():
            if  amount > 0:
                charDict[key] = amount
                charEmbed.add_field(name=f':warning: Unused {key}:', value=amount, inline=True)
        if charDict['Magic Items'] != 'None':
            charEmbed.add_field(name='Magic Items', value=charDict['Magic Items'], inline=False)
        if charDict['Consumables'] != 'None':
            charEmbed.add_field(name='Consumables', value=charDict['Consumables'], inline=False)
        charEmbed.add_field(name='Feats', value=charDict['Feats'], inline=True)
        charEmbed.add_field(name='Stats', value=f"**STR**: {charDict['STR']} **DEX**: {charDict['DEX']} **CON**: {charDict['CON']} **INT**: {charDict['INT']} **WIS**: {charDict['WIS']} **CHA**: {charDict['CHA']}", inline=False)
        
        if 'Wizard' in charDict['Class']:
            charEmbed.add_field(name='Spellbook (Wizard)', value=f"At 1st level, you have a spellbook containing six 1st-level Wizard spells of your choice (+2 free spells for each Wizard level). Please use the `{commandPrefix}shop copy` command.", inline=False)

# Put the text below after the last sentence in the previous line if this breaks anything.
# **{charDict['Free Spells']} Free Spells Available**

            fsString = ""
            fsIndex = 0
            for el in charDict['Free Spells']:
                if el > 0:
                    fsString += f"Level {fsIndex+1}: {el} free spells\n"
                fsIndex += 1

            if fsString:
                charEmbed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)

        charDictInvString = ""
        if charDict['Inventory'] != "None":
            for k,v in charDict['Inventory'].items():
                charDictInvString += f"• {k} x{v}\n"
            charEmbed.add_field(name='Starting Equipment', value=charDictInvString, inline=False)
            charEmbed.set_footer(text= None)
        
        charEmbed.set_footer(text= None)
        def charCreateCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author
        if not charEmbedmsg:
            charEmbedmsg = await channel.send(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")
        else:
            await charEmbedmsg.edit(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")

        await charEmbedmsg.add_reaction('✅')
        await charEmbedmsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
        except asyncio.TimeoutError:
            await charEmbedmsg.delete()
            await channel.send(f'Character respec cancelled. Use the following command to try again:\n```yaml\n{commandPrefix}respec "character name" "new character name" level "race" "class" "background" STR DEX CON INT WIS CHA```')
            self.bot.get_command('respec').reset_cooldown(ctx)
            return
        else:
            await charEmbedmsg.clear_reactions()
            if tReaction.emoji == '❌':
                await charEmbedmsg.edit(embed=None, content=f"Character respec cancelled. Try again using the same command:\n```yaml\n{commandPrefix}respec \"character name\" \"new character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA```")
                await charEmbedmsg.clear_reactions()
                self.bot.get_command('respec').reset_cooldown(ctx)
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
    @is_log_channel()
    @commands.command(aliases=['rr'])
    async def racerespec(self,ctx, name, race, sStr:int, sDex:int, sCon:int, sInt:int, sWis:int, sCha:int):
        author = ctx.author
        guild = ctx.guild
        channel = ctx.channel
        charEmbed = discord.Embed ()
        charEmbed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        charEmbed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

        statNames = ['STR','DEX','CON','INT','WIS','CHA']
        roles = [r.name for r in ctx.author.roles]
        charDict, charEmbedmsg = await checkForChar(ctx, name, charEmbed)
        if not charEmbedmsg:
            charEmbedmsg = await ctx.channel.send(embed=charEmbed)
        if not charDict:
            
            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return
        if not "Race Respec" in charDict:
            await channel.send(content=f"You have not been permitted this kind of respec. Contact a Mod to gain permission.")
            
            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return
        charID = charDict['_id']
        charDict['STR'] = int(sStr)
        charDict['DEX'] = int(sDex)
        charDict['CON'] = int(sCon)
        charDict['INT'] = int(sInt)
        charDict['WIS'] = int(sWis)
        charDict['CHA'] = int(sCha)

        charDict['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}

        lvl = charDict['Level']
        msg = ""

        if 'Death' in charDict.keys():
            await channel.send(content=f"You cannot respec a dead character. Use the following command to decide their fate:\n```yaml\n$death \"{charRecords['Name']}\"```")
            
            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return
        
        if not race:
            await channel.send(content=":warning: The race of your character cannot be blank! Please try again.\n")
            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return
        
        cclass = charDict["Class"]
        
        # Stats - Point Buy
        if msg == "":
            statsArray = [int(sStr), int(sDex), int(sCon), int(sInt), int(sWis), int(sCha)]
            
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
        
        characterCog = self.bot.get_cog('Character')
        # Check Character's class
        cRecord = []
        mLevel = lvl
        for class_text in cclass.split('/'):
            class_text = class_text.strip()
            class_data_split = class_text.split(" ")
            class_name = class_data_split[0]
            if len(class_data_split)>1 and class_data_split[1].isnumeric():
                mLevel = int(class_data_split[1])
            mClass, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'classes',class_name, exact=True)
            m = {'Class': mClass, 'Level':mLevel}
            cRecord.append(m)
            
            m['Subclass'] = 'None'
            if int(m['Level']) < lvl:
                className = f'{m["Class"]["Name"]} {m["Level"]}'
            else:
                className = f'{m["Class"]["Name"]}'


            if "(" in class_text:
                subclass = class_text.split("(")[1][:-1]
                m['Subclass'] = f'{className} ({subclass})' 


        
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
                
                self.bot.get_command('racerespec').reset_cooldown(ctx)  
                return
            charDict["STR"] = statsArray[0]
            charDict["DEX"] = statsArray[1]
            charDict["CON"] = statsArray[2]
            charDict["INT"] = statsArray[3]
            charDict["WIS"] = statsArray[4]
            charDict["CHA"] = statsArray[5]

        #Stats - Feats
        if msg == "":
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

            featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, rRecord['Name'], charDict['Class'], cRecord, featLevels, charEmbed, charEmbedmsg, charDict, "")

            if not featsChosen and not statsFeats and not charEmbedmsg:
                
                self.bot.get_command('racerespec').reset_cooldown(ctx)
                return

            if featsChosen:
                charDict['Feats'] = featsChosen 
            else: 
                charDict['Feats'] = "None" 
            
            for key, value in statsFeats.items():
                charDict[key] = value


            #HP
            hpRecords = []
            for cc in cRecord:
                hpRecords.append({'Level':cc['Level'], 'Subclass': cc['Subclass'], 'Name': cc['Class']['Name'], 'Hit Die Max': cc['Class']['Hit Die Max'], 'Hit Die Average':cc['Class']['Hit Die Average']})
                
            
            # Multiclass Requirements
            if len(cRecord) > 1:
                for m in cRecord:
                    reqFufillList = []
                    statReq = m['Class']['Multiclass'].split(' ')
                    if m['Class']['Multiclass'] != 'None':
                        if '/' not in m['Class']['Multiclass'] and '+' not in m['Class']['Multiclass']:
                            if int(charDict[statReq[0]]) < int(statReq[1]):
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{statReq[0]} {charDict[statReq[0]]}**\n"

                        elif '/' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('/')
                            reqFufill = False
                            for s in statReq[0]:
                                if int(charDict[s]) >= int(statReq[1]):
                                  reqFufill = True
                                else:
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**\n"

                        elif '+' in m['Class']['Multiclass']:
                            statReq[0] = statReq[0].split('+')
                            reqFufill = True
                            for s in statReq[0]:
                                if int(charDict[s]) < int(statReq[1]):
                                  reqFufill = False
                                  reqFufillList.append(f"{s} {charDict[s]}")
                            if not reqFufill:
                                msg += f":warning: In order to multiclass to or from **{m['Class']['Name']}** you need at least **{m['Class']['Multiclass']}**. Your character only has **{' and '.join(reqFufillList)}**\n"


        if msg:
            if charEmbedmsg and charEmbedmsg != "Fail":
                await charEmbedmsg.delete()
            elif charEmbedmsg == "Fail":
                msg = ":warning: You have either cancelled the command or a value was not found."
            await ctx.channel.send(f'There were error(s) when creating your character:\n{msg}')

            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return 
        
        if 'Max Stats' not in charDict:
            charDict['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
        
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
        for s in specialRecords:
            if 'Bonus Level' in s:
                for c in subclasses:
                    if s['Bonus Level'] <= c['Level'] and s['Name'] in f"{c['Name']} ({c['Subclass']})":
                        if 'MAX' in s['Stat Bonuses']:
                            statSplit = s['Stat Bonuses'].split('MAX ')[1].split(', ')
                            for stat in statSplit:
                                maxSplit = stat.split(' +')
                                charDict[maxSplit[0]] += int(maxSplit[1])
                                charDict['Max Stats'][maxSplit[0]] += int(maxSplit[1]) 


        maxStatStr = ""
        for sk in charDict['Max Stats'].keys():
            if charDict[sk] > charDict['Max Stats'][sk]:
                charDict[sk] = charDict['Max Stats'][sk]
        if hpRecords:
            charDict['HP'] = await characterCog.calcHP(ctx,hpRecords,charDict,lvl)

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
        charEmbed.clear_fields()    
        charEmbed.title = f"{charDict['Name']} (Lv {charDict['Level']}): {charDict['CP']}/{cp_bound_array[tierNum-1][1]} CP"
        charEmbed.description = f"**Race**: {charDict['Race']}\n**Class**: {charDict['Class']}\n**Background**: {charDict['Background']}\n**Max HP**: {charDict['HP']}\n**GP**: {charDict['GP']} "
        charEmbed.add_field(name='Feats', value=charDict['Feats'], inline=True)
        charEmbed.add_field(name='Stats', value=f"**STR**: {charDict['STR']} **DEX**: {charDict['DEX']} **CON**: {charDict['CON']} **INT**: {charDict['INT']} **WIS**: {charDict['WIS']} **CHA**: {charDict['CHA']}", inline=False)
        
        playersCollection = db.players
        
        charEmbed.set_footer(text=f"")
        def charCreateCheck(r, u):
            sameMessage = False
            if charEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author
        if not charEmbedmsg:
            charEmbedmsg = await channel.send(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")
        else:
            await charEmbedmsg.edit(embed=charEmbed, content="**Double-check** your character information.\nIf this is correct please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel. ")

        await charEmbedmsg.add_reaction('✅')
        await charEmbedmsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=charCreateCheck , timeout=60)
        except asyncio.TimeoutError:
            await charEmbedmsg.delete()
            await channel.send(f'Character respec cancelled. Use the following command to try again:\n```yaml\n{commandPrefix}racerespec \"character name\" \"new race\" STR DEX CON INT WIS CHA``````')
            self.bot.get_command('racerespec').reset_cooldown(ctx)
            return
        else:
            await charEmbedmsg.clear_reactions()
            if tReaction.emoji == '❌':
                await charEmbedmsg.edit(embed=None, content=f"Character respec cancelled. Try again using the same command:\n```yaml\n{commandPrefix}racerespec \"character name\" \"new race\" STR DEX CON INT WIS CHA```")
                await charEmbedmsg.clear_reactions()
                self.bot.get_command('racerespec').reset_cooldown(ctx)
                return

        try:
            if "Race Respec" in charDict:
                del charDict["Race Respec"]
            playersCollection.update_one({'_id': charID}, {"$set": charDict, "$unset":{"Race Respec" : 1}}, upsert=True)
            
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
        
            charEmbed.set_footer(text= None)
            if charEmbedmsg:
                await charEmbedmsg.clear_reactions()
                await charEmbedmsg.edit(embed=charEmbed, content =f"Congratulations! You have respecced your character!")
            else: 
                charEmbedmsg = await channel.send(embed=charEmbed, content=f"Congratulations! You have respecced your character!")
            
        self.bot.get_command('racerespec').reset_cooldown(ctx)
   
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def applyTime(self, ctx, charName, timeTransfer: str):
        msg = ctx.message
        error_msg = ""
        charEmbed = discord.Embed()
        charEmbedmsg = None
        author = ctx.author
        charDict, charEmbedmsg = await checkForChar(ctx, charName, charEmbed, author, customError=True)
        if not charDict:
            await ctx.channel.send(content=f"I could not find {charName} in the DB.")        
            self.bot.get_command('applyTime').reset_cooldown(ctx)
            return
        if "GID" in charDict:
            error_msg += f":warning: Your character is still awaiting rewards!\n"
        if "Death" in charDict:
            error_msg += f":warning: Your character is still dead!\n"
                    
        userRecords = db.users.find_one({"User ID" : str(author.id)})
        if not userRecords:
            error_msg += f":warning: I could not find you in the database!\n"
        elif "Time Bank" not in userRecords:
            error_msg += f":warning: You have no banked time in your records!\n"
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
                error_msg += f":warning: I could not find a number in your time amount!\n"
                totalTime = 0
                
            if totalTime > userRecords["Time Bank"]:
                error_msg += f":warning: You do not have enough hours to transfer!\n"
        
        if error_msg:
            await ctx.channel.send(content=error_msg)
            self.bot.get_command('applyTime').reset_cooldown(ctx)
            return
        treasureArray  = calculateTreasure(charDict["Level"], charDict["CP"], totalTime)
        totalTime = treasureArray[0] * 3600
        inc_dic = {"GP": treasureArray[2], "CP": treasureArray[0]}
        inc_dic.update(treasureArray[1])
        confirm_embed = discord.Embed()
        confirm_embed.title = f"Please confirm the **{timeConversion(totalTime, True)}** minute deduction."
        confirm_embed.description = f"\n**{charDict['Name']}** will receive **{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP**"
        confirm_message = await ctx.channel.send(embed=confirm_embed)
        decision = await confirm(confirm_message, ctx.author)
        if decision != 1:
            await confirm_message.edit(content=f"*Time transfer cancelled*", embed=None)
            self.bot.get_command('applyTime').reset_cooldown(ctx)
            return
        try:
            db.players.update_one({"_id": charDict["_id"]}, {"$inc": inc_dic})
            db.users.update_one({"User ID": f"{author.id}"}, {"$inc": {f"Time Bank": -totalTime}})
            await confirm_message.edit(content=f"**{charDict['Name']}** has received **{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP**", embed=None)
    
        except Exception as e:
            traceback.print_exc()
            
        self.bot.get_command('applyTime').reset_cooldown(ctx)
        return
        
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.command()
    async def trickortreat(self, ctx, char):
        channel = ctx.channel
        author = ctx.author
        shopEmbed = discord.Embed()
        
        # Check if character exists
        charRecords, shopEmbedmsg = await checkForChar(ctx, char, shopEmbed)

        if charRecords:
            def unfold(el):
                subel1, subel2, count  = el
                if not subel2:
                    subel2 = subel1
                return [(subel2, subel1)]*count
            pool = [("Bag of Disappointment", None, 1), 
                    ("Dread Helm", None, 2),
                    ("Pipe of Smoke Monsters", None, 2),
                    ("Common Glamerweave", None, 2),
                    ("Wand of Scowls", None, 2),
                    ("Wand of Pyrotechnics", None, 2),
                    ("Wildspace Orrery", "Projection Machine", 2),
                    ("Talking Doll", None, 2),
                    ("Potion of Diminution", None, 2),
                    ("Bottle of Boundless Coffee", "Apple Cider", 2),
                    ("Soul Coin", None, 1),
                    ]
            outcomes = []
            for el in pool:
                outcomes += unfold(el)
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
            bRecord = db.rit.find_one({"Name" : {"$regex" : f"^{selected_item.strip()}$", "$options": "i"}}) 
            text_string = f"{show_name}"
            if show_name != selected_item:
                text_string = f"{show_name} ({selected_item})"
                
            out_text = f"You reach into the gift box and find a(n) **{text_string}**\n\n*{amount-1} rolls remaining*"
            
            shopEmbed.description = out_text
            if bRecord:
                
                if shopEmbedmsg:
                    await shopEmbedmsg.edit(embed=shopEmbed)
                else:
                    shopEmbedmsg = await channel.send(embed=shopEmbed)
                if bRecord["Type"] != "Inventory":
                    if charRecords[bRecord["Type"]] != "None":
                        charRecords[bRecord["Type"]] += ', ' + selected_item
                    else:
                        charRecords[bRecord["Type"]] = selected_item
                else:
                    if charRecords['Inventory'] == "None":
                        charRecords['Inventory'] = {f"{selected_item}" : 1}
                    else:
                        if bRecord['Name'] not in charRecords['Inventory']:
                            charRecords['Inventory'][f"{selected_item}"] = 1 
                        else:
                            charRecords['Inventory'][f"{selected_item}"] += 1 
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
    @commands.command()
    async def export(self, ctx, char):
        channel = ctx.channel
        author = ctx.author
        shopEmbed = discord.Embed()
        
        # Check if character exists
        charRecords, shopEmbedmsg = await checkForChar(ctx, char, shopEmbed)
        #charRecords["Consumables"] = collections.Counter(charRecords['Consumables'].split(', '))
        desired = ["Name", "Consumables", "Magic Items", "Inventory", "Race", "STR", "INT", "CON", "WIS", "DEX", "CHA", "Class", "Spellbook", "GP", "Background", "Level", "Feats"]
        if charRecords:
            export = {}
            for key in desired:
                if key in charRecords:
                    export[key] = charRecords[key]
                else:
                    print(key)
            #shopEmbed.description = f"```{export}```"
            with io.StringIO(f"{export}") as f:
                await channel.send(file=discord.File(f, f"{charRecords['Name']}.json"))
                
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

                        # usersRecord = list(usersCollection.find({"User ID": charDict['User ID']}))[0]
                        # if 'Games' not in usersRecord:
                            # usersRecord['Games'] = charDict['Games']
                        # else:
                            # usersRecord['Games'] += charDict['Games']
                        # usersCollection.update_one({'User ID': charDict['User ID']}, {"$set": {'Games': usersRecord['Games']}}, upsert=True)
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
                    charEmbed.set_footer(text=None)
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
            spell_list = []
            if "Spellbook" in charDict:
                spell_list = [spell["Name"] for spell in charDict["Spellbook"]]
            if "Ritual Book" in charDict:
                spell_list += [spell["Name"] for spell in charDict["Ritual Book"]]
            if spell_list:
                spell_dict = {x["Name"] : x for x in db.spells.find({"Name": {"$in": spell_list}})}
                # Show Spellbook in inventory
                if "Spellbook" in charDict:
                    spellbook_string = ""
                    spell_levels = {x: [] for x in range(0,10)}
                    for spell in charDict["Spellbook"]:
                        spell_levels[spell_dict[spell["Name"]]["Level"]].append(spell_dict[spell["Name"]])
                    for level, spells in spell_levels.items():
                        if spells:
                            spellbook_string+= f"**Level {level}**\n"
                            for spell in sorted(spells, key=lambda s: s["Name"]):
                                spellbook_string += f"• {spell['Name']} ({spell['School']})\n"
                    contents.append(("Spellbook", spellbook_string, False))
                if 'Ritual Book' in charDict:
                    ritualbook_string = ""
                    spell_levels = {x: [] for x in range(0,10)}
                    for spell in charDict["Ritual Book"]:
                        spell_levels[spell_dict[spell["Name"]]["Level"]].append(spell_dict[spell["Name"]])
                    for level, spells in spell_levels.items():
                        if spells:
                            ritualbook_string+= f"**Level {level}**\n"
                            for spell in sorted(spells, key=lambda s: s["Name"]):
                                ritualbook_string += f"• {spell['Name']} ({spell['School']})\n"
                    contents.append(("Ritual Book", ritualbook_string, False))

            # Show Consumables in inventory.
            consumesString = ""
            consumesCount = collections.Counter(charDict['Consumables'].split(', '))
            for k, v in consumesCount.items():
                if v == 1:
                    consumesString += f"• {k}\n"
                else:
                    consumesString += f"• {k} x{v}\n"


            contents.append(("Consumables", consumesString, False))
            
            # Show Magic items in inventory.

            miString = ""
            miArray = collections.Counter(charDict['Magic Items'].split(', '))

            for m,v in miArray.items():
                if "Predecessor" in charDict and m in charDict["Predecessor"]:
                    upgrade_names = charDict['Predecessor'][m]["Names"]
                    stage = charDict['Predecessor'][m]["Stage"]
                    m = m + f" ({upgrade_names[stage]})"
                if v == 1:
                    miString += f"• {m}\n"
                else:
                    miString += f"• {m} x{v}\n"
            contents.append((f"Magic Items", miString, False))

            charDictAuthor = guild.get_member(int(charDict['User ID']))
            
            if charDict['Inventory'] != 'None':
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
                            amt = charDict['Inventory'][entry]
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
                                amt = v
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
    @commands.command(aliases=['u'])
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
                            
                    paused = "Paused" in charDict and charDict["Paused"]
                    charString += f"**{'[PAUSED] '*paused}{charDict['Name']}**: Lv {charDict['Level']}, {char_race}, {char_class}\n"

                    if 'Guild' in charDict:
                        charString += f"---Guild: *{charDict['Guild']}*\n"

        else:
            charString = "None"


        if 'Games' in userRecords:
            totalGamesPlayed += userRecords['Games']
        games_hosted = 0
        if 'Games Hosted' in userRecords:
            games_hosted += userRecords['Games Hosted']
        if 'Time Bank' in userRecords:
            contents.append((f"Time Bank", f"You have **{timeConversion(userRecords['Time Bank'],hmformat=True)}** available", False))
        if 'Double' in userRecords and userRecords["Double"]>0:
            contents.append((f"Double Reward", f"Your next **{userRecords['Double']}** games will have double rewards.", False))

        if "Guilds" in userRecords:
            guildNoodles = "• "
            guildNoodles += "\n• ".join(userRecords["Guilds"])
            
            contents.append((f"Guilds", f"You have created **{len(userRecords['Guilds'])}** guilds:\n {guildNoodles}", False))

        if "Campaigns" in userRecords:
            campaignString = ""
            for u, v in userRecords['Campaigns'].items():
                if not ("Hidden" in v and v["Hidden"]):
                    campaignString += f"• {(not v['Active'])*'~~'}{u}{(not v['Active'])*'~~'}: {v['Sessions']} sessions, {timeConversion(v['Time'],hmformat=True)}\n"
            contents.append((f"Campaigns", campaignString, False))

        noodles_text = "Noodles: 0:star: (Try hosting sessions to receive Noodles!)"
        dm_time = ""
        if 'Noodles' in userRecords:
            if "DM Time" in userRecords and userRecords["DM Time"] > 0:
                dm_time = f" ({int(userRecords['DM Time']/10800*100)}%)"
            noodles_text = f"Noodles: {userRecords['Noodles']}:star:"
        description = f"Total One-shots Played|Hosted: {totalGamesPlayed-games_hosted}|{games_hosted}\n{noodles_text}{dm_time}\n"
    
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
                nick_string = f"• Goes By: **{charDict['Nickname']}**\n"
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
            charEmbed.set_author(name=charDictAuthor, icon_url=charDictAuthor.display_avatar)
            charEmbed.description = description
            charEmbed.clear_fields()   
            paused = "Paused" in charDict and charDict["Paused"]
            charEmbed.title = f"{'[PAUSED] '* paused}{charDict['Name']} (Lv {charLevel}) - {charDict['CP']}/{cp_bound_array[role-1][1]} CP"
            
            
            notValidConsumables = ""
            consumesCount = collections.Counter(charDict['Consumables'].split(', '))
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
                for i in consumablesList:
                    itemFound = False
                    for jk, jv in consumesCount.items():
                        if i.strip() != "" and i.lower().replace(" ", "").strip() in jk.lower().replace(" ", ""):
                            if jv > 0 :
                                consumesCount[jk] -= 1
                                if jk in brought_consumables:
                                    brought_consumables[jk] += 1
                                else:
                                    brought_consumables[jk] = 1
                                
                                itemFound = True
                                break

                    if not itemFound:
                        notValidConsumables += f"{i.strip()}, "
                        

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


            
            attune_list = []
            if 'Attuned' in charDict:
                for attune_item in charDict['Attuned'].split(", "):
                    attune_list.append(attune_item.split(" [", 1)[0])
            
            
            miString = ""
            miArray = collections.Counter(charDict['Magic Items'].split(', '))
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
                            if jv > 0 :
                                miArray[jk] -= 1
                                if jk in brought_mits:
                                    brought_mits[jk] += 1
                                else:
                                    brought_mits[jk] = 1
                                
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
            else:
                rit_db_entries = [x["Name"] for x in list(db.rit.find({"Name": {"$in" : list(miArray.keys())}}))]
            
            for m,v in miArray.items():
                # mi was a non-con
                if m in rit_db_entries:
                    continue
                bolding = ""
                if m in attune_list:
                    bolding = "**"
                if "Predecessor" in charDict and m in charDict["Predecessor"]:
                    upgrade_names = charDict['Predecessor'][m]["Names"]
                    stage = charDict['Predecessor'][m]["Stage"]
                    m = m + f" ({upgrade_names[stage]})"
                
                miString += f"• {bolding}{m}{bolding}"
                if v == 1:
                    miString+="\n"
                else:
                    miString += f" x{v}\n"

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

    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        if payload.emoji.name == '❌':
            channel = self.bot.get_channel(payload.channel_id)
            user = self.bot.get_user(payload.user_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds)==0:
                return
            embed = message.embeds[0]
            if not embed.footer.text:
                return
            if not ("To view your character" in embed.footer.text or embed.footer.text == "Attuned magic items are bolded."):
                return
            if embed.author.name.split('#')[0] != user.name:
                return
            embed.set_footer(text="❌ Application Revoked")
            embed.clear_fields()
            embed.description = ""
            embed.set_thumbnail(url=None)
            await message.edit(embed = embed)
        
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
        authorCheck = None
        if mod_override:
            mod = "Mod Friend" in [role.name for role in author.roles]
            if ctx.message.mentions:
                authorCheck =ctx.message.mentions[0]
                mod=False
        statusEmoji = ""
        charDict, charEmbedmsg = await checkForChar(ctx, char, charEmbed, authorCheck = authorCheck, mod=mod)
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
                nick_string = f"• Goes By: **{charDict['Nickname']}**\n"
            alignment_string = "Alignment: Unknown\n"
            if "Alignment" in charDict and charDict['Alignment'] != "":
                alignment_string = f"Alignment: {charDict['Alignment']}\n"

            description = f"{nick_string}• {char_race}\n• {char_class}\n• {char_background}\n• {alignment_string}• One-shots Played: {charDict['Games']}\n"
            if 'Proficiency' in charDict:
                description +=  f"• Extra Training: {charDict['Proficiency']}\n"
            if 'NoodleTraining' in charDict:
                description +=  f"• Noodle Training: {charDict['NoodleTraining']}\n"
            if 'Event Token' in charDict and charDict['Event Token'] > 0:
                description +=  f"• Event Tokens: {charDict['Event Token']}\n"
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
            charEmbed.set_author(name=charDictAuthor, icon_url=charDictAuthor.display_avatar)
            charEmbed.description = description
            charEmbed.clear_fields()    
            
            paused = "Paused" in charDict and charDict["Paused"]
            charEmbed.title = f"{'[PAUSED] '*paused}{charDict['Name']} (Lv {charLevel}) - {charDict['CP']}/{cp_bound_array[role-1][1]} CP"
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

            if 'Max Stats' not in charDict:
                maxStatDict = charDict['Max Stats'] = {'STR': 20 ,'DEX': 20,'CON': 20, 'INT': 20, 'WIS': 20,'CHA': 20}
            else:
                maxStatDict = charDict['Max Stats']

            for sk in charDict['Max Stats'].keys():
                if charDict[sk] > charDict['Max Stats'][sk]:
                    charDict[sk] = charDict['Max Stats'][sk]
            
            specialCollection = db.special
            specialRecords = list(specialCollection.find())

            totalHPAdd = 0
            for s in specialRecords:
                                            
                                    
                if 'Attuned' in charDict:
                    if s['Type'] == "Attuned":
                        if s['Name'] in charDict[s['Type']]:
                            if 'HP' in s:
                                totalHPAdd += s['HP']

            # Check for stat increases in attuned magic items.
            if 'Attuned' in charDict:
                charEmbed.add_field(name='Attuned', value='• ' + charDict['Attuned'].replace(', ', '\n• '), inline=False)
                statBonusDict = { 'STR': 0 ,'DEX': 0,'CON': 0, 'INT': 0, 'WIS': 0,'CHA': 0}
                for a in charDict['Attuned'].split(', '):
                    if '[' in a and ']' in a:
                        statBonus = a[a.find("[")+1:a.find("]")] 
                        if '+' not in statBonus and '-' not in statBonus:
                            statSplit = statBonus.split(' ')
                            modStat = str(charDict[statSplit[0]]).replace(')', '').split(' (')[0]
                            if '[' in modStat and ']' in modStat:
                                oldStat = modStat[modStat.find("[")+1:modStat.find("]")] 
                                if '+' not in modStat and '-' not in modStat:
                                    modStat = modStat.split(' [')[0]
                                    if int(oldStat) > int(statSplit[1]):
                                        charDict[statSplit[0]] = f"{modStat} ({oldStat})"
                                else:
                                    modStat = modStat.split(' [')[0]
                                    if (int(modStat) + int(statBonusDict[statSplit[0]])) > int(statSplit[1]):
                                        charDict[statSplit[0]] = f"{modStat} (+{statBonusDict[statSplit[0]]})" 
                                    else:
                                        charDict[statSplit[0]] = f"{modStat} ({statSplit[1]})"

                            elif int(statSplit[1]) > int(modStat):
                                maxStatNum = statSplit[1]
                                if '(' in str(charDict[statSplit[0]]):
                                    maxStatNum = max(int(str((charDict[statSplit[0]])).replace(')', '').split(' (')[1]), int(statSplit[1]) )
                                charDict[statSplit[0]] = f"{modStat} ({maxStatNum})"

                        elif '+' in statBonus:
                            statBonusSplit = statBonus.split(';')
                            statSplit = statBonusSplit[0].split(' +')
                            if 'MAX' in statSplit[0]:
                                maxStat = statSplit[0][:-3]
                                statSplit[0] = statSplit[0].replace(maxStat, "")
                                maxStat = maxStat.split(" ")
                                maxStatDict[statSplit[0]] += int(statSplit[1])

                            modStat = str(charDict[statSplit[0]])
                            modStat = modStat.split(' (')[0]
                            statBonusDict[statSplit[0]] += int(statSplit[1])
                            statName = charDict[statSplit[0]]
                            maxStatBonus = []
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

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if infoRecords:
            charID = infoRecords['_id']
            data = {
                'Image': url
            }

            try:
                r = requests.head(url)
                # print(r)
                # print(r.headers)
                # print(r.status_code)
                # if r.status_code != requests.codes.ok:
                    # await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{commandPrefix}image "character name" URL```\n') 
                    # return
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
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command()
    async def pause(self,ctx,char):
        await self.pauseKernel(ctx, char, True)
        
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command()
    async def unpause(self,ctx,char):
        await self.pauseKernel(ctx, char, False)
    
    async def pauseKernel(self,ctx,char, target = False):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if infoRecords:
            charID = infoRecords['_id']
            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": {"Paused": target}})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await ctx.channel.send(content=f'I have {(not target)*"un"}paused the progress for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    async def reflavorKernel(self,ctx, char, rtype, new_flavor):
             
        if( len(new_flavor) > 20):
            await ctx.channel.send(content=f'The new {rtype.lower()} must be between 1 and 20 symbols.')
            return
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed()

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)
        if infoRecords:
            charID = infoRecords['_id']
            
            try:
                db.players.update_one({'_id': charID}, {"$set": {'Reflavor.'+rtype: new_flavor}})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try reflavoring your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the {rtype} for ***{infoRecords["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
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

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if infoRecords:
            charID = infoRecords['_id']
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
                await ctx.channel.send(content=f'I have updated the alignment for ***{infoRecords["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['rn'])
    async def rename(self,ctx, char, new_name = ""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        msg = self.name_check(new_name, author)
        if msg:
            await channel.send(msg)
            return
            
        charEmbed = discord.Embed()

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if infoRecords:
            query = new_name
            query = query.replace('(', '\\(')
            query = query.replace(')', '\\)')
            query = query.replace('.', '\\.')
            playersCollection = db.players
            userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' } }))

            if userRecords != list():
                await channel.send(f"\nYou already have a character by the name of ***{new_name}***! Please use a different name.")
                return
            charID = infoRecords['_id']
            data = {
                'Name': new_name
            }

            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await ctx.channel.send(content=f'I have updated the name for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
            
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['aka'])
    async def alias(self,ctx, char, new_name = ""):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        msg = self.name_check(new_name, author)
        if msg:
            await channel.send(msg)
            return
            
        charEmbed = discord.Embed()

        infoRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if infoRecords:
            charID = infoRecords['_id']
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
            
    def name_check(self, name, author):
        msg = ""
        # Name should be less then 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"

        # Reserved for regex, lets not use these for character names please
        invalidChars = ["[", "]", "?", "“","”", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|", "(",")" ]

        for i in invalidChars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"
        # if msg == "":
            # playersCollection = db.players
            # userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": name }))

            # if userRecords != list():
                # msg += f":warning: You already have a character by the name of ***{name}***! Please use a different name.\n"
        
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
        infoRecords, levelUpEmbedmsg = await checkForChar(ctx, char, levelUpEmbed)
        charClassChoice = ""
        if infoRecords:
            charID = infoRecords['_id']
            charDict = {}
            charName = infoRecords['Name']
            charClass = infoRecords['Class']
            cpSplit= infoRecords['CP']
            charLevel = infoRecords['Level']
            charStats = {'STR':infoRecords['STR'], 
                        'DEX':infoRecords['DEX'], 
                        'CON':infoRecords['CON'], 
                        'INT':infoRecords['INT'], 
                        'WIS':infoRecords['WIS'], 
                        'CHA':infoRecords['CHA']}
            charHP = infoRecords['HP']
            charFeats = infoRecords['Feats']
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
                
            if 'Free Spells' in infoRecords:
                freeSpells = infoRecords['Free Spells']

            if 'Death' in infoRecords.keys():
                await channel.send(f'You cannot level up a dead character. Use the following command to decide their fate:\n```yaml\n$death "{infoRecords["Name"]}"```')
                self.bot.get_command('levelup').reset_cooldown(ctx)
                return

            if charLevel > 19:
                await channel.send(f"***{infoRecords['Name']}*** is level 20 and cannot level up anymore.")
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
                levelUpEmbed.title = f"{charName}: Level Up! {charLevel} → {newCharLevel}"
                levelUpEmbed.description = f"{infoRecords['Race']}: {charClass}\n**STR**: {charStats['STR']} **DEX**: {charStats['DEX']} **CON**: {charStats['CON']} **INT**: {charStats['INT']} **WIS**: {charStats['WIS']} **CHA**: {charStats['CHA']}"
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
                            if int(infoRecords[statReq[0]]) < int(statReq[1]):
                                failMulticlassList.append(cRecord['Name'])
                                continue
                        elif '/' in cRecord['Multiclass']:
                            statReq[0] = statReq[0].split('/')
                            reqFufill = False
                            for s in statReq[0]:
                                if int(infoRecords[s]) >= int(statReq[1]):
                                    reqFufill = True
                            if not reqFufill:
                                failMulticlassList.append(cRecord['Name'])
                                continue

                        elif '+' in cRecord['Multiclass']:
                            statReq[0] = statReq[0].split('+')
                            reqFufill = True
                            for s in statReq[0]:
                                if int(infoRecords[s]) < int(statReq[1]):
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
                                    charClass = charClass.replace('(', f"{charLevel} (")
                                else:
                                    charClass += ' ' + str(charLevel)
                                
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
                                infoRecords["Free Spells"] = freeSpells

                            levelUpEmbed.description = f"{infoRecords['Race']}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"
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
                            levelUpEmbed.description = f"{infoRecords['Race']}: {charClass}\n**STR**:{charStats['STR']} **DEX**:{charStats['DEX']} **CON**:{charStats['CON']} **INT**:{charStats['INT']} **WIS**:{charStats['WIS']} **CHA**:{charStats['CHA']}"
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
                infoRecords['Level'] += 1
                charFeatsGained = ""
                charFeatsGainedStr = ""
                if featLevels != list():
                    featsChosen, statsFeats, charEmbedmsg = await characterCog.chooseFeat(ctx, infoRecords['Race'], charClass, subclasses, featLevels, levelUpEmbed, levelUpEmbedmsg, infoRecords, charFeats)
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
                if 'Free Spells' in infoRecords:
                    if freeSpells != ([0] * 9):
                        data['Free Spells'] = freeSpells

                if charFeatsGained != "":
                    if infoRecords['Feats'] == 'None':
                        data['Feats'] = charFeatsGained
                        infoRecords['Feats'] = charFeatsGained
                    elif infoRecords['Feats'] != None:
                        data['Feats'] = charFeats + ", " + charFeatsGained
                        infoRecords['Feats'] = charFeats + ", " + charFeatsGained

                statsCollection = db.stats
                statsRecord  = statsCollection.find_one({'Life': 1})
                
                if charFeatsGained != "":
                    feat_split = charFeatsGained.split(", ")
                    for feat_key in feat_split:
                        if not feat_key in statsRecord['Feats']:
                            statsRecord['Feats'][feat_key] = 1
                        else:
                            statsRecord['Feats'][feat_key] += 1

                            
                subclassCheckClass['Name'] = subclassCheckClass['Name'].split(' (')[0]
                if subclassCheckClass['Subclass'] != "" :
                    if subclassCheckClass['Subclass']  in statsRecord['Class'][subclassCheckClass['Name']]:
                        statsRecord['Class'][subclassCheckClass['Name']][subclassCheckClass['Subclass']] += 1
                    else:
                        statsRecord['Class'][subclassCheckClass['Name']][subclassCheckClass['Subclass']] = 1
                else:
                    if subclassCheckClass['Name'] in statsRecord['Class']:
                        statsRecord['Class'][subclassCheckClass['Name']]['Count'] += 1
                    else:
                        statsRecord['Class'][subclassCheckClass['Name']] = {'Count': 1}

                if 'Max Stats' not in infoRecords:
                    infoRecords['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
                
                data['Max Stats'] = infoRecords['Max Stats']

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
                            maxStatStr += f"\n{infoRecords['Name']}'s {sk} will not increase because their maximum is {data['Max Stats'][sk]}."
                infoRecords["Class"] = data["Class"]
                infoRecords['CON'] = charStats['CON']
                charHP = await characterCog.calcHP(ctx, subclasses, infoRecords, int(newCharLevel))
                data['HP'] = charHP
                tierNum += int(newCharLevel in [5, 11, 17, 20])
                levelUpEmbed.title = f'{charName} has leveled up to {newCharLevel}!\nCurrent CP: {totalCP}/{cp_bound_array[tierNum-1][1]} CP'
                levelUpEmbed.description = f"{infoRecords['Race']} {charClass}\n**STR**: {charStats['STR']} **DEX**: {charStats['DEX']} **CON**: {charStats['CON']} **INT**: {charStats['INT']} **WIS**: {charStats['WIS']} **CHA**: {charStats['CHA']}" + f"\n{charFeatsGainedStr}{maxStatStr}\n{specialStatStr}"
                if charClassChoice != "":
                    levelUpEmbed.description += f"{charName} has multiclassed into **{charClassChoice}!**"
                levelUpEmbed.set_footer(text= None)
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
                    statsCollection.update_one({'Life':1}, {"$set": statsRecord}, upsert=True)
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
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 2'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 2'))
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 5!")
            await author.remove_roles(roleRemove)
        if 'Elite Friend' not in roles and 'Journeyfriend' in roles and level > 10:
            roleName = 'Elite Friend'
            roleRemoveStr = 'Journeyfriend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 3'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 3'))
            await author.add_roles(levelRole, reason=f"***{author}***'s character ***{charName}*** is the first character who has reached level 11!")
            await author.remove_roles(roleRemove)
        if 'True Friend' not in roles and 'Elite Friend' in roles and level > 16:
            roleName = 'True Friend'
            roleRemoveStr = 'Elite Friend'
            levelRole = get(guild.roles, name = roleName)
            roleRemove = get(guild.roles, name = roleRemoveStr)
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 4'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 4'))
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 5'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 5'))
            
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
    async def attune(self,ctx, char, m):
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
            if "Attuned" not in charRecords:
                attuned = []
            else:
                attuned = charRecords['Attuned'].split(', ')


            charID = charRecords['_id']
            charRecordMagicItems = charRecords['Magic Items'].split(', ')
            if len(attuned) >= attuneLength:
                await channel.send(f"The maximum number of magic items you can attune to is {attuneLength}! You cannot attune to any more items!")
                return

            def apiEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:min(len(mList), 9)]) or (str(r.emoji) == '❌')) and u == author

            mList = []
            mString = ""
            numI = 0

            # Check if query is in character's Magic Item List. Limit is 8 to show if there are multiple matches.
            for k in charRecordMagicItems:
                if m.lower() in k.lower():
                    if k not in [a.split(' [')[0] for a in attuned]:
                        mList.append(k)
                        mString += f"{alphaEmojis[numI]} {k} \n"
                        numI += 1
                if numI > 8:
                    break

            # IF multiple matches, check which one the player meant.
            if (len(mList) > 1):
                charEmbed.add_field(name=f"There seems to be multiple results for **`{m}`**, please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.", value=mString, inline=False)
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
                m = mList[alphaEmojis.index(tReaction.emoji)]

            elif len(mList) == 1:
                m = mList[0]
            else:
                await channel.send(f"`{m}` isn't in {charRecords['Name']}'s inventory or is already attuned. Please try the command again.")
                return

            # Check if magic item's actually exist, and grab properties. (See if they're attuneable)
            mRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'mit', m)
            if not mRecord:
                mRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'rit', m)
                if not mRecord:
                    await channel.send(f"`{m}`belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic or Reward Item Table, what tier it is, and your spelling.\n")
                    return
                elif mRecord['Name'].lower() not in [x.lower() for x in charRecordMagicItems]:
                    await channel.send(f"You don't have the **{mRecord['Name']}** item in your inventory to attune to.")
                    return
            elif mRecord['Name'].lower() not in [x.lower() for x in charRecordMagicItems]:
                    await channel.send(f"You don't have the **{mRecord['Name']}** item in your inventory to attune to.")
                    return

            # Check if they are already attuned to the item.
            if mRecord['Name'] == 'Hammer of Thunderbolts':
                if 'Max Stats' not in charRecords:
                    charRecords['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
                # statSplit = MAX STAT +X
                statSplit = mRecord['Stat Bonuses'].split(' +')
                maxSplit = statSplit[0].split(' ')

                #Increase stats from Hammer and add to max stats. 
                if "MAX" in statSplit[0]:
                    charRecords['Max Stats'][maxSplit[1]] += int(statSplit[1]) 

                if 'Belt of' not in charRecords['Magic Items'] and 'Frost Giant Strength' not in charRecords['Magic Items'] and 'Gauntlets of Ogre Power' not in charRecords['Magic Items']:
                    await channel.send(f"`Hammer of Thunderbolts` requires you to have a `Belt of Giant Strength (any variety)` and `Gauntlets of Ogre Power` in your inventory in order to attune to it.")
                    return 

            if mRecord['Name'] in [a.split('[')[0].strip() for a in attuned]:
                await channel.send(f"You are already attuned to **{mRecord['Name']}**!")
                return
            elif 'Attunement' in mRecord:
                if "Predecessor" in mRecord and 'Stat Bonuses' in mRecord["Predecessor"]:
                    attuned.append(f"{mRecord['Name']} [{mRecord['Predecessor']['Stat Bonuses'][charRecords['Predecessor'][mRecord['Name']]['Stage']]}]")
                elif 'Stat Bonuses' in mRecord:
                    attuned.append(f"{mRecord['Name']} [{mRecord['Stat Bonuses']}]")
                else:
                    attuned.append(mRecord['Name'])
            else:
                await channel.send(f"`{m}` does not require attunement so there is no need to try to attune this item.")
                return
                        
            
            charRecords['Attuned'] = ', '.join(attuned)
            data = charRecords

            try:
                playersCollection = db.players
                playersCollection.update_one({'_id': charID}, {"$set": data})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
            else:
                await channel.send(f"You successfully attuned to **{mRecord['Name']}**!")

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['uatt', 'unatt'])
    async def unattune(self,ctx, char, m):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        charEmbed = discord.Embed ()
        charRecords, charEmbedmsg = await checkForChar(ctx, char, charEmbed)

        if charRecords:
            if 'Death' in charRecords:
                await channel.send(f"You cannot unattune from items with a dead character. Use the following command to decide their fate:\n```yaml\n$death \"{charRecords['Name']}\"```")
                return

            if "Attuned" not in charRecords:
                await channel.send(f"You have no attuned items to unattune from.")
                return
            else:
                attuned = charRecords['Attuned'].split(', ')

            charID = charRecords['_id']

            def apiEmbedCheck(r, u):
                sameMessage = False
                if charEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((r.emoji in alphaEmojis[:min(len(mList), 9)]) or (str(r.emoji) == '❌')) and u == author

            mList = []
            mString = ""
            numI = 0

            # Filter through attuned items, some attuned items have [STAT +X]; filter out those too and get raw.
            for k in charRecords['Attuned'].split(', '):
                if m.lower() in k.lower().split(' [')[0]:
                    mList.append(k.lower().split(' [')[0])
                    mString += f"{alphaEmojis[numI]} {k} \n"
                    numI += 1
                if numI > 8:
                    break

            if (len(mList) > 1):
                charEmbed.add_field(name=f"There seems to be multiple results for `{m}`, please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.", value=mString, inline=False)
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
                m = mList[alphaEmojis.index(tReaction.emoji)]

            elif len(mList) == 1:
                m = mList[0]
            else:
                await channel.send(f'`{m}` doesn\'t exist on the Magic Item Table! Check to see if it is a valid item and check your spelling.')
                return

            mRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'mit', m)
            if not mRecord:
                mRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg,'rit', m)
                if not mRecord:
                    await channel.send(f"`{m}` belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic or Reward Item Table, what tier it is, and your spelling.")
                    return

            if mRecord['Name'] not in [a.split(' [')[0] for a in attuned]:
                await channel.send(f"**{mRecord['Name']}** cannot be unattuned from because it is currently not attuned to you.")
                return
            else:
                if mRecord['Name'] == 'Hammer of Thunderbolts':
                    statSplit = mRecord['Stat Bonuses'].split(' +')
                    maxSplit = statSplit[0].split(' ')
                    if "MAX" in statSplit[0]:
                        charRecords['Max Stats'][maxSplit[1]] -= int(statSplit[1]) 
                
                try:
                    index = list([a.split("[")[0].strip() for a in attuned]).index(mRecord["Name"])
                    attuned.pop(index)
                except Exception as e:
                    pass
                
                charRecords['Attuned'] = ', '.join(attuned)

                try:
                    playersCollection = db.players
                    if attuned != list():
                        playersCollection.update_one({'_id': charID}, {"$set": charRecords})
                    else:
                        playersCollection.update_one({'_id': charID}, {"$unset": {"Attuned":1}})

                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    charEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
                else:
                    await channel.send(f"You successfully unattuned from **{mRecord['Name']}**!")
                    

    

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
        if rRecord:
            statsBonus = rRecord['Modifiers'].replace(" ", "").split(',')
            uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
            allStatsArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
            
            for s in statsBonus:
                
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
                    anyAmount = int(s[len(s)-1])
                    uniqueStatStr = ""
                    uniqueReacts = []

                    if 'ANY' in s:
                        uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

                    for u in range(0,len(uniqueArray)):
                        uniqueStatStr += f'{alphaEmojis[u]}: {uniqueArray[u]}\n'
                        uniqueReacts.append(alphaEmojis[u])

                    charEmbed.add_field(name=f"The {rRecord['Name']} race lets you choose **1** extra stats to increase by {anyAmount}. React below with the stat you would like to choose.", value=uniqueStatStr, inline=False)
                    if charEmbedmsg:
                        await charEmbedmsg.edit(embed=charEmbed)
                    else: 
                        charEmbedmsg = await channel.send(embed=charEmbed)
                    
                    choice = await disambiguate(len(uniqueArray), charEmbedmsg, author)
                    if choice is None:
                        await charEmbedmsg.edit(embed=None, content=f'Point buy timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None
                    elif choice == -1:
                        await charEmbedmsg.edit(embed=None, content=f'Point buy cancelled out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
                        return None, None 

                    charEmbed.clear_fields()
                    if 'AOU' in s:
                        statsArray[allStatsArray.index(uniqueArray.pop(choice))] += anyAmount
                    else:
                        statsArray[choice] += anyAmount
            return statsArray, charEmbedmsg

    async def chooseSubclass(self, ctx, subclassesList, charClass, charEmbed, charEmbedmsg):
        author = ctx.author
        channel = ctx.channel
        subclassString = ""
        for num in range(len(subclassesList)):
            subclassString += f'{alphaEmojis[num]}: {subclassesList[num]}\n'

        charEmbed.clear_fields()
        charEmbed.add_field(name=f"The {charClass} class allows you to pick a subclass at this level. React to the choices below to select your subclass.", value=subclassString, inline=False)
        if charEmbedmsg:
            await charEmbedmsg.edit(embed=charEmbed)
        else: 
            charEmbedmsg = await channel.send(embed=charEmbed)
            
        choice = await disambiguate(len(subclassesList), charEmbedmsg, author)
        if choice is None:
            await charEmbedmsg.edit(embed=None, content=f'Character creation timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
            return None, None
        elif choice == -1:
            await charEmbedmsg.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
            self.bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
            return None, None
        charEmbed.clear_fields()
        subclass = subclassesList[choice].strip()

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

        if 'Max Stats' not in charStats:
            charStats['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}

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
                        level_only = True
                        if 'Feat Restriction' not in feat and 'Race Restriction' not in feat and 'Class Restriction' not in feat and 'Stat Restriction' not in feat and (feat['Name'] not in charFeats) and 'Race Unavailable' not in feat and 'Require Spellcasting' not in feat and 'Level Restriction' not in feat:
                            featChoices.append(feat)

                        else:
                            if 'Feat Restriction' in feat and feat["Name"] not in charFeats:
                                featsList = [x.strip() for x in feat['Feat Restriction'].split(', ')]
                                level_only = False
                                for f in featsList:
                                    if f in charFeats or f in featsChosen:
                                        meetsRestriction = True
                                        
                            if 'Race Restriction' in feat:
                                featsList = [x.strip() for x in feat['Race Restriction'].split(', ')]

                                level_only = False
                                for f in featsList:
                                    if f in race:
                                        meetsRestriction = True

                            if 'Race Unavailable' in feat:
                                level_only = False
                                if race not in feat['Race Unavailable']:
                                    meetsRestriction = True
                            if 'Class Restriction' in feat:
                                featsList = [x.strip() for x in feat['Class Restriction'].split(', ')]
                                level_only = False
                                for c in cRecord:
                                    if (ctx.invoked_with.lower() == "create" 
                                        or ctx.invoked_with.lower() == "respec"
                                        or ctx.invoked_with.lower() == "rs" 
                                        or ctx.invoked_with.lower() == "racerespec"
                                        or ctx.invoked_with.lower() == "rr"):
                                        if c['Class']['Name'] in featsList or c['Subclass'] in featsList:
                                            meetsRestriction = True
                                    else:
                                        if c['Name'] in featsList or c['Subclass'] in featsList:
                                            meetsRestriction = True
                                            
                            if 'Stat Restriction' in feat:
                                level_only = False
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
                                level_only = False
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
                            if 'Level Restriction' in feat:
                                meetsRestriction = (level_only or meetsRestriction) and charStats["Level"] >= feat['Level Restriction']
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
                    charEmbed.set_footer(text=None)
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
                            charEmbed.set_footer(text= None)
                            charEmbed.add_field(name=f"The {featPicked['Name']} feat lets you choose between {featBonus}. React with [{alphaEmojis[0]}-{alphaEmojis[len(featBonusList)-1]}] below with the stat(s) you would like to choose.", value=featBonusString, inline=False)
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
    

async def setup(bot):
    await bot.add_cog(Character(bot))
