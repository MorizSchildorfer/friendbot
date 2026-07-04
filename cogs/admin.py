import discord
import asyncio
import re
from discord.utils import get        
from discord.ext import commands
from datetime import date
import sys
import io
import traceback
import collections
from math import ceil, floor
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError
from bfunc import db, traceBack, settingsRecord, liner_dic, currentTimers, connection
from cogs.util import calculateTreasure, callAPI, checkForChar, paginate, admin_or_owner, noodle_roles, \
    add_to_inventory, add_to_dictionary, check_for_char_with_end, determine_tier, InteractionCore, find_reward_item


def add_5e(item):
    item["System"] = "5E"
    del item["_id"]
    return item


def map_logs(item):
    if "Type" not in item:
        item["Type"] = "5E"
    return item

def convert_bonus_string(full):
    bonus_strings = full.split(",")
    new_bonuses = []
    for bonus in bonus_strings:
        output = {}
        bonus = bonus.strip()
        typ = "FIXED"
        if bonus.startswith("MAX"):
            typ = "MAX"
            bonus = bonus.replace("MAX ", "")
        elif "+" in bonus:
            typ = "BONUS"
            bonus = bonus.replace("+ ", "")
        output["Type"] = typ
        output["Stat"] = bonus.split(" ")[0]
        output["Value"] = int(bonus.split(" ")[1])
        new_bonuses.append(output)
    return new_bonuses

def check_for_wrong_key(dictionary):
    for k, v in dictionary.items():
        if not isinstance(k, str):
            print("ISSUE", v)
        if isinstance(v, dict):
            check_for_wrong_key(v)
            

def change_stat_bonus(item):
    if "Stat Bonuses" in item:
        item["Stat Bonuses"] = convert_bonus_string(item["Stat Bonuses"])
    if "Predecessor" in item:
        if "Stat Bonuses" in item["Predecessor"]:
            for i in range(0, len( item["Predecessor"]["Stat Bonuses"])):
                item["Predecessor"]["Stat Bonuses"][i] = convert_bonus_string(item["Predecessor"]["Stat Bonuses"][i])
    return item

def fix_hp(player, class_entries):
    total_hp = class_entries[player['Starting Class']]['Hit Die Max'] - class_entries[player['Starting Class']]['Hit Die Average']
    for name, c in player["Class"].items():
        level = int(c['Level'])
        total_hp += class_entries[name]['Hit Die Average'] * level
    player["HP"] = total_hp
    return player

def change_player(player, all_item_records):
    print(player["Name"])
    if "Max Stats" in player:
        del player["Max Stats"]
    if "Feats" not in player:
        player["Feats"] = []
    elif player["Feats"] == "None":
        player["Feats"] = []
    else:
        player["Feats"] = player["Feats"].split(", ")
    
    new_inventory = {}
    for name, count in player["Inventory"].items():
        new_inventory[name] = {"CREATE": count}
    player["Inventory"] = new_inventory
    
    new_consumables = {}
    if not player["Consumables"] == "None":
        for consumable in player["Consumables"].split(", "):
            add_to_inventory(new_consumables, consumable, 1, "CREATE")
    player["Consumables"] = new_consumables
    
    new_stats = {}
    for stat in ["STR", "DEX", "WIS", "INT", "CON", "CHA"]:
        new_stats[stat] = player[stat]
        del player[stat]
    player["Stats"] = new_stats
    
    new_class = {}
    old_classes = player["Class"].split(" / ")
    player["Starting Class"] = old_classes[0].split(" ")[0].strip()
    for multi_class in old_classes:
        entry = {"Subclass": None, "Level": player["Level"]}
        split_subclass = multi_class.split("(")
        if len(split_subclass) > 1:
            entry["Subclass"] = split_subclass[1].split(")")[0].strip()
        split_level = split_subclass[0].strip().split(" ")
        if len(split_level) > 1:
            entry["Level"] = int(split_level[1])
        new_class[split_level[0]] = entry
    player["Class"] = new_class
    
    new_items = {}
    if not player["Magic Items"] == "None":
        old_items = player["Magic Items"].split(", ")
        grouped = {}
        predecessors = {}
        if "Predecessor" in player:
            predecessors = player["Predecessor"]
            del player["Predecessor"]
        if "Grouped" in player:
            for pair in player["Grouped"]:
                grouped[pair.split(":")[1].strip()] = pair.split(":")[0].strip()
            del player["Grouped"]
        for magic_item in old_items:
            entry = {}
            key = magic_item
            if magic_item not in all_item_records:
                add_to_inventory(new_items, key, 1, "CREATE")
                new_items[key]["Name"] = key
                continue
            entry["BUY"] = 1
            if magic_item in grouped:
                key = grouped[key]
            entry["Name"] = magic_item
            if magic_item in predecessors:
                entry["Stage"] = predecessors[magic_item]["Stage"]
                entry["Stage Name"] = predecessors[magic_item]["Names"][entry["Stage"]]
            item_db_entry = all_item_records[magic_item]
            if "Attunement" in item_db_entry:
                entry["Attunement"] = item_db_entry["Attunement"]
                entry["Attuned"] = "Attuned" in player and magic_item in player["Attuned"]
            if magic_item in player["Item Spend"]:
                entry["Item Spend"] = player["Item Spend"][magic_item]
            else:
                entry["Item Spend"] = {}
            if "Stat Bonuses" in item_db_entry:
                entry["Stat Bonuses"] = item_db_entry["Stat Bonuses"]
                if "Attunement" not in item_db_entry:
                    for bonus in entry["Stat Bonuses"]:
                        new_stats[bonus["Stat"]] -= bonus["Value"]
            new_items[key] = entry
    check_for_wrong_key(new_items)
    player["Magic Items"] = new_items
    if "Attuned" in player:
        del player["Attuned"]
    if "Item Spend" in player:
        del player["Item Spend"]
    return player

def is_log_channel():
    async def predicate(ctx):
        return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
    return commands.check(predicate)


