import asyncio
import traceback
from discord.ext import commands
from os import listdir
from os.path import isfile, join
from itertools import cycle

from bfunc import *

cogs_dir = "cogs"

# Files to check for server differences: logs, timer, misc

# Things that can change
# ~ Server roles.
# ~ Quest Board.
# ~ Session Logs.
# ~ Campaign Board.
# ~ Applications.
# ~ Game Rooms (including timers).
# ~ General Rooms (excluding timers).
# ~ Suggestions.
# ~ General Reports.
# ~ Staff Reports.

async def change_status():
      await bot.wait_until_ready()
      statusLoop = cycle(statuses)

      while not bot.is_closed():
          current_status = next(statusLoop)
          await bot.change_presence(activity=discord.Activity(name=current_status, type=discord.ActivityType.watching))
          await asyncio.sleep(5)

@bot.event
async def on_ready():
    print('We have logged in as ' + bot.user.name)
    bot.loop.create_task(change_status())

    #secret area channel
    # channel = bot.get_channel(577611798442803205) 
    # await channel.send('Hello I have restarted uwu')
  
bot.remove_command('help')

@bot.event
async def on_command_error(ctx,error):
    msg = None
    print(ctx.invoked_with)
    print(ctx.command.parent)
    print(error)
    
    if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
        await ctx.channel.send("There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command. ")
        #bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
        ctx.command.reset_cooldown(ctx)
        return
    
    elif ctx.cog is not None and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
        return
        
    elif isinstance(error, commands.CommandOnCooldown):
        commandParent = ctx.command.parent
        if commandParent is None:
            commandParent = ''
        else:
            commandParent = commandParent.name + " "

        if error.retry_after == float('inf'):
            await ctx.channel.send(f"Sorry, the command **`{commandPrefix}{commandParent}{ctx.invoked_with}`** is already in progress, please complete the command before trying again.")
        else:
            await ctx.channel.send(f"Sorry, the command **`{commandPrefix}{commandParent}{ctx.invoked_with}`** is on cooldown for you! Try the command in the next " + "{:.1f}seconds".format(error.retry_after))
        return



    elif isinstance(error, commands.CommandNotFound):
        await ctx.channel.send(f'Sorry, the command **`{commandPrefix}{ctx.invoked_with}`** is not valid, please try again!')

    else:
        ctx.command.reset_cooldown(ctx)
        await traceBack(ctx,error)

@bot.command()
async def help(ctx, *, pageString=''):
    def helpCheck(r,u):
        sameMessage = False
        if helpMsg.id == r.message.id:
            sameMessage = True
        return (r.emoji in alphaEmojis[:numPages]) and u == ctx.author and sameMessage

    helpEmbedMenu = discord.Embed()
    helpEmbedGen = discord.Embed()
    helpEmbedChar = discord.Embed()
    helpEmbedItems = discord.Embed() 
    helpEmbedTimerOne = discord.Embed()
    helpEmbedTimerTwo = discord.Embed()
    helpEmbedTimerThree = discord.Embed()
    helpEmbedShop = discord.Embed()
    helpEmbedTp = discord.Embed()
    helpEmbedGuild = discord.Embed()
    helpEmbedCampaign = discord.Embed()

    page = 0
    if 'gen' in pageString:
        page = 1
    elif 'char' in pageString:
        page = 2
    elif 'tp' in pageString:
        page = 3
    elif 'shop' in pageString:
        page = 4
    elif 'guild' in pageString:
        page = 5
    elif 'timer2' in pageString:
        page = 7
    elif 'timer3' in pageString:
        page = 8
    elif 'timer1' in pageString or 'timer' in pageString:
        page = 6
    elif 'campaign' in pageString:
        page = 9


