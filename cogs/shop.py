import discord
import asyncio
import requests
import re
from discord.utils import get        
from discord.ext import commands
from bfunc import db, commandPrefix,  alphaEmojis, traceBack, settingsRecord
from cogs.util import callAPI, noodle_roles, paginate, disambiguate, findNoodleDataFromRoles, \
    add_to_inventory, check_for_char_with_end, find_matching, sum_sources, InteractionCore, reaction_response_control, remove_from_inventory, add_to_dictionary
from math import floor

def ordinal(n): 
    return "%d%s" % (n,"tsnrhtdd"[(floor(n/10)%10!=1)*(n%10<4)*n%10::4])
    
training_options = ["Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Skill/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Skill/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Skill/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Skill/Language/Tool",
"Weapon/Language/Tool",
"Weapon/Skill/Language/Tool"]

def is_log_channel():
    async def predicate(ctx):
        return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
    return commands.check(predicate)


class Shop(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.group(case_insensitive=True)
    @is_log_channel()
    async def shop(self, ctx):
        pass
        
    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command **`{commandPrefix}{ctx.invoked_with}`** requires an additional keyword to the command or is invalid, please try again!')
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'char':
                msg = "You're missing your character name in the command.\n"
            if error.param.name == 'searchQuery':
                msg = "You're missing your item name in the command.\n"
            elif error.param.name == "buyItem":
                msg = "You're missing the item you want to buy/sell in the command.\n"
            elif error.param.name == "spellName":
                msg = "You're missing the spell you want to copy in the command.\n"
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.BadArgument):
            print(error)
            # convert string to int failed
            msg = "The amount you want to buy or sell must be a number.\n"
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             msg = "Your \" placement seems to be messed up.\n"
        if msg:
            if ctx.command.name == "buy":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}shop buy \"character name\" \"item\" #```\n"
            elif ctx.command.name == "sell":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}shop sell \"character name\" \"item\" #```\n"
            elif ctx.command.name == "copy":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}shop copy \"character name\" \"spell name\"```\n"
            elif ctx.command.name == "proficiency":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}downtime training \"character name\"```\n"

            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)


    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @shop.command()
    async def buy(self, ctx, char, buyItem: str, amount=1.0):
        channel = ctx.channel
        author = ctx.author
        if "misc" != buyItem.lower() and "miscellaneous" != buyItem.lower():
            amount = int(amount)
        command_name = ctx.command.name
        char_dict, embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            return None
        #If player is trying to buy spell scroll, search for spell scroll in DB, and find level it can be bought at
        if "spell scroll" in buyItem.lower():
            if "spell scroll" == buyItem.lower().strip():
                await channel.send(f"""Please be more specific with the type of spell scroll which you're purchasing. Use the following format:\n```yaml\n{commandPrefix}shop buy "character name" "Spell Scroll (spell name)"```""")
                ctx.command.reset_cooldown(ctx)
                return None

            spellItem = buyItem.lower().replace("spell scroll", "").replace('(', '').replace(')', '')
            spell_record, core = await callAPI(core, 'spells', spellItem)

            if not spell_record:
                await core.send(f'**{buyItem}** doesn\'t exist or is an unbuyable item! Check to see if it is a valid item and check your spelling.')
                ctx.command.reset_cooldown(ctx)
                return None
            
            spell_level = spell_record['Level']
            if spell_level > 5:
                await core.send(f"You cannot purchase a spell scroll of **{spell_record['Name']}**. Spell scrolls higher than 5th level cannot be purchased.")
                ctx.command.reset_cooldown(ctx)
                return None
            item_record, core = await callAPI(core, 'shop', f'spell scroll (level {spell_level})')
            item_record['Name'] = f"Spell Scroll ({spell_record['Name']})"

        elif "misc" == buyItem.lower() or "miscellaneous" == buyItem.lower():
            item_record= {"GP" : amount, "Misc" : True, "Name": "Miscellaneous"}
            amount = 1
        # If it's anything else, see if it exists
        else:
            item_record, core = await callAPI(core, 'shop',buyItem)
        amount = int(amount)
        # Check if there's enough GP to buy
        if not item_record:
            await core.send(f'**{buyItem}** doesn\'t exist or is an unbuyable item! Check to see if it is a valid item and check your spelling.')
            ctx.command.reset_cooldown(ctx)
            return None
        gpNeeded = (item_record['GP'] * amount)

        if "Pack" in item_record:
            amount *= item_record['Pack']

        if float(char_dict['GP']) < gpNeeded:
            await channel.send(f"You do not have enough GP to purchase {amount}x **{item_record['Name']}**!")
            ctx.command.reset_cooldown(ctx)
            return None

        embed.title = f"Shop (Buy): {char_dict['Name']}"

        pack_contents = ""
        if "Unpack" in item_record:
            pack_contents = f"**Contents of {item_record['Name']}**\n"
            for pk, pv in list(item_record["Unpack"].items()):
                if type(pv) == dict:
                    alphaIndex = 0
                    unpackChoiceString = ""
                    unpackDict = []
                    for pvk, pvv in pv.items():
                        unpackDict.append(pvk)
                        unpackChoiceString += f"{alphaEmojis[alphaIndex]}: {pvk}\n"
                        alphaIndex += 1

                    embed.add_field(name=f"{item_record['Name']} lets you choose one {pk}.", value=unpackChoiceString, inline=False)
                    await core.send()
                    await core.message.add_reaction('❌')
                    try:
                        tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, alphaEmojis[:alphaIndex]), timeout=60)
                    except asyncio.TimeoutError:
                        await core.delete()
                        await channel.send(f'Shop cancelled. Try again using the same command:\n```yaml\n{commandPrefix}shop buy \"character name\" \"item\" #```')
                        self.bot.get_command('buy').reset_cooldown(ctx)
                        return None
                    else:
                        await core.message.clear_reactions()
                        if tReaction.emoji == '❌':
                            await core.send(f"Shop cancelled. Try again using the same command:\n```yaml\n{commandPrefix}shop buy \"character name\" \"item\" #```")
                            await core.message.clear_reactions()
                            self.bot.get_command('buy').reset_cooldown(ctx)

                    unpackChoice = unpackDict[alphaEmojis.index(tReaction.emoji)]
                    del item_record["Unpack"][pk]
                    item_record['Unpack'][unpackChoice] = pvv

                    await core.message.clear_reactions()
                    embed.clear_fields()
                    pack_contents += f"{unpackChoice} x{pvv}\n"
                else:
                    pack_contents += f"{pk} x{pv}\n"
            pack_contents += "\n"
        new_gp = char_dict['GP']-gpNeeded
        embed.description = f"Are you sure you want to purchase {amount}x **{item_record['Name']}** for **{gpNeeded} GP**?\n\n{pack_contents}Current GP: {char_dict['GP']} GP\nNew GP: {new_gp} GP\n\n✅: Yes\n\n❌: Cancel"

        await core.send(embed=embed)
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']), timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'Shop cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"Shop cancelled. Try again using the same command!")
                await core.message.clear_reactions()
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                inventory_increase = {}
                if "Misc" in item_record:
                    pass
                elif "Unpack" in item_record:
                    for pk, pv in item_record["Unpack"].items():
                        add_to_inventory(inventory_increase, pk, pv, "BUY")
                else:
                    add_to_inventory(inventory_increase, item_record['Name'], amount, "BUY")
                kind = "Inventory"
                if "Consumable" in item_record:
                    kind = "Consumables"
                        
                increase = {"GP": -gpNeeded}
                for key, value in inventory_increase.items():
                    for source, amount in value.items():
                        print(kind, key, source, amount)
                        increase[f"{kind}.{key}.{source}"]=amount
                try:
                    db.players.update_one({'_id': char_dict['_id']}, {"$inc": increase})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await core.send("Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    embed.description = f"{amount}x **{item_record['Name']}** purchased for **{gpNeeded} GP**!\n\n{pack_contents}Current GP: {new_gp} GP\n"
                    await core.send()
                    ctx.command.reset_cooldown(ctx)

    """
    Function extracted from sell in order to use it in adamantine and silver
    Checks the player inventory of mundane items to check for the query buyItem
    """
    async def checkInventory(self, core, buyItem, char_dict):
        ctx = core.context
        channel = ctx.channel
        author = ctx.author
        level_up_embed = core.embed
        # create a setup for disambiguation
        buyList = []
        buyString=""
        numI = 0
        if char_dict['Inventory'] == "None":
            await core.send(f'You do not have any valid items in your inventory. Please try again with an item.')
            ctx.command.reset_cooldown(ctx)
            return False

        # Iterate through character's inventory to see which items would match the query
        else:
            for k in char_dict['Inventory'].keys():
                if buyItem.lower() in k.lower():
                    # update the disambiguation trackers
                    buyList.append(k)
                    buyString += f"{alphaEmojis[numI]} {k} \n"
                    numI += 1


        # If there are multiple matches user can pick the correct one
        if len(buyList) > 1:
            # setup messages for the user interaction
            # on a failed interaction, reset the cooldown on the called command
            level_up_embed.add_field(name=f"There seems to be multiple results for **{buyItem}**! Please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.", value=buyString, inline=False)
            await core.send()
            await core.message.add_reaction('❌')

            try:
                tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, alphaEmojis[:numI]), timeout=60)
            except asyncio.TimeoutError:
                await core.delete()
                await channel.send('Timed out! Try again using the command!')
                ctx.command.reset_cooldown(ctx)
                return False
            else:
                if tReaction.emoji == '❌':
                    await core.send(f"Command cancelled. Try again using the command!")
                    await core.message.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return False
            core.embed.clear_fields()
            await core.message.clear_reactions()
            buyItem = buyList[alphaEmojis.index(tReaction.emoji)]
        # if there only was one item, select it
        elif len(buyList) == 1:
            buyItem = buyList[0]
        else:
            # inform the user if the query couldnt be found
            await core.send(f'**{buyItem}** could not be found in {char_dict["Name"]}\'s inventory! Check to see if it is a valid item and check your spelling.')
            ctx.command.reset_cooldown(ctx)
            return False
        return buyItem
            
    """
    This command is used to coat a mundane weapon in silver
    charName -> which character of the user to coat for
    buyItem -> query string of which item to coat
    amount -> how many instances to coat
    """
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @shop.command()
    async def silver(self, ctx, char, buyItem: str, amount:int =1):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        # if the character exists, check for the item in the inventory and disambiguate
        buyItem = await self.checkInventory(core, buyItem, char_dict)
        # if the item couldnt be found, end
        if not buyItem:
            return None
        # check for the additional adamantine modifer and remove it to just get the DB entry name
        searchItem = buyItem
        # if the item was already silvered, remove it
        if searchItem.startswith("Silvered "):
            await core.send(f'**{buyItem}** is already silvered!')
            ctx.command.reset_cooldown(ctx)
            return None
        elif searchItem.startswith("Adamantine "):
            searchItem = searchItem.replace("Adamantine ", "", 1)
        # since the order is always Silvered Adamantine Weapon, we can use startswith for these checks

        # search for the item in the DB to find which type it is
        bRecord, core = await callAPI(core, 'shop', searchItem, exact=True)

        if bRecord:
            # if it is not a weapon, cancel
            if not("Type" in bRecord and bRecord["Type"].startswith("Weapon")):
                await channel.send(f"**{bRecord['Name']} is not a weapon**!")
                ctx.command.reset_cooldown(ctx)
                return None
            # if they do not have enough instances of the item, cancel
            if sum_sources(char_dict['Inventory'][f"{buyItem}"]) < amount:
                await channel.send(f"You do not have enough **{buyItem}s** to coat!")
                ctx.command.reset_cooldown(ctx)
                return None
            # create the resulting item name
            fullItemName = "Silvered " + buyItem
            # call the function that handles the purchase calculations
            await self.coat(core, 100, "silver", buyItem, amount, fullItemName, char_dict, bRecord)

        # if the item couldnt be found in the DB, cancel
        else:
            await core.send(f'**{buyItem}** doesn\'t exist or is an unbuyable item! Check to see if it is a valid item and check your spelling.')
            ctx.command.reset_cooldown(ctx)
        return None

    """
    This command is used to coat a mundane weapon in adamantine
    charName -> which character of the user to coat for
    buyItem -> query string of which item to coat
    amount -> how many instances to coat
    """
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @shop.command()
    async def adamantine(self, ctx, char, buyItem, amount=1):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        # if the character exists, check for the item in the inventory and disambiguate
        buyItem = await self.checkInventory(core, buyItem, char_dict)
        # if the item couldnt be found, end
        if not buyItem:
            return None

        # check for the additional Silvered modifer and remove it to just get the DB entry name
        searchItem = buyItem
        silvered = False
        # if the item was already adamantine, cancel

        if "Adamantine " in searchItem:
            await core.send(f'**{buyItem}** is already adamantine!')
            ctx.command.reset_cooldown(ctx)
            return None
        # extract the DB name by removing the silvered property
        elif searchItem.startswith("Silvered "):
            searchItem = searchItem.replace("Silvered ", "", 1)
            silvered = True

        # search for the item in the DB
        bRecord, core = await callAPI(core, 'shop', searchItem, exact= True)

        if bRecord:
            # if it is not a weapon, canel
            if not("Type" in bRecord and bRecord["Type"].startswith("Weapon")):
                await channel.send(f"**{bRecord['Name']} is not a weapon**!")
                ctx.command.reset_cooldown(ctx)
                return None

            if sum_sources(char_dict['Inventory'][f"{buyItem}"]) < amount:
                await channel.send(f"You do not have enough **{buyItem}s** to coat!")
                ctx.command.reset_cooldown(ctx)
                return None

            # create the final name of the item
            # in order to properly maintain the naming convention we build it from the base up
            fullItemName = "Adamantine " + bRecord['Name']
            if silvered:
                fullItemName = "Silvered " + fullItemName
            # call the function handling the purchase and DB updateing
            await self.coat(core, 500, "adamantine", buyItem, amount, fullItemName, char_dict, bRecord)
        else:
            await core.send(f'**{buyItem}** doesn\'t exist or is an unbuyable item! Check to see if it is a valid item and check your spelling.')
            ctx.command.reset_cooldown(ctx)
        return None

    # TODO adjust this code to work
    """
    This function handles the DB entry manipulation of the coating process and is called by silver and adamantine
    cost -> cost per item being coated
    coatType -> string name of the process
    amount -> how many items are being coated
    fullItemName -> the final name of the item, used to create the dictionary entry
    char_dict -> DB entry of the character
    bRecord -> DB entry of the base item being covered
    """
    async def coat(self, core, cost, coatType, targetItem, amount, fullItemName, char_dict, bRecord):
        ctx = core.context
        channel = ctx.channel
        author = ctx.author
        # total cost of the process
        gpNeeded = (cost * amount)
        # if they do not have enough gold, cancel
        if float(char_dict['GP']) < gpNeeded:
            await core.send(f"You do not have enough gp to {coatType} {amount}x **{bRecord['Name']}**!")
            ctx.command.reset_cooldown(ctx)
            return None
        new_gp = char_dict['GP'] -gpNeeded
        level_up_embed = core.embed
        level_up_embed.title = f"Shop (Buy): {char_dict['Name']}"
        level_up_embed.description = f"Are you sure you want to coat {amount}x **{targetItem}** in {coatType} for **{gpNeeded} GP**?\n\nCurrent GP: {char_dict['GP']} GP\nNew GP: {new_gp} GP\n\n✅: Yes\n\n❌: Cancel"
        # get confirmation of the purchase from the user
        await core.send()
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'Shop cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"Shop cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                # deduct the amount from the item entry being coated
                reductions = remove_from_inventory(core, char_dict['Inventory'], targetItem, amount)
                increases = {"GP": -gpNeeded}
                for source, minus in reductions.items():
                    add_to_dictionary(increases, f"Inventory.{targetItem}.{source}", minus)
                add_to_dictionary(increases, f"Inventory.{fullItemName}.BUY", amount)
                
                try:
                    # update the character entry with the new inventory and gold
                    db.players.update_one({'_id': char_dict['_id']}, {"$inc":increases})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    level_up_embed.description = f"{amount}x **{targetItem}** have been coated in {coatType} for **{gpNeeded} GP**! \n\nCurrent GP: {new_gp} GP\n"
                    await core.send()
                    ctx.command.reset_cooldown(ctx)

    @shop.command()
    async def toss(self, ctx, char, searchQuery, count=1):
        channel = ctx.channel
        author = ctx.author
        # extract the name of the consumable and transform it into a standardized format
        searchItem = searchQuery.lower().replace(' ', '')
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        
        item_type = None
        item_list = char_dict["Consumables"].keys()
        item_key = None
        for j in item_list:
            # if found than we can mark it as such
            if searchItem == j.lower().replace(" ", ""):
                item_key = j
                item_type = "Consumables"
                break
        if not item_key:
            for key, inv in char_dict["Inventory"].items():
                # if found than we can mark it as such
                if searchItem == key.lower().replace(' ', '') and sum_sources(inv) > 0:
                    item_key = key
                    item_type = "Inventory"
                    break
        if not item_key:
            item_list = char_dict["Magic Items"].keys()
            for key in item_list:
                # if found than we can mark it as such
                if searchItem == key.lower().replace(' ', ''):
                    item_key = key
                    item_type = "Magic Items"
                    break  
                    
        if item_type == "Magic Items":
            mRecord = await callAPI(core,'rit', item_key)
            if not mRecord:
                await core.send(f"**{searchQuery}** is not a tossable item.")
                return None
        # inform the user if we couldnt find the item
        if not item_key:
            await core.send(f"I could not find the item **{searchQuery}** in your inventory in order to remove it.")
            return None
        total_amount = sum_sources(char_dict[item_type][item_key])
        if total_amount < count:
            await core.send(f"You only have **{total_amount}** {item_key} in your inventory.")
            return None
        # remove the entry from the list of consumables of the character
        to_set = {}
        reductions = remove_from_inventory(core, char_dict[item_type], item_key, count)
        increase = {f"{item_type}.{item_key}.{source}": value for source, value in reductions.items()}
        if (item_type == "Magic Items" and
            "Attuned" in char_dict[item_type][item_key] and
            char_dict[item_type][item_key]["Attuned"] and sum_sources(total_amount == count)):
            to_set[f"{item_type}.{item_key}.Attuned"] = False

        level_up_embed.title = f"Shop (Toss): {char_dict['Name']}"
        level_up_embed.description = f"Are you sure you want to toss **{item_key}**?\n\n✅: Yes\n\n❌: Cancel"

        await core.send()
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'Shop cancelled. Try again using the command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"Shop cancelled. Try again using the command!")
                await core.message.clear_reactions()
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                try:
                    db.players.update_one({'_id': char_dict['_id']}, {"$set": to_set, "$inc": increase})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    level_up_embed.description = f"The item **{item_key}** has been removed from your inventory."
                    await core.send()
                    ctx.command.reset_cooldown(ctx)
    
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @shop.command()
    async def sell(self, ctx, char, item_name, amount=1):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        # Check if the item being sold is a spell scroll, if it is... reject it
        if "spell scroll" in item_name.lower():
            await channel.send(f'You cannot sell spell scrolls to the shop. Please try again with a different item.')
            ctx.command.reset_cooldown(ctx)
            return None

        item_name = await self.checkInventory(core, item_name, char_dict)
        if not item_name:
            return None
        item_record, core = await callAPI(core,'shop', item_name)
        if not item_record:
            await channel.send(f'**{item_name}** doesn\'t exist or is an unsellable magic item! Check to see if it is a valid item and check your spelling.')
            ctx.command.reset_cooldown(ctx)
            return None
        # See if item is a magic item (they are unsellable)
        if 'Magic Item' in item_record:
            await core.send(f"**{item_record['Name']}** is a magic item and is not sellable. Please try again with a different item.")
            ctx.command.reset_cooldown(ctx)
            return None

        if 'Consumable' in item_record:
            await core.send(f"**{item_record['Name']}** is a consumable and is not sellable. Please try again with a different item.")
            ctx.command.reset_cooldown(ctx)
            return None
        reductions = remove_from_inventory(core, char_dict['Inventory'], item_record['Name'], amount)
        if core.hasError():
            await core.send("\n".join(core.errors))

        if "Pack" in item_record:
            item_record['GP'] /= item_record['Pack']

        gp_refund = round((item_record['GP'] / 2) * amount, 2)
        new_gp = char_dict['GP'] - gp_refund
        level_up_embed.title = f"Shop (Sell): {char_dict['Name']}"
        level_up_embed.description = f"Are you sure you want to sell {amount}x **{item_record['Name']}** for **{gp_refund} GP**?\nCurrent GP: {char_dict['GP']} GP\nNew GP: {new_gp} GP\n\n✅: Yes\n\n❌: Cancel"
        await core.send()
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.delete()
            await channel.send(f'Shop cancelled. Try again using the command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.message.edit(embed=None, content=f"Shop cancelled. Try again using the command!")
                await core.message.clear_reactions()
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                reductions = {f'Inventory.{item_record["Inventory"]}.{source}': value for source, value in reductions.items()}
                reductions["GP"] : gp_refund
                inc = {"$inc": reductions}
                try:
                    db.players.update_one({'_id': char_dict['_id']}, inc)
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    level_up_embed.description = f"{amount}x **{item_record['Name']}** sold for **{gp_refund} GP**! \n\nCurrent GP: {new_gp} GP\n"
                    await core.send()
                    ctx.command.reset_cooldown(ctx)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @shop.command()
    async def copy(self, ctx , char, spellName):
        channel = ctx.channel
        author = ctx.author
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        ritual_caster_feat = find_matching(char_dict['Feats'], lambda x: "Ritual Caster" in x)
        ritual_caster_class = None
        if ritual_caster_feat:
            ritual_caster_class = ritual_caster_feat.split("(")[1].split(")")[0]
        #TODO: check for warlock pact of tome and if you want (Book of Ancient Secrets invocation) too
        classes = char_dict['Class']
        if 'Wizard' not in classes and 'Ritual Caster' not in char_dict['Feats']:
            await channel.send(f"You must be a Wizard or have the Ritual Caster feat in order to copy spells into a spellbook!")
            ctx.command.reset_cooldown(ctx)
            return None

        consumes = char_dict['Consumables']

        spellItem = spellName.lower().replace("spell scroll", "").replace('(', '').replace(')', '')
        spell_record, core = await callAPI(core,'spells',spellItem)

        if not spell_record:
            await channel.send(f'**{spellName}** doesn\'t exist! Check to see if it is a valid spell and check your spelling.')
            ctx.command.reset_cooldown(ctx)
            return None
        if spell_record["Level"] == 0:
            await channel.send(f"**{spell_record['Name']}** is a cantrip and cannot be copied into your spellbook!")
            ctx.command.reset_cooldown(ctx)
            return None

        book_choice = 0
        gp_needed = 0
        level_up_embed.title = f"{char_dict['Name']} is copying spell: {spell_record['Name']}"
        if ritual_caster_class and 'Wizard' not in classes:
            book_choice = "Ritual Book"
        elif not ritual_caster_class and 'Wizard' in classes:
            book_choice = "Spellbook"
        else:
            level_up_embed.description = f"Which book would you like to copy into?\n\n{alphaEmojis[0]}: Ritual Book\n{alphaEmojis[1]}: Spell Book"
            await core.send(embed=level_up_embed)
            await core.message.add_reaction(alphaEmojis[0])
            await core.message.add_reaction(alphaEmojis[1])
            await core.message.add_reaction('❌')
            try:
                tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,
                                                                                       alphaEmojis[:2]) , timeout=60)
            except asyncio.TimeoutError:
                await core.send(f'Shop cancelled. Try again using the same command!')
                ctx.command.reset_cooldown(ctx)
                return None
            else:
                await core.message.clear_reactions()
                if tReaction.emoji == '❌':
                    await core.send(f"Shop cancelled. Try again using the same command!")
                    ctx.command.reset_cooldown(ctx)
                    return None
                elif tReaction.emoji == alphaEmojis[1]:
                    book_choice = "Spellbook"
                elif tReaction.emoji == alphaEmojis[0]:
                    book_choice = "Ritual Book"
        if book_choice in char_dict:
            if spell_record['Name'] in [c['Name'] for c in char_dict[book_choice]]:
                await channel.send(f"***{char_dict['Name']}*** already has the **{spell_record['Name']}** spell copied in their {book_choice}!")
                ctx.command.reset_cooldown(ctx)
                return  None

        if book_choice == "Ritual Book":
            if spell_record['Name'] in [c['Name'] for c in char_dict['Ritual Book']]:
                await core.send(f"***{char_dict['Name']}*** already has the **{spell_record['Name']}** spell copied in their ritual book!")
                ctx.command.reset_cooldown(ctx)
                return None
            if ritual_caster_class not in spell_record['Classes']:
                await core.send(f"***{spell_record['Name']}*** is not a {ritual_caster_class} spell that can be copied into your ritual book.")
                ctx.command.reset_cooldown(ctx)
                return None
            if "Ritual" not in spell_record:
                await core.send(f"***{spell_record['Name']}*** is not a ritual spell and cannot be copied into your ritual book.")
                ctx.command.reset_cooldown(ctx)
                return None
            if char_dict['Level'] < (int(spell_record['Level']) * 2 - 1):
                await core.send(f"***{char_dict['Name']}*** is not a high enough level to copy a {ordinal(spell_record['Level'])}-level spell and cannot copy ***{spell_record['Name']}*** into your ritual book.")
                ctx.command.reset_cooldown(ctx)
                return None
        if book_choice == "Spellbook":
            if 'Wizard' not in spell_record['Classes']:
                deny_string = ""
                if "Race" in spell_record:   # Determines if the spell is a Mark of X spell
                    if "Mark" not in char_dict['Race']:   # Determines if the race is a Mark of X race
                        deny_string = f"***{char_dict['Race']}*** is not a valid race for the spell ***{spell_record['Name']}*** to be copied into your spellbook."
                    elif char_dict['Race'] not in spell_record['Race']:    # Determines if the Mark of X race is a valid Mark of X race for the spell
                        deny_string = f"***{char_dict['Race']}*** is not a Mark valid race for the spell ***{spell_record['Name']}*** to be copied into your spellbook."
                else:
                    deny_string = f"***{spell_record['Name']}*** is not a Wizard spell that can be copied into your spellbook."
                if deny_string:
                    await core.send(deny_string)
                    ctx.command.reset_cooldown(ctx)
                    return None
            wizard_subclass = classes['Wizard']['Subclass']
            if "Chronurgy" in spell_record['Classes'] and "Graviturgy" in spell_record['Classes']:
                if not wizard_subclass or ("Chronurgy" in wizard_subclass and "Graviturgy" not in wizard_subclass):
                    await channel.send(f"***{spell_record['Name']}*** is restricted to the **Chronurgy** and **Graviturgy** schools and cannot be copied into your spellbook.")
                    ctx.command.reset_cooldown(ctx)
                    return None
            elif "Chronurgy" in spell_record['Classes']:
                if not wizard_subclass or "Chronurgy" not in classes:
                    await channel.send(f"***{spell_record['Name']}*** is restricted to the **Chronurgy** school and cannot be copied into your spellbook.")
                    ctx.command.reset_cooldown(ctx)
                    return None
            elif "Graviturgy" in spell_record['Classes']:
                if not wizard_subclass or "Graviturgy" not in classes:
                    await channel.send(f"***{spell_record['Name']}*** is restricted to the **Graviturgy** school and cannot be copied into your spellbook.")
                    ctx.command.reset_cooldown(ctx)
                    return None

        spellCopied = None
        spellScrollAmount = 0
        for key, value in consumes.items():
            if spell_record['Name'] in key and 'Spell Scroll' in key:
                spellCopied = key
                spellScrollAmount = sum_sources(value)
                break
        increases = {}
        to_set = {}
        scrollChoice = "Scroll"
        if "Free Spells" in char_dict:
            if char_dict["Free Spells"] != [0] * 9 and book_choice == "Spellbook":
                scrollChoice = "Free Spell"

            if char_dict["Free Spells"] != [0] * 9 and spellCopied and book_choice == "Spellbook":
                level_up_embed.description = f"Would you like to copy this spell using a free spell or a spell scroll?\n\n{alphaEmojis[0]}: Free Spell\n{alphaEmojis[1]}: Consume Spell Scroll"
                await core.send(embed=level_up_embed)

                await core.message.add_reaction(alphaEmojis[0])
                await core.message.add_reaction(alphaEmojis[1])
                await core.message.add_reaction('❌')

                try:
                    tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,
                                                                                       alphaEmojis[:2]) , timeout=60)
                except asyncio.TimeoutError:
                    await core.send(f'Shop cancelled. Try again using the same command!')
                    ctx.command.reset_cooldown(ctx)
                    return None
                else:
                    await core.message.clear_reactions()
                    if tReaction.emoji == '❌':
                        await core.send(f"Shop cancelled. Try again using the same command!")
                        ctx.command.reset_cooldown(ctx)
                        return None
                    elif tReaction.emoji == alphaEmojis[0]:
                        scrollChoice = "Free Spell"
                    elif tReaction.emoji == alphaEmojis[1]:
                        scrollChoice = "Scroll"
        fsIndex = 0
        if ('Free Spells' in char_dict and book_choice == "Spellbook") and scrollChoice == "Free Spell":
            requiredSpellLevel = (int(spell_record['Level'])* 2 - 1)
            fsValid = False
            for f in range(spell_record['Level'] - 1, 9):
                if char_dict['Free Spells'][f] > 0:
                    char_dict['Free Spells'][f] -= 1
                    to_set["Free Spells"] = char_dict['Free Spells']
                    fsValid = True
                    fsIndex = f + 1
                    break
            if char_dict["Level"] < requiredSpellLevel or fsValid is False:
                await core.send(f"**{spell_record['Name']}** is a {ordinal(spell_record['Level'])} level spell that cannot be copied into ***{char_dict['Name']}***'s spellbook! They must be level {requiredSpellLevel} or higher or you have no more free spells to copy this spell.")
                ctx.command.reset_cooldown(ctx)
                return None
        elif scrollChoice == "Scroll":
            spellScrollAmount -= 1
            gp_needed = spell_record['Level'] * 50
            if char_dict['Level'] >= 2 and spell_record['School'] in classes:
                gp_needed = gp_needed / 2
            if gp_needed > char_dict['GP']:
                await core.send(f"***{char_dict['Name']}*** does not have enough GP to copy the **{spell_record['Name']}** spell into their {book_choice}.")
                ctx.command.reset_cooldown(ctx)
                return None
            if not spellCopied:
                await core.send(f"***{char_dict['Name']}*** does not have a spell scroll of **{spell_record['Name']}** to copy into their {book_choice}!")
                ctx.command.reset_cooldown(ctx)
                return None
            increases = {f"Consumables.{spellCopied}.{source}" : value for source, value in remove_from_inventory(core, consumes, spellCopied)}
            increases["GP"] = -gp_needed
        if book_choice not in char_dict:
            char_dict[book_choice] = [{'Name':spell_record['Name'], 'School':spell_record['School']}]
        else:
            char_dict[book_choice].append({'Name':spell_record['Name'], 'School':spell_record['School']})
        to_set[book_choice] = char_dict[book_choice]
        level_up_embed.title = f"Copying a Spell: {char_dict['Name']}"
        new_gp = char_dict['GP']-gp_needed
        if fsIndex != 0:
            level_up_embed.description = f"""Are you sure you want to copy the **{spell_record['Name']}** spell? This will consume a {ordinal(spell_record['Level'])}-level free spell.\n\n✅: Yes\n\n❌: Cancel"""
        else:
            level_up_embed.description = f"Are you sure you want to copy the **{spell_record['Name']}** spell for **{gp_needed} GP**?\nCurrent GP: {char_dict['GP']} GP\nNew GP: {char_dict['GP'] - gp_needed} GP\n\n✅: Yes\n\n❌: Cancel"
        await core.send()
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'Shop cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"Shop cancelled. Try again using the same command!")
                await core.message.clear_reactions()
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                try:
                    db.players.update_one({'_id': char_dict['_id']}, {"$set": to_set, "$inc": increases})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    level_up_embed.title = f"Shop (Copy): {char_dict['Name']}"
                    if spellScrollAmount == 0:
                        level_up_embed.description = f"You have copied the **{spell_record['Name']}** spell ({ordinal(spell_record['Level'])} level) into your {book_choice} for {gp_needed} GP!\nYou copied your last spell scroll of **{spell_record['Name']}** and it has been removed from your inventory. \n\nCurrent GP: {new_gp} GP\n"
                    else:
                        level_up_embed.description = f"You have copied the **{spell_record['Name']}** spell ({ordinal(spell_record['Level'])} level) into your {book_choice} for {gp_needed} GP!\nAfter copying the spell scroll of **{spell_record['Name']}** and you have {spellScrollAmount} spell scroll(s) of **{spell_record['Name']}** left. \n\nCurrent GP: {new_gp} GP\n"
                    if 'Free Spells' in char_dict:
                        fsString = ""
                        fsIndex = 0
                        for el in char_dict['Free Spells']:
                            if el > 0:
                                fsString += f"{ordinal(fsIndex+1)} Level : {el} free spells\n"
                            fsIndex += 1
                        if fsString:
                            level_up_embed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)
                    await core.send()
                    ctx.command.reset_cooldown(ctx)

    @commands.group(aliases=['dt'], case_insensitive=True)
    async def downtime(self, ctx):
        pass
        
    """"
    Extracted purchase menu for simplifying the code
      purchaseOption -> Proficiency or NoodleTraining, to determine which stat to update
      specificationText -> The text to indicate the source of the purchase to the user
      skillFloor -> The point at which the skill option becomes available. After this point there is linear scaling using skillRate
      skillRate -> Because the two versions have different rates at which skill proficiencies can be 
                    gained this is passed through instead of creating an if-else
      gpNeeded -> how much gold the purchase will cost
      char_dict -> the database information of the character being purchased for
      channel -> the channel the interaction is being made in
      author -> who is doing the purchase
    """
    async def purchaseProficiency(self, core: InteractionCore, purchaseOption, trainingType, specificationText, purchasePossibilities, gpNeeded, char_dict):
        if gpNeeded > char_dict['GP']:
            await core.send(f"***{char_dict['Name']}*** does not have enough GP to learn a language or gain proficiency in a tool in this way.")
            return None
        #calculate gp after purchase
        new_gp = char_dict['GP'] - gpNeeded
        
        #increase the purchase level of the specific option
        char_dict[purchaseOption] += 1
        level_up_embed = core.embed
        #update embed text to ask for confirmation
        level_up_embed.title = f"Downtime {trainingType} Training: {char_dict['Name']}"
        level_up_embed.description = f"Are you sure you want to learn your **{specificationText}** {purchasePossibilities} for {gpNeeded} GP?\nCurrent GP: {char_dict['GP']} GP\nNew GP: {new_gp} GP\n\n✅: Yes\n\n❌: Cancel"
        await core.send()

        #set up menu interaction
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, core.context.author, ['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'Downtime Training cancelled. Try again using the same command!')
            return None
        else:
            #respond to the user
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"Downtime Training cancelled. Try again using the same command!")
                return None
            elif tReaction.emoji == '✅':
                #update the appropriate DB value corresponding to the purchase and update the gold
                try:
                    db.players.update_one({'_id': char_dict['_id']}, {"$inc": {purchaseOption: 1, 'GP': -gpNeeded}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await core.send(f"Uh oh, looks like something went wrong. Try again using the same command!")
                else:
                    #Inform of the purchase success
                    level_up_embed.description = f"***{char_dict['Name']}*** has been trained by an instructor and can learn a {purchasePossibilities} of your choice. :tada:\n\nCurrent GP: {new_gp} GP\n"
                    await core.send()
                    
    @downtime.command()
    async def training(self, ctx , char):
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        #create the data entry if it doesnt exist yet
        if 'Proficiency' not in char_dict:
            char_dict['Proficiency'] = 0

        #limit to 5 purchases
        if char_dict['Proficiency'] > 4:
            await core.send(f"***{char_dict['Name']}*** cannot learn any more languages or gain proficiency in any more tools in this way.")
            return None

        # calculate the scaling cost
        gpNeeded = 500+ char_dict['Proficiency'] * 250

        # text used to inform the user which purchase they are making
        textArray = ["1st", "2nd", "3rd", "4th", "5th"]

        #pick which text to show for the possibility of Skill being an option
        purchasePossibilities = "Weapon/Language/Tool"
        if char_dict["Proficiency"] == 4:
            purchasePossibilities = purchasePossibilities+"/Skill"

        #call the extracted function
        await self.purchaseProficiency(core, 'Proficiency', 'Friend', textArray[char_dict['Proficiency']], purchasePossibilities, gpNeeded, char_dict)
        return None

    @downtime.command(aliases=["n"])
    async def noodle(self, ctx , char):
        channel = ctx.channel
        author = ctx.author
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        noodle_name, noodle_data, noodle_role = findNoodleDataFromRoles(author.roles)
        if not noodle_role:
            await channel.send(f"***{author.display_name}***, you don't have any Noodle roles! A Noodle role is required in order for ***{char_dict['Name']}*** to learn a language or gain proficiency in a tool in this way.")
            return None
        noodleLimit = noodle_data['training']
        #establish the data record if it does not exist yet
        if 'NoodleTraining' not in char_dict:
            char_dict['NoodleTraining'] = 0
        training_level = char_dict['NoodleTraining']
        #limit the purchase to only the rank
        if training_level >= noodleLimit:
            await channel.send(f"**{author.display_name}**, your current **{noodle_name}** role does not allow ***{char_dict['Name']}*** to learn a language or gain proficiency in a tool in this way.")
            return None

        #all purchases past the 5th are free, but the formular can never go negative
        gpNeeded = max(0, 500 - training_level * 100)

        #call the extracted function
        await self.purchaseProficiency(core, 'NoodleTraining', 'Noodle', list(noodle_roles.keys())[training_level+1], training_options[training_level-1], gpNeeded, char_dict)
        return None

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @shop.command(aliases=["peruse", "view"])
    async def browse(self,ctx, system):
        author = ctx.author
        char_embed = discord.Embed()
        core: InteractionCore = InteractionCore(ctx, None, char_embed, system)
        contents = []
        options = ['Adventuring Gear', 'Ammunition', 'Armor \\(Heavy\\)', 'Armor \\(Light\\)', 'Armor \\(Medium\\)', 'Consumable Spell Components', 'Mount', 'Non-Consumable Spell Components', 'Poison', 'Potion', 'Shield', 'Spellcasting Focus', 'Tack and Harness', 'Tool', 'Trade Good', 'Vehicle', 'Weapon \\(Firearm, Ranged\\)', 'Weapon \\(Martial, Melee\\)', 'Weapon \\(Martial, Ranged\\)', 'Weapon \\(Simple, Melee\\)', 'Weapon \\(Simple, Ranged\\)']
        infoString = ""
        for i in range(len(options)):
            infoString += f"{alphaEmojis[i]}: {options[i]}\n"
        char_embed.add_field(name=f"Which category would you like to see?", value=infoString, inline=False)
        await core.send()
                    
        choice = await disambiguate(len(options), core.message, author)
        if choice is None:
            await core.send(f'The browse menu has timed out.')
            return None, None
        elif choice == -1:
            await core.send(f'Shop browse menu cancelled')
            return None, None 
        
        results = list(db.shop.find({"$query": {"Type": {"$regex": options[choice]}}, "$orderby": {"Type": 1, "Name": 1}}))
        spellBookString = ""
        for r in results:
            if type(r['Name']) is list:
                for name in r['Name']:
                    spellBookString += f"• {name} ({r['GP']} GP)\n"   
            else:
                spellBookString += f"• {r['Name']} ({r['GP']} GP)\n"
        
        contents.append((options[choice], spellBookString, False, False))
        await paginate(ctx, self.bot, f"General Items", contents, msg=core.message)
        return None


async def setup(bot):
    await bot.add_cog(Shop(bot))