class Admin(commands.Cog, name="Admin"):
    def __init__ (self, bot):
        self.bot = bot
    async def cog_command_error(self, ctx, error):
        msg = None

        if isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "Your parameter types were off."
        
        elif isinstance(error, commands.CheckFailure):
            msg = ""
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            msg = "You missed a parameter"

        if msg:
            
            await ctx.channel.send(msg)
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return
        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
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
    @commands.group(case_insensitive=True)
    async def react(self, ctx):	
        pass

    @react.command()
    @admin_or_owner()
    async def printGuilds(self, ctx):
        out = "All guild channels:\n"
        ch = ctx.guild.get_channel(452704598440804375)
        for channel in ch.text_channels:
            out+="  "+channel.mention+"\n"
        await ctx.channel.send(content=out)
    
    #this function allows you to specify a channel and message and have the bot react with a given emote
    #Not tested with emotes the bot might not have access to
    @react.command()
    @admin_or_owner()
    async def add(self, ctx, channel: int, msg: int, emote: str):
        ch = ctx.guild.get_channel(channel)
        message = await ch.fetch_message(msg)
        await message.add_reaction(emote)
        await ctx.message.delete()
    
    #this function allows you to specify a channel and message and have the bot remove its reaction with a given emote
    #Not tested with emotes the bot might not have access to
    @react.command()
    @admin_or_owner()
    async def remove(self, ctx, channel: int, msg: int, emote: str):
        ch = ctx.guild.get_channel(channel)
        message = await ch.fetch_message(msg)
        await message.remove_reaction(emote, self.bot.user)
        await ctx.message.delete()

    @commands.command()
    async def startT1RW(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["t1rw"] = True
            await ctx.channel.send("Let the T1 games begin!") 
    
    @commands.command()
    async def endT1RW(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["t1rw"] = False
            await ctx.channel.send("T1 no more!") 
    @commands.command()
    async def startDDMRW(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["ddmrw"] = True
            await ctx.channel.send("Let the games begin!")
    @commands.command()
    async def endDDMRW(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["ddmrw"] = False        
            await ctx.channel.send("Until next month!")
    
    @commands.command()
    async def startEvent(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["Event"] = True
            await ctx.channel.send("Let the event begin!")
            
    @commands.command()
    async def endEvent(self, ctx):
        if "Mod Friend" in [r.name for r in ctx.author.roles]:
            global settingsRecord
            settingsRecord["Event"] = False        
            await ctx.channel.send("Until next time!")
    
    @commands.command()
    async def zoop(self, ctx):
        file1 = open('find.txt', 'r', encoding="utf8")
        lines = file1.readlines()
        out = []
        for line in lines:
            print(line)
            if line.strip():
                out.append({"Text" : line.strip()})
        result = db.liners_money.insert_many(out)
        print(len(result.inserted_ids))

    # command that allows one to update each field of the liners dictionary
    @commands.command()
    @admin_or_owner()
    async def updateLiners(self, ctx):
        # get all entries of the relevant DB and extract the Text field and compile as a list and assign to the dic
        liner_dic["Find"] = list([line["Text"] for line in db.liners_find.find()])
        liner_dic["Meme"] = list([line["Text"] for line in db.liners_meme.find()])
        liner_dic["Craft"] = list([line["Text"] for line in db.liners_craft.find()])
        liner_dic["Money"] = list([line["Text"] for line in db.liners_money.find()])
        await ctx.channel.send("All liners Updated")
    #
    # @commands.command()
    # @admin_or_owner()
    # async def transferUnchanged(self, ctx):
    #     unchanged = ["shop", "backgrounds", "spells", "feats", "special", "races", "rit", "classes"] #
    #     for collection in unchanged:
    #         entries = list(map(add_5e, connection.dnd[collection].find()))
    #         try:
    #             if len(entries) > 0:
    #                 connection.dnd5r[collection].insert_many(entries)
    #         except BulkWriteError as bwe:
    #             print(bwe.details)
    #             # if it fails, we need to cancel and use the error details
    #             return
    #         await ctx.channel.send(content=f"Transferred {collection}")
    #
    # @commands.command()
    # @admin_or_owner()
    # async def transferPure(self, ctx):
    #     unchanged = ["liners_money", "liners_craft", "liners_meme", "liners_find", "guilds"] #
    #     for collection in unchanged:
    #         entries = list(connection.dnd[collection].find())
    #         try:
    #             if len(entries) > 0:
    #                 connection.dnd5r[collection].insert_many(entries)
    #         except BulkWriteError as bwe:
    #             print(bwe.details)
    #             # if it fails, we need to cancel and use the error details
    #             return
    #         await ctx.channel.send(content=f"Transferred {collection}")
    #
    #
    # @commands.command()
    # @admin_or_owner()
    # async def transferLogs(self, ctx):
    #     unchanged = ["logdata"] #
    #     for collection in unchanged:
    #         entries = list(map(map_logs, connection.dnd[collection].find()))
    #         try:
    #             if len(entries) > 0:
    #                 connection.dnd5r[collection].insert_many(entries)
    #         except BulkWriteError as bwe:
    #             print(bwe.details)
    #             # if it fails, we need to cancel and use the error details
    #             return
    #         await ctx.channel.send(content=f"Transferred {collection}")
    #
    #
    # @commands.command()
    # @admin_or_owner()
    # async def transferMit(self, ctx):
    #     unchanged = ["mit"]
    #     for collection in unchanged:
    #         entries = list(map(change_stat_bonus, map(add_5e, connection.dnd[collection].find())))
    #         try:
    #             if len(entries) > 0:
    #                 connection.dnd5r[collection].insert_many(entries)
    #         except BulkWriteError as bwe:
    #             print(bwe.details)
    #             # if it fails, we need to cancel and use the error details
    #             return
    #         await ctx.channel.send(content=f"Transferred {collection}")
    #
    # @commands.command()
    # @admin_or_owner()
    # async def transferPlayers(self, ctx):
    #     unchanged = ["players"]
    #     item_entries = connection.dnd5r["mit"].find({"System": "5E"})
    #     item_records = {}
    #     for entry in item_entries:
    #         if not isinstance(entry["Name"], list):
    #             item_records[entry["Name"]] = entry
    #         else:
    #             for name in entry["Name"]:
    #                 item_records[name] = entry
    #     class_entries = {c["Name"]: c for c in connection.dnd5r["classes"].find({"System": "5E"})}
    #
    #     for collection in unchanged:
    #         players = connection.dnd[collection].find({"Class": {"$ne": "Friend"}})
    #         entries = list(map(lambda x: fix_hp(x, class_entries), map(lambda x: change_player(x, item_records), map(add_5e, players))))
    #         try:
    #             if len(entries) > 0:
    #                 connection.dnd5r[collection].insert_many(entries)
    #         except BulkWriteError as bwe:
    #             print(bwe.details)
    #             # if it fails, we need to cancel and use the error details
    #             return
    #         await ctx.channel.send(content=f"Transferred {collection}")
    #
    # @commands.command()
    # @admin_or_owner()
    # async def delete5e(self, ctx, table):
    #     try:
    #         connection.dnd5r[table].delete_many({"System": "5E"})
    #     except BulkWriteError as bwe:
    #         print(bwe.details)
    #         # if it fails, we need to cancel and use the error details
    #         return
    #     await ctx.channel.send(content="Completed")

    @commands.command()
    @admin_or_owner()
    async def goldUpdate(self, ctx, tier: int, tp: int, gp: int):
        try:
            db.mit.update_many(
               {"Tier": tier, "TP": tp},
               {"$set" : {"GP" : gp}},
            )
            await ctx.channel.send(content=f"Successfully updated the GP cost of all T{tier} items costing {tp} TP to {gp} GP.")
    
        except Exception as e:
            traceback.print_exc()
            
    @commands.command()
    @admin_or_owner()
    async def tpUpdate(self, ctx, tier: int, tp: int, tp2: int):
        try:
            db.mit.update_many(
               {"Tier": tier, "TP": tp},
               {"$set" : {"TP" : tp2}},
            )
            await ctx.channel.send(content=f"Successfully updated the TP cost of all T{tier} items costing {tp} TP to {tp2} TP.")
    
        except Exception as e:
            traceback.print_exc()
            
    @commands.command()
    @admin_or_owner()
    async def updateInventory(self, ctx, oldName, newName):
        player_list = db.players.find(
               {"Inventory."+oldName: {"$exists": True}}
            )
        renameData = list(map(lambda item: UpdateOne({'_id': item['_id']}, {"$inc" : {"Inventory."+newName : item["Inventory"][oldName]}, "$unset" : {"Inventory."+oldName : 1}}), player_list))
        
        try:
            if(len(renameData)>0):
                db.players.bulk_write(renameData)
        except BulkWriteError as bwe:
            print(bwe.details)
            # if it fails, we need to cancel and use the error details
            return
        await ctx.channel.send(content=f"Successfully renamed {oldName} to {newName} of {len(player_list)} player inventories")
            
    @commands.command()
    @commands.has_any_role("Mod Friend")
    async def alignmentList(self, ctx):
        player_list = list(db.players.find(
               {"Alignment": {"$exists": True}})
            )
        contents = []
        alignment="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(list([x["Alignment"].replace("\"", "") for x in player_list])))).items()])
        contents.append(("Alignment", alignment, False))
        await paginate(ctx, self.bot, f"Alignments List", contents=contents, separator="\n")

    @commands.command()
    @commands.has_any_role("Mod Friend")
    async def reflavorList(self, ctx):
        player_list = list(db.players.find(
               {"Reflavor": {"$exists": True}})
            )
        rfarray = list([line["Reflavor"] for line in player_list]) #puts all the reflavors in a list
        contents = []
        raceList = []
        classList = []
        backgroundList = []
        i = 0
        while i < len(rfarray):
            if 'Race' in rfarray[i]:
                raceList.append(rfarray[i]['Race'])
            if 'Class' in rfarray[i]:
                classList.append(rfarray[i]['Class'])
            if 'Background' in rfarray[i]:
                backgroundList.append(rfarray[i]['Background'])
            i += 1
        raceContents="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(list([x.replace("\"", "") for x in raceList])))).items()])

        classContents="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(list([x.replace("\"", "") for x in classList])))).items()])

        backgroundContents="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(list([x.replace("\"", "") for x in backgroundList])))).items()])
        
        contents.append(("Race", raceContents, False))
        contents.append(("Class", classContents, False))
        contents.append(("Background", backgroundContents, False))

        await paginate(ctx, self.bot, f"Reflavor List", contents=contents, separator="\n")

    @commands.command()
    @commands.has_any_role("Mod Friend")
    async def nicknameList(self, ctx):
        player_list = list(db.players.find(
               {"Nickname": {"$exists": True}})
            )
        nickname ="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(list([x["Nickname"].replace("\"", "") for x in player_list])))).items()])
        contents = []
        contents.append(("Nickname", nickname, False))
        await paginate(ctx, self.bot, f"Nicknames List", contents=contents, separator="\n")
        
    @commands.command()
    @commands.has_any_role("Mod Friend")
    async def rewardStats(self, ctx):
        game_list = list(db.logdata.find(
               {"Tier": 3})
            )
        lst = []
        for x in game_list:
            for p in x["Players"].values():
                #if p["Level"] == 20:
                    lst.extend(p["Consumables"]["Add"])
        
        out ="\n".join([f"{x}: {y}" for x,y in dict(collections.Counter(sorted(lst))).items()])
        
        length = len(out)
        while(length>2000):
            x = out[:2000]
            x = x.rsplit("\n", 1)[0]
            await ctx.channel.send(content=x)
            out = out[len(x):]
            length -= len(x)
        await ctx.channel.send(content=out)
    
    @commands.command()
    @admin_or_owner()
    async def printTierItems(self, ctx, tier: int, tp: int):
        try:
            items = list(db.mit.find(
               {"Tier": tier, "TP": tp},
            ))
            out = f"Items in Tier {tier} costing TP {tp}:\n"
            def alphaSort(item):
                if "Grouped" in item:
                    return item["Grouped"]
                else:
                    return item["Name"]
            
            items.sort(key = alphaSort)
            for i in items:
                if "Grouped" in i:
                    out += i["Grouped"]
                else:
                    out += i["Name"]
                out += f" GP {i['GP']}\n"
            length = len(out)
            while(length>2000):
                x = out[:2000]
                x = x.rsplit("\n", 1)[0]
                await ctx.channel.send(content=x)
                out = out[len(x):]
                length -= len(x)
            await ctx.channel.send(content=out)
    
        except Exception as e:
            traceback.print_exc()        
      
    @commands.command()
    @admin_or_owner()
    async def printRewardItems(self, ctx, tier: int):
        try:
            items = list(db.rit.find(
               {"Tier": tier},
            ))
            
            out = f"Reward Items in Tier {tier}:\n"
            def alphaSort(item):
                if "Grouped" in item:
                    return (item['Minor/Major'], item["Grouped"])
                else:
                    return (item['Minor/Major'], item["Name"])
            
            items.sort(key = alphaSort)
            majors = filter(lambda x: x['Minor/Major'] == "Major", items)
            minors = filter(lambda x: x['Minor/Major'] == "Minor", items)
            groups =  [[majors, "Majors"], [minors, "Minors"]]
            for g in groups:
                out += f"\n**{g[1]}**\n"
                for i in g[0]:
                    if "Grouped" in i:
                        out += i["Grouped"]
                    else:
                        out += i["Name"]
                    out += f"\n"
            length = len(out)
            while(length>2000):
                x = out[:2000]
                x = x.rsplit("\n", 1)[0]
                await ctx.channel.send(content=x)
                out = out[len(x):]
                length -= len(x)
            await ctx.channel.send(content=out)
    
        except Exception as e:
            traceback.print_exc()        
    
    @commands.command()
    @commands.has_any_role('Mod Friend', 'A d m i n')
    async def removeImage(self, ctx, charName):
        author_check= None
        if ctx.message.mentions:
            author_check =ctx.message.mentions[0]
        mod = not author_check
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName, mod, author_check)
        channel = ctx.channel
        if not char_dict:
            await core.send(f'I was not able to find the character ***"{charName}"***!')
            return False

        await core.delete()
            
        try:
            db.players.update_one(
               {"_id": char_dict["_id"]},
                {"$unset" : {"Image": 1}}
            )
            await channel.send(content=f"Successfully deleted the image.")
    
        except Exception as e:
            traceback.print_exc()@commands.command()
            
    @commands.command()
    @commands.has_any_role('A d m i n')
    async def removeCharacter(self, ctx, charName):
        author_check= None
        if ctx.message.mentions:
            author_check =ctx.message.mentions[0]
        mod = not author_check
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName, mod, author_check)
        channel = ctx.channel
        if not char_dict:
            await core.send(f'I was not able to find the character ***"{charName}"***!')
            return False

        await core.delete()
            
        try:
            db.players.delete_one(
               {"_id": char_dict["_id"]}
            )
            await channel.send(content=f"Successfully deleted {char_dict['Name']}.")
    
        except Exception as e:
            traceback.print_exc()
            
    @commands.command()
    @commands.has_any_role('Mod Friend')
    async def permitRespec(self, ctx, charName):
        author_check= None
        if ctx.message.mentions:
            author_check =ctx.message.mentions[0]
        mod = not author_check
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName, mod, author_check)
        channel = ctx.channel
        if not char_dict:
            await core.send(f'I was not able to find the character ***"{charName}"***!')
            return False

        await core.delete()
            
        try:
            db.players.update_one(
               {"_id": char_dict["_id"]}, {"$set" : {"Respecc": 1}}
            )
            await channel.send(content=f"Successfully updated {char_dict['Name']}.")
    
        except Exception as e:
            traceback.print_exc()

                   
    @commands.command()
    @admin_or_owner()
    async def generateBoard(self, ctx):
                                        
        def is_me(m):
            return m.author == self.bot.user

        deleted = await ctx.channel.purge(limit=100, check=is_me)
        all_users = list(db.users.find( {"Noodles": {"$gt":0}}))
        all_users = list(filter(lambda x: ctx.guild.get_member(int(x['User ID'])), all_users))
        
        cut_off_list = []
        cut_offs = {}
        for noodle_name, noodle_data in noodle_roles.items():
            cut_off_list.append(max(1, noodle_data['noodles']))
            cut_offs[noodle_data['noodles']] = {"Users": [], "Role": get(ctx.guild.roles, name=noodle_name).mention}
        
        cut_off_list.reverse()
        for user in all_users:
            for cut_off_num in cut_off_list:
                if user["Noodles"] >= cut_off_num:
                    break
            cut_offs[cut_off_num]["Users"].append(user)
        
        
        all_messages = []
        count = 0
        for cut_off_num in cut_off_list:
            noodle_group = cut_offs[cut_off_num]
            if len(noodle_group["Users"]) == 0:
                continue
            curr_message = ""
            new_stuff = False
            symbol_count_fix = [0,0,0]
            role = noodle_group["Role"]
            
            count += 1
            next_message = await ctx.channel.send(str(count))
            all_messages.append([next_message, f"``` ```{role}s have run {cut_off_num}+ Games"])
            noodle_group["Users"].sort(key = lambda x: x["Noodles"], reverse=True)
            for u in noodle_group["Users"]:
                crown_count = u['Noodles']//100
                big_star_count = (u['Noodles']%100)//10
                star_count = u['Noodles']%10
                curr_message += f"<@!{u['User ID']}>: {u['Noodles']} {'👑'*(crown_count)}{'🌟'*big_star_count}{'⭐'* star_count}\n"
                symbol_count_fix[0] +=crown_count
                symbol_count_fix[1] +=big_star_count
                symbol_count_fix[2] +=star_count
                if len(curr_message) >1900-19*symbol_count_fix[0] - 19*symbol_count_fix[1] - 19*symbol_count_fix[2]:
                    count += 1
                    next_message = await ctx.channel.send(str(count))
                    all_messages.append([next_message, curr_message])
                    curr_message = ""
                    new_stuff = False
                    symbol_count_fix = [0,0,0]
                else:
                    new_stuff = True
                    
            if new_stuff:
                count += 1
                next_message = await ctx.channel.send(str(count))
                all_messages.append([next_message, curr_message])
                
        count += 1
        next_message = await ctx.channel.send(str(count))
        all_messages.append([next_message, f"``` ```Last updated {date.today().strftime('%B %d, %Y')}"])
            
        for m in all_messages:
            await m[0].edit(content=m[1])
       

    @commands.command()
    @admin_or_owner()
    async def snapGuild(self, ctx, guild):
        guildChannel = ctx.message.channel_mentions

        if guildChannel == list():
            await ctx.channel.send(f"You must provide a guild channel.")
            return 
        channel = guildChannel[0]
        
        guildRecords = db.guilds.find_one({"Channel ID": str(channel.id)})
        
        moveEmbed = discord.Embed()
        moveEmbedmsg = None
        
        moveEmbedmsg = await  ctx.channel.send(content=f"Are you sure you want to move and refund {guildRecords['Name']}?\n No: ❌\n Yes: ✅")
        
        author = ctx.author
        
        if not await self.doubleVerify(ctx, moveEmbedmsg):
            return
        costs = [0, 1000, 4000, 7000]
        returnData =[]
        player_list = list(db.players.find( {"Guild": guildRecords["Name"]}))
        
        for p in player_list:
            tier = 1
            if p["Level"] >= 17:
                tier = 4
            elif p["Level"] >= 11:
                tier = 3
            elif p["Level"] >= 5:
                tier = 2
            # refund each rank and delete entries
            returnData.append({"_id": p["_id"], "fields": {"$inc" : {"GP": costs[p["Guild Rank"]-1]+200*tier}, "$unset": {"Guild": 1, "Guild Rank": 1}}})
        try:
            db.guilds.delete_one( {"_id": guildRecords["_id"]})
        except Exception as e:
            print("ERRORpr", e)
            traceback.print_exc()
            await traceBack(ctx,e)
            return
        refundData = list(map(lambda item: UpdateOne({'_id': item['_id']}, item['fields']), returnData))
        
        try:
            if len(refundData)>0:
                db.players.bulk_write(refundData)
        except BulkWriteError as bwe:
            print(bwe.details)
            # if it fails, we need to cancel and use the error details
            return
        
        await moveEmbedmsg.edit(content="Completed")    
    
    
    # updates all player elements that match the string current_value in the element field and replaces the value with new_value
    @commands.command()
    @admin_or_owner()
    async def characterUpdate(self, ctx, element, current_value, new_value):
        
        moveEmbedmsg = await  ctx.channel.send(content=f"Are you sure you want to change the value of {current_value} to {new_value}?\n No: ❌\n Yes: ✅")
        
        if not await self.doubleVerify(ctx, moveEmbedmsg):
            return
        count = db.players.update_many( {element: current_value},
                                    {"$set" : {element : new_value}})
        await moveEmbedmsg.edit(content=f"Successfully updated {count.modified_count} player entries.")
    
    
    @commands.command()
    @admin_or_owner()
    async def moveItem(self, ctx, item, tier: int, tp: int):
        moveEmbedmsg, itemRecord = await self.refundKernel(ctx, item, "move", "moved")
        if moveEmbedmsg:
            try:
                updatedGP = itemRecord["GP"]
                targetTierInfoItem = db.mit.find_one( {"TP": tp, "Tier": tier})
                if(targetTierInfoItem):
                    updatedGP = targetTierInfoItem["GP"]
                db.mit.update_one( {"_id": itemRecord["_id"]},
                                    {"$set" : {"Tier" : tier, "TP" : tp, "GP": updatedGP}})
                                    
            except Exception as e:
                print("ERROR", e)
                traceback.print_exc()
                await traceBack(ctx,e)
                return    
            
            await moveEmbedmsg.edit(content="Completed")
        
    
    @commands.command()
    @admin_or_owner()
    async def removeItem(self, ctx, item):
    
        removeEmbedmsg, itemRecord = await self.refundKernel(ctx, item, "remove", "removed")
             
        if removeEmbedmsg:
            try:       
                
                db.mit.remove_one( {"_id": itemRecord["_id"]})
            except Exception as e:
                print("ERROR", e)
                traceback.print_exc()
                await traceBack(ctx,e)
                return    
            
            await removeEmbedmsg.edit(content="Completed")
    
    
    async def refundKernel(self, ctx, item, actionTerm, actionTermPast):
        refundEmbed = discord.Embed()
        refundEmbedmsg = None
        
        itemRecord, refundEmbed, refundEmbedmsg = await callAPI(ctx, refundEmbed, refundEmbedmsg, 'mit', item)
        
        if(refundEmbedmsg):
            await refundEmbedmsg.edit(embed=None, content=f"Are you sure you want to {actionTerm} and refund {itemRecord['Name']}?\n No: ❌\n Yes: ✅")
        else:
            refundEmbedmsg = await  ctx.channel.send(content=f"Are you sure you want to {actionTerm} and refund {itemRecord['Name']}?\n No: ❌\n Yes: ✅")
        author = ctx.author
        
        if(not await self.doubleVerify(ctx, refundEmbedmsg)):
            return None, None
        items_to_refund = [itemRecord["Name"]]
        if "Grouped" in itemRecord:
            fullItemRecord = db.mit.find_one({"Grouped": itemRecord["Grouped"]})
            items_to_refund = fullItemRecord["Name"]
        for item_to_refund in items_to_refund:
            print("moving: "+item_to_refund)
            itemRecord["Name"] = item_to_refund
            try:
                    
                returnData, playerIDs = self.characterItemRefund(ctx, itemRecord, "Magic Items")
                                                            
            except Exception as e:
                print("ERRORpr", e)
                traceback.print_exc()
                await traceBack(ctx,e)
                return None, None
            
            refundData = list(map(lambda item: UpdateOne({'_id': item['_id']}, item['fields']), returnData))
            
            try:
                if(len(refundData)>0):
                    db.players.bulk_write(refundData)
                db.stats.update_one({'Life': 1}, {"$unset": {f'Magic Items.{itemRecord["Name"]}': 1}})
            except BulkWriteError as bwe:
                print(bwe.details)
                # if it fails, we need to cancel and use the error details
                return None, None
            for playerID, charNames in playerIDs.items():
                player = ctx.guild.get_member(int(playerID))
                if player:
                    await player.send(f"The magic item **{itemRecord['Name']}** has been {actionTermPast}. **{', '.join(charNames[:-1])} and {charNames[-1]}** have been refunded their purchase.")
        return refundEmbedmsg, itemRecord
    
    def characterItemRefund(self, ctx, itemRecord, category):
        playerIDs = {}
        characters = list( db.players.find({f"Item Spend.{itemRecord['Name']}" : {"$exists": True}}))
        returnData = []
        for char in characters:
            items = char[category].split(", ")
            if itemRecord['Name'] not in items:
                continue
            if char["User ID"] in playerIDs:
               playerIDs[char["User ID"]].append(char["Name"])
            else:
               playerIDs[char["User ID"]] = [char["Name"]]
            items.remove(itemRecord['Name'])
            if(len(items)==0):
                items.append("None")
            
            entry = {"_id": char["_id"],  
                    "fields": {"$set": {category: ", ".join(items)},
                               "$inc": char["Item Spend"][itemRecord['Name']],
                               "$unset": {f"Item Spend.{itemRecord['Name']}": 1}}}

            setData = {"HP" : char["HP"]}
            statSplit = None
            statsAffected = 'Stat Bonuses' in itemRecord or ("Predecessor" in itemRecord and 'Stat Bonuses' in itemRecord["Predecessor"])
            
            # For the stat books, this will increase the characters stats permanently here.
            if 'Attunement' not in itemRecord and statsAffected:
                if 'Max Stats' not in char:
                    char['Max Stats'] = {'STR':20, 'DEX':20, 'CON':20, 'INT':20, 'WIS':20, 'CHA':20}
                    
                if "Predecessor" in itemRecord:
                    upgrade_stage = char["Predecessor"][itemRecord['Name']]["Stage"]
                    # statSplit format: MAX STAT +X
                    statSplit = itemRecord["Predecessor"]['Stat Bonuses'][upgrade_stage].split(' +')
                else:
                    statSplit = itemRecord['Stat Bonuses'].split(' +')
                
                maxSplit = statSplit[0].split(' ')
                oldStat = char[maxSplit[1]]

                #Increase stats from Manual/Tome and add to max stats. 
                if "MAX" in statSplit[0]:
                    char[maxSplit[1]] -= int(statSplit[1]) 
                    char['Max Stats'][maxSplit[1]] -= int(statSplit[1]) 

                setData[maxSplit[1]] = int(char[maxSplit[1]])
                setData['Max Stats'] = char['Max Stats']       
                # If the stat increased was con, recalc HP
                # The old CON is subtracted, and new CON is added.
                # If the player can't destroy magic items, this is done here, otherwise... it will need to be done in $info.
                if 'CON' in maxSplit[1]:
                    char['HP'] -= ((int(oldStat) - 10) // 2) * char['Level']
                    char['HP'] += ((int(char['CON']) - 10) // 2) * char['Level']
                    setData['HP'] = char['HP']            
                
            elif 'Attuned' in char  and 'Attunement' in itemRecord and statsAffected:
                attunements = char['Attuned'].split(", ")
                # Find if the item is currently attuned to inorder to update the stat bonus, if not this will error at the remove step and result in no change
                try:
                    index = list([a.split("[")[0].strip() for a in attunements]).index(itemRecord["Name"])
                    attunements.pop(index)
                    setData["Attuned"] = ", ".join(attunements)
                except Exception as e:
                    pass
            elif 'Attuned' in char  and 'Attunement' in itemRecord and itemRecord["Name"] in char['Attuned']:
                attunements = char['Attuned'].split(", ")
                attunements.remove(itemRecord["Name"])
                setData["Attuned"] = ", ".join(attunements)
            entry["fields"]["$set"].update(setData)

            if("Grouped" in itemRecord):
                groupedPair = itemRecord["Grouped"]+" : "+itemRecord["Name"]
                updatedGrouped = list(char["Grouped"])
                updatedGrouped.remove(groupedPair)
                entry["fields"]["$set"]["Grouped"] = updatedGrouped
                
            if("Predecessor" in itemRecord):
                del char["Predecessor"][itemRecord['Name']]
                entry["fields"]["$set"]["Predecessor"] = char["Predecessor"]
            
            returnData.append(entry)
        return returnData, playerIDs
            
    async def doubleVerify(self, ctx, embedMsg):
        def apiEmbedCheck(r, u):
            sameMessage = False
            if embedMsg.id == r.message.id:
                sameMessage = True
            return ((str(r.emoji) == '❌') or (str(r.emoji) == '✅')) and u == ctx.author and sameMessage
            
        await embedMsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
        except asyncio.TimeoutError:
            #stop if no response was given within the timeframe
            await embedMsg.edit(conten='Timed out! Try using the command again.')
            return False
        else:
            #stop if the cancel emoji was given
            if tReaction.emoji == '❌':
                await embedMsg.edit(embed=None, content=f"Command cancelled.")
                await embedMsg.clear_reactions()
                return False
            elif tReaction.emoji == '✅':
                await embedMsg.clear_reactions()
            else:
                await embedMsg.edit(embed=None, content=f"Command cancelled. Unexpected reaction given.")
                return False
        await embedMsg.edit(content=f"Since this process is irreversible, ARE YOU SURE?\n No: ❌\n Yes: ✅")
        
        await embedMsg.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=apiEmbedCheck, timeout=60)
        except asyncio.TimeoutError:
            #stop if no response was given within the timeframe
            await embedMsg.edit(content='Timed out! Try using the command again.')
            return False
        else:
            #stop if the cancel emoji was given
            if tReaction.emoji == '❌':
                await embedMsg.edit(embed=None, content=f"Command cancelled.")
                await embedMsg.clear_reactions()
                return False
            elif tReaction.emoji == '✅':
                await embedMsg.clear_reactions()
            else:
                await embedMsg.edit(embed=None, content=f"Command cancelled. Unexpected reaction given.")
                return False
        return True
    
    @commands.group()
    async def react(self, ctx):	
        pass
    
    #this function allows you to specify a channel and message and have the bot react with a given emote
    #Not tested with emotes the bot might not have access to
    @react.command()
    @admin_or_owner()
    async def add(self, ctx, channel: int, msg: int, emote: str):
        ch = ctx.guild.get_channel(channel)
        message = await ch.fetch_message(msg)
        await message.add_reaction(emote)
        await ctx.message.delete()
    
    
    @commands.command()
    @admin_or_owner()
    async def updateSettings(self, ctx):
        try:
            settingsRecord.update(list(db.settings.find())[0])
            await ctx.channel.send(content=f"Settings have been updated from the DB.")
    
        except Exception as e:
            traceback.print_exc()
    
    @commands.command()
    @commands.has_any_role("Mod Friend")
    async def xfer(self, ctx, system, char_name, level : int, cp :float, user, items =""):
        system = system.upper()
        if system not in ["5E", "5R"]:
            ctx.channel.send("System must be 5E or 5R.")
            return
        msg = ctx.message
        rewardList = msg.raw_mentions
        
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user to hand out a reward item.") 
            return
        rewardUser = rewardList[0]

        levelCP = (((level - 5) * 8) + 16)
        if level < 5:
            levelCP = ((level - 1) * 4)
        cp += levelCP
        level = 1
        maxCP = 4
        while cp >= maxCP and level <20:
            cp -= maxCP
            level += 1
            if level > 4:
              maxCP = 10

        char_dict = {
          'User ID': str(rewardUser),
          'Name': char_name,
          'Level': level,
            'System': system,
          'HP': 0,
          'Class': {"Friend": {"Level": level, "Subclass": None}},
          'Race': "Friend",
          'Background': "D&D Friend",
          'Stats': {'STR': 0,
                    'DEX': 0,
                    'CON': 0,
                    'INT': 0,
                    'WIS': 0,
                    'CHA': 0 },
          'CP' : cp,
          'GP': 0,
          'Magic Items': {},
          'Consumables': {},
          'Feats': [],
          'Inventory': {},
          'Games': 0,
          'Respecc' : "Transfer"
        }

        items = items.strip()
        consumablesList = []
        if items != "":
            consumablesList = items.split(',')
        core: InteractionCore = InteractionCore(ctx, None, system=system)
        rewardItemsList = {"Magic Items": [], "Consumables": [], "Inventory": []}
        for query in consumablesList:
            item_record, core = await find_reward_item(core, query, level)
            if not core.isActive():
                return None
            if core.hasError():
                await ctx.channel.send(content=core.showErrors())
                return None
            #if no item could be found, return the unchanged parameters and inform the user
            if not item_record:
                await ctx.channel.send(f'**{query}** does not seem to be a valid reward item.')
                return None
            rewardItemsList[item_record["Type"]].append(item_record)

        for key, values in rewardItemsList.items():
            for item in values:
                add_to_inventory(char_dict[key], item["Name"], 1, "CREATE")
        try:
            db.players.insert_one(char_dict)
            await ctx.channel.send(content=f"Transfer Character has been created.")
    
        except Exception as e:
            traceback.print_exc()
    
    @commands.has_any_role("Mod Friend")
    @commands.command()
    async def setNoodles(self,ctx, user, noodles: int):
        msg = ctx.message
        rewardList = msg.raw_mentions
        channel = ctx.channel
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user to hand out a reward item.") 
            #return the unchanged parameters
            return 
        usersCollection = db.users
        usersCollection.update_one({"User ID": str(rewardList[0])}, {"$set" : {"Noodles" : noodles}, "$inc" : {"Games" : 0}}, upsert= True)
        await channel.send(f"Noodles set for <@!{rewardList[0]}>")
    
    @commands.has_any_role("Bot Friend", "A d m i n")
    @commands.command()
    async def addDoubles(self,ctx, user, count: int):
        msg = ctx.message
        rewardList = msg.raw_mentions
        channel = ctx.channel
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user.") 
            #return the unchanged parameters
            return 
        usersCollection = db.users
        usersCollection.update_one({"User ID": str(rewardList[0])}, {"$inc" : {"Double" : count}})
        await channel.send(f"Increased Double Rewards for <@{rewardList[0]}> by {count}")

    @commands.has_any_role("Bot Friend", "A d m i n")
    @commands.command()
    async def addTime(self,ctx, user, time: int):
        msg = ctx.message
        rewardList = msg.raw_mentions
        channel = ctx.channel
        # if nobody was listed, inform the user
        if rewardList == list():
            await ctx.channel.send(content=f"I could not find any mention of a user.") 
            #return the unchanged parameters
            return 
        usersCollection = db.users
        usersCollection.update_one({"User ID": str(rewardList[0])}, {"$inc" : {"Time Bank" : time}})
        await channel.send(f"Increased Time Bank for <@{rewardList[0]}> by {time}")
    
    @commands.command()
    @admin_or_owner()
    async def giveRewards(self, ctx, name, user, cp: float, items=""):
        msg = ctx.message
        reward_list = msg.raw_mentions
        guild = ctx.guild
        
        # if nobody was listed, inform the user
        if reward_list == list():
            await ctx.channel.send(content=f"I could not find any mention of a user to hand out rewards.") 
            return None
        # get the first user mentioned
        reward_user = guild.get_member(reward_list[0])
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, name, author_check=reward_user)
        if not char_dict:
            await ctx.channel.send(content=f"I could not find {name} in the DB.")
            return None
        # character level
        level = int(char_dict['Level'])
        # Uses calculateTreasure to determine the rewards from the quest based on the character
        treasure_array  = calculateTreasure(level, char_dict["CP"], cp*3600)
        increment = {"GP": treasure_array[2], "CP": treasure_array[0]}
        increment.update(treasure_array[1])
        items = items.strip()
        reward_queries = []
        if items != "":
            reward_queries = items.split(',')
        reward_items = {"Magic Items": [], "Consumables": [], "Inventory": []}
        for query in reward_queries:
            item_record, core = await find_reward_item(core, query, level)
            if not core.isActive():
                return None
            if core.hasError():
                await ctx.channel.send(content=core.showErrors())
                return None
            #if no item could be found, return the unchanged parameters and inform the user
            if not item_record:
                await ctx.channel.send(f'**{query}** does not seem to be a valid reward item.')
                return None
            reward_items[item_record["Type"]].append(item_record)

        for item in reward_items["Consumables"]:
            add_to_dictionary(increment, f"Consumables.{item['Name']}.REWARD", 1)
        for item in reward_items["Inventory"]:
            add_to_dictionary(increment, f"Inventory.{item['Name']}.REWARD", 1)
        magic_items = char_dict["Magic Items"]
        for item in reward_items["Magic Items"]:
            name = item["Name"]
            already_had_it = name in magic_items
            add_to_inventory(magic_items, name, 1, "REWARD")
            if not already_had_it and "Attunement" in item:
                magic_items[name]["Attunement"] = item["Attunement"]
                magic_items[name]["Attuned"] = False
        try:
            db.players.update_one({"_id": char_dict["_id"]}, {"$set": magic_items, "$inc": increment})
            await ctx.channel.send(content=f"Rewards have been given.")
        except Exception as e:
            traceback.print_exc()
    
    #Allows the sending of messages
    @commands.command()
    @admin_or_owner()
    async def send(self, ctx, channel: int, *, msg: str):
        ch = ctx.guild.get_channel(channel)
        await ch.send(content=msg)
    
        
    @commands.command()
    @admin_or_owner()
    async def killbot(self, ctx):
        await self.bot.close()
    
    @commands.command()
    @admin_or_owner()
    async def reload(self, ctx, cog: str):
        
        try:
            await self.bot.reload_extension('cogs.'+cog)
            print(f"{cog} has been reloaded.")
            await ctx.channel.send(cog+" has been reloaded")
        except commands.ExtensionNotLoaded as e:
            try:
                await self.bot.load_extension("cogs." + cog)
                print(f"{cog} has been added.")
                await ctx.channel.send(cog+" has been loaded for the first time")
            except (discord.ClientException, ModuleNotFoundError, commands.ExtensionNotFound):
                await ctx.channel.send(f'Failed to load extension {cog}.')
                traceback.print_exc()
        except Exception as e:
            await ctx.channel.send(f'Failed to load extension {cog}.')
            traceback.print_exc()

    @commands.command()
    @commands.has_any_role("Mod Friend", "Bot Friend", "A d m i n")
    async def status(self, ctx):
        contents = []
        settings_text = ""
        settings_text += f'Event: {settingsRecord["Event"]}\n'
        settings_text += f'DDMRW: {settingsRecord["ddmrw"]}\n'
        contents.append(("Settings", settings_text, False))
        liners_text = ""
        liners_text += f'Craft: {len(liner_dic["Craft"])}\n'
        liners_text += f'Find: {len(liner_dic["Find"])}\n'
        liners_text += f'Meme: {len(liner_dic["Meme"])}\n'
        liners_text += f'Money: {len(liner_dic["Money"])}\n'
        contents.append(("Liner Count", liners_text, False))
        await paginate(ctx, self.bot, f"Bot Status", contents=contents, separator="\n")
        
    @commands.command()
    @commands.has_any_role("Mod Friend", "Bot Friend", "A d m i n")
    async def roomData(self, ctx):
        data = list(map(lambda x: x["Channel"],list(db.logdata.find(
               {"Status": "Approved"}
            ))))
        counted = collections.Counter(data)
        counter_list = sorted(list(counted.keys()))
        
        contents = []
        counter_text = "\n".join([f"{key.capitalize()}: {counted[key]}" for key in counter_list])
        contents.append(("Counts by Name", f"{counter_text}", False, True))
        counter_list = sorted(counter_list, key= lambda x: counted[x], reverse = True)
        counter_text = "\n".join([f"{key.capitalize()}: {counted[key]}" for key in counter_list])
        contents.append(("Counts by Value", f"{counter_text}", False, True))
        counter_list = sorted(list(counted.keys()))
        await paginate(ctx, self.bot, f"Game Channel Use", contents=contents, separator="\n")
        
    @commands.command()
    @commands.has_any_role("Bot Friend", "A d m i n")
    async def noodleData(self, ctx):
        channel = ctx.channel
        data = db.users.find({"Noodles": {"$gt": 0}})
        with io.StringIO('\n'.join([f"{entry['User ID']}, {entry['Noodles']}" for entry in data])) as f:
            await channel.send(file=discord.File(f, f"noodles.csv"))
                
    @commands.command()
    @commands.has_any_role("Bot Friend", "A d m i n")
    async def timerData(self, ctx):
        channel = ctx.channel
        with io.StringIO(str(currentTimers)) as f:
            await channel.send(file=discord.File(f, f"data.csv"))
    
    @commands.command()
    @commands.has_any_role("Bot Friend", "A d m i n")
    async def givealltime(self, ctx, amount : int):
        db.users.update_many({}, {"$inc": {"Time Bank": amount}})
        await ctx.channel.send(f"Increased Time Bank for everyone by {amount}")
    
    
    