# MAIN HELP MENU ($help)


    helpList = [helpEmbedMenu, helpEmbedGen, helpEmbedChar, helpEmbedTp, helpEmbedShop, helpEmbedGuild, helpEmbedTimerOne, helpEmbedTimerTwo, helpEmbedTimerThree, helpEmbedCampaign]

    helpEmbedMenu.title = 'Bot Friend Commands - Table of Contents'
    helpEmbedMenu.description = 'Please react to the group of commands you would like to see and gain more knowledge about.'
    helpEmbedMenu.add_field(name=f"{alphaEmojis[0]}General Commands\n{commandPrefix}help gen", value="Various commands which don't fit into any other section.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[1]}Character Commands\n{commandPrefix}help char", value="How to manage your character(s).", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[2]}TP Commands\n{commandPrefix}help tp", value="How to spend TP to acquire magic items.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[3]}Shop Commands\n{commandPrefix}help shop", value="How to spend GP to purchase various things or sell mundane items.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[4]}Guild Commands\n{commandPrefix}help guild", value="How to be a member of a guild or manage one.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[5]}Pre-Quest Timer Commands\n{commandPrefix}help timer1", value="How to prepare and sign up to a timer for a one-shot.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[6]}Running Timer Commands\n{commandPrefix}help timer2", value="How to do various things while hosting or participating in a one-shot.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[7]}Post-Quest Timer Commands\n{commandPrefix}help timer3", value="How to do various things after the completion of a one-shot.", inline=False)
    helpEmbedMenu.add_field(name=f"{alphaEmojis[8]}Campaign Commands\n{commandPrefix}help campaign", value="How to create, host, and participate in a campaign.", inline=False)



# DM HELP MENU ($help dm)

# THIS HELP MENU WOULD ONLY BE NECESSARY IF WE COULD SPLIT UP THE HELP MENU IN TWO BRANCHES: ONE FOR PLAYERS AND ONE FOR DMs.
#    helpList = [helpEmbedMenuDM, helpEmbedTimerOne, helpEmbedTimerTwo, helpEmbedTimerThree, helpEmbedCampaign]

#    helpEmbedMenu.title = 'Bot Friend DM Commands - Table of Contents'
#    helpEmbedMenu.description = 'Please react to the group of commands you would like to see and gain more knowledge about.'
#    helpEmbedMenu.add_field(name=f"1️⃣ Pre-Quest Timer Commands\n{commandPrefix}help dm timer1", value="", inline=False)
#    helpEmbedMenu.add_field(name=f"2️⃣ Running Timer Commands\n{commandPrefix}help dm timer2", value="", inline=False)
#    helpEmbedMenu.add_field(name=f"3️⃣ Post-Quest Timer Commands\n{commandPrefix}help dm timer3", value="", inline=False)
#    helpEmbedMenu.add_field(name=f"4️⃣ Campaign Commands\n{commandPrefix}help dm campaign", value="", inline=False)



