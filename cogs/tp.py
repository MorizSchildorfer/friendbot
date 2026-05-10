import discord
import asyncio
import requests
import re
from discord.utils import get        
from discord.ext import commands
from bfunc import db, commandPrefix, roleArray, traceBack, alphaEmojis, settingsRecord, liner_dic
from cogs.util import callAPI, checkForChar, uwuize
import traceback as traces
from random import *

class Tp(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    def is_log_channel():
        async def predicate(ctx):
            return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
        return commands.check(predicate)
       
    @commands.group(case_insensitive=True)
    @is_log_channel()
    async def tp(self, ctx):	
        pass

    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command **`{commandPrefix}{ctx.invoked_with}`** requires an additional keyword to the command or is invalid, please try again!')
            return
            
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
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
             
        if msg:
            if ctx.command.name == "find": #changed error message
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}tp find \"character name\" \"magic item\"```\n"
            elif ctx.command.name == "craft":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}tp craft \"character name\" \"magic item\"```\n"
            elif ctx.command.name == "meme":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}tp meme \"character name\" \"magic item\"```\n"
            elif ctx.command.name == "discard":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}tp discard \"character name\"```\n"
            elif ctx.command.name == "abandon":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}tp abandon \"character name\" tier```\n"

            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
    
    #@tp.command()
    async def createGroup(self, ctx, table, query, group):
    
        #channel and author of the original message creating this call
        channel = ctx.channel
        author = ctx.author
        
        collection = db[table]
        apiEmbedmsg = None
        apiEmbed = discord.Embed()
        #get the entire table if no query is given
        if query is None:
            return None, apiEmbed, apiEmbedmsg

        #if the query has no text, return nothing
        if query.strip() == "":
            return None, apiEmbed, apiEmbedmsg

        #restructure the query to be more regEx friendly
        query = query.strip()
        query = query.replace('(', '\\(')
        query = query.replace(')', '\\)')
        query = query.replace('+', '\\+')
        
        #search through the table for an element were the Name or Grouped property contain the query
        filterDic = {"Name": {
                            "$regex": query,
                            #make the check case-insensitively
                            "$options": "i"
                          }
                        }
        records = list(collection.find(filterDic))
        
        #restore the original query
        query = query.replace("\\", "")
        #sort elements by either the name, or the first element of the name list in case it is a list
        def sortingEntryAndList(elem):
            if(isinstance(elem['Name'],list)): 
                return elem['Name'][0] 
            else:  
                return elem['Name']
        
        remove_grouper = [] #track all elements that need to be removes since they act as representative for a group of items

        #for every search result check if it contains a group and create entries for each group element if it does
        for entry in records:
            # if the element is part of a group
            if("Grouped" in entry):
                # remove it later
                remove_grouper.append(entry)
        # remove all group representatives
        for group_to_remove in remove_grouper:
            records.remove(group_to_remove)
        
        #sort all items alphabetically 
        records = sorted(records, key = sortingEntryAndList)    
        
        #if no elements are left, return nothing
        if records == list():
            return None, apiEmbed, apiEmbedmsg
        else:
            try:
                latest=" Go"
                latest1=""
                latest2=""
                latest3=""
                #create a string to provide information about the items to the user
                infoString = ""
                collapseList=[]
                for rec in records:
                    infoString = f"{rec['Name']} (Tier {rec['Tier']})**\n"
                    def apiEmbedCheck(r, u):
                        sameMessage = False
                        if apiEmbedmsg.id == r.message.id:
                            sameMessage = True
                        return ((str(r.emoji) == '✅') or (str(r.emoji) == '❌') or (str(r.emoji) == '⛔')) and u == author
                    #inform the user of the current information and ask for their selection of an item               
                    apiEmbed.add_field(name=f"Latest Change", value=latest, inline=False)
                    apiEmbed.add_field(name=f"Select which one to collapse.", value=infoString, inline=False)     

                    if not apiEmbedmsg or apiEmbedmsg == "Fail":
                        apiEmbedmsg = await channel.send(embed=apiEmbed)
                    else:
                        await apiEmbedmsg.edit(embed=apiEmbed)

                    await apiEmbedmsg.add_reaction('✅')
                    await apiEmbedmsg.add_reaction('❌')
                    await apiEmbedmsg.add_reaction('⛔')
                
                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
                    except asyncio.TimeoutError:
                        #stop if no response was given within the timeframe and reenable the command
                        await apiEmbedmsg.delete()
                        await channel.send('Timed out! Try using the command again.')
                        ctx.command.reset_cooldown(ctx)
                        return None, apiEmbed, "Fail"
                    else:
                        latest3 = latest2
                        latest2 = latest1
                        latest1 = rec["Name"]+ ": "+tReaction.emoji+"\n"
                        latest=latest3+latest2+latest1
                        
                        #stop if the cancel emoji was given and reenable the command
                        if tReaction.emoji == '❌':
                            pass
                        elif tReaction.emoji == '✅':
                            collapseList.append(rec)
                        else:
                            tpEmbedmsg = await channel.send(embed=None, content=f"Grouping process cancelled.")
                            return
                    #return the selected item indexed by the emoji given by the user
                    apiEmbed.clear_fields()
                    await apiEmbedmsg.clear_reactions()
                name_list = list([x["Name"] for x in collapseList])
                charDict = collapseList[0].copy()
                charDict["Name"] = name_list
                charDict["Grouped"] = group
                charDict.pop("_id")
                collection.insert_one(charDict)
                for entry in collapseList:
                    collection.delete_one({'_id': entry['_id']})
                tpEmbedmsg = await channel.send(embed=None, content=f"Grouping process finished. These items have been grouped.\n"+"\n".join(name_list))
                return
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                traces.print_exc()
                tpEmbedmsg = await channel.send(embed=None, content=f"Uh oh, looks like something went wrong. Please try again using the same command.")

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def upgrade(self, ctx , charName, mItem):

        channel = ctx.channel
        author = ctx.author
        tpEmbed = discord.Embed()
        #this variable is never used
        tpCog = self.bot.get_cog('Tp')
        #find a character matching with charName using the function in bfunc
        charRecords, tpEmbedmsg = await checkForChar(ctx, charName, tpEmbed)

        if charRecords:
            #functions to make sure that only the intended user can respond
            def tpEmbedCheck(r, u):
                sameMessage = False
                if tpEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author and sameMessage           
            # calculate the tier of the character to limit which items they can purchase

            cLevel = charRecords["Level"]
            tier = 5
            if(cLevel < 5):
                tier= 1
            elif(cLevel < 11):
                tier= 2
            elif(cLevel < 17):
                tier= 3
            elif(cLevel < 20):
                tier= 4
            #make the call to the bfunc function to retrieve an item matching with mItem
            mRecord, tpEmbed, tpEmbedmsg = await callAPI(ctx, tpEmbed, tpEmbedmsg, 'mit', mItem,  tier=tier) 
            #if an item was found
            if mRecord:
                
                # check if the requested item is already in the inventory
                if("Predecessor" not in mRecord ): 
                    await channel.send(f"**{mRecord['Name']}** is not upgradable.")
                    ctx.command.reset_cooldown(ctx)
                    return 
                # check if the requested item is already in the inventory
                elif("Predecessor" not in charRecords or mRecord['Name'] not in charRecords["Predecessor"].keys()): 
                    await channel.send(f"You do not have **{mRecord['Name']}**.")
                    ctx.command.reset_cooldown(ctx)
                    return 
                upgrade_stage = charRecords["Predecessor"][mRecord['Name']]["Stage"]
                if(upgrade_stage + 1 >= len(charRecords["Predecessor"][mRecord['Name']]["Names"])): 
                    await channel.send(f"**{mRecord['Name']}** is already at its highest stage.")
                    ctx.command.reset_cooldown(ctx)
                    return 
                # get the tier of the item
                tierNum = mRecord['Predecessor']["Tiers"][upgrade_stage]
                

                tpBank = [0,0,0,0,0]
                tpBankString = ""
                #grab the available TP of the character
                for x in range(1,6):
                    if f'T{x} TP' in charRecords:
                      tpBank[x-1] = (float(charRecords[f'T{x} TP']))
                      tpBankString += f"{tpBank[x-1]} T{x} TP, " 
                tpNeeded = float(mRecord['Predecessor']["Costs"][upgrade_stage])
                tpNeeded_copy = tpNeeded
                used_tp = {}
                for tp in range (int(tierNum) - 1, 5):
                    if tpBank[tp] > 0 and tpNeeded > 0:
                        tp += 1
                        tp_reduction = min(charRecords[f"T{tp} TP"],  tpNeeded)
                        charRecords[f"T{tp} TP"] -= tp_reduction
                        tpNeeded -= tp_reduction
                        used_tp[f"T{tp} TP"] = tp_reduction

                # display the cost of the item to the user
                tpEmbed.title = f"Upgrading a Magic Item: {charRecords['Name']}"
                
                # if the user doesnt have the resources for the purchases, inform them and cancel
                if tpNeeded > 0:
                    await channel.send(f"You do not have enough Tier {tierNum} TP or higher to upgrade **{mRecord['Name']}**!")
                    ctx.command.reset_cooldown(ctx)
                    return

                newTP = f"Complete! :tada:"
                used_tp_text = ', '.join([f'{charRecords[tp]} {tp}' for tp in used_tp.keys()])
                tpEmbed.description = f"Are you sure you want to upgrade **{mRecord['Name']} ({mRecord['Predecessor']['Names'][upgrade_stage]})** to **{mRecord['Name']} ({mRecord['Predecessor']['Names'][upgrade_stage +1]})** for **{tpNeeded_copy} TP**?\n\nLeftover TP: {used_tp_text}\n\n✅: Yes\n\n❌: Cancel"


                tpEmbed.set_footer(text=None)
                if tpEmbedmsg:
                    await tpEmbedmsg.edit(embed=tpEmbed)
                else:
                    tpEmbedmsg = await channel.send(embed=tpEmbed)
                await tpEmbedmsg.add_reaction('✅')
                await tpEmbedmsg.add_reaction('❌')
                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=tpEmbedCheck , timeout=60)
                except asyncio.TimeoutError:
                    await tpEmbedmsg.delete()
                    await channel.send(f'TP cancelled. Try again using the same command!')
                    ctx.command.reset_cooldown(ctx)
                    return
                else:
                    await tpEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await tpEmbedmsg.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                        await tpEmbedmsg.clear_reactions()
                        ctx.command.reset_cooldown(ctx)
                        return
                    elif tReaction.emoji == '✅':
                        tpEmbed.clear_fields()
                        try:
                            playersCollection = db.players
                            setData = {"HP" : charRecords["HP"]}
                            incData = {f'Predecessor.{mRecord["Name"]}.Stage': 1}
                            statSplit = None
                            unsetTP = False
                            # For the stat books, this will increase the characters stats permanently here.
                            if 'Attunement' not in mRecord and 'Stat Bonuses' in mRecord["Predecessor"]:
                                if 'Max Stats' not in charRecords:
                                    charRecords['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}

                                # statSplit = MAX STAT +X
                                statSplit = mRecord["Predecessor"]['Stat Bonuses'][upgrade_stage+1].split(' +')
                                oldStatBonus = int(mRecord["Predecessor"]['Stat Bonuses'][upgrade_stage].split(' +')[1])
                                maxSplit = statSplit[0].split(' ')
                                oldStat = charRecords[maxSplit[1]]
                                #Increase stats from Manual/Tome and add to max stats. 
                                if "MAX" in statSplit[0]:
                                    charRecords[maxSplit[1]] += int(statSplit[1]) -  oldStatBonus
                                    charRecords['Max Stats'][maxSplit[1]] += int(statSplit[1]) - oldStatBonus

                                setData[maxSplit[1]] = int(charRecords[maxSplit[1]])
                                setData['Max Stats'] = charRecords['Max Stats']                           

                                # If the stat increased was con, recalc HP
                                # The old CON is subtracted, and new CON is added.
                                # If the player can't destroy magic items, this is done here, otherwise... it will need to be done in $info.
                                if 'CON' in maxSplit[1]:
                                    charRecords['HP'] -= ((int(oldStat) - 10) // 2) * charRecords['Level']
                                    charRecords['HP'] += ((int(charRecords['CON']) - 10) // 2) * charRecords['Level']
                                    setData['HP'] = charRecords['HP']
                            elif 'Attuned' in charRecords  and 'Attunement' in mRecord and 'Stat Bonuses' in mRecord["Predecessor"]:
                                attunements = charRecords['Attuned'].split(", ")
                                # Find if the item is currently attuned to inorder to update the stat bonus
                                try:
                                    index = list([a.split("[")[0].strip() for a in attunements]).index(mRecord["Name"])
                                    attunements[index] = f"{mRecord['Name']} [{mRecord['Predecessor']['Stat Bonuses'][upgrade_stage+1]}]"
                                    setData["Attuned"] = ", ".join(attunements)
                                except Exception as e:
                                    pass
                                
                            unsetData = {"Dummy Entry" : 1}
                            for tp, value in used_tp.items():
                                if charRecords[tp] == 0:
                                    unsetData[tp] = 1
                                else:
                                    setData[tp] = charRecords[tp]
                                incData[f"Item Spend.{mRecord['Name']}.{tp}"] = value
                            playersCollection.update_one({'_id': charRecords['_id']}, {"$set": setData, "$unset": unsetData, "$inc" : incData})
                            
                        except Exception as e:
                            print ('MONGO ERROR: ' + str(e))
                            tpEmbedmsg = await channel.send(embed=None, content=f"Uh oh, looks like something went wrong. Try again using the same command!")
                            ctx.command.reset_cooldown(ctx)
                        else:
                            tpEmbed.description = f"You have upgraded **{mRecord['Name']}** for {tpNeeded_copy} TP! :tada:\n\nCurrent TP: {used_tp_text}\n\n"
                            
                            await tpEmbedmsg.edit(embed=tpEmbed)
                            ctx.command.reset_cooldown(ctx)

            else:
                await channel.send(f'''**{mItem}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic Item Table, what tier it is, and your spelling.''')
                ctx.command.reset_cooldown(ctx)
                return
    
    async def acquireKernel(self, ctx , charName, mItem, source, sourcePast, sourceString, oneLiner):

        channel = ctx.channel
        author = ctx.author
        tpEmbed = discord.Embed()
        #this variable is never used
        tpCog = self.bot.get_cog('Tp')
        #find a character matching with charName using the function in bfunc
        charRecords, tpEmbedmsg = await checkForChar(ctx, charName, tpEmbed)
            
        if charRecords:
            #functions to make sure that only the intended user can respond
            def tpChoiceEmbedCheck(r, u):
                sameMessage = False
                if tpEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((str(r.emoji) == '1️⃣' and tpNeeded <= 0) or (charRecords['GP'] >= gpNeeded and str(r.emoji) == '2️⃣') or (str(r.emoji) == '❌')) and u == author and sameMessage
            def tpEmbedCheck(r, u):
                sameMessage = False
                if tpEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author and sameMessage           
            # calculate the tier of the character to limit which items they can purchase

            cLevel = charRecords["Level"]
            tier = 5
            if(cLevel < 5):
                tier= 1
            elif(cLevel < 11):
                tier= 2
            elif(cLevel < 17):
                tier= 3
            elif(cLevel < 20):
                tier= 4
            #make the call to the bfunc function to retrieve an item matching with mItem
            mRecord, tpEmbed, tpEmbedmsg = await callAPI(ctx, tpEmbed, tpEmbedmsg, 'mit', mItem,  tier=tier) 
            #if an item was found
            if mRecord:
                """
                Alright boyo, here is my masterstroke in this madness
                Since callAPI we generated the subitems of a grouping as entries and Grouped property has been maintained for them
                we can now use this to indentify if an item was part of a bigger group
                The Grouped property for characters acts as a tracker of which item the character worked/is working forward in the group
                If the user does not have the property, we can thus skip since they could not have gotten the item
                """
                if("Grouped" in mRecord and "Grouped" in charRecords):
                    """
                    We can now check if the group name is in any of the Groups that character has interacted with
                    We can then check for every element in Grouped if the currently requested item is in any of them
                    The last check is to make sure that all other items beside the initially selected one get blocked
                    
                    if(any(mRecord["Grouped"] in group_item_pair for group_item_pair in charRecords["Grouped"])):
                    """
                    for groupName in charRecords["Grouped"]:
                        group_name_split = groupName.split(":")
                        if(mRecord["Grouped"] == group_name_split[0].strip() and mRecord["Name"] != group_name_split[1].strip()):
                            #inform the user that they already have an item from this group
                            await channel.send(f"**{mRecord['Name']}** is a variant of the **{mRecord['Grouped']}** item and ***{charRecords['Name']}*** already owns a variant of the that item.")
                            ctx.command.reset_cooldown(ctx)
                            return 
                character_item_list = [name.strip() for name in charRecords['Magic Items'].split(",")]
                    
                # check if the requested item is already in the inventory
                if(mRecord['Name'] in character_item_list): 
                    await channel.send(f"You already have **{mRecord['Name']}** and cannot spend TP or GP on another one.")
                    ctx.command.reset_cooldown(ctx)
                    return 
                
                
                indefinite = "a"
                if mRecord['Name'][0].lower() in "aeiou":
                    indefinite = "an"
                    
                # get the tier of the item
                tierNum = mRecord['Tier']
                # get the gold cost of the item
                gpNeeded = mRecord['GP']
                #get the list of all items currently being worked towards

                tpBank = [0,0,0,0,0]
                tpBankString = ""
                #grab the available TP of the character
                for x in range(1,6):
                    if f'T{x} TP' in charRecords:
                      tpBank[x-1] = (float(charRecords[f'T{x} TP']))
                      tpBankString += f"{tpBank[x-1]} T{x} TP, " 

                tpNeeded = float(mRecord['TP'])
                tpNeeded_copy = tpNeeded
                used_tp = {}
                for tp in range (int(tierNum) - 1, 5):
                    if tpBank[tp] > 0 and tpNeeded > 0:
                        tp += 1
                        tp_reduction = min(charRecords[f"T{tp} TP"],  tpNeeded)
                        charRecords[f"T{tp} TP"] -= tp_reduction
                        tpNeeded -= tp_reduction
                        used_tp[f"T{tp} TP"] = tp_reduction

                # display the cost of the item to the user
                tpEmbed.title = f"{sourceString}: {charRecords['Name']}"
                
                # if the user doesnt have the resources for the purchases, inform them and cancel
                if tpNeeded > 0 and float(charRecords['GP']) < gpNeeded:
                    await channel.send(f"You do not have enough Tier {tierNum} TP or higher, or GP, to {source} **{mRecord['Name']}**!")

                    ctx.command.reset_cooldown(ctx)
                    return
                  
                # get confirmation from the user for the purchase
                elif tpNeeded > 0:
                    tpEmbed.description = f"Do you want to {source} **{mRecord['Name']}** with TP or GP?\n\n You have don't have enough TP and **{charRecords[f'GP']} GP**.\n\n1️⃣: ~~{mRecord['TP']} TP (Treasure Points)~~ You do not have enough TP.\n2️⃣: {mRecord['GP']} GP (gold pieces)\n\n❌: Cancel"                 
                    

                elif float(charRecords['GP']) < gpNeeded:
                    tpEmbed.description = f"Do you want to {source} **{mRecord['Name']}** with TP or GP?\n\n You have **{tpBankString}** and **{charRecords[f'GP']} GP**.\n\n1️⃣: {mRecord['TP']} TP (Treasure Points)\n2️⃣: ~~{mRecord['GP']} GP (gold pieces)~~ You do not have enough GP.\n\n❌: Cancel"                 

                else:
                    tpEmbed.description = f"Do you want to {source} **{mRecord['Name']}** with TP or GP?\n\n You have **{tpBankString}** and **{charRecords[f'GP']} GP**.\n\n1️⃣: {mRecord['TP']} TP (Treasure Points)\n2️⃣: {mRecord['GP']} GP (gold pieces)\n\n❌: Cancel"                 
                
                if tpEmbedmsg:
                    await tpEmbedmsg.edit(embed=tpEmbed)
                else:
                    tpEmbedmsg = await channel.send(embed=tpEmbed)
                # get choice from the user
                if tpNeeded <= 0:
                    await tpEmbedmsg.add_reaction('1️⃣')
                if float(charRecords['GP']) >= gpNeeded:
                    await tpEmbedmsg.add_reaction('2️⃣')
                await tpEmbedmsg.add_reaction('❌')
                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=tpChoiceEmbedCheck , timeout=60)
                except asyncio.TimeoutError:
                    #cancel if the user didnt respond within the timeframe
                    await tpEmbedmsg.delete()
                    await channel.send(f'TP cancelled. Try again using the same command!')
                    ctx.command.reset_cooldown(ctx)
                    return
                else:
                    await tpEmbedmsg.clear_reactions()
                    newGP = ""
                    newTP = ""
                    refundTP = 0.0
                    #cancel if the user decided to cancel the purchase
                    if tReaction.emoji == '❌':
                        await tpEmbedmsg.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                        await tpEmbedmsg.clear_reactions()
                        ctx.command.reset_cooldown(ctx)
                        return
                    #refund the TP in the item if the user decides to purchase with gold
                    elif tReaction.emoji == '2️⃣':
                        newGP = round(charRecords['GP'] - gpNeeded,2)
                        #search for the item in the items currently worked towards

                        tpEmbed.description = f"Are you sure you want to {source} **{mRecord['Name']}** for **{mRecord['GP']} GP**?\n\nCurrent GP: {charRecords['GP']}\nNew GP: {newGP} GP\n\n✅: Yes\n\n❌: Cancel"


                    # If user decides to buy item with TP:
                    elif tReaction.emoji == '1️⃣':
                        mIndex = 0
                        
                        newTP = f"Complete! :tada:"
                        used_tp_text = ', '.join([f'{charRecords[tp]} {tp}' for tp in used_tp.keys()])
                                
                        tpEmbed.description = f"Are you sure you want to {source} **{mRecord['Name']}** for **{mRecord['TP']} TP**?\n\nLeftover TP: {used_tp_text}\n\n✅: Yes\n\n❌: Cancel"


                    # If not complete, leave in current items, otherwise add to magic item list / consuambles
                    if charRecords['Magic Items'] == "None":
                        charRecords['Magic Items'] = mRecord['Name']
                    else:
                        newMagicItems = charRecords['Magic Items'].split(', ')
                        newMagicItems.append(mRecord['Name'])
                        newMagicItems.sort()
                        charRecords['Magic Items'] = ', '.join(newMagicItems)
                    if("Predecessor" not in charRecords):
                        charRecords["Predecessor"] = {}
                    if("Predecessor" in mRecord and mRecord["Name"] not in charRecords["Predecessor"]):
                        charRecords["Predecessor"][mRecord["Name"]] ={"Names" : mRecord["Predecessor"]["Names"], "Stage" : 0}
                    tpEmbed.set_footer(text=None)
                    await tpEmbedmsg.edit(embed=tpEmbed)
                    await tpEmbedmsg.add_reaction('✅')
                    await tpEmbedmsg.add_reaction('❌')
                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=tpEmbedCheck , timeout=60)
                    except asyncio.TimeoutError:
                        await tpEmbedmsg.delete()
                        await channel.send(f'TP cancelled. Try again using the same command!')
                        ctx.command.reset_cooldown(ctx)
                        return
                    else:
                        await tpEmbedmsg.clear_reactions()
                        if tReaction.emoji == '❌':
                            await tpEmbedmsg.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                            await tpEmbedmsg.clear_reactions()
                            ctx.command.reset_cooldown(ctx)
                            return
                        elif tReaction.emoji == '✅':
                            tpEmbed.clear_fields()
                            try:
                                playersCollection = db.players
                                if("Grouped" not in charRecords):
                                    charRecords["Grouped"] = []
                                if("Grouped" in mRecord and mRecord["Grouped"]+" : "+mRecord["Name"] not in charRecords["Grouped"]):
                                    charRecords["Grouped"].append(mRecord["Grouped"]+" : "+mRecord["Name"])
                                
                                
                                setData = {"Magic Items":charRecords['Magic Items'], "Grouped":charRecords['Grouped'], "Predecessor":charRecords['Predecessor']}
                                statSplit = None
                                unsetTP = False
                                
                                statsAffected = 'Stat Bonuses' in mRecord or ("Predecessor" in mRecord and 'Stat Bonuses' in mRecord["Predecessor"])
                                
                                # For the stat books, this will increase the characters stats permanently here.
                                if 'Attunement' not in mRecord and statsAffected:
                                    if 'Max Stats' not in charRecords:
                                        charRecords['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
                                    
                                    # statSplit = MAX STAT +X
                                    if "Predecessor" in mRecord:
                                        statSplit = mRecord["Predecessor"]['Stat Bonuses'][0].split(' +')
                                    else:
                                        statSplit = mRecord['Stat Bonuses'].split(' +')
                                        
                                    maxSplit = statSplit[0].split(' ')
                                    oldStat = charRecords[maxSplit[1]]

                                    #Increase stats from Manual/Tome and add to max stats. 
                                    if "MAX" in statSplit[0]:
                                        charRecords[maxSplit[1]] += int(statSplit[1]) 
                                        charRecords['Max Stats'][maxSplit[1]] += int(statSplit[1]) 

                                    setData[maxSplit[1]] = int(charRecords[maxSplit[1]])
                                    setData['Max Stats'] = charRecords['Max Stats']                           

                                    # If the stat increased was con, recalc HP
                                    # The old CON is subtracted, and new CON is added.
                                    # If the player can't destroy magic items, this is done here, otherwise... it will need to be done in $info.
                                    if 'CON' in maxSplit[1]:
                                        charRecords['HP'] -= ((int(oldStat) - 10) // 2) * charRecords['Level']
                                        charRecords['HP'] += ((int(charRecords['CON']) - 10) // 2) * charRecords['Level']
                                        setData['HP'] = charRecords['HP']
                                unsetData = {"Dummy Entry" : 1}
                            
                                
                                if newTP != "":
                                
                                    for tp, value in used_tp.items():
                                        if charRecords[tp] == 0:
                                            unsetData[tp] = 1
                                        else:
                                            setData[tp] = charRecords[tp]
                                        setData[f"Item Spend.{mRecord['Name']}.{tp}"] = value
                                
                                
                                elif newGP != "":
                                    setData['GP'] = newGP
                                    setData[f"Item Spend.{mRecord['Name']}.GP"] = gpNeeded

                                playersCollection.update_one({'_id': charRecords['_id']}, {"$set": setData, "$unset": unsetData})
                            
                                db.stats.update_one({"Life": 1}, {"$inc" : {"Magic Items."+mRecord['Name']: 1}})
                                
                            except Exception as e:
                                await traceBack(ctx, e)
                                ctx.command.reset_cooldown(ctx)
                                print ('MONGO ERROR: ' + str(e))
                                tpEmbedmsg = await channel.send(embed=None, content=f"Uh oh, looks like something went wrong. Try again using the same command!")
                            else:
                                outputLiner = oneLiner.replace("<magic item>", str(mRecord['Name'])).replace(f"a {str(mRecord['Name'])}", f"{indefinite} {str(mRecord['Name'])}")
                                if newTP != "":
                                    tpEmbed.description = f"{outputLiner}\n\nYou have {sourcePast} **{mRecord['Name']}** for {mRecord['TP']} TP! :tada:\n\nLeftover TP: {used_tp_text}\n\n"
                                elif newGP != "":
                                    tpEmbed.description = f"{outputLiner}\n\nYou have {sourcePast} **{mRecord['Name']}** for {mRecord['GP']} GP! :tada:\n\nCurrent GP: {newGP}\n"

                                await tpEmbedmsg.edit(embed=tpEmbed)
                                ctx.command.reset_cooldown(ctx)

            else:
                await channel.send(f'''**{mItem}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic Item Table, what tier it is, and your spelling.''')
                ctx.command.reset_cooldown(ctx)
                return


    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def find(self, ctx , charName, mItem): 
        # Assigns 4 variables that are then passed to the buy command. These variables are used to change the text to a one-liner system.
        source = "find"
        sourceString = "Find a Magic Item"
        sourcePast = "found"
        oneLiner = sample(liner_dic["Find"], 1)[0] # Random one-liner assigned from the corresponding collection
        await self.acquireKernel(ctx, charName, mItem, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def craft(self, ctx , charName, mItem):

        source = "craft"
        sourceString = "Craft a Magic Item"
        sourcePast = "crafted"
        oneLiner = sample(liner_dic["Craft"], 1)[0]
        await self.acquireKernel(ctx, charName, mItem, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def meme(self, ctx , charName, mItem):

        source = "meme"
        sourceString = "Meme a Magic Item"
        sourcePast = "memed"
        oneLiner = sample(liner_dic["Meme"], 1)[0]
        await self.acquireKernel(ctx, charName, mItem, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def buy(self, ctx, charName = "", mItem = ""): # prints the format for the replacement commands.
        if mItem == "":
            mItem = "magic item"
        if charName == "":
            charName = "character name"
        
        msg = f"This command has been reworked and will be removed in the future. Please use one of the formats below: \n```yaml\n{commandPrefix}tp find \"{charName}\" \"{mItem}\"\n{commandPrefix}tp craft \"{charName}\" \"{mItem}\"\n{commandPrefix}tp meme \"{charName}\" \"{mItem}\"```\n"
        ctx.command.reset_cooldown(ctx)
        await ctx.channel.send(msg)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def abandon(self, ctx , charName, tierNum):
        channel = ctx.channel
        author = ctx.author
        tpEmbed = discord.Embed()
        tpCog = self.bot.get_cog('Tp')


        if tierNum not in ('1','2','3','4', '5') and tierNum.lower() not in [r.lower() for r in roleArray]:
            await channel.send(f"**{tierNum}** is not a valid tier. Please try again with **Junior** or **1**, **Journey** or **2**, **Elite** or **3**, **True** or **4**, or **Ascended** or **5**.")
            ctx.command.reset_cooldown(ctx)
            return

        charRecords, tpEmbedmsg = await checkForChar(ctx, charName, tpEmbed)

        if charRecords:
            def tpEmbedCheck(r, u):
                sameMessage = False
                if tpEmbedmsg.id == r.message.id:
                    sameMessage = True
                return ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author and sameMessage
            
            role = 0
            if tierNum.isdigit():
                role = int(tierNum)
            else:
                role = roleArray.index(tierNum.capitalize())

            if f"T{role} TP" not in charRecords:
                await channel.send(f"You do not have T{role} TP to abandon.")
                ctx.command.reset_cooldown(ctx)
                return
            

            tpEmbed.title = f"Abandoning TP: {charRecords['Name']}"  
            tpEmbed.description = f"Are you sure you want to abandon your Tier {role} TP?\n\nYou currently have {charRecords[f'T{role} TP']} Tier {role} TP.\n\n**Note: this action is permanent and cannot be reversed.**\n\n✅: Yes\n\n❌: Cancel"
            tpEmbed.set_footer(text=None)
            if tpEmbedmsg:
                await tpEmbedmsg.edit(embed=tpEmbed)
            else:
                tpEmbedmsg = await channel.send(embed=tpEmbed)
            await tpEmbedmsg.add_reaction('✅')
            await tpEmbedmsg.add_reaction('❌')
            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=tpEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await tpEmbedmsg.delete()
                await channel.send(f'TP cancelled. Try again using the same command!')
                ctx.command.reset_cooldown(ctx)
                return
            else:
                await tpEmbedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await tpEmbedmsg.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                    await tpEmbedmsg.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return
                elif tReaction.emoji == '✅': 
                    tpEmbed.clear_fields()
                    try:
                        playersCollection = db.players
                        playersCollection.update_one({'_id': charRecords['_id']}, {"$unset": {f"T{role} TP":1}})
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        tpEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Try again using the same command!")
                    else:
                        tpEmbed.description = f"You have abandoned {charRecords[f'T{role} TP']} T{role} TP!"
                        await tpEmbedmsg.edit(embed=tpEmbed)
                        ctx.command.reset_cooldown(ctx)


async def setup(bot):
    await bot.add_cog(Tp(bot))