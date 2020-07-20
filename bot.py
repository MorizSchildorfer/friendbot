import asyncio
import traceback
from discord.ext import commands
from os import listdir
from os.path import isfile, join
from itertools import cycle

from bfunc import *

cogs_dir = "cogs"

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
    # bot.loop.create_task(change_status())

    #secret area channel
    # channel = bot.get_channel(577611798442803205) 
    # await channel.send('Hello I have restarted uwu')
  
bot.remove_command('help')

@bot.event
async def on_command_error(ctx,error):
    # TODO: Fix for char create and guild create
    msg = None
    print(ctx.invoked_with)
    print(error)

    if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
        await ctx.channel.send("There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command. ")
        bot.get_command(ctx.invoked_with).reset_cooldown(ctx)
        return

    elif isinstance(error, commands.CommandOnCooldown):
        if error.retry_after == float('inf'):
            await ctx.channel.send(f"Sorry, the command `{commandPrefix}{ctx.invoked_with}` is already in progress, please complete the command before trying again.")
        else:
            await ctx.channel.send(f"Sorry, the command `{commandPrefix}{ctx.invoked_with}` is on cooldown for you!\nTry the command in the next " + "{:.1f}seconds".format(error.retry_after))
        return

    elif ctx.cog is not None and ctx.cog._get_overridden_method(ctx.cog.cog_command_error) is not None:
        return

    elif isinstance(error, commands.CommandNotFound):
        await ctx.channel.send(f'Sorry, the command `{commandPrefix}{ctx.invoked_with}` is not valid, please try again!')

    else:
        ctx.command.reset_cooldown(ctx)
        await traceBack(ctx,error)