# GENERAL COMMANDS ($help general)

    helpEmbedGen.title = 'General Commands'

    helpEmbedGen.add_field(name=f'▫️ Creating and Viewing Your User Profile', value=f'{commandPrefix}user', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Viewing the List of Allowed Races', value=f'{commandPrefix}printRaces', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Viewing the Help Menu', value=f'{commandPrefix}help', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Applying to a One-shot', value=f'{commandPrefix}apply "character name" "consumable1, consumable2, [...]" "magic item1, magic item2, [...]"', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Calculating Rewards', value=f'{commandPrefix}reward XhYm tier', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Viewing Server Stats', value=f'{commandPrefix}stats', inline=False)

    helpEmbedGen.add_field(name=f'▫️ Viewing Fanatic Competition Stats', value=f'{commandPrefix}fanatic', inline=False)




# CHARACTER COMMANDS MENU ($help char)

    helpEmbedChar.title = 'Character Commands'

    helpEmbedChar.add_field(name=f'▫️ Creating a Character', value=f'{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Viewing a Character\'s Information', value=f'{commandPrefix}info "character name"\n[{commandPrefix}char, {commandPrefix}i]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Viewing a Character\'s Inventory', value=f'{commandPrefix}inventory "character name"\n[{commandPrefix}inv, {commandPrefix}bag]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Adding an Image to a Character', value=f'{commandPrefix}image "character name" "URL"\n[{commandPrefix}img]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Leveling Up', value=f'{commandPrefix}levelup "character name"\n[{commandPrefix}lvlup, {commandPrefix}lvl, {commandPrefix}lv]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Creating a Multiclass Character', value=f'{commandPrefix}create "character name" total level "race" "class1 level / class2 level, [...]" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Respecing a Character', value=f'{commandPrefix}respec "character name" "new character name" "race" "class" "background" STR DEX CON INT WIS CHA', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Respecing a Character into a Multiclass', value=f'{commandPrefix}respec "character name" "new character name" "race" "class1 level / class2 level / class3 level / class4 level" "background" STR DEX CON INT WIS CHA', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Reflavoring a Character', value=f'{commandPrefix}reflavor race "character name" race name\n{commandPrefix}reflavor class "character name" class name\n{commandPrefix}reflavor background "character name" background name\n[{commandPrefix}rf]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Adding Extra Names', value=f'{commandPrefix}alias "character name" "surname, nickname1, nickname2, othername, [...]\n[{commandPrefix}aka]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Adding Alignment', value=f'{commandPrefix}align "character name" alignment', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Retiring a Character', value=f'{commandPrefix}retire "character name"', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Attuning to a Magic Item', value=f'{commandPrefix}attune "character name" "magic item"\n[{commandPrefix}att]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Unattuning from a Magic Item', value=f'{commandPrefix}unattune "character name" "magic item"\n[{commandPrefix}unatt, {commandPrefix}uatt]', inline=False)

    helpEmbedChar.add_field(name=f'▫️ Death Options', value=f'{commandPrefix}death "character name"', inline=False)


# PRE-QUEST TIMER COMMANDS MENU ($help timer1)

# PLAYER COMMANDS

    helpEmbedTimerOne.title = f"Pre-Quest Timer Commands\n{commandPrefix}timer, {commandPrefix}t"

    helpEmbedTimerOne.add_field(name=f'▫️ Signing Up (Player)', value=f'{commandPrefix}timer signup "character name" "consumable1, consumable2, [...]"', inline=False)

# DM COMMANDS

    helpEmbedTimerOne.add_field(name=f'▫️ Preparing the Timer (DM)', value=f'{commandPrefix}timer prep "@player1, @player2, [...]" "quest name" #guild-channel-1 #guild-channel-2', inline=False)

    helpEmbedTimerOne.add_field(name=f'▫️ Adding Players to the Roster (DM)', value=f'{commandPrefix}timer add @player', inline=False)

    helpEmbedTimerOne.add_field(name=f'▫️ Removing Players from the Roster (DM)', value=f'{commandPrefix}timer remove @player', inline=False)

    helpEmbedTimerOne.add_field(name=f'▫️ Adding Guilds (DM)', value=f'{commandPrefix}timer guild #guild1, #guild2, #guild3', inline=False)

    helpEmbedTimerOne.add_field(name=f'▫️ Cancelling the Timer (DM)', value=f'{commandPrefix}timer cancel', inline=False)

    helpEmbedTimerOne.add_field(name=f'▫️ Starting the Timer (DM)', value=f'{commandPrefix}timer start', inline=False)


# RUNNING TIMER COMMANDS MENU ($help timer2)

# PLAYER COMMANDS

    helpEmbedTimerTwo.title = f"Running Timer Commands\n{commandPrefix}timer, {commandPrefix}t"

    helpEmbedTimerTwo.add_field(name=f'▫️ Adding Yourself (Player)', value=f'{commandPrefix}timer addme "character name" "consumable1, consumable2, [...]"', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Using Items (Player)', value='- item', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Removing Yourself (Player)', value=f'{commandPrefix}timer removeme', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Checking the Timestamp (Player)', value=f'{commandPrefix}timer removeme', inline=False)

# DM COMMANDS

    helpEmbedTimerTwo.add_field(name=f'▫️ Adding Players During a Quest (DM)', value=f'{commandPrefix}timer add @player "character name" "consumable1, consumable2, [...]"', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Removing Players During a Quest (DM)', value=f'{commandPrefix}timer remove @player', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Awarding Reward Items (DM)', value=f'{commandPrefix}timer reward @player "reward item1, reward item2, [...]"', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Revoking Reward Items (DM)', value=f'{commandPrefix}timer undo rewards @player "reward item1, reward item2, [...]"', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Character Death (DM)', value=f'{commandPrefix}timer death @player', inline=False)

    helpEmbedTimerTwo.add_field(name=f'▫️ Stopping the Timer (DM)', value=f'{commandPrefix}timer stop', inline=False)


# POST-QUEST TIMER COMMANDS MENU ($help timer3)

# PLAYER COMMANDS

    helpEmbedTimerThree.title = f"Post-Quest Timer Commands\n{commandPrefix}timer, {commandPrefix}t"

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Out of Guild 2x Rewards (Player)', value=f'{commandPrefix}session optout2xR gameID', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Into of Guild 2x Rewards (Player)', value=f'{commandPrefix}session optin2xR gameID', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Out of Guild 2x Items (Player)', value=f'{commandPrefix}session optout2xI gameID', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Into of Guild 2x Items (Player)', value=f'{commandPrefix}session optin2xI gameID', inline=False)

# DM COMMANDS

    helpEmbedTimerThree.add_field(name=f'▫️ Submitting a Session Log (DM)', value=f'{commandPrefix}session log gameID summary', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Approve Guild 2x Rewards (DM)', value=f'{commandPrefix}session approveRewards gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Deny Guild 2x Rewards (DM)', value=f'{commandPrefix}session denyRewards gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Approve Guild 2x Items (DM)', value=f'{commandPrefix}session approveItems gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Deny Guild 2x Items (DM)', value=f'{commandPrefix}session denyItems gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Approve Recruitment Drive (DM)', value=f'{commandPrefix}approveDrive gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Deny Recruitment Drive (DM)', value=f'{commandPrefix}session denyDrive gameID #guild-channel', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Out of DDMRW (DM)', value=f'{commandPrefix}session ddmrw optout gameID', inline=False)

    helpEmbedTimerThree.add_field(name=f'▫️ Opting Into DDMRW (DM)', value=f'{commandPrefix}session ddmrw optin gameID', inline=False)


# ITEM TABLE COMMANDS MENU ($help itemtable)

############### THIS IS OBSOLETE UNTIL YOU MAKE A NEW SYSTEM.

#    helpEmbedItems.title = 'Item Table Commands'
#    helpEmbedItems.add_field(name=f'▫️ Magic Item Table Lookup\n{commandPrefix}mit [optional name search]', value=f"Look up items from the Magic Item Table, sorted by tier and TP cost. React to the lists to change pages or view items. You can also search by name, for example: {commandPrefix}mit Folding Boat", inline=False)
#    helpEmbedItems.add_field(name=f'▫️ Reward Item Table Lookup\n{commandPrefix}rit [optional name search]', value=f"Look up items from the Reward Item Table, sorted by tier and Minor/Major. React to the lists to change pages or view items. You can also search by name, for example: {commandPrefix}rit Clockwork Dog", inline=False)
#    helpEmbedItems.add_field(name=f'▫️ Random Reward Item\n{commandPrefix}rit random', value=f"Display a random reward item based on the tier and sub-tier you selected.", inline=False)


# TP COMMANDS MENU ($help tp)

    helpEmbedTp.title = 'TP Commands'

    helpEmbedTp.add_field(name=f'▫️ Finding a Magic Item', value=f'{commandPrefix}tp find "character name" "magic item"', inline=False)

    helpEmbedTp.add_field(name=f'▫️ Crafting a Magic Item', value=f'{commandPrefix}tp craft "character name" "magic item"', inline=False)

    helpEmbedTp.add_field(name=f'▫️ Memeing a Magic Item', value=f'{commandPrefix}tp meme "character name" "magic item"', inline=False)

    helpEmbedTp.add_field(name=f'▫️ Discarding an Incomplete Magic Item', value=f'{commandPrefix}tp discard "character name"', inline=False)

    helpEmbedTp.add_field(name=f'▫️ Abandoning Leftover TP', value=f'{commandPrefix}tp abandon "character name" tier', inline=False)

    helpEmbedTp.add_field(name=f'▫️ Upgrading a Vestige of Divergence or Arm of the Betrayer', value=f'{commandPrefix}tp upgrade "character name" "item name"', inline=False)


# SHOP COMMANDS MENU ($help shop)

    helpEmbedShop.title = 'Shop Commands'

    helpEmbedShop.add_field(name=f'▫️ Buying a Shop Item', value=f'{commandPrefix}shop buy "character name" "item" #', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Buying a Miscellaneous Item', value=f'{commandPrefix}shop buy "character name" Miscellaneous #', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Selling a Mundane Item', value=f'{commandPrefix}shop sell "character name" "item" #', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Tossing a Consumable or Mundane Item', value=f'{commandPrefix}shop toss "character name" "item"', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Copying a Spell Scroll', value=f'{commandPrefix}shop copy "character name" "spell name"', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Coating a Weapon in Silver or Adamantine', value=f'{commandPrefix}shop silver "character name" "weapon name" #\n{commandPrefix}shop adamantine', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Downtime Friend Training', value=f'{commandPrefix}downtime training "character name"\n[{commandPrefix}dt training]', inline=False)

    helpEmbedShop.add_field(name=f'▫️ Downtime Noodle Training', value=f'{commandPrefix}downtime noodle "character name"\n[{commandPrefix}dt noodle]', inline=False)


# GUILD COMMANDS MENU ($help guild)

    helpEmbedGuild.title = 'Guild Commands'

    helpEmbedGuild.add_field(name=f'▫️ Viewing a Guild’s Information', value=f'{commandPrefix}guild info #guild-channel', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Joining a Guild', value=f'{commandPrefix}guild join "character name" #guild-channel', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Increasing Your Rank', value=f'{commandPrefix}guild rankup "character name"', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Leaving a Guild', value=f'{commandPrefix}guild leave "character name"', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Creating a Guild', value=f'{commandPrefix}guild create "character name" "guild name" @guildrole #guild-channel', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Funding a Guild', value=f'{commandPrefix}guild fund "character name" #guild-channel GP', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Pinning a Message (Guildmaster only)', value=f'{commandPrefix}guild pin', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Unpinning a Message (Guildmaster only)', value=f'{commandPrefix}guild unpin', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Changing the Channel Topic (Guildmaster only)', value=f'{commandPrefix}guild topic text', inline=False)


# CAMPAIGN COMMANDS MENU ($help campaign)

# PLAYER CAMPAIGN COMMANDS

    helpEmbedCampaign.title = f"Campaign Commands\n{commandPrefix}c"

    helpEmbedCampaign.add_field(name=f'▫️ Viewing a Campaign’s Information', value=f'{commandPrefix}campaign info #campaign-channel', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Signing Up (Player)', value=f'{commandPrefix}campaign timer signup', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Adding Yourself (Player)', value=f'{commandPrefix}campaign timer addme', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Removing Yourself (Player)', value=f'{commandPrefix}campaign timer removeme', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Checking the Timestamp (Player)', value=f'{commandPrefix}campaign timer removeme', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Creating a Character with a Campaign Transfer', value=f'{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]" #campaign-channel XhYm', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Creating a Multiclass Character with a Campaign Transfer', value=f'{commandPrefix}create "character name" starting level "race" "class1 final level / class2 final level / [...]" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]" #campaign-channel XhYm', inline=False)


# DM CAMPAIGN COMMANDS

    helpEmbedCampaign.add_field(name=f'▫️ Creating a Campaign (DM)', value=f'{commandPrefix}campaign create @campaignrole #campaign-channel', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Adding Players to a Campaign Roster (DM)', value=f'{commandPrefix}campaign add @player #campaign-channel', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Removing Players from a Campaign Roster (DM)', value=f'{commandPrefix}campaign remove @player #campaign-channel', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Preparing the Timer (DM)', value=f'{commandPrefix}campaign timer prep "@player1, @player2, [...]" "session name"', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Adding Players During a Session (DM)', value=f'{commandPrefix}campaign timer add @player', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Removing Players During a Session (DM)', value=f'{commandPrefix}campaign timer remove @player', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Cancelling the Timer (DM)', value=f'{commandPrefix}campaign timer cancel', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Starting the Timer (DM)', value=f'{commandPrefix}campaign timer start', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Stopping the Timer (DM)', value=f'{commandPrefix}campaign timer stop', inline=False)

    helpEmbedCampaign.add_field(name=f'▫️ Submitting a Campaign Log (DM)', value=f'{commandPrefix}campaign log gameID summary', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Pinning a Message', value=f'{commandPrefix}campaign pin', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Unpinning a Message', value=f'{commandPrefix}campaign unpin', inline=False)

    helpEmbedGuild.add_field(name=f'▫️ Changing the Channel Topic', value=f'{commandPrefix}campaign topic text', inline=False)




    numPages = len(helpList)

    for i in range(0, len(helpList)):
        helpList[i].set_footer(text= f"Page {i+1} of {numPages}")

    helpMsg = await ctx.channel.send(embed=helpList[page])
    if page == 0:
        for num in range(0,numPages-1): await helpMsg.add_reaction(alphaEmojis[num])

# THIS ERROR MESSAGE WILL NEED TO BE CHANGED TO ACCOMMODATE THE NEW COMMANDS.
    try:
        hReact, hUser = await bot.wait_for("reaction_add", check=helpCheck, timeout=30.0)
    except asyncio.TimeoutError:
        await helpMsg.edit(content=f"Your help menu has timed out! I'll leave this page open for you. Use the first command if you need to cycle through help menu again or use any of the other commands to view a specific help menu:\n```yaml\n{commandPrefix}help gen\n{commandPrefix}help char\n{commandPrefix}help timer1\n{commandPrefix}help timer2\n{commandPrefix}help timer3\n{commandPrefix}help shop\n{commandPrefix}help tp\n{commandPrefix}help guild\n{commandPrefix}help campaign```")
        await helpMsg.clear_reactions()
        await helpMsg.add_reaction('💤')
        return
    else:
        await helpMsg.edit(embed=helpList[alphaEmojis.index(hReact.emoji)+1])
        await helpMsg.clear_reactions()


if __name__ == '__main__':
    for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
        try:
            bot.load_extension(cogs_dir + "." + extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to load extension {extension}.')
            traceback.print_exc()

bot.run(token)
