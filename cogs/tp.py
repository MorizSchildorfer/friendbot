import discord
import asyncio
import requests
import re
from discord.utils import get        
from discord.ext import commands
from bfunc import db, commandPrefix, roleArray, traceBack, alphaEmojis, settingsRecord, liner_dic
from cogs.util import callAPI, checkForChar, uwuize, determine_tier, add_to_dictionary
import traceback as traces
from random import *


def is_log_channel():
    async def predicate(ctx):
        return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
    return commands.check(predicate)

class Tp(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

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
            if error.param.name == 'char':
                msg = "You're missing your character name in the command. "
            elif error.param.name == "magic_item":
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

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def upgrade(self, ctx, char, magic_item):
        author = ctx.author
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        level = charRecords["Level"]
        tier = determine_tier(level)
        #make the call to the bfunc function to retrieve an item matching with magic_item
        item_record, core = await callAPI(core, 'mit', magic_item, tier=tier)
        #if an item was found
        if not item_record:
            await channel.send(
                f'''**{magic_item}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic Item Table, what tier it is, and your spelling.''')
            ctx.command.reset_cooldown(ctx)
            return None

        item_name = item_record['Name']
        item_key = item_name
        if 'Grouped' in item_record:
            item_key = item_record['Grouped']
        # check if the requested item is already in the inventory
        if "Predecessor" not in item_record:
            await channel.send(f"**{item_name}** is not upgradable.")
            ctx.command.reset_cooldown(ctx)
            return None
        # check if the requested item is already in the inventory
        elif item_key not in charRecords["Magic Items"]:
            await channel.send(f"You do not have **{item_name}**.")
            ctx.command.reset_cooldown(ctx)
            return None
        upgrade_stage = charRecords[item_name]["Stage"]
        if upgrade_stage + 1 >= len(item_record['Predecessor']["Names"]):
            await channel.send(f"**{item_name}** is already at its highest stage.")
            ctx.command.reset_cooldown(ctx)
            return None
        # get the tier of the item
        required_tier = item_record['Predecessor']["Tiers"][upgrade_stage]
        tpBank = [0,0,0,0,0]
        tpBankString = ""
        #grab the available TP of the character
        for x in range(1,6):
            if f'T{x} TP' in charRecords:
              tpBank[x-1] = (float(charRecords[f'T{x} TP']))
              tpBankString += f"{tpBank[x-1]} T{x} TP, "
        tpNeeded = float(item_record['Predecessor']["Costs"][upgrade_stage])
        tpNeeded_copy = tpNeeded
        used_tp = {}
        for tp in range (int(required_tier) - 1, 5):
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
            await channel.send(f"You do not have enough Tier {required_tier} TP or higher to upgrade **{item_name}**!")
            ctx.command.reset_cooldown(ctx)
            return None

        used_tp_text = ', '.join([f'{charRecords[tp]} {tp}' for tp in used_tp.keys()])
        tpEmbed.description = f"Are you sure you want to upgrade **{item_name} ({item_record['Predecessor']['Names'][upgrade_stage]})** to **{item_name} ({item_record['Predecessor']['Names'][upgrade_stage + 1]})** for **{tpNeeded_copy} TP**?\n\nLeftover TP: {used_tp_text}\n\n✅: Yes\n\n❌: Cancel"
        tpEmbed.set_footer(text=None)
        await core.send(embed=tpEmbed)
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await channel.send(f'TP cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.message.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                tpEmbed.clear_fields()
                try:
                    setData = {}
                    incData = {f'Magic Items.{item_key}.Stage': 1}
                    setData[f'Magic Items.{item_key}.Stage Name'] = mRecord["Predecessor"]["Names"][upgrade_stage]
                    if 'Stat Bonuses' in mRecord["Predecessor"]:
                        setData[f'Magic Items.{item_key}.Stat Bonuses'] = mRecord["Predecessor"]["Stat Bonuses"][upgrade_stage]
                    for tp, value in used_tp.items():
                        incData[f"Magic Items.{item_key}.Item Spend.{tp}"] = value
                    db.players.update_one({'_id': charRecords['_id']}, {"$set": setData, "$inc" : incData})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await core.send(f"Uh oh, looks like something went wrong. Try again using the same command!")
                    ctx.command.reset_cooldown(ctx)
                else:
                    tpEmbed.description = f"You have upgraded **{item_name}** for {tpNeeded_copy} TP! :tada:\n\nCurrent TP: {used_tp_text}\n\n"
                    await core.send()
                    ctx.command.reset_cooldown(ctx)

    async def acquireKernel(self, ctx , char, magic_item, source, sourcePast, sourceString, oneLiner):
        author = ctx.author
        tpEmbed = discord.Embed()
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        level = charRecords["Level"]
        tier = determine_tier(level)
        #make the call to the bfunc function to retrieve an item matching with magic_item
        item_record = await callAPI(core, 'mit', magic_item,  tier=tier)
        #if an item was found
        if not item_record:
            await channel.send(f'''**{magic_item}** belongs to a tier which you do not have access to or it doesn't exist! Check to see if it's on the Magic Item Table, what tier it is, and your spelling.''')
            ctx.command.reset_cooldown(ctx)
            return None
        character_items: dict = charRecords['Magic Items']
        if "Grouped" in item_record and item_record["Grouped"] in character_items:
            #inform the user that they already have an item from this group
            await core.send(f"**{item_record['Name']}** is a variant of the **{item_record['Grouped']}** item and ***{charRecords['Name']}*** already owns a variant of the that item.")
            ctx.command.reset_cooldown(ctx)
            return None
        # check if the requested item is already in the inventory
        if item_record['Name'] in character_items: 
            await core.send(f"You already have **{item_record['Name']}** and cannot spend TP or GP on another one.")
            ctx.command.reset_cooldown(ctx)
            return None
        
        indefinite = "a"
        if item_record['Name'][0].lower() in "aeiou":
            indefinite = "an"
            
        # get the tier of the item
        tierNum = item_record['Tier']
        # get the gold cost of the item
        gpNeeded = item_record['GP']
        #get the list of all items currently being worked towards

        tpBank = [0,0,0,0,0]
        tpBankString = ""
        #grab the available TP of the character
        for x in range(1,6):
            if f'T{x} TP' in charRecords:
              tpBank[x-1] = (float(charRecords[f'T{x} TP']))
              tpBankString += f"{tpBank[x-1]} T{x} TP, " 

        # TODO extract this and use it in upgrade as well
        tpNeeded = float(item_record['TP'])
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
            await channel.send(f"You do not have enough Tier {tierNum} TP or higher, or GP, to {source} **{item_record['Name']}**!")
            ctx.command.reset_cooldown(ctx)
            return None
          
        # get confirmation from the user for the purchase
        elif tpNeeded > 0:
            tpEmbed.description = f"Do you want to {source} **{item_record['Name']}** with TP or GP?\n\n You have don't have enough TP and **{charRecords[f'GP']} GP**.\n\n1️⃣: ~~{item_record['TP']} TP (Treasure Points)~~ You do not have enough TP.\n2️⃣: {item_record['GP']} GP (gold pieces)\n\n❌: Cancel"                 
        elif float(charRecords['GP']) < gpNeeded:
            tpEmbed.description = f"Do you want to {source} **{item_record['Name']}** with TP or GP?\n\n You have **{tpBankString}** and **{charRecords[f'GP']} GP**.\n\n1️⃣: {item_record['TP']} TP (Treasure Points)\n2️⃣: ~~{item_record['GP']} GP (gold pieces)~~ You do not have enough GP.\n\n❌: Cancel"                 
        else:
            tpEmbed.description = f"Do you want to {source} **{item_record['Name']}** with TP or GP?\n\n You have **{tpBankString}** and **{charRecords[f'GP']} GP**.\n\n1️⃣: {item_record['TP']} TP (Treasure Points)\n2️⃣: {item_record['GP']} GP (gold pieces)\n\n❌: Cancel"                 
        
        await core.send()
        choices = []
        if tpNeeded <= 0:
            await core.message.add_reaction('1️⃣')
            choices.append('1️⃣')
        if float(charRecords['GP']) >= gpNeeded:
            await core.message.add_reaction('2️⃣')
            choices.append('2️⃣')
        choices.append('❌')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,choices) , timeout=60)
        except asyncio.TimeoutError:
            #cancel if the user didnt respond within the timeframe
            await core.send(f'TP cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            newGP = charRecords['GP']
            bought_with_tp = False
            #cancel if the user decided to cancel the purchase
            if tReaction.emoji == '❌':
                await core.send(f"TP cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None
            #refund the TP in the item if the user decides to purchase with gold
            elif tReaction.emoji == '2️⃣':
                newGP = round(charRecords['GP'] - gpNeeded,2)
                remaining_resources_text = f"New GP: {newGP} GP"
                #search for the item in the items currently worked towards
                tpEmbed.description = f"Are you sure you want to {source} **{item_record['Name']}** for **{item_record['GP']} GP**?\n\nCurrent GP: {charRecords['GP']}\n{remaining_resources_text}\n\n✅: Yes\n\n❌: Cancel"

            # If user decides to buy item with TP:
            elif tReaction.emoji == '1️⃣':
                bought_with_tp = True
                remaining_resources_text = 'Leftover TP: ' + ', '.join([f'{charRecords[tp]} {tp}' for tp in used_tp.keys()])
                tpEmbed.description = f"Are you sure you want to {source} **{item_record['Name']}** for **{item_record['TP']} TP**?\n\n{remaining_resources_text}\n\n✅: Yes\n\n❌: Cancel"

            new_item = {'Name': item_record['Name']}
            item_key = item_record['Name']
            if 'Attunement' in item_record:
                new_item['Attunement'] = item_record['Attunement']
                new_item['Attuned'] = False
            if 'Grouped' in item_record:
                item_key = item_record['Grouped']
                pass
            if 'Predecessor' in item_record:
                new_item['Stage'] = 0
                new_item['Stage Name'] = item_record["Predecessor"]['Names'][0]
            if 'Stat Bonuses' in item_record:
                new_item['Stat Bonuses'] = item_record["Stat Bonuses"]
            tpEmbed.set_footer(text=None)
            await core.send()
            await core.message.add_reaction('✅')
            await core.message.add_reaction('❌')
            try:
                tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
            except asyncio.TimeoutError:
                await channel.send(f'TP cancelled. Try again using the same command!')
                ctx.command.reset_cooldown(ctx)
                return None
            else:
                await core.message.clear_reactions()
                if tReaction.emoji == '❌':
                    await core.message.edit(embed=None, content=f"TP cancelled. Try again using the same command!")
                    await core.message.clear_reactions()
                    ctx.command.reset_cooldown(ctx)
                    return None
                elif tReaction.emoji == '✅':
                    tpEmbed.clear_fields()
                    try:
                        setData = {f"Magic Items.{item_key}": new_item}
                        item_spend = {}
                        if bought_with_tp:
                            for tp, value in used_tp.items():
                                setData[tp] = charRecords[tp]
                                add_to_dictionary(item_spend, tp, value)
                        else:
                            setData['GP'] = newGP
                            add_to_dictionary(item_spend, "GP", gpNeeded)
                        new_item[f"Item Spend"] = item_spend
                        db.players.update_one({'_id': charRecords['_id']}, {"$set": setData})
                        db.stats.update_one({"Life": 1}, {"$inc" : {"Magic Items."+item_record['Name']: 1}})
                    except Exception as e:
                        await traceBack(ctx, e)
                        ctx.command.reset_cooldown(ctx)
                        print ('MONGO ERROR: ' + str(e))
                        await core.send(f"Uh oh, looks like something went wrong. Try again using the same command!")
                        return None
                    else:
                        outputLiner = oneLiner.replace("<magic item>", str(item_record['Name'])).replace(f"a {str(item_record['Name'])}", f"{indefinite} {str(item_record['Name'])}")
                        if bought_with_tp != "":
                            tpEmbed.description = f"{outputLiner}\n\nYou have {sourcePast} **{item_record['Name']}** for {item_record['TP']} TP! :tada:\n\n{remaining_resources_text}\n\n"
                        elif newGP != "":
                            tpEmbed.description = f"{outputLiner}\n\nYou have {sourcePast} **{item_record['Name']}** for {item_record['GP']} GP! :tada:\n\n{remaining_resources_text}\n"
                        await core.send()
                        ctx.command.reset_cooldown(ctx)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def find(self, ctx , char, magic_item):
        # Assigns 4 variables that are then passed to the buy command. These variables are used to change the text to a one-liner system.
        source = "find"
        sourceString = "Find a Magic Item"
        sourcePast = "found"
        oneLiner = sample(liner_dic["Find"], 1)[0] # Random one-liner assigned from the corresponding collection
        await self.acquireKernel(ctx, char, magic_item, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def craft(self, ctx , char, magic_item):
        source = "craft"
        sourceString = "Craft a Magic Item"
        sourcePast = "crafted"
        oneLiner = sample(liner_dic["Craft"], 1)[0]
        await self.acquireKernel(ctx, char, magic_item, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def meme(self, ctx , char, magic_item):
        source = "meme"
        sourceString = "Meme a Magic Item"
        sourcePast = "memed"
        oneLiner = sample(liner_dic["Meme"], 1)[0]
        await self.acquireKernel(ctx, char, magic_item, source, sourcePast, sourceString, oneLiner)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @tp.command()
    async def abandon(self, ctx , char, tierNum):
        channel = ctx.channel
        author = ctx.author
        if tierNum not in ('1','2','3','4') and tierNum.lower() not in [r.lower() for r in roleArray]:
            await channel.send(f"**{tierNum}** is not a valid tier. Please try again with **Junior** or **1**, **Journey** or **2**, **Elite** or **3**, **True** or **4**, or **Ascended** or **5**.")
            ctx.command.reset_cooldown(ctx)
            return None
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        tp_embed = core.embed
        if tierNum.isdigit():
            role = int(tierNum)
        else:
            role = roleArray.index(tierNum.capitalize())

        if f"T{role} TP" not in charRecords:
            await core.send(f"You do not have T{role} TP to abandon.")
            ctx.command.reset_cooldown(ctx)
            return None

        tp_embed.title = f"Abandoning TP: {charRecords['Name']}"
        tp_embed.description = f"Are you sure you want to abandon your Tier {role} TP?\n\nYou currently have {charRecords[f'T{role} TP']} Tier {role} TP.\n\n**Note: this action is permanent and cannot be reversed.**\n\n✅: Yes\n\n❌: Cancel"
        tp_embed.set_footer(text=None)
        await core.send()
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
        except asyncio.TimeoutError:
            await core.send(f'TP cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            if tReaction.emoji == '❌':
                await core.send(f"TP cancelled. Try again using the same command!")
                ctx.command.reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                tp_embed.clear_fields()
                try:
                    db.players.update_one({'_id': charRecords['_id']}, {"set": {f"T{role} TP": 0}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await core.send("Uh oh, looks like something went wrong. Try again using the same command!")
                else:
                    tp_embed.description = f"You have abandoned {charRecords[f'T{role} TP']} T{role} TP!"
                    await core.send()
                    ctx.command.reset_cooldown(ctx)


async def setup(bot):
    await bot.add_cog(Tp(bot))