@bot.command()
async def help(ctx, *, pageString=''):
    def helpCheck(r,u):
        sameMessage = False
        if helpMsg.id == r.message.id:
            sameMessage = True
        return (r.emoji in numberEmojis[:numPages]) and u == ctx.author

    helpEmbedMenu = discord.Embed()
    helpEmbedChar = discord.Embed()
    helpEmbedItems = discord.Embed() 
    helpEmbedTimerOne = discord.Embed()
    helpEmbedTimerTwo = discord.Embed()
    helpEmbedShop = discord.Embed()
    helpEmbedTp = discord.Embed()
    helpEmbedGuild = discord.Embed()

    page = 0
    if 'char' in pageString or 'character' in pageString:
        page = 1
    elif 'timer2' in pageString:
        page = 3
    elif 'timer1' in pageString or 'timer' in pageString:
        page = 2
    elif 'itemtable' in pageString:
        page = 4
    elif 'shop' in pageString:
        page = 5
    elif 'tp' in pageString:
        page = 6
    elif 'guild' in pageString:
        page = 7


    helpList = [helpEmbedMenu, helpEmbedChar, helpEmbedTimerOne, helpEmbedTimerTwo, helpEmbedItems, helpEmbedShop, helpEmbedTp, helpEmbedGuild]

    helpEmbedMenu.title = 'Bot Friend Commands - Table of Contents:'
    helpEmbedMenu.description = 'Please react to the group of commands you would like to see and gain more knowledge about.'
    helpEmbedMenu.add_field(name=f"1️⃣ Character Commands  ({commandPrefix}help char)", value="Manages your character and help with character creation and character leveling process.", inline=False)
    helpEmbedMenu.add_field(name=f"2️⃣ Timer (Pre/Post Game) Commands  ({commandPrefix}help timer1)", value="Prepare and manage a game before and after a timer.", inline=False)
    helpEmbedMenu.add_field(name=f"3️⃣ Timer (During Game) Commands ({commandPrefix}help timer2)", value="Manage a timer during a game as a DM or a player.", inline=False)
    helpEmbedMenu.add_field(name=f"4️⃣ Item Table Commands ({commandPrefix}help itemtable)", value="Provide lookup for the Magic Item Table (MIT) or the Reward Item Table (RIT)", inline=False)
    helpEmbedMenu.add_field(name=f"5️⃣ Shop Commands ({commandPrefix}help shop)", value="Purchase or sell items.", inline=False)
    helpEmbedMenu.add_field(name=f"6️⃣ TP Commands ({commandPrefix}help tp)", value="Purchase magic items.", inline=False)
    helpEmbedMenu.add_field(name=f"7️⃣ Guild Commands ({commandPrefix}help guild)", value="Manage your guild as a guildmaster, or join / leave a guild", inline=False)

    helpEmbedChar.title = 'Available Character Commands'
    helpEmbedChar.add_field(name=f'{commandPrefix}create "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "MIT items" "RIT items"', value="Creates your character with the following information.", inline=False)
    helpEmbedChar.add_field(name='MULTICLASS Creation -' + commandPrefix + 'create "character name" level "race" "class1 # / class2 #..." "background" STR DEX CON INT WIS CHA "MIT items" "RIT items"', value="Creates your character just like `$create`. However, please use this format if you would like to multiclass.", inline=False)
    helpEmbedChar.add_field(name=commandPrefix + 'respec "character name" "new character name" level "race" "class" "background" STR DEX CON INT WIS CHA', value="Respecs your character based on the hours your have played. Your character can choose a new name, class, race, background, and stats. Any items gained during hours of play will be lost and TP and gp will be allocated based on CP.", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}levelup "character name" [{commandPrefix}lvl, {commandPrefix}lv {commandPrefix}lvlup]', value="Levels your character to the next level. You may also choose to multiclass your character.", inline=False)
    helpEmbedChar.add_field(name=commandPrefix + 'user', value="Shows your TOTAL games played with all characters, your Noodles, and all of your characters. You must play in at least one game before this command works for you.", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}info "character name" [{commandPrefix}i, {commandPrefix}char]', value="Looks up your character and shows their stats and character information", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}image "character name" url [{commandPrefix}img]', value="Adds an image to the `$info` command using a URL. Please keep images SFW!", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}inventory "character name" [{commandPrefix}inv, {commandPrefix}bag]', value="Shows your character's inventory. Inventories can consist of magic items, mundane items, and consumables.", inline=False)
    helpEmbedChar.add_field(name=commandPrefix + 'retire "character name"', value="Retires your character. Your character will no longer be accessible.", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}attune "character name" "magic item" [{commandPrefix}att]', value="Allows your character to attune to a magic item. Stats bonuses from magic items are applied to your character when attuned to the item.", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}unattune "character name" "magic item" [{commandPrefix}uatt, {commandPrefix}unatt]', value="Allows your character to unattune from a magic item. Stat bonuses from magic items are removed from your character when unattuned from the item.", inline=False)
    helpEmbedChar.add_field(name=f'{commandPrefix}death "character name"', value="If your character has died during your game, this command is available. You can choose to retire or revive your character.", inline=False)
    
    helpEmbedTimerOne.title = f"Available Timer Commands: Before/After a timer.\n(Only available in **Game Rooms** and **Campaigns**) - {commandPrefix}timer (aliases={commandPrefix}t)"
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer prep "@player1, @player2, @player3,..." gamename(*) ', value="Preps a game for @players and #guilds. This allows the DM and players to signup characters to receive rewards. (*) You can choose to name your game (optional).", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer cancel', value="Cancels the current timer prep.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer guild #guild1, #guild2...', value="**DM Only**: Adds a guild to the game. Guild rewards will apply if appropriate.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer signup "charactername" "consumable list"', value="Signs up your character to the one-shot.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer add @player', value="**DM Only**: Adds a player to the roster so they can sign up with their character.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer remove @player', value="**DM Only**: Removes a player from the roster.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + 'timer start', value=f"**Followed by **:`{commandPrefix}timer prep` - Starts a timer to keep track of time and calculate rewards for your game. Only one timer per channel can be active at once and the timer can only be stopped by its owner or a Mod.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + "timer resume", value="Resumes the last running timer that was started and behaves identical to " + commandPrefix + "timer start.", inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + "reward [XhYm] [tier] ", value="This calculates player and DM rewards based on the time and tier you type in. The tier names are **Junior**, **Journey**, **Elite**, and **True**. Example: " + commandPrefix + 'reward 3h30m Elite', inline=False)
    helpEmbedTimerOne.add_field(name=commandPrefix + "session log gameid summary", value="After a game has finished, the DM may edit the log and add a summary to the game in the session logs channel. After using this command to edit the log, the log will be checked and rewards will be given out.", inline=False)

    helpEmbedTimerTwo.title = f"Available Timer Commands: During a timer - {commandPrefix}timer (aliases={commandPrefix}t)"
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer transfer", value="Transfers the timer from the owner to another user. The new owner will be able to stop and resume the timer.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer add @player \"charactername\" \"consumables\"", value="**DM Only**: if a player joins your game late, this command will add @player to the running timer. Their individual rewards will be displayed once the timer has been stopped.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer addme charactername \"consumables\"", value="If you join a game late, this command will add you to the running timer. Their individual rewards will be displayed once the timer has been stopped.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer remove @player", value="**DM Only**: removes the user mentioned from the running timer and displays their individual rewards for the time they played.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer removeme", value="If you leave a game early, this command will remove you from the running timer and display your individual rewards for the time you played.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer death @player", value="Removes a player from the game when a character dies during a game. The player can choose to retire or revive their character outside of the game.", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer reward @player \"rewards\"", value="**DM Only**: Rewards @player item(s) from the RIT. Reward limits depend on your Noodle role.", inline=False)
    helpEmbedTimerTwo.add_field(name="- Consumable", value="Consumes the consumable your character uses and deletes it from their inventory", inline=False)
    helpEmbedTimerTwo.add_field(name=commandPrefix + "timer stop", value="**DM Only**: stops a timer that you have started and shows how much CP, TP, and gp to reward to the players who played. Players who joined the game late will have their rewards displayed separately. The timer can only be stopped by its owner or a Mod.", inline=False)

    helpEmbedItems.title = 'Available Item Table Commands'
    helpEmbedItems.add_field(name=commandPrefix + "mit [optional name search]", value="This shows you items from the Magic Item Table, sorted by tier and TP cost. React to the lists to change pages or view items. You can also search by name, for example: " + commandPrefix + "mit Cloak of Displacement" )
    helpEmbedItems.add_field(name=commandPrefix + "rit [optional name search]", value="This shows you items from the Reward Item Table, sorted by tier and Minor / Major. React to the lists to change pages or view items. You can also search by name, for example: " + commandPrefix + "rit Moon-Touched Sword" )
    helpEmbedItems.add_field(name=commandPrefix + "rit random", value="This randomly awards you a reward item based on which tier and sub-tier you react to." )

    helpEmbedShop.title = 'Available Shop Commands'
    helpEmbedShop.add_field(name=commandPrefix + 'shop buy "character name" "item" #', value="Purchase a specified number of a single mundane item from the shop", inline=False)
    helpEmbedShop.add_field(name=commandPrefix + 'shop sell "character name" "item" #', value="Sell a specified number of a single mundane item to the shop", inline=False)
    helpEmbedShop.add_field(name=commandPrefix + 'shop copy "character name" "spell" #', value="Limited to classes that have access to a spellbook. This copies a spell scroll into your character's spellbook. Some subclasses offer discounts which are applied.", inline=False)
    helpEmbedShop.add_field(name=commandPrefix + 'proficiency "character name"', value="For Noodle roles to purchase proficiencies for your character.", inline=False)

    helpEmbedTp.title = 'Available TP Commands'
    helpEmbedTp.add_field(name=commandPrefix + 'tp buy "character name" "MIT Item" #', value="Put TP towards a magic item or purchase it with gp.", inline=False)
    helpEmbedTp.add_field(name=commandPrefix + 'tp discard "character name"', value="Deletes an incomplete magic item in progress as well as all TP that has been spent on it.", inline=False)
    helpEmbedTp.add_field(name=commandPrefix + 'tp abandon "character name" tier', value="Abandon excess TP in the tier of your choosing.", inline=False)

    helpEmbedGuild.title = 'Available Guild Commands'
    helpEmbedGuild.add_field(name=commandPrefix + 'guild create "character name" "guild name" @role #channel', value="After a role and channel are designated, a guild will be created. It will require funding before it is officially opened.", inline=False)
    helpEmbedGuild.add_field(name=commandPrefix + 'guild fund "character name" gp "guild name"', value="Fund the establishment of the guild. Upon funding the minimum required amount, your character will be added the the guild's roster.", inline=False)
    helpEmbedGuild.add_field(name=commandPrefix + 'guild info "guild name"', value="Displays the guild roster and the amount of reputation inside a guild bank. If your guild has yet to be funded, it will show the amount gp required before the guild will open.", inline=False)
    helpEmbedGuild.add_field(name=commandPrefix + 'guild join "character name" "guild name"', value="Allows your character to join a specified guild.", inline=False)
    helpEmbedGuild.add_field(name=commandPrefix + 'guild leave "character name"', value="Allows your character to leave the guild.", inline=False)
    helpEmbedGuild.add_field(name=commandPrefix + 'guild rep "character name" #', value="Increase your rank in the guild by spending gp. **THIS NEEDS TO BE UPDATED.**", inline=False)


    numPages = len(helpList)

    for i in range(0, len(helpList)):
        helpList[i].set_footer(text= f"Page {i+1} of {numPages}")

    helpMsg = await ctx.channel.send(embed=helpList[page])
    if page == 0:
        for num in range(0,numPages-1): await helpMsg.add_reaction(numberEmojis[num])

    try:
        hReact, hUser = await bot.wait_for("reaction_add", check=helpCheck, timeout=30.0)
    except asyncio.TimeoutError:
        await helpMsg.edit(content=f"Your help menu has timed out! I'll leave this page open for you. If you need to cycle through the list of commands again use `{commandPrefix}help`!")
        await helpMsg.clear_reactions()
        await helpMsg.add_reaction('💤')
        return
    else:
        await helpMsg.edit(embed=helpList[int(hReact.emoji[0])])
        await helpMsg.clear_reactions()


    # while True:
    #     await helpMsg.add_reaction(left) 
    #     await helpMsg.add_reaction(right)
    #     try:
    #         hReact, hUser = await bot.wait_for("reaction_add", check=helpCheck, timeout=30.0)
    #     except asyncio.TimeoutError:
    #         await helpMsg.edit(content=f"Your help menu has timed out! I'll leave this page open for you. If you need to cycle through the list of commands again use `{commandPrefix}help`!")
    #         await helpMsg.clear_reactions()
    #         await helpMsg.add_reaction('💤')
    #         return
    #     else:
    #         if hReact.emoji == left:
    #             page -= 1
    #             if page < 0:
    #                 page = len(helpList) - 1
    #         if hReact.emoji == right:
    #             page += 1
    #             if page > len(helpList) - 1:
    #                 page = 0

    #         await helpMsg.edit(embed=helpList[page]) 
    #         await helpMsg.clear_reactions()


if __name__ == '__main__':
    for extension in [f.replace('.py', '') for f in listdir(cogs_dir) if isfile(join(cogs_dir, f))]:
        try:
            bot.load_extension(cogs_dir + "." + extension)
        except (discord.ClientException, ModuleNotFoundError):
            print(f'Failed to load extension {extension}.')
            traceback.print_exc()

bot.run(token)
