import discord
import pytz
import asyncio
import time
import requests
import re
import shlex
import decimal
import random
from math import ceil, floor
from itertools import product
from discord.utils import get        
from datetime import datetime, timezone,timedelta
from discord.ext import commands
from bfunc import numberEmojis, gameCategory, commandPrefix, roleArray, timezoneVar, currentTimers, db, traceBack, settingsRecord, alphaEmojis, cp_bound_array, settingsRecord
from cogs.util import callAPI, checkForChar, disambiguate, timeConversion, noodleRoleArray, uwuize, confirm

from pymongo import UpdateOne
from cogs.logs import generateLog
from pymongo.errors import BulkWriteError
from cogs.reward import randomReward

time_bonus = 3600 * 0
def lowerLimit(value):
    if value > 0:
        value = max((value)//2, 1)
    return value
def blocking_type(item):
    if "Grouped" in item:
        return item["Grouped"]
    return item["Name"]

class Timer(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.group(aliases=['t'], case_insensitive=True)
    async def timer(self, ctx):	
        pass

    @timer.command()
    async def help(self,ctx, page="1"):
        helpCommand = self.bot.get_command('help')
        if page == "2":
            await ctx.invoke(helpCommand, pageString='timer2')
        else:
            await ctx.invoke(helpCommand, pageString='timer')

    async def cog_command_error(self, ctx, error):
        msg = None
        if isinstance(error, commands.CommandOnCooldown):
            msg = f"A timer is already prepared in this channel. Please cancel the current timer and try again." 
        elif isinstance(error, commands.MissingAnyRole):
            msg = "You do not have the required permissions for this command."        
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             msg = "Your \" placement seems to be messed up.\n"
        elif isinstance(error, commands.BadArgument):
            # convert string to int failed
            return
        else:
            if isinstance(error, commands.MissingRequiredArgument):
                if error.param.name == 'userList':
                    msg = "You can't prepare a timer without any players! \n"
                elif error.param.name == 'game':
                    msg = "You can't prepare a timer without a game name! \n"
                else:
                    msg = "Your command was missing an argument! "
            
        if msg:
            if ctx.command.name == "prep":
                msg +=  f'Please follow this format:\n```yaml\n{commandPrefix}timer prep "@player1 @player2 [...]" "quest name" #guild-channel-1 #guild-channel-2```'
            
            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(content=msg)
        else:
            if ctx.channel.mention in currentTimers and "State" in currentTimers[ctx.channel.mention]:
                currentTimers[ctx.channel.mention]["State"] = "Crashed"
                await ctx.channel.send(f"This timer has crashed. The DM can use `{commandPrefix}timer resume` to continue the timer.")
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)


    
    """
    This is the command meant to setup a timer and allowing people to sign up. Only one of these can be active at a time in a single channel
    The command gets passed in a list of players as a single entry userList
    the last argument passed in will be treated as the quest name
    """
    @commands.cooldown(1, float('inf'), type=commands.BucketType.channel) 
    @commands.has_any_role('D&D Friend', 'Campaign Friend')
    @timer.command()
    async def prep(self, ctx, userList, game):
        ctx.message.content = ctx.message.content.replace("“", "\"").replace("”", "\"")
                
        #this checks that only the author's response with one of the Tier emojis allows Tier selection
        #the response is limited to only the embed message
        def startEmbedcheck(r, u):
            sameMessage = False
            if  prepEmbedMsg.id == r.message.id:
                sameMessage = True
            return (r.emoji in alphaEmojis[:6] or str(r.emoji) == '❌') and u == author and sameMessage
        #simplifying access to various variables
        channel = ctx.channel
        author = ctx.author
        #the name shown on the server
        user = author.display_name
        #the general discord name
        userName = author.name
        guild = ctx.guild
        #information on how to use the command, set up here for ease of reading and repeatability
        prepFormat =  f'Please follow this format:\n```yaml\n{commandPrefix}timer prep "@player1 @player2 [...]" "quest name" #guild-channel-1 #guild-channel-2```'
        #check if the current channel is a campaign channel
        isCampaign = "campaign" in channel.category.name.lower()
        #prevent the command if not in a proper channel (game/campaign)
        if channel.category.id != settingsRecord[str(ctx.guild.id)]["Game Rooms"]:
            #exception to the check above in case it is a testing channel
            if str(channel.id) in settingsRecord['Test Channel IDs'] or channel.id in [728456736956088420, 757685149461774477, 757685177907413092]:
                pass
            else: 
                #inform the user of the correct location to use the command and how to use it
                await channel.send('Try this command in a game channel! ' + prepFormat)
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
        
        #check if the user mentioned themselves in the command, this is also meant to avoid having the user be listed twice in the roster below
        if author in ctx.message.mentions:
            #inform the user of the proper command syntax
            await channel.send(f"You cannot start a timer with yourself in the player list! {prepFormat}")
            self.timer.get_command('prep').reset_cooldown(ctx)
            return 

        # create a list of all expected players for the game so far, including the user who will always be the first 
        # element creating an invariant of the DM being the first element
        playerRoster = [author] + ctx.message.mentions

        # player limit + 1 (includes DM)
        playerLimit = 7 + 1 

        if len(playerRoster) > playerLimit:
            await channel.send(f'You cannot start a timer with more than {playerLimit - 1} players. Please try again.')
            self.timer.get_command('prep').reset_cooldown(ctx)
            return

        # set up the user communication for tier selection, this is done even if norewards is selected
        prepEmbed.add_field(name=f"React with [0-5] for the tier of your quest: **{game}**.\n", 
                            value=f"""{numberEmojis[0]} Tutorial One-shot (Level 1)
        {numberEmojis[1]} Junior Friend (Level 1-4)
        {numberEmojis[2]} Journeyfriend (Level 5-10)
        {numberEmojis[3]} Elite Friend (Level 11-16)
        {numberEmojis[4]} True Friend (Level 17-19)
        {numberEmojis[5]} Ascended Friend (Level 17+)\n""", inline=False)
        # the discord name is used for listing the owner of the timer
        prepEmbed.set_author(name=user, icon_url=author.display_avatar)
        prepEmbed.set_footer(text= "React with ❌ to cancel.")
        # setup the variable to access the message for user communication
        
        #create the message to begin talking to the user
        prepEmbedMsg = await channel.send(embed=prepEmbed)
        choice = await disambiguate(6, prepEmbedMsg, author, emojies = numberEmojis)
        if choice is None or choice == -1:
            await prepEmbedMsg.edit(embed=None, content=f"""Timer cancelled. {prepFormat}""")
            self.timer.get_command('prep').reset_cooldown(ctx)
            return
        #create the role variable for future use
        # the array is stored in bfunc and the options are 'New', 'Junior', 'Journey', 'Elite' and 'True' in this order
        role = roleArray[choice]

        command_checklist_string = f"""__**Command Checklist**__
**1. Players and DM sign up:**• {commandPrefix}timer signup \"character name\" \"consumable1, consumable2, [...]\"
**2. DM adds guild(s) (optional):**• {commandPrefix}timer guild #guild1, #guild2
**3. DM adds or removes players (optional):**• **Add**: {commandPrefix}timer add @player
• **Remove**: {commandPrefix}timer remove @player
**4. DM cancels or starts the one-shot:**• **Cancel**: {commandPrefix}timer cancel
• **Start**: {commandPrefix}timer start"""

        #clear the embed message
        prepEmbed.clear_fields()
        # if is not a campaign add the selected tier to the message title and inform the users about the possible commands (signup, add player, remove player, add guild)
        prepEmbed.title = f"{game} (Tier {choice})"
        prepEmbed.description = command_checklist_string

        guildsList = []
        guildCategoryID = settingsRecord[str(ctx.guild.id)]["Guild Rooms"]

        if (len(ctx.message.channel_mentions) > 2):
            await channel.send(f"The number of guilds exceeds two. Please follow this format and try again:\n```yaml\n{commandPrefix}timer guild #guild1 #guild2```") 
        elif ctx.message.channel_mentions != list():
            for g in ctx.message.channel_mentions:
                if g.category_id == guildCategoryID:
                    guildsList.append(g)
                    
            if guildsList:
                prepEmbed.description = f"**Guilds**: {', '.join([g.mention for g in guildsList])}\n\n{command_checklist_string}"

        #setup a variable to store the string showing the current roster for the game
        rosterString = ""
        #now go through the list of the user/DM and the initially given player list and build a string
        for p in playerRoster:
            #since the author is always the first entry this if statement could be extracted, but the first element would have to be skipped
            #extracting could make the code marginally faster
            if p == author:
                #set up the special field for the DM character
                prepEmbed.add_field(name = f"{author.display_name} **(DM)**", value = "The DM has not signed up a character for DM rewards.")
            else:
                # create a field in embed for each player and their character, they could not have signed up so the text reflects that               # the text differs only slightly if it is a campaign
                prepEmbed.add_field(name=p.display_name, value='Has not yet signed up for the campaign.', inline=False)
        #set up a field to inform the DM on how to start the timer or how to get help with it
        prepEmbed.set_footer(text= f"Use the following command to see a list of timer commands: {commandPrefix}help timer")

        # if it is a campaign or the previous message somehow failed then the prepEmbedMsg would not exist yet send we now send another message
        if not prepEmbedMsg:
            prepEmbedMsg = await channel.send(embed=prepEmbed)
        else:
            #otherwise we just edit the contents
            await prepEmbedMsg.edit(embed=prepEmbed)
        
        
        # create a dictionary of all player and characters they have signed up with
        # this is a nested list where the contained entries are [member object, DB character entry, Consumable list for the game, character DB ID]
        # currently this starts with a dummy initial entry for the DM to enable later users of these entries in the code
        # this entry will be overwritten if the DM signs up with a character
        
        signedPlayers = {"Players" : {}, 
                            "DM" : {"Member" : author, 
                                "Character": "No Rewards",
                                "Brought": [],
                                "Character ID": None,
                                "Consumables": {"Add": [], "Remove": []}, 
                                "Inventory": {"Add": [], "Remove": []},
                                "Magic Items": []},
                            "Game" : game,
                            "Role" : role,
                            "Guilds" : guildsList,
                            "Started": False}
        
        # create a list of all possible commands that could be used during the signup phase
        timerAlias = ["timer", "t"]
        timerCommands = ['signup', 'cancel', 'guild', 'start', 'add', 'remove']
      
        timerCombined = []
        # pair up each command group alias with a command and store it in the list
        for x in product(timerAlias,timerCommands):
            timerCombined.append(f"{commandPrefix}{x[0]} {x[1]}")
        
        """
        This is the heart of the command, this section runs continuously until the start command is used to change the looping variable
        during this process the bot will wait for any message that contains one of the commands listed in timerCombined above 
        and then invoke the appropriate method afterwards, the message check is also limited to only the channel signup was called in
        Relevant commands all have blocks to only run when called
        """
        while not signedPlayers["Started"]:
            # get any message that managed to satisfy the check described above, it has to be a command as a result
            msg = await self.bot.wait_for('message', check=lambda m: any(x in m.content for x in timerCombined) and m.channel == channel)
            msg.content = msg.content.replace("“", "\"").replace("”", "\"")
            """
            the following commands are all down to check which command it was
            the checks are all doubled up since the commands can start with $t and $timer
            """
            
            """
            The signup command has different behaviors if the signup is from the DM, a player
            """
            if msg.content.startswith(f"{commandPrefix}timer signup") or msg.content.startswith(f"{commandPrefix}t signup"):
                # if the message author is the one who started the timer, call signup with the special DM moniker
                # the character is extracted from the message in the signup command 
                # special behavior:
                playerChar = None
                if msg.author in playerRoster and msg.author == author:
                    playerChar = await self.signup(ctx, char=msg, author=author, role='DM') 
                # allow for people in the roster to sign up with their characters
                elif msg.author in playerRoster:
                    playerChar = await self.signup(ctx, char=msg, author=msg.author, role=role)
                # if the message author has not been permitted to the game yet, inform them of such
                # a continue statement could be used to skip the following if statement
                else:
                    await channel.send(f"***{msg.author.display_name}***, you must be on the roster in order to participate in this quest.")
                
                """
                if the signup command successfuly returned a player record ([author, char, consumables, char id])
                we then can process these and add the signup to the roster
                """
                if playerChar:
                    # this check is meant to see if the player who is signing up is the DM
                    # Since the DM is always the front element this check will always work and 
                    if playerRoster.index(playerChar["Member"]) == 0:
                        #update the the specific info about the DM sign up
                        prepEmbed.set_field_at(0, name=f"{author.display_name} **(DM)**", value= f"***{playerChar['Character']['Name']}*** will receive DM rewards.", inline=False)
                        # with the dummy element can now be replaced with a more straight forward check
                        signedPlayers["DM"] = playerChar
                    else:
                        consumables_string = "None"
                        if playerChar['Brought']:
                            consumables_string = ', '.join(playerChar['Brought']).strip()
                        prepEmbed.set_field_at(playerRoster.index(playerChar['Member']), name=f"{playerChar['Character']['Name']}", value= f"{playerChar['Member'].mention}\nLevel {playerChar['Character']['Level']}: {playerChar['Character']['Race']} {playerChar['Character']['Class']}\nConsumables: {consumables_string}\n", inline=False)
                        signedPlayers["Players"][msg.author.id] = playerChar

            elif (msg.content.startswith(f"{commandPrefix}timer add ") or msg.content.startswith(f"{commandPrefix}t add ")):
                if await self.permissionCheck(msg, author):
                    if len(playerRoster) + 1 > playerLimit:
                        await channel.send(f'You cannot add more than {playerLimit - 1} players to the timer.')
                    else:
                        addList = msg.mentions
                        # if there was no player added
                        if addList == list():
                            await ctx.channel.send(content=f"You forgot to mention a player! Please try the command again and ping the player.")
                        else:
                            error_users = []
                            for addUser in addList:
                                if addUser not in playerRoster:
                                    # set up the embed fields for the new user if they arent in the roster yet
                                    prepEmbed.add_field(name=addUser.display_name, value='Has not yet signed up a character to play.', inline=False)
                                    # add them to the roster
                                    playerRoster.append(addUser)
                                else:
                                    #otherwise inform the user of the failed add
                                    error_users.append(addUser.display_name) 
                            if error_users:
                                await channel.send(f'These players are already on the timer: ***{", ".join(error_users)}***')

            elif (msg.content.startswith(f"{commandPrefix}timer remove ") or msg.content.startswith(f"{commandPrefix}t remove ")) :
                if await self.permissionCheck(msg, author):
                    removeList = msg.mentions
                    if len(removeList) == 0:
                        await channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
                    else:
                        for removeUser in removeList:
                            #check if the user is not the DM
                            if removeUser in playerRoster:
                                if playerRoster.index(removeUser) != 0:
                                    # remove the embed field of the player
                                    prepEmbed.remove_field(playerRoster.index(removeUser))
                                    # remove the player from the roster
                                    playerRoster.remove(removeUser)
                                    # remove the player from the signed up players
                                    if removeUser.id in signedPlayers["Players"]:
                                        del signedPlayers["Players"][removeUser.id]
                                else:
                                    await channel.send('You cannot remove yourself from the timer.')

            #the command that starts the timer, it does so by allowing the code to move past the loop
            elif (msg.content == f"{commandPrefix}timer start" or msg.content == f"{commandPrefix}t start"):
                if await self.permissionCheck(msg, author):
                    if len(signedPlayers["Players"]) == 0:
                        await channel.send(f'There are no players signed up! Players, use the following command to sign up to the quest with your character before the DM starts the timer:\n```yaml\n{commandPrefix}timer signup```') 
                    else:
                        signedPlayers["Started"] = True
            #the command that cancels the timer, it does so by ending the command all together                              
            elif (msg.content == f"{commandPrefix}timer cancel" or msg.content == f"{commandPrefix}t cancel"):
                if await self.permissionCheck(msg, author):
                    await channel.send(f'Timer cancelled! If you would like to prep a new quest {prepFormat.lower()}') 
                    # allow the call of this command again
                    self.timer.get_command('prep').reset_cooldown(ctx)
                    return

            elif (msg.content.startswith(f'{commandPrefix}timer guild') or msg.content.startswith(f'{commandPrefix}t guild')):
                if await self.permissionCheck(msg, author):
                    guildCategoryID = settingsRecord[str(ctx.guild.id)]["Guild Rooms"]

                    if (len(msg.channel_mentions) > 2):
                        await channel.send(f"The number of guilds exceeds two. Please follow this format and try again:\n```yaml\n{commandPrefix}timer guild #guild1 #guild2```") 
                    else:
                        guildsList = msg.channel_mentions
                        invalidChannel = False
                        for g in guildsList:
                            if g.category_id != guildCategoryID:
                                invalidChannel = True
                                await channel.send(f"***{g}*** is not a guild channel. Please follow this format and try again:\n```yaml\n{commandPrefix}timer guild #guild1, #guild2```") 
                                break
                        if not invalidChannel:
                            signedPlayers["Guilds"] = guildsList
                            prepEmbed.description = f"**Guilds**: {', '.join([g.mention for g in signedPlayers['Guilds']])}\n\n{command_checklist_string}"

            await prepEmbedMsg.delete()
            prepEmbedMsg = await channel.send(embed=prepEmbed)
        await self.start(ctx, signedPlayers)


    """
    This is the command used to allow people to enter their characters into a game before the timer starts
    char is a message object which makes the default value of "" confusing as a mislabel of the object
    role is a string indicating which tier the game is for or if the player signing up is the DM
    """
    #@timer.command()
    async def signup(self,ctx, char="", author="", role=""):
        #check if the command was called using one of the permitted other commands
        # set up a informative error message for the user
        signupFormat = f'Please follow this format:\n```yaml\n{commandPrefix}timer signup "character name" "consumable1, consumable2, [...]"```'
        # create an embed object
        charEmbed = discord.Embed()
        # set up the variable for the message for charEmbed
        charEmbedmsg = None
        #get quicker access to some variables from the context
        channel = ctx.channel
        guild = ctx.guild
        # set up the string for the consumables list
        consumablesList = ""
        # check if the entire message was just one of the triggering commands which indicates a lack of character
        if f'{commandPrefix}timer signup' == char.content.strip() or f'{commandPrefix}t signup' == char.content.strip():
            await channel.send(content=f'You did not input a character, please try again.\n\n{signupFormat}')
            # this is a valid return, since the resume and sign up code will check for this before executing further
            return False
        #check which message caused the invocation to create different behaviors
        try:
            if 'timer signup ' in char.content or 't signup ' in char.content:
                #shlex allows the splitting in a way that respects the '"' in the string and splits according to white space
                #this retrieves the character + consumable list from the command 
                # first the command part gets removed with the first split and then the remainder gets split like arguments for the command line
                if f'{commandPrefix}timer signup ' in char.content:
                    charList = shlex.split(char.content.split(f'{commandPrefix}timer signup ')[1].strip())
                elif f'{commandPrefix}t signup ' in char.content:
                    charList = shlex.split(char.content.split(f'{commandPrefix}t signup ')[1].strip())
                # since the character is the first parameter after the command name this will get the char name
                charName = charList[0]

            else:
            # this is a similar process to above but with the added adjustment that a player name is also included
            
                if 'timer add ' in char.content or 't add ' in char.content:
                    if 'timer add ' in char.content:
                        charList = shlex.split(char.content.split(f'{commandPrefix}timer add ')[1].strip())
                    elif 't add' in char.content:
                        charList = shlex.split(char.content.split(f'{commandPrefix}t add ')[1].strip())
                    # since two parameters are needed for 'add' we need to inform the user
                    if len(charList) == 1:
                        # again block repeat messages in case of a resume command, the check is different for some reason
                        await ctx.channel.send("You're missing a character name for the player you're trying to add. Please try again.")
                        return
                    # in this case the character name is the second parameter
                    charName = charList[1]
                # this is the exact same set up as for signup, since a person is adding themselves only one parameter is expected
                elif ('timer addme ' in char.content) and (char.content != f'{commandPrefix}timer addme '):
                    charList = shlex.split(char.content.split(f'timer addme ')[1].strip())
                    charName = charList[0]
                elif ('t addme ' in char.content) and (char.content != f'{commandPrefix}t addme '):
                    charList = shlex.split(char.content.split(f't addme ')[1].strip())
                    charName = charList[0]
                else:
                    await ctx.channel.send("I wasn't able to add this character. Please check your format.")
                    return
        except ValueError as e:
            await ctx.channel.send("Something was off with your character name. Did you miss a quotation mark?")
            return
        # if the last parameter is not the character name then we know that the player registered consumables
        if charList[len(charList) - 1] != charName:
            # consumables are separated by ','
            consumablesList = list(map(lambda x: x.strip(), charList[len(charList) - 1].split(',')))


        # use the bfunc function checkForChar to handle character selection, gives us the DB entry of the character
        cRecord, charEmbedmsg = await checkForChar(ctx, charName, charEmbed, authorOverride = author, customError=True)
        
        if not cRecord:
            await channel.send(content=f'I was not able to find the character "***{charName}***"!\n\n{signupFormat}')
            return False

        if charEmbedmsg:
            await charEmbedmsg.delete()

        if 'Death' in cRecord:
            await channel.send(content=f'You cannot sign up with ***{cRecord["Name"]}*** because they are dead. Please use the following command to resolve their death:\n```yaml\n{commandPrefix}death {cRecord["Name"]}```')
            return False 

        elif 'Respecc' in cRecord:
            await channel.send(content=f'You cannot sign up with ***{cRecord["Name"]}*** because they need to respec. Please use the following command to resolve their death:\n```yaml\n{commandPrefix}respec {cRecord["Name"]} "new character name" "race" "class1 level / class2 level / class3 level / class4 level" "background" STR DEX CON INT WIS CHA```')
            return False 
        # check if there is any record of a game in charRecords
        elif 'GID' in cRecord:
            await channel.send(content=f'You cannot sign up with ***{cRecord["Name"]}*** because they have not received their rewards from their last quest. Please wait until the session log has been approved.')
            return False    
        # get how much CP the character has and how much they need
        cpSplit = cRecord['CP']
        validLevelStart = 1
        validLevelEnd = 1
        charLevel = cRecord['Level']
        
        # set up the bounds of which level the character is allowed to be
        if role == "Ascended":
            validLevelStart = 17
            validLevelEnd = 20
        elif role == "True":
            validLevelStart = 17
            validLevelEnd = 19
        elif role == "Elite":
            validLevelStart = 11
            validLevelEnd = 16
        elif role == "Journey":
            validLevelStart = 5
            validLevelEnd = 10
        elif role == "Junior":
            validLevelEnd = 4
        elif role == "New":
            validLevelEnd = 4
        elif role == "DM":
            validLevelEnd = 20
        
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
        
        # block a character with an invalid level for the tier and inform the user
        if charLevel < validLevelStart or charLevel > validLevelEnd:
            await channel.send(f"***{cRecord['Name']}*** is not between levels {validLevelStart} - {validLevelEnd} to play in this quest. Please choose a different character.")
            return False 

        # if the character has more cp than needed for a level up, they need to perform that level up first so we block the command
        if charLevel <20 and cpSplit >= cp_bound_array[tierNum-1][0]:
            await channel.send(content=f'You need to level up ***{cRecord["Name"]}*** before they can join the quest! Use the following command to level up:\n```yaml\n{commandPrefix}levelup "character name"```')
            return False 

        # handle the list of consumables only if it is not empty
        # there is also a special block for DMs since they can't use consumables
        if consumablesList and role != "DM":
            #get all consumables the character has
            charConsumables = {}
            for c in cRecord['Consumables'].split(', '):
                if c not in charConsumables:
                    charConsumables[c] = 1
                else:
                    charConsumables[c] += 1

            
            gameConsumables = []
            notValidConsumables = ""
            # This sets up how many consumables are permitted based on the character level
            consumableLength = 2 + (charLevel-1)//4
            if("Ioun Stone (Mastery)" in cRecord['Magic Items']):
                consumableLength += 1
            # block the command if more consumables than allowed (limit or available) are being registed
            if len(consumablesList) > consumableLength:
                await channel.send(content=f'You are trying to bring in too many consumables (**{len(consumablesList)}/{consumableLength}**)! The limit for your character is **{consumableLength}**.')
                return False
            
            #loop over all consumable pairs and check if the listed consumables are in the inventory

           
            # consumablesList is the consumable list the player intends to bring
            # charConsumables are the consumables that the character has available.
            # gameConsumables are the final list of consumables characters are bringing
            for i in consumablesList:
                itemFound = False
                for jk, jv in charConsumables.items():
                    if i.strip() != "" and i.lower().replace(" ", "").strip() in jk.lower().replace(" ", ""):
                        if jv > 0 :
                            gameConsumables.append(jk.strip())
                            charConsumables[jk] -= 1
                            itemFound = True
                            break

                if not itemFound:
                    notValidConsumables += f"`• {i.strip()}`\n"
                    

            # if there were any invalid consumables, inform the user on which ones cause the issue
            if notValidConsumables:
                await channel.send(f"These items were not found in your character's inventory:\n{notValidConsumables}")
                return False
            # If no consumables were listed, create a special entry
            if not gameConsumables:
                gameConsumables = []
            # this sets up the player list of the game, it stores who it is, all the consumables and which character they are using and their stuff
            return {"Member" : author, 
                                "Character": cRecord,
                                "Brought": gameConsumables,
                                "Character ID": cRecord['_id'],
                                "Consumables": {"Add": [], "Remove": []}, 
                                "Inventory": {"Add": [], "Remove": []},
                                "Magic Items": []}

        # since no consumables were listed we can default to the special None option
        return {"Member" : author, 
                    "Character": cRecord,
                    "Brought": [],
                    "Character ID": cRecord['_id'],
                    "Consumables": {"Add": [], "Remove": []}, 
                    "Inventory": {"Add": [], "Remove": []},
                    "Magic Items": []}



    """
    This command is used to remove consumables during play time
    msg -> the msg that caused the invocation
    userInfo -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    """
    #@timer.command()
    async def deductConsumables(self, ctx, msg, userInfo): 
        channel = ctx.channel
        # extract the name of the consumable and transform it into a standardized format
        searchQuery =  msg.content.split('-')[1].strip()
        searchItem = searchQuery.lower().replace(' ', '')
        removedItem = ""  
        if msg.author.id not in userInfo["Players"]:
            await channel.send(f"Looks like you were trying to remove **{searchItem}** from your inventory. I could not find you on the timer to do that.")
            return userInfo
        player = userInfo["Players"][msg.author.id]
        item_type = None
        consumable_matches = set([])
        for j in player["Brought"]:
            # if found then we can mark it as such
            if searchItem in j.lower().replace(" ", ""):
                consumable_matches.add(j)
        item_list = [(x, "Consumables") for x in consumable_matches]
        for key, inv in player["Character"]["Inventory"].items():
            # if found than we can mark it as such
            if searchItem in key.lower().replace(' ', '') and inv > 0:
                item_list.append((key, "Inventory"))
                    
        # inform the user if we couldnt find the item
        if not item_list:
            await channel.send(f"I could not find the item **{searchQuery}** in your inventory in order to remove it.")
            return userInfo   
        apiEmbed = discord.Embed()
        choice_key = 0
        if len(item_list) > 1:            
            queryLimit = 15
            infoString = ""
            #limit items to queryLimit
            for i in range(0, min(len(item_list), queryLimit)):
                item_name, item_type = item_list[i]
                infoString += f"{alphaEmojis[i]}: {item_name}\n"
            #inform the user of the current information and ask for their selection of an item
            apiEmbed.add_field(name=f"There seems to be multiple results for \"**{searchItem}**\"! Please choose the correct one.\nThe maximum number of results shown is {queryLimit}. If the result you are looking for is not here, please react with ❌ and be more specific.", value=infoString, inline=False)
            apiEmbedmsg = await channel.send(embed=apiEmbed)
            
            #check if the response from the user matches the limits
            choice = await disambiguate(min(queryLimit, len(item_list)), apiEmbedmsg, msg.author)
            if choice is None or choice == -1:
                #stop if no response was given within the timeframe
                await apiEmbedmsg.edit(embed=None, content="Command cancelled. Try using the command again.")
                return userInfo
            await apiEmbedmsg.delete()
            choice_key = choice
        item_name, item_type = item_list[choice_key]
        if item_type == "Consumables":
            # remove the item from the brought consumables
            player["Brought"].remove(item_name) 
        elif item_type == "Inventory":
            player["Character"][item_type][item_name] -= 1
        player[item_type]["Remove"].append(item_name)
        await channel.send(f"The item **{item_name}** has been removed from your inventory.")

        # this variable is set when the user is found, thus this shows that the player was not on the timer
        return userInfo
    
    """
    This command is used to remove rewarded consumables during play time
    msg -> the msg that caused the invocation
    userInfo -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    """
    async def undoConsumables(self, ctx, msg=None, userInfo=None): 
        channel = ctx.channel
        if msg and msg.mentions:
            for player in msg.mentions:
                if player == userInfo["DM"]["Member"]:
                    userInfo["DM"]["Magic Items"]= []
                    userInfo["DM"]["Consumables"]["Add"] = []
                    userInfo["DM"]["Inventory"]["Add"] = []
                else:
                    userInfo["Players"][player.id]["Magic Items"]= []
                    userInfo["Players"][player.id]["Consumables"]["Add"] = []
                    userInfo["Players"][player.id]["Inventory"]["Add"] = []
        else:  
            for item in userInfo["Players"].values():
                item["Magic Items"]= []
                item["Consumables"]["Add"] = []
                item["Inventory"]["Add"] = []
            userInfo["DM"]["Magic Items"]= []
            userInfo["DM"]["Consumables"]["Add"] = []
            userInfo["DM"]["Inventory"]["Add"] = []
            
        await channel.send(f"Reward items have been removed.")
        return userInfo
    
    
    """
    This command handles all the intial setup for a running timer
    this includes setting up the tracking variables of user playing times,
    """
    #@timer.command()
    async def start(self, ctx, userInfo):
        # access the list of all current timers
        # this is used to enable the list command and as a management tool for seeing if the timers are working
        #global currentTimers
        # make some common variables more accessible
        channel = ctx.channel
        author = ctx.author
        userName = author.display_name
        guild = ctx.guild
        role = userInfo["Role"]
        game = userInfo["Game"]
        # create an entry in the DM player entry that keeps track of rewards in the future
        userInfo["DM"]["Noodle"] = 'Junior Noodle'

        # find the name of which noodle role the DM has
        for r in userInfo["DM"]["Member"].roles:
            if r.name in noodleRoleArray:
                userInfo["DM"]["Noodle"] = r.name
                break
        
        # get the current time for tracking the duration
        startTime = time.time()
        userInfo["Start"] = startTime
        # format the time for a localized version defined in bfunc
        datestart = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%d-%y %I:%M %p")
        # create a list of entries to track players with
        
        userInfo["Date"] = datestart
        userInfo["State"] = "Running"
        userInfo["Paused"] = False
        userInfo["Paused Time"] = 0
        userInfo["Last Pause"] = startTime
        userInfo["Pause Type"] = 0
        
        for u in userInfo["Players"].values():
            u["Latest Join"] = startTime
            u["State"] = "Full"
            u["Duration"] = 0
        
        roleString = f"({role})"
        
        # Inform the user of the started timer
        await channel.send(content=f"Starting the timer for **{userInfo['Game']}** {roleString}.\n" )
        # add the timer to the list of runnign timers
        
        currentTimers[channel.mention] = userInfo
        
        # set up an embed object for displaying the current duration, help info and DM data
        stampEmbed = discord.Embed()
        stampEmbed.title = f'**{game}**: 0 Hours 0 Minutes\n'
        stampEmbed.set_footer(text=f'#{ctx.channel}\nUse the following command to see a list of running timer commands: $help timer2')
        stampEmbed.set_author(name=f'DM: {userName}', icon_url=author.display_avatar)

        
        # for every player check their consumables and create a field in the embed to display them
        # this field also show the charater name
        for u in userInfo["Players"].values():
            consumablesString = ""
            if u["Brought"]:
                consumablesString = "\nConsumables: " + ', '.join(u["Brought"])
            stampEmbed.add_field(name=f"**{u['Member'].display_name}**", value=f"**{u['Character']['Name']}**{consumablesString}\n", inline=False)
        
        stampEmbedmsg = await channel.send(embed=stampEmbed)

        userInfo["DDMRW"] = settingsRecord["ddmrw"]
        # During Timer
        await self.duringTimer(ctx, userInfo, stampEmbed, stampEmbedmsg)
        
        # allow the creation of a new timer
        self.timer.get_command('prep').reset_cooldown(ctx)
        # when the game concludes, remove the timer from the global tracker
        del currentTimers[channel.mention]
        return

    """
    userInfo -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    """    
    async def reward(self,ctx,msg, userInfo="", exact=False):
        # get the list of people receiving rewards
        rewardList = msg.mentions
        # create an embed text object
        charEmbed = discord.Embed()
        charEmbedmsg = None
        dmChar = userInfo["DM"]
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user to hand out a reward item.") 
            #return the unchanged parameters
            return userInfo
        else:
            # get the first user mentioned
            rewardUser = rewardList[0]
            userFound = rewardUser.id in userInfo["Players"]
            
            # if the user getting rewards is the DM we can save time by not going through the loop
            if rewardUser == dmChar["Member"] and not dmChar["Character ID"]:
                await ctx.channel.send(content=f"You did not sign up with a character to reward items to.") 
                #return the unchanged parameters
                return userInfo
            elif rewardUser == dmChar["Member"]: 
                userFound = True
                # the player entry of the player getting the item
                user_dic = dmChar
            elif userFound:
                user_dic = userInfo["Players"][rewardUser.id]
            cur_time = time.time()
            # since this checks for multiple things, this cannot be avoided
            totalDurationTime = (cur_time - userInfo["Start"] - userInfo["Paused Time"] - (cur_time - userInfo["Last Pause"])*userInfo["Paused"] + time_bonus) // 60 #Set multiplier to wanted hour shift 
            if totalDurationTime < 180: #Allows rewards to be handed out if less than 3 hours, gives specific message mentioning that they will be denied if the game lasts less than 3 hours.
                await ctx.channel.send(content=f"Because this is less than 3 hours into the game, the consumables will be denied if the game ends before 3 hours.")
            
            if userFound:
                if '"' in msg.content:
                    consumablesList = msg.content.split('"')[1::2][0].split(', ')

                else:
                    await ctx.channel.send(content=f'You need to include quotes around the reward item in your command. Please follow this format and try again:\n```yaml\n{commandPrefix}timer reward @player "reward item1, reward item2, [...]"```')
                    return userInfo
                half_reward_time_count = 0
                for player in userInfo["Players"].values():
                    playtime = player["Duration"] + time_bonus
                    if player["State"] in ["Full", "Partial"] and not userInfo["Paused"]:
                        playtime += cur_time - player["Latest Join"]
                    if (playtime)//3600 >= 3:
                        half_reward_time_count += 1
                    
                charLevel = user_dic["Character"]["Level"]
                # the current counts of items rewarded
                item_rewards = []
                for player in userInfo["Players"].values():
                    item_rewards += player["Inventory"]["Add"] + player["Consumables"]["Add"] + player["Magic Items"]
                major = len([x for x in item_rewards if x['Minor/Major'] == 'Major'])
                minor = len([x for x in item_rewards if x['Minor/Major'] == 'Minor'])
                dm_item_rewards = dmChar["Inventory"]["Add"] + dmChar["Consumables"]["Add"] + dmChar["Magic Items"]
                dmMajor = len([x for x in dm_item_rewards if x['Minor/Major'] == 'Major'])
                dmMinor = len([x for x in dm_item_rewards if x['Minor/Major'] == 'Minor'])
                
                totalDurationTimeMultiplier = int(totalDurationTime // 180)
                # set up the total reward item limits based on noodle roles
                # check out hosting-a-one-shot for details
                # Minor limit is the total sum of rewards allowed
                noodle_value = 0
                if dmChar["Noodle"] in noodleRoleArray:
                    noodle_value = noodleRoleArray.index(dmChar["Noodle"])
                rewardMajorLimit = (noodle_value)//2+1
                rewardMinorLimit = (noodle_value)+2
                dmMajorLimit = max(0,(noodle_value - 4)//2+1)
                dmMinorLimit = max(0,(noodle_value - 3))+1
                # if the DM has to pick a reward of a lower tier
                lowerTier = noodle_value < 3
                # if the DM has to pick a non-consumable
                dmMnc = noodle_value == 0
                # if the DM has to choose between major and minor
                chooseOr = False
                # exceptions to the general progression starting at True
                if dmChar["Noodle"] in ['Elite Noodle', 'True Noodle']:
                    dmMajorLimit = 1
                    chooseOr = True
                
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
                    
                # make adjustments to the tier number if it is the DM character and the role needs tier lowering
                if lowerTier and rewardUser == dmChar["Member"]:
                    # set the minimum to 1
                    if tierNum < 2:
                        tierNum = 1
                    else:
                        tierNum -= 1
                
                dmMajorLimit += max((totalDurationTimeMultiplier -1)//2, 0)
                dmMinorLimit += max((totalDurationTimeMultiplier -1), 0)
                
                rewardMajorLimit += max((totalDurationTimeMultiplier -1)// 2, 0)
                rewardMinorLimit += max((totalDurationTimeMultiplier -1), 0)
                
                mnc_limit = dmMnc
                player_type = "Players"
                if dmMnc:
                    if rewardUser == dmChar["Member"]:
                        for dm_item in dm_item_rewards:
                            if (dm_item['Minor/Major'] == 'Minor' and dm_item["Type"] == "Magic Items"):
                                mnc_limit = False
                                break
                    
                    player_type = "DM"
                    item_rewards = dm_item_rewards
                if half_reward_time_count < 2:
                    dmMajorLimit = lowerLimit(dmMajorLimit)
                    dmMinorLimit = lowerLimit(dmMinorLimit)
                    rewardMajorLimit = lowerLimit(rewardMajorLimit)
                    rewardMinorLimit = lowerLimit(rewardMinorLimit)
                dm_cap = (dmMinorLimit)
                item_rewards = list(map(blocking_type, item_rewards))
                character_add = {"Inventory": [], "Consumables": [], "Magic Items": []}
                item_list = []
                blocking_list_additions = []
                for query in consumablesList:
                    # if the player is getting a spell scoll then we need to determine which spell they are going for
                    # we do this by searching in the spell table instead
                    if 'spell scroll' in query.lower():
                        # extract the spell
                        spellItem = query.lower().replace("spell scroll", "").replace('(', '').replace(')', '')
                        # use the callAPI function from bfunc to search the spells table in the DB for the spell being rewarded
                        sRecord, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg, 'spells', spellItem, exact=exact)
                        
                        # if no spell was found then we inform the user of the failure and stop the command
                        if not sRecord:
                            await ctx.channel.send(f'''**{query}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Reward Item Table, what tier it is, and your spelling.''')
                            return userInfo

                        else:
                            if sRecord["Level"] == 0:
                                query = f"Spell Scroll (Cantrip)"
                            else:
                                # Converts number to ordinal - 1:1st, 2:2nd, 3:3rd...
                                # floor(n/10)%10!=1, this acts as an if statement to check if the number is in the teens
                                # (n%10<4), this acts as an if statement to check if the number is below 4
                                # n%10 get the last digit of the number
                                # by multiplying these number together we end up with calculation that will be 0 unless both conditions have been met, otherwise it is the digit
                                # this number x is then used as the starting point of the selection and ::4 will then select the second letter by getting the x+4 element
                                # technically it will get more, but since the string is only 8 characters it will return 2 characters always
                                # th, st, nd, rd are spread out by 4 characters in the string 
                                ordinal = lambda n: "%d%s" % (n,"tsnrhtdd"[(floor(n/10)%10!=1)*(n%10<4)*n%10::4])
                                # change the query to be an accurate representation
                                query = f"Spell Scroll ({ordinal(sRecord['Level'])} Level)"
                    

                    # search for the item in the DB with the function from bfunc
                    # this does disambiguation already so if there are multiple results for the item they will have already selected which one specifically they want
                    rewardConsumable, charEmbed, charEmbedmsg = await callAPI(ctx, charEmbed, charEmbedmsg ,'rit',query, tier=tierNum, exact=exact) 
                
                    #if no item could be found, return the unchanged parameters and inform the user
                    if not rewardConsumable:
                        await ctx.channel.send(f'**{query}** does not seem to be a valid reward item.')
                        return userInfo
                    else:
                       
                        rewardConsumable_group_type = "Name"
                        if "Grouped" in rewardConsumable:
                           rewardConsumable_group_type = "Grouped"
                        # check if the item has already been rewarded to the player
                        if (rewardConsumable[rewardConsumable_group_type] in item_rewards or
                            rewardConsumable[rewardConsumable_group_type] in blocking_list_additions):
                            # inform the user of the issue
                            await ctx.channel.send(f"You cannot award the more than one of the same reward item. Please choose a different reward item.")
                            # return unchanged parameters
                            return userInfo 
                        
                            
                        # increase the appropriate counters based on what the reward is and who is receiving it
                        if rewardConsumable['Minor/Major'] == 'Minor':
                            if rewardUser == dmChar["Member"]:
                                dmMinor += 1
                                if (rewardConsumable["Type"] == "Magic Items"):
                                    mnc_limit = False
                            else:
                                minor += 1
                        elif rewardConsumable['Minor/Major'] == 'Major':
                            if rewardUser == dmChar["Member"]:
                                dmMajor += 1
                            else:
                                major += 1
                        # if the item is rewarded to the DM and they are not allowed to pick a consumable
                        # and the item is neither minor nor consumable
                        if dmMnc and rewardUser == dmChar["Member"] and (dm_cap - dmMajor - dmMinor) == 0 and mnc_limit:
                            await ctx.channel.send(f"You cannot award yourself this reward item because you have not yet rewarded yourself a Minor Non-Consumable.")
                            # return unchanged parameters
                            return userInfo
                        
                        # set up error messages based on the allowed item counts inserted appropriately
                        rewardMajorErrorString = f"You cannot award any more **{rewardConsumable['Minor/Major']}** reward items.\n```md\nTotal attempted to reward so far:\n({major}/{rewardMajorLimit}) Major Rewards \n({minor}/{rewardMinorLimit-rewardMajorLimit}) Minor Rewards```"

                        if rewardUser == dmChar["Member"]:
                            if chooseOr:
                                if dmMajor > dmMajorLimit or (dmMinor+dmMajor) > dmMinorLimit:
                                    await ctx.channel.send(f"You cannot award yourself any more Major or Minor reward items {dmMajor}/{dmMajorLimit}.")
                                    return userInfo 
                            else:
                                if dmMajor > dmMajorLimit:
                                    await ctx.channel.send(f"You cannot award yourself any more Major reward items {dmMajor}/{dmMajorLimit}.")
                                    return userInfo
                                elif dmMinor+dmMajor > dmMinorLimit:
                                    await ctx.channel.send(f"You cannot award yourself any more Minor reward items {dmMinor}/{dmMinorLimit-dmMajorLimit}.")
                                    return userInfo 
                        
                        else:
                            if (major > rewardMajorLimit or (major+minor)>rewardMinorLimit):
                                await ctx.channel.send(rewardMajorErrorString)
                                return userInfo
                            
                        # If it is a spell scroll, since we search for spells, we need to adjust the name
                        blocking_list_additions.append(rewardConsumable[rewardConsumable_group_type])
                        if 'spell scroll' in query.lower():
                            rewardConsumable['Name'] = f"Spell Scroll ({sRecord['Name']})"
                        item_list.append(rewardConsumable['Name'])
                        character_add[rewardConsumable["Type"]].append(rewardConsumable)
                
                # add all awarded items to the players reward tracker
                for key, items in character_add.items():
                    if(key == "Magic Items"):
                        user_dic[key] += items
                    else:
                        user_dic[key]["Add"] += items
                # on completion inform the users that of the success and of the current standings with rewards
                await ctx.channel.send(content=f"You have awarded ***{rewardUser.display_name}*** the following reward items: **{', '.join(item_list)}**.\n```md\nTotal rewarded so far:\n({major}/{rewardMajorLimit}) Major Reward Items\n({minor}/{rewardMinorLimit-rewardMajorLimit}) Minor Reward Items\n({dmMajor}/{dmMajorLimit}) DM Major Reward Items\n({dmMinor}/{dmMinorLimit-dmMajorLimit}) DM Minor Reward Items```")
                
            else:
                await ctx.channel.send(content=f"***{rewardUser}*** is not on the timer to receive rewards.")
        return userInfo
    """
    This command gets invoked by duringTimer and resume
    userInfo -> a dictionary of duration strings and player entry lists
    msg -> the message that caused the invocation, used to find the name of the character being added
    user -> the user being added, required since this command is invoked by add as well where the author is not the user necessarily
    """
    #@timer.command()
    async def addme(self,ctx, msg=None, userInfo="", user=""):
        # user found is used to check if the user can be found in one of the current entries in start
        userFound = user.id in userInfo["Players"]
        # the user to add
        addUser = user
        channel = ctx.channel
        dmChar = userInfo["DM"]
        # Check if the player that will be added will exceed the player limit
        playerCount = len(userInfo["Players"])
        playerLimit = 7
        
        # make sure that only the the relevant user can respond
        def addMeEmbedCheck(r, u):
            sameMessage = False
            if addEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and (u == dmChar["Member"])
        
        role = userInfo["Role"]
        # take the current time
        startTime = time.time()
        
        # if we didnt find the user we now need to the them to the system
        if not userFound:
            
            if addUser == userInfo["DM"]["Member"]:
                role = "DM"
            
            elif playerCount + 1 > playerLimit:
                await channel.send(f'You cannot add more than {playerLimit} players to the timer.')
                return userInfo
            
            # first we invoke the signup command
            # this will return a player entry
            user_dic =  await self.signup(ctx, role=role, char=msg, author=addUser) 
            # if a character was found we then can proceed to setup the timer tracking
            if user_dic:
                # create an embed object for user communication
                addEmbed = discord.Embed()
                # get confirmation to add the character to the game
                addEmbed.title = f"Add ***{user_dic['Character']['Name']}*** to timer?"
                addEmbed.description = f"***{addUser.mention}*** is requesting their character to be added to the timer.\n***{user_dic['Character']['Name']}*** - Level {user_dic['Character']['Level']}: {user_dic['Character']['Race']} {user_dic['Character']['Class']}\nConsumables: {', '.join(user_dic['Brought'])}\n\n✅: Add to timer\n\n❌: Deny"
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
                    await channel.send(f'Timer addme cancelled. Try again using the following command:\n```yaml\n{commandPrefix}timer addme "character name" "consumable1, consumable2, [...]"```')
                    # cancel this command and avoid things being added to the timer
                    return userInfo
                else:
                    await addEmbedmsg.clear_reactions()
                    # cancel if the DM wants to deny the user
                    if tReaction.emoji == '❌':
                        await addEmbedmsg.edit(embed=None, content=f"Request to be added to timer denied.")
                        await addEmbedmsg.clear_reactions()
                        # cancel this command and avoid things being added to the timer
                        return userInfo
                    await addEmbedmsg.edit(embed=None, content=f"I've added ***{addUser.display_name}*** to the timer.")
            
                if addUser == dmChar["Member"]:
                    userInfo["DM"].update(user_dic)
                else:
                    # since the timer has already been going when this user is added it has to be partial rewards
                    user_dic["Duration"] = 0
                    user_dic["Latest Join"] = startTime
                    user_dic["State"] = "Partial"
                    userInfo["Players"][addUser.id] = user_dic
        # the following are the case where the player has already been on the timer
        elif userInfo["Players"][user.id]["State"] in ["Full", "Partial"]:
            await channel.send(content='Your character has already been added to the timer.')
        elif userInfo["Players"][user.id]["State"] in ["Removed", "Dead"]:
            userInfo["Players"][user.id]["Latest Join"] = startTime
            userInfo["Players"][user.id]["State"] = "Partial"
            await channel.send(content='You have been re-added to the timer.')
        
        return userInfo
    """
    This command is used to add players to the prep list or the running timer
    The code for adding players to the timer has been refactored into 'addme' and here just limits the addition to only one player
    """
    #@timer.command()
    async def add(self,ctx, msg, userInfo=None):
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
            # if this was done during the prep phase then we only need to return the user
            if prep:
                return addUser
            # in the duringTimer stage we need to add them to the timerDictionary instead
            # the dictionary gets manipulated directly which affects all versions
            else:
                #otherwise we need to add the user properly to the timer and perform the setup
                await self.addme(ctx, userInfo=userInfo, msg=msg, user=addUser) 
        return userInfo
    
    async def addDuringTimer(self,ctx, msg=None, userInfo=None):
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
            await self.addme(ctx, userInfo=userInfo, msg=msg, user=addUser) 
        return userInfo

    #@timer.command()
    async def removeme(self,ctx, msg=None, userInfo="",user="", death=False):
        # take the current time
        endTime = time.time()
        # if no entry could be found we inform the user and return the unchanged state
        if not user.id in userInfo["Players"]:
            await ctx.channel.send(content=f"***{user}***, I couldn't find you on the timer to remove you.") 
            return userInfo
        user_dic = userInfo["Players"][user.id]
        
        if user_dic["State"] == "Removed": 
            # since they have been removed last time, they cannot be removed again
            await ctx.channel.send(content=f"You have already been removed from the timer.")  
        
        # if the player has been there the whole time
        else:
            if not userInfo["Paused"]:
                user_dic["Duration"] += endTime - user_dic["Latest Join"] 
            user_dic["State"] = "Removed"
            if death:
                user_dic["State"] = "Dead"
            await ctx.channel.send(content=f"***{user}***, you have been removed from the timer.")
        
        return userInfo
    
    async def pause(self,ctx, userInfo="", msg=""):
        channel = ctx.channel
        if userInfo["Paused"]:
            await channel.send(f'Sorry, the timer is already paused.')
            return
        msg_split = msg.content.split(' ', 2)
        if len(msg_split)<3:
            reason = None
        else:
            reason =  msg_split[2].strip()
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
        await pause_msg.edit(embed=None, content=f"Timer Paused. {options[choice]} Reason:\n```{reason}```Use `$timer unpause` to continue the timer")
        
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
    
    #@timer.command()
    async def death(self,ctx, msg=None, userInfo="", role=""):
        await self.removeDuringTimer(ctx, msg=msg, userInfo=userInfo, death=True)
    
    """
    This command is used to remover players from the prep list or the running timer
    The code for removing players from the timer has been refactored into 'removeme' and here just limits the addition to only one player
    msg -> the message that caused the invocation of this command
    userInfo-> this would be clearer as a None object since the final return element is a Member object
    death -> if the removal is because the character died in the game
    """
    #@timer.command()
    async def remove(self,ctx, msg, userInfo=None, death=False):
        guild = ctx.guild
        removeList = msg.mentions

        if len(removeList) > 1:
            await ctx.channel.send(content=f"I cannot remove more than one player! Please try the command with one player and check your format and spelling.")
            return None
        elif len(removeList) == 0:
            await ctx.channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
        elif not removeList[0].id in userInfo["Players"]:
            await ctx.channel.send(content=f"I cannot find the mentioned player in the roster.")
            return None
        else:
            removeUser = removeList[0]
            await self.removeme(ctx, userInfo=userInfo, msg=msg, user=removeList[0], death=death)
                
    async def removeDuringTimer(self,ctx, msg=None, userInfo=None, death=False):
        guild = ctx.guild
        removeList = msg.mentions
        removeUser = ""

        if len(removeList) > 1:
            await ctx.channel.send(content=f"I cannot remove more than one player! Please try the command with one player and check your format and spelling.")
            return None

        elif removeList != list():
            removeUser = removeList[0]
            await self.removeme(ctx, msg, userInfo, user=removeUser,death=death)
        else:
            await ctx.channel.send(content=f"I cannot find any mention of the user you are trying to remove. Please check your format and spelling.")
        return userInfo

    """
    the command used to display the current state of the game timer to the users
    userInfo -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    author -> the Member object of the DM of the game
    """
    #@timer.command()
    async def stamp(self,ctx,userInfo, author="",embed="", embedMsg=""):
        user = author.display_name
        # calculate the total duration of the game so far
        end = time.time()
        pause_duration = (end - userInfo["Last Pause"])*userInfo["Paused"]
        duration = end - userInfo["Start"] - userInfo["Paused Time"] - pause_duration
        durationString = timeConversion(duration + time_bonus)
        if userInfo["Paused"]:
            pause_shift = 1800 * (userInfo["Pause Type"]+1) + 90
            durationString = f"{durationString} || **PAUSE [{timeConversion(pause_shift-pause_duration)} Remaining]**"
        # reset the fields in the embed object
        embed.clear_fields()
        guild_text = "\n".join([guild_channel.mention for guild_channel in userInfo["Guilds"]])
        embed.description = guild_text
        # for every entry in the timer dictionary we need to perform calculations
        for player in userInfo["Players"].values():
            consumablesString = ""
            rewardsString = ""
            # if the game were without rewards we would not have to check for consumables
            if player["Brought"] != []:
                consumablesString = "\nConsumables: " + ', '.join(player["Brought"])
            rList = player["Inventory"]["Add"]+player["Consumables"]["Add"]+player["Magic Items"]
            if rList != list():
                rewardsString = "\nRewards: " + ', '.join([x["Name"] for x in rList])
            # create field entries for every reward entry as appropriate
            if player["State"] == "Full":
                embed.add_field(name= f"**{player['Member'].display_name}**", value=f"{player['Character']['Name']}\nLevel {player['Character']['Level']}: {player['Character']['Race']} {player['Character']['Class']}{consumablesString}{rewardsString}", inline=False)
            elif player["State"] == "Removed":
                pass
            # list that the character died
            elif player["State"] == "Dead":
                duration = player["Duration"]
                embed.add_field(name= f"~~{player['Member'].display_name}~~", value=f"{player['Character']['Name']} - **DEATH**{consumablesString}{rewardsString}", inline=False) 
            else:
                duration = player["Duration"]+ (end - player["Latest Join"])* (not userInfo["Paused"])
                embed.add_field(name= f"**{player['Member'].display_name}** - {timeConversion(duration)} (Latecomer)\n", value=f"{player['Character']['Name']}\nLevel {player['Character']['Level']}: {player['Character']['Race']} {player['Character']['Class']}{consumablesString}{rewardsString}", inline=False)
                
        dm_text = "No Character"
        if(userInfo["DM"]["Character ID"]):
            item_rewards = userInfo["DM"]["Inventory"]["Add"]+userInfo["DM"]["Consumables"]["Add"]+userInfo["DM"]["Magic Items"]
            dm_text = userInfo["DM"]["Character"]["Name"]+ ("\nRewards:"+"\n"+(', '.join([x["Name"] for x in item_rewards])))*(item_rewards != list())
        embed.add_field(name= f"**DM: {userInfo['DM']['Member'].display_name}**", value=dm_text, inline=False)
        # update the title of the embed message with the current time
        embed.title = f'**{userInfo["Game"]}**: {durationString}'
        msgAfter = False
        
        stampHelp = f"""```yaml
Command Checklist
- - - - - - - - -
1. Player uses an item: - item
2. DM adds themselves or a player or a player joins late:
   • DM adds: $timer add @player "character name" "consumable1, consumable2, [...]"
   • Player joins: $timer addme "character name" "consumable1, consumable2, [...]"
3. DM removes a player or they leave early:
   • DM removes: $timer remove @player
   • Player leaves: $timer removeme
4. DM awards Reward Items: $timer reward @player "reward item1, reward item2, [...]"
5. DM revokes Reward Items: $timer undo rewards [@player1 @player2 ...]
6. DM removes a dead character: $timer death @player
7. DM stops the one-shot: $timer stop
8. DM pause the timer: $timer pause reason```"""
            
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

    #@timer.command(aliases=['end'])
    async def stop(self,ctx,userInfo):
        if userInfo["Paused"]:
            await self.unpause(ctx, userInfo=userInfo, silent=True)
        end = time.time() + time_bonus
        tierNum = 0
        guild = ctx.guild
        role = userInfo["Role"]
        game = userInfo["Game"]
        dmChar = userInfo["DM"]
        stopEmbed = discord.Embed()
        
        stopEmbed.set_footer(text=f"Placeholder, if this remains remember the wise words DO NOT PANIC and get a towel.")
        
        # turn Tier string into tier number
        if role == "Ascended":
            tierNum = 5
        elif role == "True":
            tierNum = 4
        elif role == "Elite":
            tierNum = 3
        elif role == "Journey":
            tierNum = 2
        elif role == "New":
            tierNum = 0
        else:
            tierNum = 1
    
        deathChars = []
        
        # Session Log Channel
        logChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Sessions"])  # 728456783466725427 737076677238063125
        
        
        dbEntry = {}
        dbEntry["Role"] = role
        dbEntry["Tier"] = tierNum
        dbEntry["Channel"] = ctx.channel.name
        dbEntry["End"] = end
        dbEntry["Game"] = game
        dbEntry["Status"] = "Processing"
        dbEntry["Players"] = {}
        
        dbEntry["DDMRW"] = settingsRecord["ddmrw"] or userInfo["DDMRW"]
        dbEntry["Event"] = settingsRecord["Event"]
        if tierNum < 1:
            tierNum = 1
        rewardsCollection = db.rit
        rewardList = list(rewardsCollection.find({"Tier": tierNum}))
        rewardList_lower = list(rewardsCollection.find({"Tier": max(tierNum-1, 1)}))
        starting_time = userInfo["Start"]
        # list of players in this entry
        playerList = []
        totalDurationTime = end - starting_time - userInfo["Paused Time"]
        # get the string to represent the duration in hours and minutes
        totalDuration = timeConversion(totalDurationTime)
        # go through the dictionary of times and calculate the rewards of every player
        
        for player in userInfo["Players"].values():
            duration = player["Duration"]
            if player["State"] in ["Full", "Partial"]:
                duration += end - player["Latest Join"]
            playerDBEntry={}
            randomItems = [random.choice(rewardList).copy(), random.choice(rewardList_lower).copy()]
            playerDBEntry["Double Items"] = []
            for i in randomItems:
                if("Grouped" in i):
                    i["Name"] = random.choice(i["Name"])
                elif("Spell Scroll" in i["Name"]):
                    if("Cantrip" in i["Name"]):
                        spell_level = 0
                    else:
                        spell_level = [int(x) for x in i["Name"] if x.isnumeric()][0]
                    
                    spell_result = list(db.spells.aggregate([{ "$match": { "Level": spell_level } }, { "$sample": { "size": 1 } }]))[0]
                    i["Name"] = f"Spell Scroll ({spell_result['Name']})"
                playerDBEntry["Double Items"].append([i["Type"], i["Name"]])
            playerDBEntry["Magic Items"] = [x["Name"] for x in player["Magic Items"]]
            playerDBEntry["Consumables"] = player["Consumables"]
            playerDBEntry["Consumables"]["Add"] = [x["Name"] for x in player["Consumables"]["Add"]]
            playerDBEntry["Inventory"] = player["Inventory"]
            playerDBEntry["Inventory"]["Add"] = [x["Name"] for x in player["Inventory"]["Add"]]
            playerDBEntry["Status"] = "Alive"
            if player["State"] == "Dead":
                playerDBEntry["Status"] = "Dead"
            playerDBEntry["Character ID"] = player["Character"]["_id"]
            playerDBEntry["Character Name"] = player["Character"]["Name"]
            playerDBEntry["Level"] = player["Character"]["Level"]
            if "Guild" in player["Character"]:
                playerDBEntry["Guild"] = player["Character"]["Guild"]
                playerDBEntry["2xR"] = True
                playerDBEntry["2xI"] = True
                playerDBEntry["Guild Rank"] = player["Character"]["Guild Rank"]
            playerDBEntry["Character CP"] = player["Character"]["CP"]
            playerDBEntry["Mention"] = player["Member"].mention

            playerDBEntry["CP"] = (duration// 1800) / 2
            # add the player to the list of completed entries
            dbEntry["Players"][f"{player['Member'].id}"] = playerDBEntry
            playerList.append(player)
        hoursPlayed = (totalDurationTime // 1800) / 2
        
        if hoursPlayed < 0.5:
            await ctx.channel.send(content=f"The session was less than 30 minutes and therefore was not counted.")
            return
            
        if hoursPlayed < 3: 
            await self.undoConsumables(ctx, userInfo=userInfo)
            
        # post a session log entry in the log channel
        sessionMessage = await logChannel.send(embed=stopEmbed)
        await ctx.channel.send(f"The timer has been stopped! Your session log has been posted in the {logChannel.mention} channel. Write your session log summary in this channel by using the following command:\n```ini\n$session log {sessionMessage.id} [Replace the brackets and this text with your session summary log.]```")

        stopEmbed.set_footer(text=f"Game ID: {sessionMessage.id}")
        modChannel = self.bot.get_channel(settingsRecord[str(ctx.guild.id)]["Mod Logs"])
        modEmbed = discord.Embed()
        modEmbed.description = f"""A one-shot session log was just posted for {ctx.channel.mention}.

DM: {dmChar["Member"].mention} 
Game ID: {sessionMessage.id}
Link: {sessionMessage.jump_url}

React with :construction: if a summary log has not yet been appended by the DM.
React with :pencil: if you messaged the DM to fix something in their summary log.
React with ✅ if you have approved the session log.
React with :x: if you have denied the session log.
React with :classical_building: if you have denied one of the guilds.

Reminder: do not deny any session logs until we have spoken about it as a team."""
        modMessage = await modChannel.send(embed=modEmbed)
        for e in ["🚧", "📝", "✅", "❌", "🏛️"]:
            await modMessage.add_reaction(e)    
            
        
        dbEntry["Start"] = starting_time
        dbEntry["Paused Time"] = userInfo["Paused Time"]
        dbEntry["Log ID"] = sessionMessage.id
        
        stopEmbed.title = f"Timer: {game} [END] - {totalDuration}"
        stopEmbed.description = "**General Summary**" + """
• Give context to pillars and guild quest guidelines.
• Focus on the outline of quest and shouldn't include "fluff".
• Must list which pillar(s) were fulfilled.

In order to help determine if the adventurers fulfilled a pillar or a guild's quest guidelines, answer the following questions:

**Exploration**
• Did they deal with environmental effects? How did they resolve them?
• Did they interact the environment to gather info and make informed decisions? What were the clues? How did these contribute to their success?
• Did they travel or solve a puzzle/trap within a limited time frame? What problems did they have to face? How were they solved?
• How did any unsuccessful attempts negatively affect future events?

**Social**
• Did they change an NPC's attitude? How did they do it and why was it important?
• Did they convince an NPC of something against their nature or traits? Why was it important?
• Did they retrieve info from an NPC? How did they retrieve it? How was it relevant to the main objective?
• How did any unsuccessful attempts negatively affect future events?

**Combat**
• Did they fight? What kind of creatures and why? How did these encounters relate to the main objective?
• Did they engage in combat as a result of unsuccessful attempts in the Exploration or Social pillars?
• Did combat present complications for future events?

**Guilds**
• How were guilds central to plot and setting, main objectives, core elements, and overall progression of your one-shot?
• Which guidelines were fulfilled and how?
• If guidelines were not fulfilled, how/why did the party fail?
""" 
        # get the collections of characters
        playersCollection = db.players
        logCollection = db.logdata
        # and players
        usersCollection = db.users

        # Noodles Math
        # get the user record of the DM
        uRecord  = usersCollection.find_one({"User ID": str(dmChar["Member"].id)})
        noodles = 0
        # get the total amount of minutes played
        
        #DM REWARD MATH STARTS HERE
        dmDBEntry = {}
        if(dmChar["Character ID"]):
            dm_char_level = dmChar["Character"]["Level"]
            if dm_char_level < 5:
                dm_tier_num = 1
            elif dm_char_level < 11:
                dm_tier_num = 2
            elif dm_char_level < 17:
                dm_tier_num = 3
            elif dm_char_level < 20:
                dm_tier_num = 4
            else:
                dm_tier_num = 5
                
            player = dmChar
            rewardList = list(rewardsCollection.find({"Tier": dm_tier_num}))
            rewardList_lower = list(rewardsCollection.find({"Tier": max(dm_tier_num -1,1)}))
            randomItems = [random.choice(rewardList), random.choice(rewardList_lower)]
            
            dmDBEntry["Double Items"] = []
            
            for i in randomItems:
                if("Grouped" in i):
                    i["Name"] = random.choice(i["Name"])
                elif("Spell Scroll" in i["Name"]):
                    if("Cantrip" in i["Name"]):
                        spell_level = 0
                    else:
                        spell_level = [int(x) for x in i["Name"] if x.isnumeric()][0]
                    
                    spell_result = list(db.spells.aggregate([{ "$match": { "Level": spell_level } }, { "$sample": { "size": 1 } }]))[0]
                    i["Name"] = f"Spell Scroll ({spell_result['Name']})"
                dmDBEntry["Double Items"].append([i["Type"], i["Name"]])
            dmDBEntry["Magic Items"] = [x["Name"] for x in player["Magic Items"]]
            dmDBEntry["Consumables"] = player["Consumables"]
            dmDBEntry["Consumables"]["Add"] = [x["Name"] for x in player["Consumables"]["Add"]]
            dmDBEntry["Inventory"] = player["Inventory"]
            dmDBEntry["Inventory"]["Add"] = [x["Name"] for x in player["Inventory"]["Add"]]
            dmDBEntry["Character ID"] = player["Character"]["_id"]
            dmDBEntry["Character Name"] = player["Character"]["Name"]
            dmDBEntry["Level"] = player["Character"]["Level"]
            if "Guild" in player["Character"]:
                dmDBEntry["Guild"] = player["Character"]["Guild"]
                dmDBEntry["2xR"] = True
                dmDBEntry["2xI"] = True
                dmDBEntry["Guild Rank"] = player["Character"]["Guild Rank"]
            dmDBEntry["Character CP"] = player["Character"]["CP"]
            dmDBEntry["DM Double"] = True
            playerList.append(player)
                
        dmDBEntry["ID"] = str(dmChar["Member"].id)
        dmDBEntry["Mention"] = dmChar["Member"].mention
        n=0
        if uRecord and "Noodles" in uRecord:
            n = uRecord["Noodles"]
        dmDBEntry["Noodles"] = n
        
        dmDBEntry["CP"] = hoursPlayed
        
        dbEntry["DM"] = dmDBEntry
        
        dbEntry["Guilds"] = {}
        
        # get the db collection of guilds and set up variables to track relevant information
        guildsCollection = db.guilds
        # if a member of the guild was in the game
        guildMember = False
        # list of all guild records that need to be update, with the updates applied
        guildsRecordsList = list()
        guildsList = userInfo["Guilds"]
        # passed in parameter, check if there were guilds involved
        if guildsList != list():
            # for every guild in the game
            for g in guildsList:
                # get the DB record of the guild
                gRecord  = guildsCollection.find_one({"Channel ID": str(g.id)})
                if not gRecord:
                    continue
                guildDBEntry = {}
                guildDBEntry["Status"] = True
                guildDBEntry["Rewards"] = False
                guildDBEntry["Items"] = False
                guildDBEntry["Drive"] = False
                guildDBEntry["Mention"] = g.mention
                guildDBEntry["Name"] = gRecord["Name"]
                
                dbEntry["Guilds"][gRecord["Name"]] = guildDBEntry
                
                # if the guild exists in the DB
        # create a list of of UpdateOne objects from the data entries for the bulk_write
        timerData = list(map(lambda item: UpdateOne({'_id': item["Character ID"]}, {"$set": {"GID": dbEntry["Log ID"]}}), playerList))
        

        # try to update all the player entries
        try:
            playersCollection.bulk_write(timerData)

            logCollection.insert_one(dbEntry)
        except BulkWriteError as bwe:
            print(bwe.details)
            # if it fails, we need to cancel and use the error details
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
            return
        await sessionMessage.edit(embed=stopEmbed)

        try:
            # create a bulk write entry for the players
            usersData = list(map(lambda item: UpdateOne({'User ID':str(item["Member"].id) }, {'$set': {'User ID':str(item["Member"].id) }}, upsert=True), playerList))
            usersCollection.bulk_write(usersData)
        except BulkWriteError as bwe:
            print(bwe.details)
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            charEmbedmsg = await ctx.channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the timer again.")
        await generateLog(self, ctx, dbEntry["Log ID"], sessionInfo = dbEntry)
            

        return
    
    @timer.command()
    @commands.has_any_role('Mod Friend', 'A d m i n')
    async def list(self,ctx):
        timer_list = list(currentTimers.keys())
        if not timer_list:
            currentTimersString = "There are currently NO timers running!"
        else:
            currentTimersString = "There are currently timers running in these channels:\n"
        currentTimersString += f"\n".join([f"{x}: {currentTimers[x]['State']}" for x in timer_list])
        await ctx.channel.send(content=currentTimersString)

    @timer.command()
    @commands.has_any_role('Mod Friend', 'A d m i n')
    async def resetcooldown(self,ctx):
        self.timer.get_command('prep').reset_cooldown(ctx)
        await ctx.channel.send(f"Timer has been reset in #{ctx.channel}")
    
    
    
    #extracted the checks to here to generalize the changes
    async def permissionCheck(self, msg, author):
        # check if the person who sent the message is either the DM, a Mod or a Admin
        if not (msg.author == author or "Mod Friend".lower() in [r.name.lower() for r in msg.author.roles] or "A d m i n s".lower() in [r.name.lower() for r in msg.author.roles]):
            await msg.channel.send(f'You cannot use this command!') 
            return False
        else: 
            return True
    
    @timer.command()
    @commands.cooldown(1, float('inf'), type=commands.BucketType.channel) 
    @commands.has_any_role('D&D Friend', 'Campaign Friend')
    async def resume(self,ctx):
        
        channel = ctx.channel
        if channel.mention not in currentTimers:
            self.timer.get_command('resume').reset_cooldown(ctx)
            return
        userInfo = currentTimers[channel.mention]
        if userInfo["State"] != "Crashed":
            self.timer.get_command('resume').reset_cooldown(ctx)
            return
        author = userInfo["DM"]["Member"]
        if author != ctx.author and not await self.permissionCheck(ctx.message, ctx.author):
            self.timer.get_command('resume').reset_cooldown(ctx)
            return
            
        userInfo["State"] = "Running"
        stampEmbed = discord.Embed()
        stampEmbed.title = f' a '
        stampEmbed.set_footer(text=f'#{ctx.channel}\nUse the following command to see a list of timer commands: {commandPrefix}help timer')
        stampEmbed.set_author(name=f'DM: {author.name}', icon_url=author.display_avatar)
        stampEmbedMsg =  await self.stamp(ctx, userInfo, ctx.author, stampEmbed)
        await self.duringTimer(ctx, userInfo, stampEmbed, stampEmbedMsg)
        del currentTimers[channel.mention]
        self.timer.get_command('resume').reset_cooldown(ctx)

    """
    userInfo -> a dictionary of strings and player list pairs, the strings are made out of the kind of reward and the duration and the value is a list of players entries (format can be found as the return value in signup)
    """  
    async def randomRew(self,ctx, msg=None, userInfo="", rewardType=None):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild

        rewardList = msg.mentions
        dmChar = userInfo["DM"]
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user to hand out a random item.") 
            #return the unchanged parameters
            return None
        else:
            # get the first user mentioned
            rewardUser = rewardList[0]
            userFound = rewardUser.id in userInfo["Players"]

            # if the user getting rewards is the DM we can save time by not going through the loop
            if rewardUser == dmChar["Member"] and dmChar["Character"]=="No Rewards":
                await ctx.channel.send(content=f"You did not sign up with a character to reward items to.") 
                #return the unchanged parameters
                return None #cause error
            elif rewardUser == dmChar["Member"]: 
                userFound = True
                # the player entry of the player getting the item
                player = dmChar
            else:
                player = userInfo["Players"][rewardUser.id]
        if not userFound:
            await ctx.channel.send(content=f"***{rewardUser}*** is not on the timer to receive rewards.")
            return None
        
        charLevel = int(player["Character"]['Level'])
        # calculate the tier of the rewards
        tierNum = 5
        if charLevel < 5:
            tierNum = 1
        elif charLevel < 11:
            tierNum = 2
        elif charLevel < 17:
            tierNum = 3
        elif charLevel < 20:
            tierNum = 4

        player_type = "Players"
        item_rewards = []
        if rewardUser == dmChar["Member"]:
            if dmChar["Noodle"] in ["Newdle", "Junior Noodle", "Good Noodle", "Elite Noodle"]:
                tierNum = max(tierNum - 1, 1)
            player_type = "DM"
            item_rewards = dmChar["Inventory"]["Add"] + dmChar["Consumables"]["Add"] + dmChar["Magic Items"]
        else:
            for player in userInfo["Players"].values():
                item_rewards += player["Inventory"]["Add"] + player["Consumables"]["Add"] + player["Magic Items"]
        
        blocking = list(map(blocking_type, item_rewards))
        rewardCollection = db.rit
        randomItem = await randomReward(self, ctx, tier=tierNum, rewardType=rewardType, block=blocking, player_type=player_type, amount=1)
        if randomItem == None:
            await channel.send(f'Try again!\n')
            return None

        return f"{randomItem[0]}"
    def startsWithCheck(self, message, target):
        return any([message.content.startswith(f"{commandPrefix}{x} {target}") for x in ["t", "timer"]])
        
    
    """
    This functions runs continuously while the timer is going on and waits for commands to come in and then invokes them itself
    stampEmbed -> the Embed object containing the information in regards to current timer state
    stampEmbedMsg -> the message containing stampEmbed
    """
    async def duringTimer(self,ctx,  userInfo, stampEmbed, stampEmbedmsg):
        # set up the variable for the continuous loop
        timerStopped = False
        channel = ctx.channel
        author = userInfo["DM"]["Member"]
        user = author.display_name
        timerAlias = ["timer", "t"]

        #in no rewards games characters cannot die or get rewards
        timerCommands = ['stop', 'end', 'add', 'remove', 'death', 'reward', 'stamp', 'undo rewards', "guild", 'major', 'minor', 'pause', 'unpause']
        
        timerCombined = []
        #create a list of all command an alias combinations
        for x in product(timerAlias,timerCommands):
            timerCombined.append(f"{commandPrefix}{x[0]} {x[1]}")
        
        #repeat this entire chunk until the stop command is given
        while not timerStopped:
            try:
                #the additional check for  '-' being only in games with a tier allows for consumables to be used only in proper games
                msg = await self.bot.wait_for('message', timeout=60.0, check=lambda m: (any(x in m.content for x in timerCombined) or m.content.startswith('-')) and m.channel == channel)
                msg.content = msg.content.replace("“", "\"").replace("”", "\"")
                
                #unpause the timer
                if (self.startsWithCheck(msg, "unpause")):
                    if await self.permissionCheck(msg, author):
                        await self.unpause(ctx, userInfo=userInfo)
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                #pause the timer
                elif (self.startsWithCheck(msg, "pause")):
                    if await self.permissionCheck(msg, author):
                        await self.pause(ctx, userInfo=userInfo, msg=msg)
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                # this is the command used to stop the timer
                # it invokes the stop command with the required information, explanations for the parameters can be found in the documentation
                # the 'end' alias could be removed for minimal efficiancy increases
                elif (self.startsWithCheck(msg, "stop") or self.startsWithCheck(msg, "end")):
                    # check if the author of the message has the right permissions for this command
                    if await self.permissionCheck(msg, author):
                        confirm_embed = discord.Embed()
                        confirm_embed.title = "**Please confirm that you have you signed up a character for DM Rewards if desired, and that you have given out all the reward items you want to hand out**"
                        stop_confirm_message = await channel.send(embed=confirm_embed)
                        decision = await confirm(stop_confirm_message, ctx.author)
                        await stop_confirm_message.delete()
                        if decision == 1:
                            await self.stop(ctx, userInfo=userInfo)
                            timerStopped = True
                       
                # this behaves just like add below, but skips the ambiguity check of addme since only the author of the message could be added
                elif (self.startsWithCheck(msg, "addme ")):
                    userInfo = await self.addme(ctx, userInfo=userInfo, msg=msg, user=msg.author)
                    stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                # @player is a protection from people copying the command
                elif (self.startsWithCheck(msg, "add ")) and '@player' not in msg.content:
                    # check if the author of the message has the right permissions for this command
                    if await self.permissionCheck(msg, author):
                        # update the userInfo with the new added player
                        await self.addDuringTimer(ctx, userInfo=userInfo, msg=msg)
                        # update the msg with the new stamp
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "removeme")):
                    userInfo = await self.removeme(ctx, userInfo=userInfo, user=msg.author)
                    stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "remove ")):
                    if await self.permissionCheck(msg, author): 
                        await self.removeDuringTimer(ctx, msg, userInfo)
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "stamp")):
                    stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "reward")):
                    if await self.permissionCheck(msg, author):
                        userInfo = await self.reward(ctx, msg=msg, userInfo=userInfo)
                elif (self.startsWithCheck(msg, "major")):
                    if await self.permissionCheck(msg, author):
                        rewardItem = await self.randomRew(ctx, msg=msg, userInfo=userInfo, rewardType="Major")
                        if rewardItem is not None:
                            msg.content = msg.content + " " + f'"{rewardItem}"'
                            userInfo = await self.reward(ctx, msg=msg, userInfo=userInfo, exact=True)
                elif (self.startsWithCheck(msg, "minor")):
                    if await self.permissionCheck(msg, author):
                        rewardItem = await self.randomRew(ctx, msg=msg, userInfo=userInfo, rewardType="Minor")
                        if rewardItem is not None:
                            msg.content = msg.content + " " + f'"{rewardItem}"'
                            userInfo = await self.reward(ctx, msg=msg, userInfo=userInfo, exact=True)
                elif (self.startsWithCheck(msg, "death")):
                    if await self.permissionCheck(msg, author):
                        await self.death(ctx, msg=msg, userInfo=userInfo)
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif msg.content.startswith('-') and msg.author != userInfo["DM"]["Member"]:
                    await self.deductConsumables(ctx, msg=msg, userInfo=userInfo)
                    stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "undo rewards")):
                    # check if the author of the message has the right permissions for this command
                    if await self.permissionCheck(msg, author):
                        # update the userInfo with the new added player
                        await self.undoConsumables(ctx, msg, userInfo)
                        # update the msg with the new stamp
                        stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
                elif (self.startsWithCheck(msg, "guild")):
                    if await self.permissionCheck(msg, author):
                        guildCategoryID = settingsRecord[str(ctx.guild.id)]["Guild Rooms"]

                        if (len(msg.channel_mentions) > 2):
                            await channel.send(f"The number of guilds exceeds two. Please follow this format and try again:\n```yaml\n{commandPrefix}timer guild #guild1 #guild2```") 
                        else:
                            guildsList = msg.channel_mentions
                            invalidChannel = False
                            for g in guildsList:
                                if g.category_id != guildCategoryID:
                                    await channel.send(f"***{g}*** is not a guild channel. Please follow this format and try again:\n```yaml\n{commandPrefix}timer guild #guild1, #guild2```") 
                                    invalidChannel = True
                            if not invalidChannel:
                                userInfo["Guilds"] = guildsList
                                stampEmbedmsg = await self.stamp(ctx, userInfo, author=author, embed=stampEmbed, embedMsg=stampEmbedmsg)

            except asyncio.TimeoutError:
                stampEmbedmsg = await self.stamp(ctx, userInfo, author, embed=stampEmbed, embedMsg=stampEmbedmsg)
            else:
                pass
            if userInfo["Paused"] and time.time()-60 - userInfo["Last Pause"] > 1800 * (userInfo["Pause Type"]+1):
                await channel.send(f"Pause limit exceeded. Timer has been stopped") 
                await self.stop(ctx, userInfo=userInfo)
                timerStopped = True
               
async def setup(bot):
    await bot.add_cog(Timer(bot))