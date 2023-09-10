import discord
import asyncio
import re
import pytz
from discord.utils import get        
from discord.ext import commands  
from discord.errors import Forbidden
from datetime import datetime, timezone,timedelta
from bfunc import db, traceBack, roleArray, settingsRecord, timezoneVar
from cogs.util import calculateTreasure, callAPI, timeConversion, noodleRoleArray, uwuize
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError




guild_drive_costs = [4, 4, 6, 9, 13, 13]

async def generateLog(self, ctx, num : int, sessionInfo=None, guildDBEntriesDic=None, characterDBentries=None, userDBEntriesDic=None, ):
    logData = db.logdata
    if sessionInfo == None:
        sessionInfo = logData.find_one({"Log ID": int(num)})
    
    channel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"]) 
    editMessage = await channel.fetch_message(num)

    if not editMessage or editMessage.author != self.bot.user:
        print("Invalid Message")
        return None
        
    # get the collections of characters
    playersCollection = db.players
    guildCollection = db.guilds
    statsCollection = db.stats
    usersCollection = db.users

    sessionLogEmbed = editMessage.embeds[0]
    summaryIndex = sessionLogEmbed.description.find('Summary**')
    description = sessionLogEmbed.description[summaryIndex:]+"\n"
    
    role = sessionInfo["Role"]
    game = sessionInfo["Game"]
    start = sessionInfo["Start"] 
    end = sessionInfo["End"] 
    tierNum = sessionInfo["Tier"]
    
    guilds = sessionInfo["Guilds"]
    
    players = sessionInfo["Players"] 
    #dictionary indexed by user id
    # {cp, magic items, consumables, inventory, partial, status, user id, character id, character name, character level, character cp, double rewards, guild, }
    
    dm = sessionInfo["DM"] 
    # {cp, magic items, consumables, inventory, partial, status, user id, character id, character name, character level, character cp, double rewards, guild, noodles}
    
    maximumCP = dm["CP"]
    
    deathChars = []
    allRewardStrings = {}
                
    characterIDs = [p["Character ID"] for p in players.values()]
    userIDs = list(players.keys())
    guildIDs = list(guilds.keys())
    for gt in guildIDs:
        if guilds[gt]["Status"] == False:
            del guilds[gt]
            
    
    guildIDs = list(guilds.keys())
    
    userIDs.append(str(dm["ID"]))
    
    # the db entry of every character
    if characterDBentries == None:
        characterDBentries = list(playersCollection.find({"_id": {"$in": characterIDs}}))
    characterDBentriesDic = {character["_id"] : character for character in characterDBentries}
    # the db entry of every user
    if userDBEntriesDic == None:
        userDBentries = usersCollection.find({"User ID": {"$in": userIDs}})
        userDBEntriesDic = {}
        for u in userDBentries:
            userDBEntriesDic[u["User ID"]] = u
        
    
    # the db entry of every guild
    if guildDBEntriesDic == None:
        guildDBEntriesDic = {}
        guildDBentries = guildCollection.find({"Name": {"$in": guildIDs}})
        for g in guildDBentries:
            guildDBEntriesDic[g["Name"]] = g
            
            if g["Reputation"] >= guild_drive_costs[sessionInfo["Tier"]]:
                g["Reputation"] -= guild_drive_costs[sessionInfo["Tier"]]*guilds[g["Name"]]["Drive"]
            else:
                guilds[g["Name"]]["Drive"] = False
            
            if g["Reputation"] >= 25:
                g["Reputation"] -= 25*guilds[g["Name"]]["Rewards"]
            else:
                guilds[g["Name"]]["Rewards"] = False
            
            if g["Reputation"] >= 10:
                g["Reputation"] -= 10*guilds[g["Name"]]["Items"]
            else:
                guilds[g["Name"]]["Items"] = False
    gold_modifier = 100
    if "Gold Modifier" in sessionInfo:
        gold_modifier = sessionInfo["Gold Modifier"]
    item_rewards = True
    if "Items" in sessionInfo:
        item_rewards = sessionInfo["Items"]
    for k, player in players.items():
        # this indicates that the character had died
        if player["Status"] == "Dead":
            deathChars.append(player)
        
        duration = player["CP"] * 3600
        
        guildDouble = False
        playerDouble = False
        dmDouble = False
        
        if role != "":
            guild_valid =("Guild" in player and 
                            player["Guild"] in guilds and 
                            guilds[player["Guild"]]["Status"] and
                            player["CP"]>= 3 and player['Guild Rank'] > 1)
            guildDouble = (guild_valid and 
                            guilds[player["Guild"]]["Rewards"] and 
                            player["2xR"])
            if(guild_valid and 
                guilds[player["Guild"]]["Items"] and 
                    player["2xI"]):
                
                for i in player["Double Items"]:
                    if i[0] == "Magic Items":
                        player["Magic Items"].append(i[1])
                    else:
                        player[i[0]]["Add"].append(i[1])
                
            player["Double"] = k in userDBEntriesDic.keys() and "Double" in userDBEntriesDic[k] and userDBEntriesDic[k]["Double"] >0
            playerDouble = player["Double"]
                
            dmDouble = False
            bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
            
            treasureArray  = calculateTreasure(player["Level"], player["Character CP"], duration, guildDouble, playerDouble, dmDouble, bonusDouble, gold_modifier)
            treasureString = f"{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP"
            
            
        else:
            # if there were no rewards we only care about the time
            treasureString = timeConversion(duration) 
        groupString = ""
        groupString += guildDouble * "2xR "
        groupString += playerDouble * "Fanatic "
        groupString += bonusDouble * "Bonus "
        groupString += f'{role} Friend {"Full"*(player["CP"]==dm["CP"])+"Partial"*(not player["CP"]==dm["CP"])} Rewards:\n{treasureString}'
        
        # if the player was not present the whole game and it was a no rewards game
        if role == "" and not (player["CP"]==dm["CP"]):
            # check if the reward has already been added to the reward dictionary
            if treasureString not in allRewardStrings:
                # if not, create the entry
                allRewardStrings[treasureString] = [player]
            else:
                # otherwise add the new players
                allRewardStrings[treasureString] += [player] 
        else:
            # check if the full rewards have already been added, if yes create it and add the players
            if groupString in allRewardStrings:
                allRewardStrings[groupString] += [player]
            else:
                allRewardStrings[groupString] = [player]

    
    paused_time = 0
    if "Paused Time" in sessionInfo:
        paused_time = sessionInfo["Paused Time"]
    datestart = datetime.fromtimestamp(start).astimezone(pytz.timezone(timezoneVar)).strftime("%b-%d-%y %I:%M %p")
    dateend = datetime.fromtimestamp(end).astimezone(pytz.timezone(timezoneVar)).strftime("%b-%d-%y %I:%M %p")
    totalDuration = timeConversion(end - start - paused_time)
    sessionLogEmbed.title = f"Timer: {game} [END] - {totalDuration}"
    dm_double_string = ""
    dmRewardsList = []
    #DM REWARD MATH STARTS HERE
    if("Character ID" in dm):
        charLevel = int(dm['Level'])
        k = (dm['ID'])
        player = dm
        dm_tier_num = 5
        # calculate the tier of the DM character
        if charLevel < 5:
            dmRole = 'Junior'
            dm_tier_num = 1
        elif charLevel < 11:
            dmRole = 'Journey'
            dm_tier_num = 2
        elif charLevel < 17:
            dmRole = 'Elite'
            dm_tier_num = 3
        elif charLevel < 20:
            dmRole = 'True'
            dm_tier_num = 4
        else:
            dmRole = 'Ascended'
            
        duration = player["CP"]*3600
        if role != "":
            guild_valid =("Guild" in player and 
                            player["Guild"] in guilds and 
                            guilds[player["Guild"]]["Status"] and
                            player["CP"]>= 3 and player['Guild Rank'] > 1)
                            
            guildDouble = (guild_valid and 
                            guilds[player["Guild"]]["Rewards"] and 
                            player["2xR"])
            
            player["Double"] = k in userDBEntriesDic.keys() and "Double" in userDBEntriesDic[k] and userDBEntriesDic[k]["Double"] >0
            
            playerDouble = player["Double"]
            
            if(guild_valid and 
                guilds[player["Guild"]]["Items"] and 
                    player["2xI"]):
                
                for i in player["Double Items"]:
                    if i[0] == "Magic Items":
                        player["Magic Items"].append(i[1])
                    else:
                        player[i[0]]["Add"].append(i[1])
            
            dmDouble = player["DM Double"] and sessionInfo["DDMRW"]
            bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
            
            dm_double_string += guildDouble * "2xR "
            dm_double_string += playerDouble * "Fanatic "
            dm_double_string += dmDouble * "DDMRW "
            dm_double_string += bonusDouble * "Bonus "
            
            dmtreasureArray  = calculateTreasure(player["Level"], player["Character CP"], duration, guildDouble, playerDouble, dmDouble, bonusDouble)
            
        
        # add the items that the DM awarded themselves to the items list
        
        if item_rewards:
            for d in dm["Magic Items"]+dm["Consumables"]["Add"]+dm["Inventory"]["Add"]:
                dmRewardsList.append("+"+d)
    
    # get the collections of characters
    playersCollection = db.players
    dmEntry = userDBEntriesDic[dm["ID"]]
    if 'Noodles' not in dmEntry:
        dmEntry['Noodles'] = 0
    if "DM Time" not in dmEntry:
        dmEntry["DM Time"] = 0
    noodles = dmEntry["Noodles"]
    # Noodles Math
    
        
    duration = end - start - paused_time
    noodlesGained = int((duration + dmEntry["DM Time"])//(3*3600))
    
    # that is the base line of sparkles and noodles gained
    sparklesGained = int(maximumCP) // 3
    # add the noodles to the record or start a record if needed
        
    #new noodle total
    noodleFinal = noodles + noodlesGained
    noodleFinalString = f"{str(noodleFinal)}:star: (+{noodlesGained}:star:)"

    # if the game received rewards
    if role != "": 
        # clear the embed message to repopulate it
        sessionLogEmbed.clear_fields() 
        # for every unique set of TP rewards
        for key, value in allRewardStrings.items():
            temp = ""
            # for every player of this reward
            for v in value:
                vRewardList = []
                # for every brough consumable for the character
                if item_rewards:
                    for r in  v["Magic Items"]+ v["Consumables"]["Add"]+ v["Inventory"]["Add"]:
                        # add the awarded items to the list of rewards
                        vRewardList.append("+"+r)
                # if the character was not dead at the end of the game
                char_name = v['Character Name']
                if "Paused" in characterDBentriesDic[v['Character ID']] and characterDBentriesDic[v['Character ID']]["Paused"]:
                    char_name = "[PAUSED] " + char_name
                    vRewardList = []
                if v not in deathChars:
                    temp += f"{v['Mention']} | {char_name} {', '.join(vRewardList).strip()}\n"
                else:
                    # if they were dead, include that death
                    temp += f"~~{v['Mention']} | {char_name}~~ **DEATH** {', '.join(vRewardList).strip()}\n"
            
            # since if there is a player for this reward, temp will have text since every case above results in changes to temp
            # this informs us that there were no players
            if temp == "":
                temp = 'None'
            # add the information about the reward to the embed object
            sessionLogEmbed.add_field(name=f"**{key}**\n", value=temp, inline=False)
            # add temp to the total output string

        # list of all guilds
        guildsListStr = ""
        
        guildRewardsStr = ""
        players[dm["ID"]] = dm
        # passed in parameter, check if there were guilds involved
        if guilds != dict():
            guildsListStr = "Guilds: "
            # for every guild in the game
            for name, g in guilds.items():
                
                guildsListStr += "\n"+(g["Drive"]*"**Recruitment Drive** ")+(g["Rewards"]*"**2xR** ")+(g["Items"]*"**2xI** ")+g["Mention"]
                # get the DB record of the guild
                #filter player list by guild
                gPlayers = [p for p in players.values() if "Guild" in p and p["Guild"]==name]
                if(len(gPlayers)>0): 
                    gain = 0
                    for p in gPlayers:
                        gain += p["CP"]  // 3
                    
                    gain += sparklesGained*int("Guild" in dm and dm["Guild"] == name)
                    guildRewardsStr += f"{g['Name']}: +{int(gain)} :sparkles:\n"
        
        noodleCongrats = ""
        # for the relevant noodle role cut-off check if the user would now qualify for the role and if they do not have it and remove the old role
        noodles_barrier = 0
        for i in range(len(noodleRoleArray)):
            if noodles < max(noodles_barrier, 1) and noodleFinal >= max(noodles_barrier, 1):
                noodleCongrats = f"Congratulations! You have reached {noodleRoleArray[i]}!"
            noodles_barrier += 10*(i+1)
        game_channel = get(ctx.guild.text_channels, name = sessionInfo['Channel'])
        if not game_channel:
            game_channel = sessionInfo['Channel']
        else:
            game_channel = f"<#{game_channel.id}>"
        sessionLogEmbed.title = f"\n**{game}**\n*Tier {tierNum} Quest*"
        sessionLogEmbed.description = f"{game_channel}\n{guildsListStr}\n**Start**: {datestart} EDT\n**End**: {dateend} EDT\n**Runtime**: {totalDuration}\n**General "+description
        status_text = "Log is being processed! Characters are currently on hold."
        await editMessage.clear_reactions()
        if sessionInfo["Status"] == "Approved":
            status_text = "✅ Log approved! The DM and players have received their rewards and their characters can be used in further one-shots."
        elif sessionInfo["Status"] == "Denied":
            status_text = "❌ Log Denied! Characters have been cleared"
            noodleCongrats = ""
        elif sessionInfo["Status"] == "Pending":
            status_text = "❔ Log Pending! DM has been messaged due to session log issues."
            
            await editMessage.add_reaction('<:nipatya:408137844972847104>')
        gold_mod_text = f"Current GP earned: {gold_modifier}%\n"
        sessionLogEmbed.set_footer(text=f"Game ID: {num}\n{status_text}\n{gold_mod_text}{noodleCongrats}")
        if noodleCongrats:
            await editMessage.add_reaction('🎉')
            await editMessage.add_reaction('🎊')
            await editMessage.add_reaction('🥳')
            await editMessage.add_reaction('🍾')
            await editMessage.add_reaction('🥂')
        
        # add the field for the DM's player rewards
        dm_text = "**No Character**"
        dm_name_text = "**No Rewards**"
        # if no character signed up then the character parts are excluded
        if("Character ID" in dm):
            dm_char = playersCollection.find_one({"_id": dm["Character ID"]})
            paused = "Paused" in dm_char and dm_char["Paused"]
            dm_text = f"{'[PAUSED] ' * paused + dm['Character Name']} {', '.join(dmRewardsList* (not paused))}"
            dm_name_text = f"DM {dm_double_string}Rewards (Tier {dm_tier_num}):\n**{dmtreasureArray[0]} CP, {sum(dmtreasureArray[1].values())} TP, {dmtreasureArray[2]} GP**\n"
        sessionLogEmbed.add_field(value=f"{dm['Mention']} | {dm_text}\n{noodleFinalString}", name=dm_name_text)
        
        # if there are guild rewards then add a field with relevant information
        if guildRewardsStr != "":
            sessionLogEmbed.add_field(value=guildRewardsStr, name=f"Guild Rewards", inline=False)
        await editMessage.edit(embed=sessionLogEmbed)
    
    pass
        
class Log(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
    def is_log_channel():
        async def predicate(ctx):
            if ctx.channel.type == discord.ChannelType.private:
                return False
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Game Rooms"] or
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"])
        return commands.check(predicate)
    @commands.group(case_insensitive=True)
    @is_log_channel()
    async def session(self, ctx):	
        pass
        
    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.MissingAnyRole):
            msg = "You do not have the required permissions for this command."
        elif isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your session ID was an incorrect format."
        elif isinstance(error, discord.NotFound):
            msg = "The session log could not be found."
        else:
            if isinstance(error, commands.MissingRequiredArgument):
                msg = "Your command was missing an argument! "
            elif isinstance(error, commands.CheckFailure):
                msg = "This channel or user does not have permission for this command."
            elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
              msg = ""

            if msg:
                ctx.command.reset_cooldown(ctx)
                await ctx.channel.send(msg)
                #await traceBack(ctx,error)
            else:
                ctx.command.reset_cooldown(ctx)
                await traceBack(ctx,error)

    @commands.has_any_role('Mod Friend', 'Admins')
    @session.command()
    async def approve(self,ctx,  num : int):
        channel = self.bot.get_channel
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        channel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"]) 
        editMessage = None
        
        try:
            editMessage = await channel.fetch_message(num)
        except Exception as e:
            return await ctx.channel.send("Log could not be found.")
            
            

        if not sessionInfo:
            return await ctx.channel.send("Session could not be found.")
            
        if sessionInfo["Status"] == "Approved" or sessionInfo["Status"] == "Denied":
            await ctx.channel.send("This session has already been processed")
            return
        if ctx.author.id == int(sessionInfo["DM"]["ID"]):
            await ctx.channel.send("You cannot approve your own log.")
            return
        if not editMessage or editMessage.author != self.bot.user:
            return await ctx.channel.send("Session has no corresponding message in the log channel.")


        
        guilds = sessionInfo["Guilds"]
        tierNum = sessionInfo["Tier"]
        role = sessionInfo["Role"]
        
        #dictionary indexed by user id
        players = sessionInfo["Players"] 
        # {cp, magic items, consumables, inventory, status, character id, character name, character level, character cp, double rewards, guild, }
                
                    
        dm = sessionInfo["DM"] 
        # {cp, magic items, consumables, inventory, character id, character name, character level, character cp, double rewards, guild, noodles, dm double}
        event_inc = 1*("Event" in sessionInfo and sessionInfo["Event"])
        maximumCP = dm["CP"]
        deathChars = []
        playerUpdates = []
        
        # get the collections of characters
        playersCollection = db.players
        guildCollection = db.guilds
        statsCollection = db.stats
        usersCollection = db.users
        
        characterIDs = [p["Character ID"] for p in players.values()]
        userIDs = list(players.keys())
        guildIDs = list(guilds.keys())
        
        userIDs.append(str(dm["ID"]))
        
        # the db entry of every character
        characterDBentries = list(playersCollection.find({"_id": {"$in": characterIDs}}))
        
        # the db entry of every user
        userDBentries = usersCollection.find({"User ID": {"$in": userIDs}})
    
        # the db entry of every guild
        guildDBentries = guildCollection.find({"Name": {"$in": guildIDs}})
        guildDBEntriesDic = {}
        for g in guildDBentries:
            guildDBEntriesDic[g["Name"]] = g
            if g["Reputation"] >= guild_drive_costs[sessionInfo["Tier"]]:
                g["Reputation"] -= guild_drive_costs[sessionInfo["Tier"]]*guilds[g["Name"]]["Drive"]
            else:
                guilds[g["Name"]]["Drive"] = False
            
            if g["Reputation"] >= 25:
                g["Reputation"] -= 25*guilds[g["Name"]]["Rewards"]
            else:
                guilds[g["Name"]]["Rewards"] = False
            
            if g["Reputation"] >= 10:
                g["Reputation"] -= 10*guilds[g["Name"]]["Items"]
            else:
                guilds[g["Name"]]["Items"] = False
        
        userDBEntriesDic = {}
        for u in userDBentries:
            userDBEntriesDic[u["User ID"]] = u

        
        gold_modifier = 100
        if "Gold Modifier" in sessionInfo:
            gold_modifier = sessionInfo["Gold Modifier"]
        item_rewards = True
        if "Items" in sessionInfo:
            item_rewards = sessionInfo["Items"]
        for character in characterDBentries:
            player = players[str(character["User ID"])]
            # this indicates that the character had died
            if player["Status"] == "Dead":
                deathChars.append(player)
            
            duration = player["CP"] * 3600
            player["Double"] = False
            guildDouble = False
            playerDouble = False
            dmDouble = False

            if not ("Paused" in character and character["Paused"]):
                guild_valid =("Guild" in player and 
                                player["Guild"] in guilds and 
                                guilds[player["Guild"]]["Status"] and
                            player["CP"]>= 3 and player['Guild Rank'] > 1)
                guildDouble = (guild_valid and 
                                guilds[player["Guild"]]["Rewards"] and 
                                player["2xR"])
                

                player["Double"] = str(character["User ID"]) in userDBEntriesDic.keys() and "Double" in userDBEntriesDic[str(character["User ID"])] and userDBEntriesDic[str(character["User ID"])]["Double"] >0
                playerDouble = player["Double"]
                dmDouble = False
                bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
                
                treasureArray  = calculateTreasure(player["Level"], character["CP"] , duration, guildDouble, playerDouble, dmDouble, bonusDouble, gold_modifier)
                
                if(guild_valid and 
                        guilds[player["Guild"]]["Items"] and 
                        player["2xI"]):
                    
                    for i in player["Double Items"]:
                        if i[0] == "Magic Items":
                            player["Magic Items"].append(i[1])
                        else:
                            player[i[0]]["Add"].append(i[1])
                    player["Double Items"] = []
                
                
                # create a list of all items the character has
                consumableList = character["Consumables"].split(", ")
                consumablesString = ""
                if not item_rewards:
                    player["Consumables"]["Add"] = []
                    player["Inventory"]["Add"] = []
                    player["Magic Items"] = []
                
                #if we know they didnt have any items, we know that changes could only be additions
                if(character["Consumables"]=="None"):
                    # turn the list of added items into the new string
                    consumablesString = ", ".join(player["Consumables"]["Add"])
                else:
                    #remove the removed items from the list of original items and then combine the remaining and the new items                
                    for i in player["Consumables"]["Remove"]:
                        consumableList.remove(i)
                    consumablesString = ", ".join(player["Consumables"]["Add"]+consumableList)
                    
                # if the string is empty, turn it into none
                consumablesString += "None"*(consumablesString=="")
                
                # magic items cannot be removed so we only care about addtions
                # if we have no items and no additions, string is None
                
                magicItemString = "None"
                if(character["Magic Items"]=="None"):
                    if(len(player["Magic Items"])==0):
                        pass
                    else:
                        # otherwise it is just the combination of new items
                        magicItemString = ", ".join(player["Magic Items"])
                else:
                    # otherwise connect up the old and new items
                    magicItemString = character["Magic Items"]+(", "+ ", ".join(player["Magic Items"]))*(len(player["Magic Items"])>0)
                
                
                # increase the relevant inventory entries and create them if necessary
                for i in player["Inventory"]["Add"]:
                    if i in character["Inventory"]:
                        character["Inventory"][i] += 1
                    else:
                        character["Inventory"][i] = 1
                
                # decrement the relevant items and delete the entry when necessary
                for i in player["Inventory"]["Remove"]:
                    character["Inventory"][i] -= 1
                    if int(character["Inventory"][i]) <= 0:
                        del character["Inventory"][i]
                
                # set up all db values that need to be incremented
                increment = {"CP":  treasureArray[0], 
                            "GP":  treasureArray[2],
                            "Games": 1,
                            "Playtime": player["CP"],
                            "Event Token" : event_inc}
                # for every TP tier value that was gained create the increment field
                for k,v in treasureArray[1].items():
                    increment[k] = v
                player_set = {"Consumables": consumablesString, 
                                "Magic Items": magicItemString, 
                                "Inventory" : character["Inventory"], 
                                "Drive" : []}
                for g in guilds.values():
                    if g["Drive"] and player["CP"]>= 3:
                        player_set["Drive"]=g["Name"]
                
                charRewards = {'_id': player["Character ID"],  
                                    "fields": {"$unset": {f"GID": 1} ,"$inc": increment, 
                                    "$set": player_set}}
                if(player["Status"] == "Dead"):
                    del charRewards["fields"]["$inc"]["Games"]
                    deathDic = {"inc": increment.copy(), "set": charRewards["fields"]["$set"]}
                    charRewards["fields"]["$inc"] = {"Games": 1}
                    charRewards["fields"]["$set"] = {"Death": deathDic}
                playerUpdates.append(charRewards)
            else:
                playerUpdates.append({'_id': player["Character ID"],
                                        'fields': {"$unset": {f"GID": 1} ,
                                        "$inc": {"Stored": duration,
                                                    "Playtime": player["CP"],
                                                    "Games": 1,
                                                    "Event Token" : event_inc}}})
        dmRewardsList = []
        dm["Double"] = False
        dm_time_bank = 0
        #DM REWARD MATH STARTS HERE
        if("Character ID" in dm):
        
            player = dm
            
            duration = player["CP"] * 3600
            
            # the db entry of every character
            character = playersCollection.find_one({"_id": dm["Character ID"]})
            player["Double"] = False
            if not ("Paused" in character and character["Paused"]):
                charLevel = int(dm['Level'])
                # calculate the tier of the DM character
                dmTierNum= 5
                dmRole = "Ascended"
                if charLevel < 5:
                    dmRole = 'Junior'
                    dmTierNum = 1
                elif charLevel < 11:
                    dmRole = 'Journey'
                    dmTierNum = 2
                elif charLevel < 17:
                    dmRole = 'Elite'
                    dmTierNum = 3
                elif charLevel < 20:
                    dmRole = 'True'
                    dmTierNum = 4
                
                guild_valid =("Guild" in player and 
                                    player["Guild"] in guilds and 
                                    guilds[player["Guild"]]["Status"] and
                                player["CP"]>= 3 and player['Guild Rank'] > 1)
                guildDouble = (guild_valid and 
                                guilds[player["Guild"]]["Rewards"] and 
                                player["2xR"])
                    
                
                 
                player["Double"] = dm["ID"] in userDBEntriesDic.keys() and "Double" in userDBEntriesDic[dm["ID"]] and userDBEntriesDic[dm["ID"]]["Double"] >0
                playerDouble = player["Double"]
                
                dmDouble = player["DM Double"] and sessionInfo["DDMRW"]
                bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
                
                treasureArray  = calculateTreasure(charLevel, character["CP"], duration, guildDouble, playerDouble, dmDouble, bonusDouble)
                    
                    
                if(guild_valid and 
                        guilds[player["Guild"]]["Items"] and 
                        player["2xI"]):
                    for i in player["Double Items"]:
                        if i[0] == "Magic Items":
                            player["Magic Items"].append(i[1])
                        else:
                            player[i[0]]["Add"].append(i[1])
                    player["Double Items"] = []
                    
                
                if not item_rewards:
                    player["Consumables"]["Add"] = []
                    player["Inventory"]["Add"] = []
                    player["Magic Items"] = []
                    
                # create a list of all items the character has
                consumableList = character["Consumables"].split(", ")
                consumablesString = ""
                
                
                #if we know they didnt have any items, we know that changes could only be additions
                if(character["Consumables"]=="None"):
                    # turn the list of added items into the new string
                    consumablesString = ", ".join(player["Consumables"]["Add"])
                else:
                    #remove the removed items from the list of original items and then combine the remaining and the new items                
                    for i in player["Consumables"]["Remove"]:
                        consumableList.remove(i)
                    consumablesString = ", ".join(player["Consumables"]["Add"]+consumableList)
                    
                # if the string is empty, turn it into none
                consumablesString += "None"*(consumablesString=="")
                
                # magic items cannot be removed so we only care about addtions
                # if we have no items and no additions, string is None
                magicItemString = "None"
                if(character["Magic Items"]=="None"):
                    if(len(player["Magic Items"])==0):
                        pass
                    else:
                        # otherwise it is just the combination of new items
                        magicItemString = ", ".join(player["Magic Items"])
                else:
                    # otherwise connect up the old and new items
                    magicItemString = character["Magic Items"]+(", "+ ", ".join(player["Magic Items"]))*(len(player["Magic Items"])>0)
                    
                    
                
                # increase the relevant inventory entries and create them if necessary
                for i in player["Inventory"]["Add"]:
                    if i in character["Inventory"]:
                        character["Inventory"][i] += 1
                    else:
                        character["Inventory"][i] = 1
                
                # decrement the relevant items and delete the entry when necessary
                for i in player["Inventory"]["Remove"]:
                    character["Inventory"][i] -= 1
                    if int(character["Inventory"][i]) <= 0:
                        del character["Inventory"][i]
                
                # set up all db values that need to be incremented
                increment = {"CP":  treasureArray[0], "GP":  treasureArray[2],"Games": 1, "Event Token": event_inc}
                
                # for every TP tier value that was gained create the increment field
                for k,v in treasureArray[1].items():
                    increment[k] = v
                
                player_set = {"Consumables": consumablesString, 
                                "Magic Items": magicItemString, 
                                "Inventory" : character["Inventory"], 
                                "Drive" : []}

                for g in guilds.values():
                    if g["Drive"] and player["CP"] >= 3:
                        player_set["Drive"] = g["Name"]
                        break
                
                charRewards = {'_id': player["Character ID"],  
                                "fields": {"$unset": {f"GID": 1},
                                "$inc": increment, 
                                "$set": player_set}}
                                 
                playerUpdates.append(charRewards)
            else:
                playerUpdates.append({'_id': player["Character ID"],
                                        'fields': {"$unset": {f"GID": 1},
                                        "$inc": {"Stored": duration,
                                                    "Games": 1,
                                                    "Event Token" : event_inc}}})
        else:
            paused_time = 0
            if "Paused Time" in sessionInfo:
                paused_time = sessionInfo["Paused Time"]
            dm_time_bank = (sessionInfo["End"] - sessionInfo["Start"] - paused_time) * (1+ sessionInfo["DDMRW"] + ("Bonus" in sessionInfo and sessionInfo["Bonus"]))
        # that is the base line of sparkles and noodles gained
        sparklesGained = int(maximumCP) // 3
        timerData = list(map(lambda item: UpdateOne({'_id': item['_id']}, item['fields']), playerUpdates))
        players[dm["ID"]] = dm
        guildsData = []
        # if the game received rewards
        if role != "": 
            # passed in parameter, check if there were guilds involved
            if guilds != list():
                # for every guild in the game
                for g in guildDBEntriesDic.values():
                    name = g["Name"]                    
                    gain = 0
                    # get the DB record of the guild
                    #filter player list by guild
                    gPlayers = [p for p in players.values() if "Guild" in p and p["Guild"] == name]
                    p_count = len(gPlayers) - int("Guild" in dm and dm["Guild"] == name)
                    for p in gPlayers:
                        gain += p["CP"]  // 3
                    guilds[name]["Player Sparkles"] = gain - sparklesGained*int("Guild" in dm and dm["Guild"] == name)
                    guilds[name]["DM Sparkles"] = 2*sparklesGained*int("Guild" in dm and dm["Guild"] == name)

                    gain += sparklesGained*int("Guild" in dm and dm["Guild"] == name)
                    
                    reputationCost = (20*guilds[name]["Rewards"]+10*guilds[name]["Items"]+guild_drive_costs[sessionInfo["Tier"]]*guilds[name]["Drive"])*guilds[name]["Status"]
                    if guilds[name]["Status"]:
                        guildsData.append(UpdateOne({"Name": name},
                                                   {"$inc": {"Games": 1, "Reputation": int(gain- reputationCost), "Total Reputation": gain}}))
        
        del players[dm["ID"]]
        
        end = sessionInfo["End"]
        start = sessionInfo["Start"]
        
        # Noodles Math
        dmEntry = userDBEntriesDic[dm["ID"]]
        
        if "DM Time" not in dmEntry:
            dmEntry["DM Time"] = 0
        if "Noodles" not in dmEntry:
            dmEntry["Noodles"] = 0
        noodles = dmEntry["Noodles"]
        paused_time = 0
        if "Paused Time" in sessionInfo:
            paused_time = sessionInfo["Paused Time"]
        duration = totalDuration = end - start - paused_time
        noodlesGained = int((duration + dmEntry["DM Time"])//(3*3600))
        new_dm_time = (duration + dmEntry["DM Time"])%(3*3600)
        noodles += noodlesGained
        try:
            
            # get the stats for the month and create an entry if it doesnt exist yet
            statsIncrement ={"Games": 1, "Playtime": totalDuration, 'Players': len(players.keys())}
            statsAddToSet = {}
            for name in [g["Name"] for g in guilds.values() if g["Status"]]:
                # Track how many guild quests there were
                statsIncrement["Guilds."+name+".GQ"] = 1
                statsIncrement["Guilds."+name+".GQM"] = 0
                statsIncrement["Guilds."+name+".GQDM"] = 0
                statsIncrement["Guilds."+name+".GQNM"] = 0
                statsIncrement["Guilds."+name+".Player Sparkles"] = guilds[name]["Player Sparkles"]
                statsIncrement["Guilds."+name+".DM Sparkles"] = guilds[name]["DM Sparkles"]
                # track how many games had a guild memeber with rewards and how many have not
                if guilds[name]["Player Sparkles"] > 0: 
                    statsIncrement["Guilds."+name+".GQM"] = 1
                elif guilds[name]["DM Sparkles"] > 0:
                    statsIncrement["Guilds."+name+".GQDM"] = 1
                else:
                    statsIncrement["Guilds."+name+".GQNM"] = 1
            # Total Number of Games for the Month / Life
            
            # increment or create the stat entry for the DM of the game
            statsIncrement[f"DM.{dm['ID']}.T{tierNum}"] = 1
            statsIncrement[f"T{tierNum}"] = 1
            statsIncrement[f"GQ Total"] = int(any ([g["Status"] for g in guilds.values()]))
            if totalDuration > 10800: #3 hours
                if (tierNum in [0, 1]):
                    statsIncrement[f"DM.{dm['ID']}.Friend"] = 1
                if (len(guildsData)>0):
                    statsIncrement[f"DM.{dm['ID']}.Guild Fanatic"] = 1
                    for g in guildDBEntriesDic.values():
                        if guilds[g["Name"]]["Status"]:
                            statsIncrement[f"DM.{dm['ID']}.Guild Fanatic"] = 1
                            statsIncrement[f"DM.{dm['ID']}.Guilds.{g['Name']}"] = 1
            
            
            # track a list of unique players
            statsAddToSet = { 'Unique Players': { "$each":  list([p for p in players.keys()])} }
            
            
            # track playtime and players


            
            dateyear = datetime.fromtimestamp(start).astimezone(pytz.timezone(timezoneVar)).strftime("%b-%y")
            # update all the other data entries
            # update the DB stats
            statsCollection.update_one({'Date': dateyear}, {"$set": {'Date': dateyear}, "$inc": statsIncrement, "$addToSet": statsAddToSet}, upsert=True)
            statsCollection.update_one({'Life': 1}, {"$inc": statsIncrement, "$addToSet": statsAddToSet}, upsert=True)
            # update the DM' stats
            
            usersCollection.update_one({'User ID': str(dm["ID"])}, {"$set": {'User ID':str(dm["ID"]),'DM Time': new_dm_time}, "$inc": {'Games': 1, 'Games Hosted': 1, 'Noodles': noodlesGained, 'Double': -1*dm["Double"], 'Time Bank': dm_time_bank}}, upsert=True)
            playersCollection.bulk_write(timerData)
            
            usersData = list([UpdateOne({'User ID': key}, {'$inc': {'Games': 1, 'Double': -1*item["Double"] }}, upsert=True) for key, item in {character["User ID"] : players[character["User ID"] ] for character in characterDBentries}.items()])
            usersCollection.bulk_write(usersData)
            
            logData.update_one({"_id": sessionInfo["_id"]}, {"$set" : {"Status": "Approved"}})
            sessionInfo["Status"]="Approved"
            
            if guildsData != list():
                # do a bulk write for the guild data
                db.guilds.bulk_write(guildsData)
            
            await  generateLog(self, ctx, num, sessionInfo=sessionInfo, userDBEntriesDic=userDBEntriesDic, guildDBEntriesDic=guildDBEntriesDic, characterDBentries=characterDBentries)
            
            del players[dm["ID"]]
            game = sessionInfo["Game"]
            for k,p in players.items():
                c = ctx.guild.get_member(int(k))
                if(c):
                    try:
                        await c.send(f"The session log for **{game}** has been approved. **{p['Character Name']}** has received their rewards.")
                    except Forbidden as cie:
                        await ctx.channel.send(content=f"{c.mention} has blocked the bot.")
            dm_text = ""
            if("Character ID" in dm):
                dm_text += f" **{dm['Character Name']}** has received their rewards."
            
            c = ctx.guild.get_member(int(dm["ID"]))
            if(c):
                try:
                    await c.send(f"Your session log for **{game}** has been approved.{dm_text}")
                except Forbidden as cie:
                    await ctx.channel.send(content=f"{c.mention} has blocked the bot.")
            await ctx.channel.send("The session has been approved.")
            
        except BulkWriteError as bwe:
            print(bwe.details)
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
        guild = ctx.guild
        dmUser = ctx.guild.get_member(int(dm["ID"]))
        if dmUser:
            noodleString = ""
            dmRoleNames = [r.name for r in dmUser.roles]
            # for the relevant noodle role cut-off check if the user would now qualify for the role and if they do not have it and remove the old role
            noodles_barrier=0
            broken_barrier=0
            noodles_position = -1
            for i in range(len(noodleRoleArray)):
                if noodles >= max(noodles_barrier, 1):
                    noodles_position = i
                    broken_barrier = max(noodles_barrier, 1)
                noodles_barrier += 10*(i+1)
            if noodles_position >= 0:
                noodle_name = noodleRoleArray[noodles_position]
                if noodle_name not in dmRoleNames:
                    noodleRole = get(guild.roles, name = noodle_name)
                    await dmUser.add_roles(noodleRole, reason=f"Hosted {broken_barrier} sessions. This user has {broken_barrier}+ Noodles.")
                    if noodles_position>0:
                        remove_role = noodleRoleArray[noodles_position-1]
                        if remove_role in dmRoleNames:
                            await dmUser.remove_roles(get(guild.roles, name = remove_role))


    @commands.has_any_role('Mod Friend', 'A d m i n')
    @session.command()
    async def deny(self,ctx,  num : int):
        channel = self.bot.get_channel
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        channel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"]) 
        
        try:
            editMessage = await channel.fetch_message(num)
        except Exception as e:
            return await ctx.channel.send("Log could not be found.")
            
        if not sessionInfo:
            return await ctx.channel.send("Session could not be found.")
        
        if sessionInfo["Status"] == "Approved" or sessionInfo["Status"] == "Denied":
            await ctx.channel.send("This session has already been processed")
            return
        if ctx.message.author.id == int(sessionInfo["DM"]["ID"]):
            await ctx.channel.send("You cannot deny your own log.")
            return
        if not editMessage or editMessage.author != self.bot.user:
            return await ctx.channel.send("Session has no corresponding message in the log channel.")

        sessionLogEmbed = editMessage.embeds[0]
        #dictionary indexed by user id
        players = sessionInfo["Players"] 
        # {cp, magic items, consumables, inventory, status, character id, character name, character level, character cp, double rewards, guild, }
                
                 
        playerUpdates = []   
        dm = sessionInfo["DM"] 
        # {cp, magic items, consumables, inventory, character id, character name, character level, character cp, double rewards, guild, noodles, dm double}
        if "Character ID" in dm:
            charRewards = {'_id': dm["Character ID"],  
                                "fields": {"$unset": {f"GID": 1} }}
            playerUpdates.append(charRewards)
        
        role = sessionInfo["Role"]
        
        # get the collections of characters
        playersCollection = db.players

        
        for player in players.values():
            if role != "":
                charRewards = {'_id': player["Character ID"],  
                                    "fields": {"$unset": {f"GID": 1} }}
                playerUpdates.append(charRewards)
                
            else:
                # if there were no rewards we only care about the time
                pass
                
        timerData = list(map(lambda item: UpdateOne({'_id': item['_id']}, item['fields']), playerUpdates))
        
                                               
        try:                
            playersCollection.bulk_write(timerData)
            logData.update_one({"_id": sessionInfo["_id"]}, {"$set" : {"Status": "Denied"}})
            
            game = sessionInfo["Game"]
            for k,p in players.items():
                c = ctx.guild.get_member(int(k))
                if(c):
                    await c.send(f"The session log for **{game}** has been denied. **{p['Character Name']}** has been cleared.")
            dm_text = ""
            if("Character ID" in dm):
                dm_text += f" **{dm['Character Name']}** has been cleared."
            
            c = ctx.guild.get_member(int(dm["ID"]))
            if(c):
                await c.send(f"Your session log for **{game}** has been denied."+dm_text)
            #logData.delete_one({"Log ID": num})
            sessionLogEmbed.set_footer(text=f"Game ID: {num}\n❌ Log Denied! Characters have been cleared.")
            await editMessage.edit(embed=sessionLogEmbed)
            await ctx.channel.send("The session has been denied.")
        except BulkWriteError as bwe:
            print(bwe.details)
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
        #except Exception as e:
        #    print ('MONGO ERROR: ' + str(e))
        #    charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")


    @session.command()
    async def denyGuild(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Status", False, 0)
    @session.command()
    async def approveGuild(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Status", True, 0)
        
    #@session.command()
    async def denyRewards(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Rewards", False, 0)
    #@session.command()
    async def approveRewards(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Rewards", True, 3)
        
        
    #@session.command()
    async def denyDrive(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Drive", False, 0, unique = False)
    #@session.command()
    async def approveDrive(self, ctx,  num : int, *, guilds):
        await self.guildPermission(ctx, num, "Drive", True, 0, unique = True)
        
    async def guildPermission(self, ctx, num : int, target, goal, min_members, unique = False):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"):
                mod = "Mod Friend" in [r.name for r in ctx.author.roles]
                if( (str(ctx.author.id) == sessionInfo["DM"]["ID"]) or mod):
                # if the game received rewards
                    if len(sessionInfo["Guilds"].keys()) > 0: 
                        players = sessionInfo["Players"]
                        players[sessionInfo["DM"]["ID"]] = sessionInfo["DM"]
                        guilds = sessionInfo["Guilds"]
                        if unique and ((len(ctx.message.channel_mentions) > 1) or any([g["Drive"] for g in guilds.values()])):
                            await ctx.channel.send("The Recruitment Drive Guild Boon can only be used by one guild per guild quest.")
                            return
                        guild_dic = {}
                        for g in guilds.values():
                            guild_dic[g["Mention"]] = g
                        err_message = ""
                        for guildChannel in ctx.message.channel_mentions:
                            
                            m = guildChannel.mention
                            # filter player list by guild
                            gPlayers = [p for p in players.values() if "Guild" in p and 
                                            p["Guild"] in guilds and
                                            guilds[p["Guild"]]["Mention"] == m
                                            and  p["CP"]>= 3 and p['Guild Rank'] > 1]
                            if(len(gPlayers) >= min_members):
                                if guildChannel.mention in guild_dic:
                                    try:
                                        db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {"Guilds."+guild_dic[m]["Name"]+"."+target: goal}})
                                    except BulkWriteError as bwe:
                                        print(e)
                                else:
                                    err_message += m +" not found in game.\n"
                            else:
                                err_message += "There needs to be a minimum of three guild members from "+ m +" in order to activate its Guild Boons."
                        if err_message != "":
                            await ctx.channel.send(err_message)
                        else:
                            await ctx.channel.send("Session updated.")
                            await generateLog(self, ctx, num)
                    else:
                        await ctx.channel.send("There were no guilds in the session.")
                else:
                    await ctx.channel.send("You do not have the permissions to perform this change to the session.")
            else:
                await ctx.channel.send("This session has already been processed")
        else:
            await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
            
    @session.command()
    async def addGuilds(self, ctx,  num : int, *, guilds):
    
        mod = "Mod Friend" in [r.name for r in ctx.author.roles]
        if(mod):
            logData = db.logdata
            sessionInfo = logData.find_one({"Log ID": int(num)})
            if( sessionInfo):
                if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"):
                    guilds = sessionInfo["Guilds"]
                    guild_dic = {}
                    for g in guilds.values():
                        guild_dic[g["Mention"]] = g
                    err_message = ""
                    for guildChannel in ctx.message.channel_mentions:
                        
                        # get the DB record of the guild
                        gRecord  = db.guilds.find_one({"Channel ID": str(guildChannel.id)})
                        if not gRecord:
                            continue
                        guildDBEntry = {}
                        guildDBEntry["Status"] = True
                        guildDBEntry["Rewards"] = False
                        guildDBEntry["Items"] = False
                        guildDBEntry["Drive"] = False
                        guildDBEntry["Mention"] = guildChannel.mention
                        guildDBEntry["Name"] = gRecord["Name"]
                        
                        
                        mention = guildChannel.mention
                        if mention not in guild_dic:
                            try:
                                db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {"Guilds."+gRecord["Name"]: guildDBEntry}})
                            except BulkWriteError as bwe:
                                print(e)
                        else:
                            err_message += mention +" already found in game.\n"
                       
                    if err_message != "":
                        await ctx.channel.send(err_message)
                    await ctx.channel.send("Session updated.")
                    await generateLog(self, ctx, num)

                else:
                    await ctx.channel.send("This session has already been processed")
            else:
                await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
     
    @commands.has_any_role('Mod Friend', 'Admins')      
    @session.command()
    async def denyBonus(self, ctx,  num : int):
        await self.session_set(ctx, num, "Bonus", False)
        
    @commands.has_any_role('Mod Friend', 'Admins')
    @session.command()
    async def approveBonus(self, ctx,  num : int):
        await self.session_set(ctx, num, "Bonus", True)
     
    @commands.has_any_role('Mod Friend', 'Admins')      
    @session.command()
    async def denyDDMRW(self, ctx,  num : int):
        await self.session_set(ctx, num, "DDMRW", False)
        
    @commands.has_any_role('Mod Friend', 'Admins')
    @session.command()
    async def approveDDMRW(self, ctx,  num : int):
        await self.session_set(ctx, num, "DDMRW", True)
        
    @commands.has_any_role('Mod Friend', 'Admins')      
    @session.command()
    async def denyEvent(self, ctx,  num : int):
        await self.session_set(ctx, num, "Event", False)
        
        
    @commands.has_any_role('Mod Friend', 'Admins')  
    @session.command()
    async def denyItems(self, ctx,  num : int):
        await self.session_set(ctx, num, "Items", False)
        
    @commands.has_any_role('Mod Friend', 'Admins')  
    @session.command()
    async def approveItems(self, ctx,  num : int):
        await self.session_set(ctx, num, "Items", True)
        
    @commands.has_any_role('Mod Friend', 'Admins')
    @session.command()
    async def approveEvent(self, ctx,  num : int):
        await self.session_set(ctx, num, "Event", True)
    @commands.has_any_role('Mod Friend', 'Admins')
    @session.command()
    async def pending(self, ctx,  num : int):
        await self.session_set(ctx, num, "Status", "Pending")
        
    async def session_set(self, ctx, num : int, target, goal):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"):
                try:
                    db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {target: goal}})
                except BulkWriteError as bwe:
                    print(e)
                await ctx.channel.send("Session updated.")
                await generateLog(self, ctx, num)
            else:
                await ctx.channel.send("This session has already been processed")
        else:
            await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
                        
    @session.group()
    async def ddmrw(self, ctx):	
        pass
    
    @ddmrw.command()
    async def optout(self, ctx, num :int):
        await self.ddmrwOpt(ctx, num, False)
    @ddmrw.command()
    async def optin(self, ctx, num : int):
        await self.ddmrwOpt(ctx, num, True)
    
    # allows DMs to opt in or out of DDMRW
    async def ddmrwOpt(self, ctx, num : int, goal):
        logData =db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"):
                if (str(ctx.author.id) == sessionInfo["DM"]["ID"] or "Mod Friend" in [r.name for r in ctx.author.roles] and sessionInfo["DDMRW"]):
                    try:
                        db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {"DM.DM Double": goal}})
                        await generateLog(self, ctx, num)
                    except BulkWriteError as bwe:
                        print(bwe)
                else:
                    await ctx.channel.send("You were not the DM of that session or it was not DDMRW.")
            else:
                await ctx.channel.send("This session has already been processed")
        else:
            await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
      
    #@session.command()
    async def optout2xR(self, ctx,  num : int):
        await self.userOpt(ctx, num, "2xR", False)
    #@session.command()
    async def optin2xR(self, ctx,  num : int):
        await self.userOpt(ctx, num, "2xR", True)
        
    #@session.command()
    async def optout2xI(self, ctx,  num : int):
        await self.userOpt(ctx, num, "2xI", False)
    #@session.command()
    async def optin2xI(self, ctx,  num : int):
        await self.userOpt(ctx, num, "2xI", True)
        
    async def userOpt(self, ctx, num : int, target, goal):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"):
                if sessionInfo["Role"] != "": 
                    players = sessionInfo["Players"]
                    players[sessionInfo["DM"]["ID"]] = sessionInfo["DM"]
                    user_id = str(ctx.author.id)
                    if user_id in players.keys():
                        if "Guild" in players[user_id] and players[user_id]["Guild"] in sessionInfo["Guilds"].keys():
                            player_target = f"Players.{ctx.author.id}."
                            if user_id == sessionInfo["DM"]["ID"]:
                                player_target = "DM."
                            try:
                                db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {player_target+target: goal}})
                            except BulkWriteError as bwe:
                                print(bwe)
                            else:
                                await ctx.channel.send("Session updated.")
                                await generateLog(self, ctx, num) 
                        else:
                            await ctx.channel.send("Your character's guild is not valid for this session.")
                        
                    else:
                        await ctx.channel.send("You were not part of the session")
            else:
                await ctx.channel.send("This session has already been processed")
        else:
            await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
    
    @session.command()
    async def setGold(self, ctx,  num : int, gold_modifier : int):
        if gold_modifier < 0 or gold_modifier > 100:
            await ctx.channel.send(f"{gold_modifier} is an invalid percentage.")
            return
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if( sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied"): # True):#
                mod = "Mod Friend" in [r.name for r in ctx.author.roles]
                if( (str(ctx.author.id) == sessionInfo["DM"]["ID"]) or mod):
                    try:
                        db.logdata.update_one({"_id": sessionInfo["_id"]}, {"$set": {"Gold Modifier": gold_modifier}})
                    except BulkWriteError as bwe:
                        print(e)
                    
                    await ctx.channel.send("Session updated.")
                    await generateLog(self, ctx, num)
                else:
                    await ctx.channel.send("You do not have the permissions to perform this change to the session.")
            else:
                await ctx.channel.send("This session has already been processed")
        else:
            await ctx.channel.send("The session could not be found, please double check your number or if the session has already been approved.")
    
    
    @commands.has_any_role('Mod Friend', 'A d m i n')
    @session.command()
    async def genLog(self, ctx,  num : int):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if(sessionInfo):
            await generateLog(self, ctx, num) 
            await ctx.channel.send("Log has been generated.")
    
        else:
            await ctx.channel.send("The session could not be found, please double check your number.")
    
    @session.command()
    async def log(self, ctx,  num : int, *, editString=""):
        # The real Bot
        botUser = self.bot.user
        # Logs channel 
        channel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"]) 
        editMessage = await channel.fetch_message(num)

        async with channel.typing():
            if not editMessage or editMessage.author != self.bot.user:
                delMessage = await ctx.channel.send(content=f"I couldn't find your session with ID `{num}`. Please try again. I will delete your message and this message in 10 seconds.\n\n:warning: **DO NOT DELETE YOUR OWN MESSAGE.** :warning")
                await asyncio.sleep(10) 
                await delMessage.delete()
                await ctx.message.delete() 
                return


        logData =db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if( sessionInfo):
            if (str(ctx.author.id) == sessionInfo["DM"]["ID"] or 
                "Mod Friend" in [r.name for r in ctx.author.roles]):
                pass
                 
            else:
                await ctx.channel.send("You were not the DM of that session and cannot edit it.")
                return 
        else:
            await ctx.channel.send("The session could not be found. Please double check your number or if the session has already been approved.")
            return
        sessionLogEmbed = editMessage.embeds[0]

        if sessionInfo["Status"] != "Approved" and sessionInfo["Status"] != "Denied":
            summaryIndex = sessionLogEmbed.description.find('Summary**')
            sessionLogEmbed.description = sessionLogEmbed.description[:summaryIndex]+"Summary**\n" + editString+"\n"
        else:
            sessionLogEmbed.description += "\n"+editString
        try:
            await editMessage.edit(embed=sessionLogEmbed)
        except Exception as e:
            delMessage = await ctx.channel.send(content=f"The maximum length of the session log summary is 2048 symbols. Please reduce the length of your summary.")
        else:
            try:
                delMessage = await ctx.channel.send(content=f"I've edited the summary for quest #{num}.\n```{editString}```\nPlease double-check that the edit is correct. I will now delete your message and this one in 30 seconds.")
            except Exception as e:
                delMessage = await ctx.channel.send(content=f"I've edited the summary for quest #{num}.\nPlease double-check that the edit is correct. I will now delete your message and this one in 30 seconds.")
        
        await asyncio.sleep(30) 
        try:
            await ctx.message.delete()
        except Exception as e:
            pass
        await delMessage.delete()
        
async def setup(bot):
    await bot.add_cog(Log(bot))