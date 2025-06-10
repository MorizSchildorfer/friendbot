import pytz
import time
import requests
import re
import shlex
import decimal
import random
import discord
import asyncio
from cogs.guild import pin_control
from discord.utils import get        
from discord.ext import commands
from math import ceil, floor
from itertools import product      
from datetime import datetime, timezone,timedelta
from bfunc import gameCategory, commandPrefix, roleArray, timezoneVar, currentTimers, db, traceBack, settingsRecord, alphaEmojis, roleArray, cp_bound_array, settingsRecord
from cogs.util import callAPI, paginate, timeConversion, noodleRoleArray, disambiguate, noodleCheck, noodleBarrier
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError


def game_channel_check(channel):
    channel_name = str(channel.category.name).lower()
    return "campaign" in channel_name or "game rooms" in channel_name
    
def is_campaign_session(sessionDict):
    return "campaign" == sessionDict["Type"].lower()
    
async def generateLog(self, ctx, num : int, sessionInfo=None):
    logData = db.logdata
    if sessionInfo == None:
        sessionInfo = logData.find_one({"Log ID": int(num)})
    if sessionInfo == None:
        print("Invalid Log")
        return None
        
    channel = self.bot.get_channel(sessionInfo["Log Channel ID"]) 
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
    
    game = sessionInfo["Game"]
    start = sessionInfo["Start"] 
    end = sessionInfo["End"] 
    
    
    players = sessionInfo["Players"] 
    #dictionary indexed by user id
    # {cp, magic items, consumables, inventory, partial, status, user id, character id, character name, character level, character cp, double rewards, guild, }
    
    dm = sessionInfo["DM"] 
    # {cp, magic items, consumables, inventory, partial, status, user id, character id, character name, character level, character cp, double rewards, guild, noodles}
    
    bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
    
    allRewardStrings = {}
        
    for k, player in players.items():
        player_duration = player["Rewards"] * (1 + bonusDouble) 
        treasureString = timeConversion(player_duration) 
        
        groupString = ""
        groupString += bonusDouble * "Bonus "
        groupString += f'Rewards:\n{treasureString}'
        
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
    
    dmDouble = sessionInfo["DDMRW"]
    dm_double_string = ""
    dm_double_string += dmDouble * "DDMRW "
    dm_double_string += bonusDouble * "Bonus "
    dm_time_bank = dm["Rewards"] * (1 + bonusDouble + dmDouble) * 1.5
    dmRewardsList = []
    #DM REWARD MATH STARTS HERE
    
    dmEntry = usersCollection.find_one({"User ID": str(dm["ID"])})
    if 'Noodles' not in dmEntry:
        dmEntry['Noodles'] = 0
    if "DM Time" not in dmEntry:
        dmEntry["DM Time"] = 0
    noodles = dmEntry["Noodles"]
    # Noodles Math
    
        
    duration = end - start - paused_time
    noodlesGained = int((duration + dmEntry["DM Time"])//(3*3600))
    
    # add the noodles to the record or start a record if needed
        
    #new noodle total
    noodleFinal = noodles + noodlesGained
    noodleFinalString = f"{str(noodleFinal)}:star: (+{noodlesGained}:star:)"

    # clear the embed message to repopulate it
    sessionLogEmbed.clear_fields() 
    # for every unique set of TP rewards
    for key, value in allRewardStrings.items():
        temp = ""
        # for every player of this reward
        for v in value:
            temp += f"{v['Mention']}\n"
        # add the information about the reward to the embed object
        sessionLogEmbed.add_field(name=f"**{key}**\n", value=temp, inline=False)
        # add temp to the total output string

    noodleCongrats = noodleBarrier(noodles, noodleFinal)
    game_channel = get(ctx.guild.text_channels, name = sessionInfo['Channel'])
    if not game_channel:
        game_channel = sessionInfo['Channel']
    else:
        game_channel = f"<#{game_channel.id}>"
    sessionLogEmbed.title = f"\n**{game}**"
    sessionLogEmbed.description = f"{game_channel}\n**Start**: {datestart} EDT\n**End**: {dateend} EDT\n**Runtime**: {totalDuration}\n**General "+description
    status_text = "Log is being processed!"
    await editMessage.clear_reactions()
    if sessionInfo["Status"] == "Approved":
        status_text = "✅ Log approved! The DM and players have received their rewards and their characters can be used in further one-shots."
    elif sessionInfo["Status"] == "Denied":
        status_text = "❌ Log Denied! Characters have been cleared"
        noodleCongrats = ""
    elif sessionInfo["Status"] == "Pending":
        status_text = "❔ Log Pending! DM has been messaged due to session log issues."
        await editMessage.add_reaction('<:nipatya:408137844972847104>')
    sessionLogEmbed.set_footer(text=f"Game ID: {num}\n{status_text}\n{noodleCongrats}")
    if noodleCongrats:
        await editMessage.add_reaction('🎉')
        await editMessage.add_reaction('🎊')
        await editMessage.add_reaction('🥳')
        await editMessage.add_reaction('🍾')
        await editMessage.add_reaction('🥂')
    
    # add the field for the DM's player rewards
    dm_name_text = f"DM {dm_double_string} Rewards: "+ timeConversion(dm_time_bank)
    # if no character signed up then the character parts are excluded
    sessionLogEmbed.add_field(value=f"{dm['Mention']}\n{noodleFinalString}", name=dm_name_text)
    await editMessage.edit(embed=sessionLogEmbed)
    
    pass

class GenericTimer(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
       
    def is_log_channel():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"])
        return commands.check(predicate)
    async def cog_command_error(self, ctx, error):
        msg = None
        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command `{commandPrefix}rpg {ctx.invoked_with}` requires an additional keyword to the command or is invalid, please try again!')
            return
        if isinstance(error, commands.CommandOnCooldown):
            msg = f"The command is on cooldown." 
        elif isinstance(error, discord.NotFound):
            msg = "The session log could not be found."
        elif isinstance(error, commands.MissingAnyRole):
            await ctx.channel.send("You do not have the required permissions for this command.")
            return
        elif isinstance(error, commands.BadArgument):
            await ctx.channel.send("One of your parameters was of an incorrect type.")
            return
        else:
            if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
              msg = "There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command."

            if msg:
                if ctx.command.name == "prep":
                    msg += f'Please follow this format:\n```yaml\n{commandPrefix}rpg timer prep "@player1, @player2, [...]" "session name"```'
        if msg:
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            if ctx.channel.mention in currentTimers and "State" in currentTimers[ctx.channel.mention]:
                currentTimers[ctx.channel.mention]["State"] = "Crashed"
                await ctx.channel.send(f"This timer has crashed. The DM can use `{commandPrefix}rpg timer resume` to continue the timer.")
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)
    
        
    @commands.group(case_insensitive=True)
    async def rpg(self, ctx):
        pass
    
    @rpg.group(aliases=['t'])
    async def timer(self, ctx):	
        pass

    @timer.command()
    async def help(self,ctx):
        helpCommand = self.bot.get_command('help')
        await ctx.invoke(helpCommand, pageString='ttrpg')

    def startsWithCheck(self, message, target):
        return any([message.content.startswith(f"{commandPrefix}{x} {y} {target}") for x,y in [("rpg", "t"), ("rpg", "t"), ("rpg", "timer"), ("rpg", "timer")]])
        
    """
    This is the command meant to setup a timer and allowing people to sign up. Only one of these can be active at a time in a single channel
    The command gets passed in a list of players as a single entry userList
    the last argument passed in will be treated as the quest name
    """
    @commands.cooldown(1, float('inf'), type=commands.BucketType.channel) 
    @commands.has_any_role('D&D Friend', 'Campaign Friend')
    @timer.command()
    async def prep(self, ctx, userList, game = ""):
        
        ctx.message.content = ctx.message.content.replace("“", "\"").replace("”", "\"")
        #this checks that only the author's response with one of the Tier emojis allows Tier selection
        #the response is limited to only the embed message
        
        #simplifying access to various variables
        channel = ctx.channel
        author = ctx.author
        #the name shown on the server
        user = author.display_name
        #the general discord name
        userName = author.name
        if game == "":
            game = ctx.channel.name
        guild = ctx.guild
        #information on how to use the command, set up here for ease of reading and repeatability
        prepFormat =  f'Please follow this format:\n```yaml\n{commandPrefix}rpg timer prep "@player1, @player2, [...]" "session name"(*)```***** - The session name is optional.'
        
        usersCollection = db.users
        dm_record_check = list(usersCollection.find({"User ID": str(author.id)}))
        if len(dm_record_check) < 1:
            await channel.send(f"The DM has no DB record. Use the `$user` command in a log channel.")
            self.timer.get_command('prep').reset_cooldown(ctx)
            return 
            
        gameInfo = {"Players" : {}, 
                            "DM" : {"Member" : author, "DB Entry": dm_record_check[0]},
                            "Game" : game,
                            }
        campaignRecords = None
        #prevent the command if not in a proper channel (game/campaign)
        if "campaign" in channel.category.name.lower(): #!= settingsRecord[ctx.guild.id]["Campaign Rooms"]:
            gameInfo["Type"] = "Campaign"
            campaignCollection = db.campaigns
            campaignRecords = campaignCollection.find_one({"Channel ID": f"{ctx.channel.id}"})
            if not campaignRecords:
                await channel.send(f"There are no campaigns in this channel")
                self.timer.get_command('prep').reset_cooldown(ctx)
                return 
            gameInfo["Campaign"] = campaignRecords
        elif "game rooms" in channel.category.name.lower(): #!= settingsRecord[ctx.guild.id]["Campaign Rooms"]:
            gameInfo["Type"] = "TTRPG"
            #exception to the check above in case it is a testing channel
        elif str(channel.id) in settingsRecord['Test Channel IDs']:
            pass
        else: 
            #inform the user of the correct location to use the command and how to use it
            await channel.send('Try this command in a play channel! ' + prepFormat)
            #permit the use of the command again
            self.timer.get_command('prep').reset_cooldown(ctx)
            return
        #check if the userList was given in the proper way or if the norewards option was taken, this avoids issues with the game name when multiple players sign up
        if '"' not in ctx.message.content:
            #this informs the user of the correct format
            await channel.send(f"Make sure you put quotes **`\"`** around your list of players and retry the command!\n\n{prepFormat}")
            #permit the use of the command again
            self.timer.get_command('prep').reset_cooldown(ctx)
            return

        #create an Embed object to use for user communication and information
        prepEmbed = discord.Embed()

        # create a list of all expected players for the game so far, including the user who will always be the first 
        # element creating an invariant of the DM being the first element
        playerRoster = ctx.message.mentions
        if author in playerRoster:
            playerRoster.remove(author)


        #clear the embed message
        prepEmbed.clear_fields()
        # if is not a campaign add the seleceted tier to the message title and inform the users about the possible commands (signup, add player, remove player, add guild, use guild reputation)

        # otherwise give an appropriate title and inform about the limited commands list (signup, add player, remove player)
        prepEmbed.title = f"{game} ({gameInfo['Type']})"
        prepEmbed.description = f"""__**Command Checklist**__
**1. Players sign up:**• {commandPrefix}rpg timer signup
**2. DM adds or removes players (optional):**• **Add**: {commandPrefix}rpg timer add @player
• **Remove**: {commandPrefix}rpg timer remove @player
**3. DM cancels or starts the rpg session:**• **Cancel**: {commandPrefix}rpg timer cancel
• **Start**: {commandPrefix}rpg timer start"""

         #set up the special field for the DM character
        prepEmbed.add_field(name = f"{author.display_name} **(DM)**", value = author.mention)
        
        
        #setup a variable to store the string showing the current roster for the game
        rosterString = ""
        #now go through the list of the user/DM and the initially given player list and build a string
        for p in playerRoster:
            prepEmbed.add_field(name=p.display_name, value='Has not yet signed up for the session.', inline=False)
        playerRoster = [author] + playerRoster
        #set up a field to inform the DM on how to start the timer or how to get help with it
        prepEmbed.set_footer(text= f"Use the following command to see a list of ttrpg timer commands: {commandPrefix}help ttrpg")

        prepEmbedMsg = await channel.send(embed=prepEmbed)

        
        
        # create a list of all possible commands that could be used during the signup phase
        timerAlias = ["timer", "t"]
        timerCommands = ['signup', 'cancel', 'start', 'add', 'remove']
      
        timerCombined = []
        
        
        # pair up each command group alias with a command and store it in the list
        for x in product(timerAlias, timerCommands):
            timerCombined.append(f"{commandPrefix}rpg {x[0]} {x[1]}")
        """
        This is the heart of the command, this section runs continuously until the start command is used to change the looping variable
        during this process the bot will wait for any message that contains one of the commands listed in timerCombined above 
        and then invoke the appropriate method afterwards, the message check is also limited to only the channel signup was called in
        Relevant commands all have blocks to only run when called
        """
        #set up a variable for the current state of the timer
        timerStarted = False
        while not timerStarted:
            # get any message that managed to satisfy the check described above, it has to be a command as a result
            msg = await self.bot.wait_for('message', check=lambda m: any(x in m.content for x in timerCombined) and m.channel == channel)
            """
            the following commands are all down to check which command it was
            the checks are all doubled up since the commands can start with $t and $timer
            the current issue is that it will respond to any message containing these strings, not just when they are at the start
            """
            
            """
            The signup command has different behaviors if the signup is from the DM, a player or campaign player
            
            """
            if self.startsWithCheck(msg, "signup"):
                # if the message author is the one who started the timer, call signup with the special DM moniker
                # the character is extracted from the message in the signup command 
                # special behavior:
                playerChar = None
                if msg.author in playerRoster:
                    playerChar = await ctx.invoke(self.timer.get_command('signup'), char=None, author=msg.author, campaignRecords = campaignRecords) 
                    if playerChar:
                        gameInfo["Players"][msg.author.id] = playerChar
                        prepEmbed.set_field_at(playerRoster.index(msg.author), name=msg.author.display_name, value= f"{msg.author.mention}", inline=False)
                        
                # if the message author has not been permitted to the game yet, inform them of such
                # a continue statement could be used to skip the following if statement
                else:
                    await channel.send(f"***{msg.author.display_name}***, you must be on the player roster in order to signup.")
                

            # similar issues arise as mentioned above about wrongful calls
            elif self.startsWithCheck(msg, "add"):
                if await self.permissionCheck(msg, author):
                    # this simply checks the message for the user that is being added, the Member object is returned
                    addUser = await self.addDuringPrep(ctx, msg=msg)
                    #failure to add a user does not have an error message if no user is being added
                    if addUser is None:
                        pass
                    elif addUser not in playerRoster:
                        # set up the embed fields for the new user if they arent in the roster yet
                        prepEmbed.add_field(name=addUser.display_name, value='Has not yet signed up for the session.', inline=False)
                        # add them to the roster
                        playerRoster.append(addUser)
                    else:
                        #otherwise inform the user of the failed add
                        await channel.send(f'***{addUser.display_name}*** is already on the timer.')

            # same issues arise again
            
            elif self.startsWithCheck(msg, "remove"):
                if await self.permissionCheck(msg, author):
                    # this simply checks the message for the user that is being added, the Member object is returned
                    removeUser = await self.removeDuringPrep(ctx, msg=msg, start=playerRoster)

                    if removeUser is None:
                        pass
                    #check if the user is not the DM
                    elif playerRoster.index(removeUser) != 0:
                        # remove the embed field of the player
                        prepEmbed.remove_field(playerRoster.index(removeUser))
                        # remove the player from the roster
                        playerRoster.remove(removeUser)
                        # remove the player from the signed up players
                        if removeUser.id in gameInfo["Players"]:
                            del gameInfo["Players"][removeUser.id]
                    else:
                        await channel.send('You cannot remove yourself from the timer.')

            #the command that starts the timer, it does so by allowing the code to move past the loop
            elif self.startsWithCheck(msg, "start"):
                if await self.permissionCheck(msg, author):
                    if len(gameInfo["Players"].keys()) == -1:
                        await channel.send(f'There are no players signed up! Players, use the following command to sign up to the quest with your character before the DM starts the timer:\n```yaml\n{commandPrefix}rpg timer signup```') 
                    else:
                        timerStarted = True
            #the command that cancels the timer, it does so by ending the command all together                              
            elif self.startsWithCheck(msg, "cancel"):
                if await self.permissionCheck(msg, author):
                    await channel.send(f'Timer cancelled! If you would like to prep a new quest, {prepFormat}') 
                    # allow the call of this command again
                    self.timer.get_command('prep').reset_cooldown(ctx)
                    return
            await prepEmbedMsg.delete()
            
            prepEmbedMsg = await channel.send(embed=prepEmbed)
        await ctx.invoke(self.timer.get_command('start'), userList = gameInfo, game=game, campaignRecords = campaignRecords)


    """
    This is the command used to allow people to enter their characters into a game before the timer starts
    char is a message object which makes the default value of "" confusing as a mislabel of the object
    role is a string indicating which tier the game is for or if the player signing up is the DM
    resume is boolean quick check to see if the command was invoked by the resume command   
        this property is technically not needed since it could quickly be checked, 
        but it does open the door to creating certain behaviors even if not commaning from $resume
        the current state would only allow this from prep though, which never sets this property
        The other way around does not work, however since checking for it being true instead of checking for
        the invoke source (ctx.invoked_with == "resume") would allow manual calls to this command
    """
    @timer.command()
    async def signup(self,ctx, char=None, author=None, campaignRecords = None):
        #check if the command was called using one of the permitted other commands
        if ctx.invoked_with == 'prep' or ctx.invoked_with == "resume":
            # set up a informative error message for the user
            signupFormat = f'Please follow this format:\n```yaml\n{commandPrefix}rpg timer signup```'
            # create an embed object
            # This is only true if this is during a campaign, in that case there are no characters or consumables
            if char is None and author.id != ctx.author.id: 
                usersCollection = db.users
                # grab the DB records of the first user with the ID of the author
                userRecord = usersCollection.find_one({"User ID": str(author.id)})
                if not userRecord:
                    await ctx.channel.send(f"{author.mention} could not be found in the DB.")
                elif(not campaignRecords or ("Campaigns" in userRecord and campaignRecords["Name"] in userRecord["Campaigns"].keys() and userRecord["Campaigns"][campaignRecords["Name"]]["Active"])):
                    # this indicates a selection of user info that seems to never be used
                    return {"Member" : author, "DB Entry": userRecord}
                else:
                    await ctx.channel.send(f"{author.mention} could not be found as part of the campaign.")
        return None

    
    """
    This command handles all the intial setup for a running timer
    this includes setting up the tracking variables of user playing times,
    """
    @timer.command()
    async def start(self, ctx, userList="", game="", campaignRecords = None):
        # access the list of all current timers, this list is reset on reloads and resets
        # this is used to enable the list command and as a management tool for seeing if the timers are working
        global currentTimers
        # start cannot be invoked by resume since it has its own structure
        if ctx.invoked_with == 'prep': 
            # make some common variables more accessible
            channel = ctx.channel
            author = ctx.author
            user = author.display_name
            userName = author.name
            guild = ctx.guild
            # this uses the invariant that the DM is always the first signed up
            dmChar = userList["DM"]

            userList["State"] = "Running"
            # get the current time for tracking the duration
            startTime = time.time()
            userList["Start"] = startTime
            # format the time for a localized version defined in bfunc
            datestart = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%d-%y %I:%M %p")
            userList["datestart"] = datestart
            
            userList["Paused"] = False
            userList["Paused Time"] = 0
            userList["Last Pause"] = startTime
            userList["Pause Type"] = 0
            userList["DDMRW"] = settingsRecord["ddmrw"]
            
            for p_key, p_entry in userList["Players"].items():
                p_entry["State"] = "Full"
                p_entry["Latest Join"] = startTime
                p_entry["Duration"] = 0
              
            # Inform the user of the started timer
            await channel.send(content=f"Starting the timer for **{game}** ({userList['Type']}).\n" )
            # add the timer to the list of runnign timers
            currentTimers[channel.mention] = userList
            
            # set up an embed object for displaying the current duration, help info and DM data
            stampEmbed = discord.Embed()
            stampEmbed.title = f'**{game}**: 0 Hours 0 Minutes\n'
            stampEmbed.set_footer(text=f'#{ctx.channel}\nUse the following command to see a list of timer commands: {commandPrefix}help ttrpg')
            stampEmbed.set_author(name=f'DM: {userName}', icon_url=author.display_avatar)

            for u in userList["Players"].values():
                stampEmbed.add_field(name=f"**{u['Member'].display_name}**", value=u['Member'].mention, inline=False)
            

            stampEmbedmsg = await channel.send(embed=stampEmbed)

            # During Timer
            await self.duringTimer(ctx, datestart, startTime, userList, game, author, stampEmbed, stampEmbedmsg,dmChar, campaignRecords)
            
            # allow the creation of a new timer
            self.timer.get_command('prep').reset_cooldown(ctx)
            # when the game concludes, remove the timer from the global tracker
            del currentTimers[channel.mention]
            return
            
    """
    This command gets invoked by duringTimer and resume
    user -> Member object when passed in which makes the string label confusing
    start -> a dictionary of duration strings and player entry lists
    msg -> the message that caused the invocation, used to find the name of the character being added
    dmChar -> player entry of the DM of the game
    user -> the user being added, required since this command is invoked by add as well where the author is not the user necessarily
    resume -> used to indicate if this was invoked by the resume process where the messages are being retraced
    """
    @timer.command()
    async def addme(self,ctx, *, msg=None, start="", user="", dmChar=None, campaignRecords = None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            # user found is used to check if the user can be found in one of the current entries in start
            addUser = user
            channel = ctx.channel
                
            # make sure that only the the relevant user can respond
            def addMeEmbedCheck(r, u):
                sameMessage = False
                if addEmbedmsg.id == r.message.id:
                    sameMessage = True
                return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and (u == dmChar["Member"])
            startTime = time.time()
            
            userFound = addUser.id in start["Players"]
            
            # if we didnt find the user we now need to the them to the system
            if not userFound:
                # first we invoke the signup command
                # no character is necessary if there are no rewards
                # this will return a player entry
                userInfo =  await ctx.invoke(self.timer.get_command('signup'), char=None, author=addUser, campaignRecords = campaignRecords) 
                # if a character was found we then can proceed to setup the timer tracking
                if userInfo:
                    # create an embed object for user communication
                    addEmbed = discord.Embed()
                    # get confirmation to add the player to the game
                    addEmbed.title = f"Add ***{addUser.display_name}*** to timer?"
                    addEmbed.description = f"***{addUser.mention}*** is requesting to be added to the timer.\n\n✅: Add to timer\n\n❌: Deny"
                    # send the message to communicate with the DM and get their response
                    # ping the DM to get their attention to the message
                    addEmbedmsg = await channel.send(embed=addEmbed, content=dmChar["Member"].mention)
                    await addEmbedmsg.add_reaction('✅')
                    await addEmbedmsg.add_reaction('❌')

                    try:
                        # wait for a response from the user
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=addMeEmbedCheck , timeout=60)
                    # cancel when the user doesnt respond within the timefram
                    except asyncio.TimeoutError:
                        await addEmbedmsg.delete()
                        await channel.send(f'Timer addme cancelled. Try again using the following command:\n```yaml\n{commandPrefix}rpg timer addme```')
                        # cancel this command and avoid things being added to the timer
                        return start
                    else:
                        await addEmbedmsg.clear_reactions()
                        # cancel if the DM wants to deny the user
                        if tReaction.emoji == '❌':
                            await addEmbedmsg.edit(embed=None, content=f"Request to be added to timer denied.")
                            await addEmbedmsg.clear_reactions()
                            # cancel this command and avoid things being added to the timer
                            return start
                        await addEmbedmsg.edit(embed=None, content=f"I've added ***{addUser.display_name}*** to the timer.")
                        userInfo["Duration"] = 0
                        start["Players"][addUser.id] = userInfo
                else:
                    await ctx.channel.send(embed=None, content=f"***{addUser.display_name}*** could not be added to the timer.")
                    return start
            userInfo = start["Players"][addUser.id]
            userInfo["Latest Join"] = startTime
            userInfo["State"] = "Partial"
            return start
    """
    This command is used to add players to the prep list or the running timer
    The code for adding players to the timer has been refactored into 'addme' and here just limits the addition to only one player
    prep does not pass in any value for 'start' but prep = True
    There is an important distinction between checking for invoked_with == 'prep' and prep = True
    the former would not be true if the resume command was used, but the prep property still allows to differentiate between the two stages
    This command returns two different values, if called during the prep stage then the member object of the player is returned, otherwise it is a dictionary as explained in duringTimer startTimes
    msg -> the message that caused the invocation of this command
    start-> this is a confusing variable, if this is called during prep it is returned as a member object and no value is passed in
        if called during resume than it is a timer dictionary as described in duringTimer startTimes
        this works because in that specific case start will be returned
    """
    async def addDuringPrep(self,ctx, *, msg, start=None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            guild = ctx.guild
            #if normal mentions were used then no users would have to be gotten later
            addList = msg.mentions
            addUser = None
            # limit adds to only one player at a time
            if len(addList) > 1:
                await ctx.channel.send(content=f"I cannot add more than one player! Please try the command with one player and check your format and spelling.")
                return None
            # if there was no player added
            elif addList == list():
                await ctx.channel.send(content=f"You cannot sign up to a timer unless the DM has added you to the prepared timer!")
                return None
            else:
                # get the first ( and only ) mentioned user 
                return addList[0]
            return start
    
    async def addDuringTimer(self,ctx, *, msg, start=None, dmChar=None, campaignRecords = None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            guild = ctx.guild
            #if normal mentions were used then no users would have to be gotten later
            addList = msg.mentions
            addUser = None
            # limit adds to only one player at a time
            if len(addList) > 1:
                await ctx.channel.send(content=f"I cannot add more than one player! Please try the command with one player and check your format and spelling.")
                return None
            # if there was no player added
            elif addList == list():
                await ctx.channel.send(content=f"You forgot to mention a player! Please try the command again and ping the player.")
                return None
            else:
                # get the first ( and only ) mentioned user 
                addUser = addList[0]
                # in the duringTimer stage we need to add them to the timerDictionary instead
                # the dictionary gets manipulated directly which affects all versions
                #otherwise we need to add the user properly to the timer and perform the setup
                await ctx.invoke(self.timer.get_command('addme'), start=start, msg=msg, user=addUser, dmChar=dmChar, campaignRecords = campaignRecords) 
            return start


    async def pause(self,ctx, userInfo="", msg=""):
        channel = ctx.channel
        if userInfo["Paused"]:
            await channel.send(f'Sorry, the timer is already paused.')
            return
        msg_split = msg.content.split(' ', 3)
        if len(msg_split)<4:
            reason = None
        else:
            reason =  msg_split[3].strip()
        if not reason:
            await channel.send(f'Sorry, you need to provide a reason to pause the timer.')
            return
        
        pause_embed = discord.Embed()
        pause_embed.title = "Which kind of issue are you having?"
        pause_embed.description = """🇦: Personal [30 Minutes]
        🇧: Tech [1 Hour]"""
        pause_msg = await channel.send(embed=pause_embed)
        choice = await disambiguate(2, pause_msg, msg.author, cancel=False)
        if choice is None or choice == -1:
            #stop if no response was given within the timeframe
            await pause_msg.edit(embed=None, content="Command cancelled. Try using the command again.")
            return
        options = ["Personal", "Tech"]
        await pause_msg.edit(embed=None, content=f"Timer Paused. {options[choice]} Reason:\n```{reason}```Use `$rpg timer unpause` to continue the timer")
        
        pause_time = time.time()
        userInfo["Paused"] = True
        userInfo["Last Pause"] = pause_time
        userInfo["Pause Type"] = choice
        for user_dic in userInfo["Players"].values():
            if user_dic["State"] not in ["Dead", "Removed"]:
                user_dic["Duration"] += pause_time - user_dic["Latest Join"] 
                user_dic["Latest Join"] = pause_time                 
        return
        
    async def unpause(self,ctx, userInfo="", silent=False):
        channel = ctx.channel
        if not userInfo["Paused"]:
            await channel.send(f'Sorry, the timer is already running.')
            return
        unpause_time = time.time()
        userInfo["Paused"] = False
        userInfo["Paused Time"] += unpause_time - userInfo["Last Pause"]
        for user_dic in userInfo["Players"].values():
            if user_dic["State"] not in ["Dead", "Removed"]:
                user_dic["Latest Join"] = unpause_time     
        userInfo["DM"]["Latest Join"] = unpause_time
        if not silent:
            await channel.send(f'The timer is now runnning.')        
        return

    @timer.command()
    async def removeme(self,ctx, msg=None, start="", user=""):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            
            # user found is used to check if the user can be found in one of the current entries in start
            userFound = user.id in start["Players"]
            # if no entry could be found we inform the user and return the unchanged state
            if not userFound:
                await ctx.channel.send(content=f"***{user}***, I couldn't find you on the timer to remove you.") 
                return start
            user_dic = start["Players"][user.id]
            
            if user_dic["State"] == "Removed": 
                # since they have been removed last time, they cannot be removed again
                await ctx.channel.send(content=f"You have already been removed from the timer.")  
            
            # if the player has been there the whole time
            else:
                user_dic["State"] = "Removed"
                if not start["Paused"]:
                    endTime = time.time()
                    user_dic["Duration"] += endTime - user_dic["Latest Join"] 
                await ctx.channel.send(content=f"***{user}***, you have been removed from the timer.")
        return start

    
    """
    This command is used to remover players from the prep list or the running timer
    The code for removing players from the timer has been refactored into 'removeme' and here just limits the addition to only one player
    prep does not pass in any value for 'start' but prep = True
    msg -> the message that caused the invocation of this command
    start-> this would be clearer as a None object since the final return element is a Member object
    """
    async def removeDuringPrep(self,ctx, msg, start=None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            guild = ctx.guild
            removeList = msg.mentions
            removeUser = ""
            
            if removeList == list():
                await ctx.channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
                return None
            elif len(removeList) > 1:
                await ctx.channel.send(content=f"I cannot remove more than one player! Please try the command with one player and check your format and spelling.")
                return None
            elif not removeList[0] in start:
                await ctx.channel.send(content=f"I cannot find the player to remove in the roster.")
                return None
            elif removeList != list():
                return removeList[0]
            else:
                await ctx.channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
            return start
            
    async def removeDuringTimer(self,ctx, msg, start=None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            guild = ctx.guild
            removeList = msg.mentions
            removeUser = ""

            if len(removeList) > 1:
                await ctx.channel.send(content=f"I cannot remove more than one player! Please try the command with one player and check your format and spelling.")
                return None

            elif removeList != list():
                removeUser = removeList[0]
                await ctx.invoke(self.timer.get_command('removeme'), start=start, msg=msg, user=removeUser)
            else:
                await ctx.channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
            return start

    """
    the command used to display the current state of the game timer to the users
    start -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    game -> the name of the running game
    stamp -> the start time of the game
    author -> the Member object of the DM of the game
    """
    @timer.command()
    async def stamp(self,ctx, stamp=0, game="", author="", start="", dmChar={}, embed="", embedMsg=""):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            # calculate the total duration of the game so far
            end = time.time()
            pause_duration = (end - start["Last Pause"])*start["Paused"]
            duration = end - start["Start"] - start["Paused Time"] - pause_duration
            durationString = timeConversion(duration)
            if start["Paused"]:
                pause_shift = 1800 * (start["Pause Type"]+1) + 90
                durationString = f"{durationString} || **PAUSE [{timeConversion(pause_shift-pause_duration)} Remaining]**"
            # reset the fields in the embed object
            embed.clear_fields()

            # fore every entry in the timer dictionary we need to perform calculations
            for key, v in start["Players"].items():
                if v["State"] == "Full":
                    embed.add_field(name= f"**{v['Member'].display_name}**", value=f"{v['Member'].mention} {timeConversion(duration)}", inline=False)
                elif v["State"] == "Removed":
                    pass
                else:
                    embed.add_field(name= f"**{v['Member'].display_name}**", value=f"{v['Member'].mention} {timeConversion(v['Duration'] + (end - v['Latest Join'])*(not start['Paused'] ))}", inline=False)
                
            
            # update the title of the embed message with the current time
            embed.title = f'**{game}**: {durationString}'
            msgAfter = False
            
            # we need separate advice strings if there are no rewards
            stampHelp = f"""```yaml
Command Checklist
- - - - - - - - -
1. DM adds a player or they join late:
   • DM adds: {commandPrefix}rpg timer add @player
   • Player joins: {commandPrefix}rpg timer addme
2. DM removes a player or they leave early:
   • DM removes: {commandPrefix}rpg timer remove @player
   • Player leaves: {commandPrefix}rpg timer removeme
3. DM stops the rpg session: {commandPrefix}rpg timer stop
4. DM pauses the rpg session: {commandPrefix}rpg timer pause reason```"""
            # check if the current message is the last message in the chat
            # this checks the 1 message after the current message, which if there is none will return an empty list therefore msgAfter remains False
            async for message in ctx.channel.history(after=embedMsg, limit=1):
                msgAfter = True
            # if it is the last message then we just need to update
            if not msgAfter:
                await embedMsg.edit(embed=embed, content=stampHelp)
            else:
                # otherwise we delete the old message and resend the time stamp
                if embedMsg:
                    await embedMsg.delete()
                embedMsg = await ctx.channel.send(embed=embed, content=stampHelp)

            return embedMsg

    @timer.command()
    @commands.has_any_role('Mod Friend', 'A d m i n')
    async def resetcooldown(self,ctx):
        self.timer.get_command('prep').reset_cooldown(ctx)
        await ctx.channel.send(f"Timer has been reset in #{ctx.channel}")
    
    @timer.command()
    @commands.cooldown(1, float('inf'), type=commands.BucketType.channel) 
    @commands.has_any_role('D&D Friend', 'Campaign Friend')
    async def resume(self,ctx):
    
        if ctx.channel.mention not in currentTimers:
            self.timer.get_command('resume').reset_cooldown(ctx)
            return
        userList = currentTimers[ctx.channel.mention]
        if userList["State"] != "Crashed":
            self.timer.get_command('resume').reset_cooldown(ctx)
            return
        dmChar = userList["DM"]
        author = dmChar["Member"]
        if author != ctx.author and not await self.permissionCheck(ctx.message, ctx.author):
            return
        datestart = userList["datestart"]
        startTime = userList["Start"]
        game = userList["Game"]
        userList["State"] = "Running"
        campaignRecords = None
        if is_campaign_session(userList):
            campaignRecords = userList["Campaign"]
        stampEmbed = discord.Embed()
        stampEmbed.title = f' a '
        stampEmbed.set_footer(text=f'#{ctx.channel}\nUse the following command to see a list of timer commands: {commandPrefix}help ttrpg')
        stampEmbed.set_author(name=f'DM: {author.name}', icon_url=author.display_avatar)
        stampEmbedMsg =  await self.stamp(ctx, stamp = startTime, game = game, start = userList ,embed = stampEmbed)
        await self.duringTimer(ctx, datestart, startTime, userList, game, author, stampEmbed, stampEmbedMsg, dmChar,campaignRecords)
        del currentTimers[ctx.channel.mention]
        self.timer.get_command('resume').reset_cooldown(ctx)
    
    
    #extracted the checks to here to generalize the changes
    async def permissionCheck(self, msg, author):
        # check if the person who sent the message is either the DM, a Mod or a Admin
        if not (msg.author == author or "Mod Friend".lower() in [r.name.lower() for r in msg.author.roles] or "A d m i n s".lower() in [r.name.lower() for r in msg.author.roles]):
            await msg.channel.send(f'You cannot use this command!') 
            return False
        else: 
            return True
    
    """
    This functions runs continuously while the timer is going on and waits for commands to come in and then invokes them itself
    datestart -> the formatted date of when the game started
    startTime -> the specific time that the game started
    startTimes -> the dictionary of all the times that players joined and the player entries at that point (format of entries found in signup)
        the keys for startTimes are of the format "{Tier} (Friend Partial or Full) Rewards: {duration}"
    author -> person in control (normally the DM)
    stampEmbed -> the Embed object containing the information in regards to current timer state
    stampEmbedMsg -> the message containing stampEmbed
    dmChar -> the character of the DM 
    guildsList -> the list of guilds involved with the timer
    """
    async def duringTimer(self,ctx, datestart, startTime, startTimes, game, author, stampEmbed, stampEmbedmsg, dmChar,campaignRecords):
        # if the timer is being restarted then we create a new message with the stamp command
        if ctx.invoked_with == "resume":
            stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, embed=stampEmbed, embedMsg=stampEmbedmsg)
        
        # set up the variable for the continuous loop
        timerStopped = False
        channel = ctx.channel
        user = author.display_name

        timerAlias = ["timer", "t"]

        #in no rewards games characters cannot die or get rewards
        
        timerCommands = ['stop', 'end', 'add', 'remove', 'stamp', 'pause', 'unpause']

      
        timerCombined = []
        #create a list of all command an alias combinations
        for x in product(timerAlias,timerCommands):
            timerCombined.append(f"{commandPrefix}rpg {x[0]} {x[1]}")
        
        #repeat this entire chunk until the stop command is given
        while not timerStopped:
            try:
                msg = await self.bot.wait_for('message', timeout=60.0, check=lambda m: (any(x in m.content for x in timerCombined)) and m.channel == channel)
                
                #unpause the timer
                if (self.startsWithCheck(msg, "unpause")):
                    if await self.permissionCheck(msg, author):
                        await self.unpause(ctx, userInfo=startTimes)
                        stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                #pause the timer
                elif (self.startsWithCheck(msg, "pause")):
                    if await self.permissionCheck(msg, author):
                        await self.pause(ctx, userInfo=startTimes, msg=msg)
                        stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                
                # this is the command used to stop the timer
                # it invokes the stop command with the required information, explanations for the parameters can be found in the documentation
                # the 'end' alias could be removed for minimal efficiancy increases
                
                if self.startsWithCheck(msg, "stop") or self.startsWithCheck(msg, "end"):
                    # check if the author of the message has the right permissions for this command
                    if await self.permissionCheck(msg, author):
                        await ctx.invoke(self.timer.get_command('stop'), gameInfo=startTimes, game=game, datestart=datestart, dmChar=dmChar, campaignRecords = campaignRecords)
                        return

                # this behaves just like add above, but skips the ambiguity check of addme since only the author of the message could be added
                elif self.startsWithCheck(msg, "addme") and '@player' not in msg.content:
                    # if the message author is the one who started the timer, call signup with the special DM moniker
                # the character is extracted from the message in the signup command 
                # special behavior:
                    startTimes = await ctx.invoke(self.timer.get_command('addme'), start=startTimes, msg=msg, user=msg.author, dmChar=dmChar, campaignRecords = campaignRecords)
                    stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif self.startsWithCheck(msg, "stamp"):
                    # if the message author is the one who started the timer, call signup with the special DM moniker
                # the character is extracted from the message in the signup command 
                # special behavior:
                    stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                # @player is a protection from people copying the command
                elif self.startsWithCheck(msg, "add") and '@player' not in msg.content:
                    # check if the author of the message has the right permissions for this command
                    if await self.permissionCheck(msg, author):
                        # update the startTimes with the new added player
                        await self.addDuringTimer(ctx, start=startTimes, msg=msg, dmChar = dmChar, campaignRecords = campaignRecords)
                        # update the msg with the new stamp
                        stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                # this invokes the remove command, since we do not pass prep = True through, the special removeme command will be invoked by remove
                elif self.startsWithCheck(msg, "removeme"):
                    startTimes = await ctx.invoke(self.timer.get_command('removeme'), start=startTimes, user=msg.author)
                    stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif self.startsWithCheck(msg, "remove"):
                    if await self.permissionCheck(msg, author): 
                        startTimes = await self.removeDuringTimer(ctx, msg=msg, start=startTimes)
                        stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
                

            except asyncio.TimeoutError:
                stampEmbedmsg = await ctx.invoke(self.timer.get_command('stamp'), stamp=startTime, game=game, author=author, start=startTimes, dmChar=dmChar, embed=stampEmbed, embedMsg=stampEmbedmsg)
            else:
                pass
            if startTimes["Paused"] and time.time()-60 - startTimes["Last Pause"] > 1800 * (startTimes["Pause Type"]+1):
                await channel.send(f"Pause limit exceeded. Timer has been stopped") 
                await ctx.invoke(self.timer.get_command('stop'), gameInfo=startTimes, game=game, datestart=datestart, dmChar=dmChar, campaignRecords = campaignRecords)
                timerStopped = True
        
    @timer.command(aliases=['end'])
    async def stop(self,ctx,*,gameInfo="", game="", datestart="", dmChar="", campaignRecords = None):
        if ctx.invoked_with == 'prep' or ctx.invoked_with == 'resume':
            
            if gameInfo["Paused"]:
                await self.unpause(ctx, userInfo=gameInfo, silent=True)
            
            end = time.time() + 3600 * 0
            allRewardStrings = {}
            guild = ctx.guild
            startTime = gameInfo["Start"]
            total_duration = end - startTime - gameInfo["Paused Time"]
            
            stopEmbed = discord.Embed()
            
            stopEmbed.colour = discord.Colour(0xffffff)
        
            players = {}
            for p_key, p_val in gameInfo["Players"].items():
                player = {}
                reward = end - p_val["Latest Join"] + p_val["Duration"]
                if p_val["State"] == "Removed":
                    reward = p_val["Duration"]
                player["Rewards"] = reward
                player["Mention"] = p_val['Member'].mention
                players[str(p_key)] = player

            # Session Log Channel
            if is_campaign_session(gameInfo):
                logChannel = ctx.channel
            else:
                logChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"])
            stopEmbed.clear_fields()
            stopEmbed.set_footer(text=None)
            dateend = datetime.fromtimestamp(end).astimezone(pytz.timezone(timezoneVar)).strftime("%b-%d-%y %I:%M %p")
            absoluteDuration = timeConversion(end - startTime)

            stopEmbed.description = f"**{game}**\n**Start**: {datestart} EDT\n**End**: {dateend} EDT\n**Runtime**: {absoluteDuration}\nPut your summary here."

            playerData = []
            campaignCollection = db.campaigns
            # get the record of the campaign for the current channel
            campaignRecord = campaignRecords
            sessionRecord = {}
            sessionRecord["Channel"] = ctx.channel.name
            sessionRecord["Channel ID"] = ctx.channel.id
            sessionRecord["Log Channel ID"] = logChannel.id 
            sessionRecord["End"] = end
            sessionRecord["Start"] = end
            sessionRecord["Game"] = game
            sessionRecord["Status"] = "Processing"
            sessionRecord["Players"] = players
            sessionRecord["Start"] = startTime
            sessionRecord["Paused Time"] = gameInfo["Paused Time"]
            sessionRecord["Type"] = gameInfo["Type"]
            sessionRecord["DDMRW"] = settingsRecord["ddmrw"] or ("DDMRW" in gameInfo and gameInfo["DDMRW"])
            dmDBEntry= {"ID": dmChar["Member"].id, 
                "Rewards": total_duration,
                "Mention": dmChar["Member"].mention}
            sessionRecord["DM"] =  dmDBEntry
            
            
            stopEmbed.set_footer(text=f"Placeholder, if this remains remember the wise words DO NOT PANIC and get a towel.")
            session_msg = await logChannel.send(embed=stopEmbed)
            await ctx.channel.send(f"The timer has been stopped! Your session log has been posted {session_msg.jump_url}. Write your session log summary in this channel by using the following command:\n```ini\n$rpg log {session_msg.id} [Replace the brackets and this text with your session summary log.]```")

            sessionRecord["Log ID"] = session_msg.id
            stopEmbed.title = f"Timer: {game} [END] - {absoluteDuration}"
            stopEmbed.description = "**General Summary**" + """
• Please write a session log detailing what transpired during the session. It need not be longer then a paragraph as long as it's clear that a game occured.
""" 
            await session_msg.edit(embed=stopEmbed)
            await generateLog(self, ctx, session_msg.id, sessionInfo = sessionRecord)
            
            modChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Mod TTRPG Logs"])
            if is_campaign_session(sessionRecord):
                modChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Mod Campaign Logs"])
            modEmbed = discord.Embed()
            modEmbed.description = f"""A {gameInfo["Type"]} session log was just posted for {ctx.channel.mention}.

DM: {dmChar["Member"].mention} 
Game ID: {session_msg.id}
Link: {session_msg.jump_url}

React with :construction: if a summary log has not yet been appended by the DM.
React with :pencil: if you messaged the DM to fix something in their summary log.
React with ✅ if you have approved the session log.
```ini\n$rpg approve {session_msg.id}```
React with :x: if you have denied the session log.
```ini\n$rpg deny {session_msg.id}```

Reminder: do not deny any logs until we have spoken about it as a team."""

            modMessage = await modChannel.send(embed=modEmbed)
            for e in ["🚧", "📝", "✅", "❌"]:
                await modMessage.add_reaction(e)
            # try to update all the player entries
            try:
                logCollection = db.logdata
                logCollection.insert_one(sessionRecord)
            except BulkWriteError as bwe:
                print(bwe.details)
                # if it fails, we need to cancel and use the error details
                charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
                return
        # enable the starting timer commands
        self.timer.get_command('prep').reset_cooldown(ctx)

        return

            
    @rpg.command()
    async def log(self, ctx, num : int, *, editString=""):
        # The real Bot
        botUser = self.bot.user
        # botUser = self.bot.get_user(650734548077772831)

        if not game_channel_check(ctx.channel):
            #inform the user of the correct location to use the command and how to use it
            await channel.send('Try this command in a game channel! ')
            return
            
        logData = db.logdata
        sessionInfo = db.logdata.find_one({"Log ID": int(num)})
        if( not sessionInfo):
            await ctx.channel.send("The session could not be found. Please double check your number or if the session has already been approved.")
            return

        channel = self.bot.get_channel(sessionInfo["Log Channel ID"])
        try:
            editMessage = await channel.fetch_message(num)
        except Exception as e:
            return await ctx.channel.send("Log could not be found.")
        if not editMessage:
            delMessage = await ctx.channel.send(content=f"I couldn't find your game with ID - `{num}`. Please try again, I will delete your message and this message in 10 seconds.")
            await asyncio.sleep(10) 
            await delMessage.delete()
            await ctx.message.delete() 
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
            delMessage = await ctx.channel.send(content=f"Your session log caused an error with Discord, most likely from length.")
        else:
            try:
                delMessage = await ctx.channel.send(content=f"I've edited the summary for quest #{num}.\n```{editString}```\nPlease double-check that the edit is correct. I will now delete your message and this one in 20 seconds.")
            except Exception as e:
                delMessage = await ctx.channel.send(content=f"I've edited the summary for quest #{num}.\nPlease double-check that the edit is correct. I will now delete your message and this one in 20 seconds.")
        modChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Mod TTRPG Logs"])
        if is_campaign_session(sessionInfo):
            modChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Mod Campaign Logs"])
        modEmbed = discord.Embed()
        modEmbed.description = f"""An updated log for {ctx.channel.mention} has been posted
Game ID: {editMessage.id}
Link: {editMessage.jump_url}
"""
        modMessage = await modChannel.send(embed=modEmbed)
        await asyncio.sleep(20) 
        await delMessage.delete()
        try:
            await ctx.message.delete()
        except Exception as e:
            pass
        
    @commands.has_any_role('Mod Friend', 'Admins')
    @rpg.command()
    async def approve(self, ctx, num : int):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if not sessionInfo:
            return await ctx.channel.send("Session could not be found.") 
        if "Type" not in sessionInfo or sessionInfo["Type"] == "5e":
            await ctx.channel.send(f"Please use $session approve {num} instead")
            return
        if sessionInfo["Status"] == "Approved" or sessionInfo["Status"] == "Denied":
            await ctx.channel.send("This session has already been processed")
            return
        #if ctx.message.author.id == int(sessionInfo["DM"]["ID"]):
        #    await ctx.channel.send("You cannot approve your own log.")
        #    return
        
        channel = self.bot.get_channel(sessionInfo["Log Channel ID"])
        try:
            editMessage = await channel.fetch_message(num)
        except Exception as e:
            return await ctx.channel.send("Log could not be found.")
        if not editMessage or editMessage.author != self.bot.user:
            return await ctx.channel.send("Session has no corresponding message in the log channel.")

        sessionLogEmbed = editMessage.embeds[0]
        players = sessionInfo["Players"]
        players[str(sessionInfo["DM"]["ID"])] = sessionInfo["DM"]
        dm = sessionInfo["DM"] 
        bonusDouble = "Bonus" in sessionInfo and sessionInfo["Bonus"]
        
        usersCollection = db.users
        userRecordsList = list(usersCollection.find({"User ID" : {"$in": list(players.keys())}}))
        data = []
        for playerDict in userRecordsList:
            gameTime = players[playerDict["User ID"]]["Rewards"]
            timeBank = gameTime
            bonusMultiplier = 1 + bonusDouble
            playerRewards = {}
            if playerDict["User ID"] == str(dm["ID"]):
                dmDouble = sessionInfo["DDMRW"]
                bonusMultiplier = (bonusMultiplier + dmDouble) * 1.5
                timeBank *= bonusMultiplier
                if 'DM Time' not in playerDict:
                    playerDict['DM Time'] = 0
                #subtract because it is in $inc section
                playerRewards["DM Time"] = (gameTime + playerDict["DM Time"])%(3*3600) - playerDict["DM Time"]
                playerRewards["Noodles"] = int((gameTime + playerDict["DM Time"])//(3*3600))
            playerRewards["Time Bank"] = timeBank
            data.append({'_id': playerDict['_id'], "fields": {"$inc": playerRewards}})
        if is_campaign_session(sessionInfo):
            campaignCollection = db.campaigns
            # get the record of the campaign for the current channel
            campaignRecord = list(campaignCollection.find({"Channel ID": str(sessionInfo["Channel ID"])}))[0]
            campaignPath = "Campaigns."+campaignRecord["Name"]
            for dataEntry in data:
                inc = dataEntry["fields"]["$inc"]
                inc[campaignPath+".Time"] = inc["Time Bank"]
                inc[campaignPath+".Sessions"] = 1
        game = sessionInfo["Game"]
        start = sessionInfo["Start"] 
        playersData = list(map(lambda item: UpdateOne({'_id': item['_id']}, item['fields']), data))
        try:
            if len(playersData) > 0:
                usersCollection.bulk_write(playersData)
            if is_campaign_session(sessionInfo):
                campaignCollection.update_one({"_id": campaignRecord["_id"]}, {"$inc" : {"Sessions" : 1}})
                dateyear = datetime.fromtimestamp(start).astimezone(pytz.timezone(timezoneVar)).strftime("%b-%y")
                db.stats.update_one({"Date": dateyear}, {"$inc" : {"Campaigns" : 1}})
                db.stats.update_one({"Life": 1}, {"$inc" : {"Campaigns" : 1}})
            for key in sessionInfo["Players"].keys():
                c = ctx.guild.get_member(int(key))
                if(c):
                    await c.send(f"The session log for **{game}** has been approved. Time has been added to the Time Bank.")
            c = ctx.guild.get_member(int(dm["ID"]))
            if(c):
                await c.send(f"Your session log for **{game}** has been approved. Time has been added to the Time Bank.")
                
            logData.update_one({"_id": sessionInfo["_id"]}, {"$set" : {"Status": "Approved"}})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the command again.")
        else:
            sessionLogEmbed.set_footer(text=f"Game ID: {num}\n✅ Log approved! The DM has received their Noodle(s) and time and the players have received their time.")
            await editMessage.edit(embed=sessionLogEmbed)
            await ctx.channel.send("The session has been approved.")
        await noodleCheck(ctx, dm["ID"])
            
    @commands.has_any_role('Mod Friend', 'Admins')
    @rpg.command()
    async def deny(self, ctx, num : int):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if not sessionInfo:
            return await ctx.channel.send("Session could not be found.") 
        if "Type" not in sessionInfo or sessionInfo["Type"] == "5e":
            await ctx.channel.send(f"Please use $session deny {num} instead")
            return
        if sessionInfo["Status"] == "Approved" or sessionInfo["Status"] == "Denied":
            await ctx.channel.send("This session has already been processed")
            return
        if ctx.message.author.id == int(sessionInfo["DM"]["ID"]):
            await ctx.channel.send("You cannot deny your own log.")
            return
        
        channel = self.bot.get_channel(sessionInfo["Log Channel ID"])
        try:
            editMessage = await channel.fetch_message(num)
        except Exception as e:
            return await ctx.channel.send("Log could not be found.")
        if not editMessage or editMessage.author != self.bot.user:
            return await ctx.channel.send("Session has no corresponding message in the log channel.")

        sessionLogEmbed = editMessage.embeds[0]
        players = sessionInfo["Players"]  
        dm = sessionInfo["DM"] 
        try:                
            logData.update_one({"_id": sessionInfo["_id"]}, {"$set" : {"Status": "Denied"}})
            game = sessionInfo["Game"]
            for key in players.keys():
                c = ctx.guild.get_member(int(key))
                if(c):
                    await c.send(f"The session log for **{game}** has been denied.")
            c = ctx.guild.get_member(int(dm["ID"]))
            if(c):
                await c.send(f"Your session log for **{game}** has been denied.")
            sessionLogEmbed.set_footer(text=f"Game ID: {num}\n❌ Log Denied!")
            await editMessage.edit(embed=sessionLogEmbed)
            await ctx.channel.send("The session has been denied.")
        except BulkWriteError as bwe:
            print(bwe.details)
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")

    @rpg.command()
    async def apply(self, ctx,*, editString=""):
        message = ctx.message
        message_id = message.id
        await message.delete()
        embed=discord.Embed(title="TTRPG Application", description=editString, color=0x00ff00)
        name = ctx.message.author.display_name
        embed.set_author(name=name, icon_url=ctx.message.author.display_avatar)
        await ctx.message.channel.send(embed=embed)
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self,payload):
        if payload.emoji.name == '❌':
            channel = self.bot.get_channel(payload.channel_id)
            user = self.bot.get_user(payload.user_id)
            message = await channel.fetch_message(payload.message_id)
            if len(message.embeds)==0:
                return
            embed = message.embeds[0]
            if not embed.title:
                return
            if not ("TTRPG Application" in embed.title):
                return
            if embed.author.name.split('#')[0] != user.name:
                return
            embed.set_footer(text="❌ Application Revoked")
            embed.color=0xff0000
            embed.clear_fields()
            embed.description = ""
            embed.set_thumbnail(url=None)
            await message.edit(embed = embed)

    @commands.has_any_role('Mod Friend', 'A d m i n', "Bot Friend")
    @rpg.command()
    async def genLog(self, ctx,  num : int):
        logData = db.logdata
        sessionInfo = logData.find_one({"Log ID": int(num)})
        if(sessionInfo):
            await generateLog(self, ctx, num) 
            await ctx.channel.send("Log has been generated.")
    
        else:
            await ctx.channel.send("The session could not be found, please double check your number.")
    
    
async def setup(bot):
    await bot.add_cog(GenericTimer(bot))