async def setup(bot):
    await bot.add_cog(Admin(bot))



#### Secret Admin/Dev-only Commands

## Note: these commands are not case-sensitive and are only capitalized to emphasize the name of the commands.

# $removeCharacter "character name"
    # Deletes a character from the database.

# $giveRewards "character name" @user CP "Reward Items"
    # Gives CP and reward items to a character belonging to a specific user.

# $reload <file name> | $reload misc
    # Hot reloads the specific cog file and updates the commands of the cog to the latest local version while resetting cooldowns and variables. This allows you to change anything in the cog folder without requiring a restart.

# $updateSettings
    # Updates the "settingsRecord" variable with the current dnd.settings collection database entry without requiring a restart.

# $session genLog ID
    # Updates the specified session log with the corresponding dnd.logdata collection database entry.

# $printTierItems tier TP
    # Prints a list of magic items in the specified tier and TP.

# $printRewardItems tier
    # Prints a list of reward items in the specified tier.

# $tpUpdate tier TP newTP
    # Updates all magic items in the specified tier and TP to the new TP value.

# $goldUpdate tier TP newGP
    # Updates all magic items int he specified tier and TP to the new GP value.

# $moveItem "item" tier TP
    # Moves the specified magic item to the specified tier and TP and refunds all characters who purchased the item with TP or GP (whichever was spent).
    
# $guild rename "new name" #guild-channel
    # Renames a guild in the following sub-databases: guilds.db (the guild entry itself), players.db (each individual character entry that is part of the guild), stats.db (monthly and lifetime quest tracking), and users.db (which displays the Noodle role used to create the guild).

# $snapGuild #channel
    # Removes the guild entry in guilds.db, refunds all GP spent joining the guild and upgrading guild ranks, and removes all instances of it from individual entries in players.db. It leaves stats untouched and doesn't refund the Guildmaster's Noodle role in guilds.db.

# $generateBoard
    # Posts a list of all users that have a Noodle count in descending order.

# $send channelID message
    # Forces Bot Friend to send a message in the specified channel.

# $react add/remove channelID messageID :emoji:
    # Forces Bot Friend to add or remove a Unicode emoji as a reaction to the specified message within a channel.

# $killbot
    # Forcefully shuts down Bot Friend.




#### Mod-Only Commands

# $permitRespec "character name"
    # Sets a flag in the database for the specified character to allow them to use the `$respec` command once regardless of their level. Will confirm which character if multiple users have a character by that name.

# $permitRaceRespec "character name"
    # Sets a flag in the database for the specified character to allow them to use the `$racerespec` command. Will confirm which character if multiple users have a character by that name. Temporary command (August 2021).

# $raceRespec "character name" "new race" STR DEX CON INT WIS CHA
    # Only functions if `$permitRaceRespec` has been used for the character. Allows the user to respec their character's race, starting ASIs, and any ASIs gained through leveling up. Temporary command (August 2021).
    
# $status
    # Shows the current status of different Bot aspects. Useful for seeing if generally non-visible actions have occured like starting events.
# $roomData
    # Shows the statistic of game room usage by count