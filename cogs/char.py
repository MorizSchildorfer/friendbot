import discord
import pytz
import re
import random
import requests
import asyncio
import io
import collections
from discord.utils import get        
from math import floor
from discord.ext import commands
from bfunc import alphaEmojis, commandPrefix, left,right,back, db, traceBack, cp_bound_array, settingsRecord, bot
from cogs.util import calculateTreasure, callAPI, check_for_char_with_end, paginate, disambiguate, timeConversion, confirm, noodle_roles, findNoodleDataFromRoles, convert_to_seconds, reaction_response_control, InteractionCore, find_reward_item, paginate_options, add_to_inventory, show_inventory, determine_tier, add_to_dictionary, sum_sources, select_inventory_choices, format_classes

def search_magic_item(search: str, items: dict) -> list:
    results = []
    for key in items.keys():
        if search.lower() in key.lower():
            results.append(key)
    return results


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


class Character(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

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
    async def races(self, ctx, system):
        system = system.strip().upper()
        try:
            items = list(db.races.find(
               {"System" : system},
            ))
            race_embed = discord.Embed()
            race_embed.title = f"All Valid Races:\n"
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
                race_embed.add_field(name=i[0], value= i, inline = True)
            await ctx.channel.send(embed=race_embed)
    
        except Exception as e:
            traceback.print_exc()  


    def getLeveLimit(self, roles):
        role_creation_dict = {
            'D&D Friend': 2,
            'Journeyfriend': 3,
            'Elite Friend': 3,
            'True Friend': 3,
            'Ascended Friend': 3
        }
        # Check if level or roles are vaild
        # A set that filters valid levels depending on user's roles
        role_limit = 1
        for d in role_creation_dict.keys():
            if d in roles:
                role_limit = max(role_limit, role_creation_dict[d])

        # If roles are present, add base levels + 1 for extra levels for these special roles.
        if ("Nitro Booster" in roles):
            role_limit += 1

        if ("Bean Friend" in roles):
            role_limit += 2
            
        for noodle_name, noodle_data in noodle_roles.items():
            if noodle_name in roles:
                role_limit += noodle_data["creation_level_bonus"]
                break
        return role_limit
            
    async def check_parameter(self, ctx, parameter_name, value) -> bool:
        if value:
            return True
        await ctx.channel.send(content=f":warning: The {parameter_name} cannot be blank! Please try again\n")
        self.bot.get_command(ctx.command.name).reset_cooldown(ctx)
        return False
    
    @commands.group(case_insensitive=True)
    async def dnd5e(self, ctx):
        pass
    
    def time_transfer(self, transferInfo: str, level: int, userId: str):
        user_records = db.users.find_one({"User ID": userId})
        error_messages = ""
        cp_transferred = 0
        cp = 0
        if not user_records:
            error_messages += f":warning: I could not find you in the database!\n"
        elif "Time Bank" not in user_records.keys():
            error_messages += f":warning: I could not find you timebank!\n"
        else:
            transferInfo = transferInfo.lower()
            l = list((re.findall('.*?[hm]', transferInfo)))
            total_time = 0
            try:
                for timeItem in l:
                    total_time += convert_to_seconds(timeItem)
            except Exception as e:
                error_messages += f":warning: I could not find a number in your time amount!\n"
                total_time = 0
            if total_time > user_records["Time Bank"]:
                error_messages += f":warning: You do not have enough hours to transfer!\n"
            else:
                if level < 5:
                    max_cp = 4
                else:
                    max_cp = 10
                cp = (total_time // 900) / 4
                cp_transferred = cp
                while cp >= max_cp and level <20:
                    cp -= max_cp
                    level += 1
                    if level > 4:
                        max_cp = 10
        return level, cp, cp_transferred, error_messages
    
    # Stats - Point Buy
    def pointBuy(self, statsArray):
        error_messages = []
        totalPoints = 0
        for s in statsArray:
            if (13-s) < 0:
                totalPoints += ((s - 13) * 2) + 5
            else:
                totalPoints += (s - 8)
                
        if any([s < 8 for s in statsArray]):
            error_messages.append(f":warning: You have at least one stat below the minimum of 8.")
        if any([s > 15 for s in statsArray]):
            error_messages.append(f":warning: You have at least one stat above the maximum of 15.")
        if totalPoints != 27:
            error_messages.append(f":warning: Your stats do not add up to 27 using point buy ({totalPoints}/27). Remember that you must list your stats before applying racial modifiers! Please check your point allocation using this calculator: <https://chicken-dinner.com/5e/5e-point-buy.html>")
        return '\n'.join(error_messages)
    
    async def determineRewardItems(self, core: InteractionCore, rewardItems: list[str], level: int):
        context = core.context
        allRewardItems = []
        for r in rewardItems:
            item_record, core = await find_reward_item(core, r, level)
            if not core.isActive():
                return core, None, None, None
            allRewardItems.append(item_record)
        if core.hasError():
            return core, None, None, None
        allRewardItems.sort(key=lambda x: x["Tier"])
        rewardConsumables = []
        rewardMagics = []
        rewardInv = []
        magic_items = {}
        consumables = {}
        inventory = {}
        
        noodle_name, noodle_data, _  = findNoodleDataFromRoles(context.author.roles)
        tierConsumableCounts = noodle_data["creation_items"].copy()
        if 'Bean Friend' in [role.name for role in context.author.roles]:
            tierConsumableCounts[0] += 2
            tierConsumableCounts[2] += 2
        startCounts = tierConsumableCounts.copy()
        for item in allRewardItems:
            count_balance = 2
            if item['Minor/Major'] == 'Minor' and item["Type"] == 'Magic Items':
                count_balance = 0
            elif item['Minor/Major'] == 'Minor':
                count_balance = 1
            i = count_balance
            while i < len(tierConsumableCounts):
                if tierConsumableCounts[i] > 0 or i == len(tierConsumableCounts)-1:
                    tierConsumableCounts[i] -= 1
                    break
                i += 1
            
            if item["Type"] == 'Consumables':
                rewardConsumables.append(item)
            elif item["Type"] == 'Magic Items':
                rewardMagics.append(item)
            else:
                rewardInv.append(item)

        if any([count < 0 for count in tierConsumableCounts]):
            core.addError(f":warning: You do not have the right roles for these reward items. You can only choose **{startCounts[2]}** Majors, **{startCounts[1]}** Minors and, **{startCounts[0]}** Non-Consumables")
        else:
            for r in rewardConsumables:
                add_to_inventory(consumables, r["Name"], 1, "CREATE")
            for r in rewardMagics:
                name = r["Name"]
                add_to_inventory(magic_items, name, 1, "CREATE")
                if "Attunement" in r:
                    magic_items[name]["Attunement"] = r["Attunement"]
                    magic_items[name]["Attuned"] = False
            for r in rewardInv:
                add_to_inventory(inventory, r["Name"], 1, "CREATE")
                
        return core, magic_items, consumables, inventory
        
    def nameVerification(self, core: InteractionCore, name: str, author):
        # Name should be less than 65 chars
        if len(name) > 64:
            core.addError(":warning: Your character's name is too long! The limit is 64 characters.)")

        # Reserved for regex, lets not use these for character names please
        invalid_chars = ["[", "]", "?", "“","”", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|"]

        for i in invalid_chars:
            if i in name:
                core.addError(f":warning: Your character's name cannot contain `{i}`. Please revise your character name.")
        if core.hasError():
            pass
        else:
            query = name
            query = query.replace('(', '\\(')
            query = query.replace(')', '\\)')
            query = query.replace('.', '\\.')
            playersCollection = db.players
            userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' } }))
            if userRecords != list():
                core.addError(f":warning: You already have a character by the name of ***{name}***! Please use a different name.")
        return core
    
    async def handle_class(self, core: InteractionCore, class_string: str, level: int, inventory: dict):
        class_string = class_string.strip()
        # Check Character's class
        starting_class = None
        classes = {}
        total_level = 0
        broken = []
        is_multi_class = '/' in class_string
        # If there's a /, character is creating a multiclass character
        if is_multi_class:
            multiclass_list = class_string.replace(' ', '').split('/')
            # Iterates through the multiclass list 
            for description in multiclass_list:
                # Separate level and class
                level_search = re.search('\d+', description)
                if not level_search:
                    core.addError(":warning: You are missing the level for your multiclass class. Please check your format.")
                    break
                class_level = level_search.group()
                class_name = description[:len(description) - len(class_level)]
                # Todo is there a better way?
                class_entry, core = await callAPI(core, 'classes', class_name)
                if not class_entry:
                    broken.append(class_name)
                    continue
                class_name = class_entry["Name"]
                if starting_class is None:
                    starting_class = class_name
                
                # Check for class duplicates (ex. Paladin 1 / Paladin 2 = Paladin 3)
                if class_name in classes:
                    classes[class_name]["Level"] += int(class_level)
                else:
                    classes[class_name] = {'Class': class_entry, 'Level': int(class_level), 'Subclass': None}
                total_level += int(class_level)
        else:
            starting_class = class_string
            single_class, core = await callAPI(core, 'classes', starting_class)
            if single_class:
                classes[single_class["Name"]] = {'Class':single_class, 'Level': int(level), 'Subclass': None}
            else:
                broken.append(starting_class)
        if len(broken)>0:
            core.addError(f':warning: **{broken}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.')
        if is_multi_class and total_level != level:
            print(total_level, level)
            core.addError(':warning: Your classes do not add up to the total level. Please double-check your multiclasses.')
        if not core.hasError():
            is_multi_class = len(classes) > 1
            starting_entry = classes[starting_class]['Class']
            if 'Starting Equipment' in starting_entry:
                options = []
                for item in starting_entry['Starting Equipment']:
                    choices = {"Choice": True}
                    def amount_text(v):
                        count = 1
                        if type(v) == int:
                            count = v
                        return count
                    for seList in item:
                        # Todo: add amounts as well
                        choice_text = ", ".join([f"{k} x{amount_text(v)}" for k, v in seList.items()])
                        print("choice_text", choice_text)
                        choices[choice_text] = seList
                    options.append({"Starting Equipment": choices})
                core, inventory = await select_inventory_choices(core, options, inventory, "CREATE")
            # Subclass
            for class_name, entry in classes.items():
                entry['Subclass'] = None
                if not core.hasError() and int(entry['Class']['Subclass Level']) <= int(entry['Level']):
                    subclasses = entry['Class']['Subclasses']
                    core, subclass = await self.choose_subclass(core, subclasses, entry['Class']['Name'])
                    if not subclass:
                        core.cancel()
                    entry['Subclass'] = subclass
        if "Wizard" in classes:
            char_dict['Free Spells'] = [6, 0, 0, 0, 0, 0, 0, 0, 0]
            index = 0
            for i in range(2, classes["Wizard"]['Level'] + 1):
                if i % 2 != 0:
                    index += 1
                char_dict['Free Spells'][index] += 2

        return core, classes, starting_class

    #TODO
    async def selectClassFeats(self, core: InteractionCore, classes: dict, char_dict: dict):
        feat_levels = []
        for class_name, record in classes.items():
            if record['Level'] > 3:
                feat_levels.append(4)
            if 'Fighter' in class_name and int(record['Level']) > 5:
                feat_levels.append(6)
            if record['Level'] > 7:
                feat_levels.append(8)
            if 'Rogue' in class_name and int(record['Level']) > 9:
                feat_levels.append(10)
            if record['Level'] > 11:
                feat_levels.append(12)
            if 'Fighter' in class_name and record['Level'] > 13:
                feat_levels.append(14)
            if record['Level'] > 15:
                feat_levels.append(16)
            if record['Level'] > 18:
                feat_levels.append(19)
        core, _, char_dict = await self.choose_feat(core, classes, feat_levels, char_dict)
        return core, char_dict

    def check_multiclass(self, core, classes: dict, stats: dict):
        for class_name, entry in classes.items():
            failed_requirement = self.check_multiclass_requirement(entry, stats)
            if req_fulfill_list is not None:
                req_fulfill_list.append(failed_requirement)
            if len(req_fulfill_list) > 0:
                core.addError(f":warning: In order to multiclass to or from **{class_name}** you need at least **{entry['Class']['Multiclass']}**. Your character only has **{' and '.join(req_fulfill_list)}**!")
        return core

    def check_multiclass_requirement(self, entry, stats):
        stat_req = entry['Class']['Multiclass'].split(' ')
        requirements = entry['Class']['Multiclass']
        failed_requirement = None
        if requirements != 'None':
            if '/' in requirements:
                stat_requirements = stat_req[0].split('/')
                issues = []
                for s in stat_requirements:
                    if int(stats[s]) < int(stat_req[1]):
                        issues.append(f"{s} {stats[s]}")
                if len(issues) == len(stat_requirements):
                    failed_requirement = "or".join(issues)
            elif '+' in requirements:
                stat_req[0] = stat_req[0].split('+')
                for s in stat_req[0]:
                    if int(stats[s]) < int(stat_req[1]):
                        failed_requirement = f"{s} {stats[s]}"
            else:
                if int(stats[stat_req[0]]) < int(stat_req[1]):
                    failed_requirement = f'{stat_req[0]} {stats[stat_req[0]]}'
        return failed_requirement

    @is_log_channel()
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @commands.command(aliases=['cn'])
    async def create(self, ctx, system, name, level: int, race, character_class, bg, sStr : int, sDex :int, sCon:int, sInt:int, sWis:int, sCha :int, consumes="", timeTransfer = None):
        system = system.strip().upper()
        command_name = ctx.command.name
        if system not in ["5E", "5R"]:
            await ctx.channel.send(content=f":warning: Unknown System: {system}. Options: 5E, or 5R")
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        
        name = name.strip()
        channel = ctx.channel
        print(system, name, level, race, character_class, bg, sStr, sDex, sCon, sInt, sWis, sCha)
        # Prevents name, level, race, class, background from being blank. Resets infinite cooldown and prompts
        if not (await self.check_parameter(ctx, "name", name)
                and await self.check_parameter(ctx, "level", level)
                and await self.check_parameter(ctx, "race", race)
                and await self.check_parameter(ctx, "class", character_class)
                and await self.check_parameter(ctx, "background", bg)):
            return None
        author = ctx.author
        roles = [r for r in author.roles]
        char_embed = discord.Embed()
        char_embed.set_author(name=author.display_name, icon_url=author.display_avatar)
        char_embed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        lvl = int(level)
        stats = {
          'STR': sStr,
          'DEX': sDex,
          'CON': sCon,
          'INT': sInt,
          'WIS': sWis,
          'CHA': sCha}
        char_dict = {
          'System': system,
          'User ID': str(author.id),
          'Name': name,
          'Level': lvl,
          'HP': 0,
          'Class': {},
          'Background': bg,
          'Stats': stats,
          'Alignment': 'Unknown',
          'CP' : 0,
          'GP': 0,
          'Magic Items': {},
          'Consumables': {},
          'Feats': [],
          'Inventory': {},
          'Stat Bonuses': {},
          'Games': 0
        }
        inventory = {}
        core = InteractionCore(ctx, None, char_embed, system)
        core = self.nameVerification(core, name, author)
        role_limit = self.getLeveLimit(list([role.name for role in roles]))
        if lvl > role_limit:
            core.addError(f":warning: You cannot create a character of **{lvl}**! You do not have the correct role and are limited to level **{role_limit}**!")
        
        # Checks CP
        cp = 0
        cp_transferred = 0
        time_transfer_success = False
        if timeTransfer:
            lvl, cp, cp_transferred, error_messages = self.time_transfer(timeTransfer, lvl, str(author.id))
            core.addError(error_messages)
        
        char_dict['CP'] = cp
        
        level_cp = (((lvl-5) * 10) + 16)
        if lvl < 5:
            level_cp = ((lvl -1) * 4)
        cp_tp_gp_array = calculateTreasure(1, 0, (level_cp+cp)*3600)
        totalGP = cp_tp_gp_array[2]
        tp_bank = cp_tp_gp_array[1]
        char_dict["GP"] += totalGP
        if lvl > 20:
            lvl = 20
            char_dict["Level"] = 20
        point_buy_error = self.pointBuy(list(stats.values()))
        core.addError(point_buy_error)
        
        # Reward Items
        if consumes.strip() != "":
            reward_items = consumes.strip().split(',')
            core, magic_items, consumables, inventory = await self.determineRewardItems(core, reward_items, lvl)
            char_dict["Magic Items"] = magic_items
            char_dict["Consumables"] = consumables
                      
        # check race
        race_record, core = await callAPI(core, 'races', race)
        if not core.isActive():
            return None
        if not race_record:
            core.addError(f'• {race} isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.')
        else:
            char_dict['Race'] = race_record['Name']
            if "Extra Feat" in race_record:
                core, feats_chosen, char_dict = await self.choose_feat(core, {}, ["Extra Feat"], char_dict)

                if not core.isActive():
                    return core, None

        core, classes, starting_class = await self.handle_class(core, character_class, lvl, inventory)
        char_dict["Class"] = {name: {"Subclass": entry["Subclass"], "Level": entry["Level"]} for name, entry in classes.items()}
        char_dict["Starting Class"] = starting_class
        # check bg and gp
        bRecord, core = await callAPI(core, 'backgrounds', bg)
        stat_bonus_record = race_record
        if system == '5R':
            stat_bonus_record = bRecord
        if not bRecord:
            core.addError(f':warning: **{bg}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n')
        if not core.hasError():
            char_dict['Background'] = bRecord['Name']
            backgroundGp = bRecord["GP"]
            char_dict["GP"] += backgroundGp
            core, inventory = await select_inventory_choices(core, bRecord["Equipment"], inventory, "CREATE")
            if system == '5R':
                char_dict["Feats"].append(bRecord["Feat"])

        # Stats - Point Buy
        if not core.hasError():
            core, stats = await self.starting_stat_modification(core, [stats["STR"], stats["DEX"], stats["CON"], stats["INT"], stats["WIS"], stats["CHA"]], stat_bonus_record)
            if not core.isActive():
                return None
        
        #Stats - Feats
        if not core.hasError():
            core, char_dict = await self.selectClassFeats(core, classes, char_dict)

        #HP
        hp_records = []
        for class_name, entry in classes.items():
            hp_records.append({'Level':entry['Level'], 'Subclass': entry['Subclass'], 'Name': class_name, 'Hit Die Max': entry['Class']['Hit Die Max'], 'Hit Die Average':entry['Class']['Hit Die Average']})

        # Multiclass Requirements
        if len(classes) > 1:
            # TODO: pass a new dictionary
            core = self.check_multiclass(core, classes, char_dict)
        if not core.isActive() or core.hasError():
            await core.delete()
            if not core.isActive():
                core.addError('Command cancelled')
            error_text = '\n'.join(core.errors)
            main_message = f":warning: Command aborted. Reasons: {error_text}"
            await ctx.channel.send(main_message)
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None

        display_hp = 0
        stat_bonuses, max_stat_bonuses, stat_setters = self.calculate_stat_bonuses(char_dict, system)
        if hp_records:
            hp: int = self.calculate_base_hp(classes, char_dict, lvl)
            char_dict['HP'] = hp
            display_hp = hp + self.calculate_bonus_hp(lvl, stats["CON"], stat_bonuses, max_stat_bonuses, stat_setters)
        
        level = char_dict['Level']
        if level == 20:
            tier = 5
        else:
            tier = determine_tier(level)
        core.embed.clear_fields()    
        core.embed.title = f"{char_dict['Name']} (Lv {level}): {char_dict['CP']}/{cp_bound_array[tier-1][1]} CP"
        class_summary = format_classes(char_dict["Class"])
        core.embed.description = f"**Race**: {char_dict['Race']}\n**Class**: {class_summary}\n**Background**: {char_dict['Background']}\n**Max HP**: {display_hp}\n**GP**: {char_dict['GP']} "

        for x in range(1,6):
            tier_key = f'T{x} TP'
            if tier_key in tp_bank:
                char_dict[tier_key] = tp_bank[tier_key]
                core.embed.add_field(name=f':warning: Unused T{x} TP', value=char_dict[f'T{x} TP'], inline=True)
        if len(char_dict['Magic Items']) > 0:
            core.embed.add_field(name='Magic Items', value=", ".join(show_inventory(char_dict['Magic Items'])), inline=False)
        if len(char_dict['Consumables']) > 0:
            core.embed.add_field(name='Consumables', value=", ".join(show_inventory(char_dict['Consumables'])), inline=False)
        core.embed.add_field(name='Feats', value=", ".join(char_dict['Feats']), inline=True)
        stat_string = ""
        for stat_name, stat_value in stats.items():
            _, description = self.determine_stat(stat_value, stat_name, max_stat_bonuses, stat_bonuses, stat_setters)
            stat_string += description + " "

        core.embed.add_field(name='Stats', value=stat_string, inline=False)

        if 'Wizard' in char_dict['Class']:
            core.embed.add_field(name='Spellbook (Wizard)', value=f"At 1st level, you have a spellbook containing six 1st-level Wizard spells of your choice (+2 free spells for each wizard level). Please use the `{commandPrefix}shop copy` command." , inline=False)
            fsString = ""
            fsIndex = 0
            for el in char_dict['Free Spells']:
                if el > 0:
                    fsString += f"Level {fsIndex+1}: {el} free spells\n"
                fsIndex += 1

            if fsString:
                core.embed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)
        char_dict["Inventory"] = inventory
        if len(inventory) > 0:
            inventory_string = "\n".join(show_inventory(inventory))
            core.embed.add_field(name='Starting Equipment', value=inventory_string, inline=False)

        core.embed.set_footer(text=None)
        await core.send("**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel.")
        
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, ['✅', '❌']), timeout=60)
        except asyncio.TimeoutError:
            await core.delete()
            await channel.send(f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        else:
            await  core.message.clear_reactions()
            if tReaction.emoji == '❌':
                core.cancel()
                await core.message.edit(embed=None, content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await  core.message.clear_reactions()
                self.bot.get_command(command_name).reset_cooldown(ctx)
                return None

        stats_collection = db.stats
        stat_increase = {f"Background.{char_dict['Background']}": 1, f"Race.{char_dict['Race']}": 1}
        for feat in char_dict["Feats"]:
            stat_increase[f"Feats.{feat}"] = 1
        try:
            db.players.insert_one(char_dict)
            if time_transfer_success:
                db.users.update_one({"User ID": str(author.id)}, {"$inc" : {"Time Bank": -cpTransfered *3600}})
                await self.level_check(ctx, char_dict["Level"], char_dict["Name"])
            stats_collection.update_one({'Life':1, 'System': system}, {"$inc": stat_increase}, upsert=True)
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            core.embed.set_footer(text= None)
            await core.send(f"Congratulations! :tada: You have created ***{char_dict['Name']}***!")
            await core.message.clear_reactions()
        self.bot.get_command(command_name).reset_cooldown(ctx)
        return None

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command(aliases=['rs'])
    async def respec(self, ctx, name, new_name, race, character_class, bg, sStr : int, sDex :int, sCon:int, sInt:int, sWis:int, sCha :int):
        new_name = new_name.strip()
        command_name = ctx.command.name
        name = name.strip()
        channel = ctx.channel
        # Prevents name, new_name, race, class, background from being blank. Resets infinite cooldown and prompts
        if not (await self.check_parameter(ctx, "name", name)
                and await self.check_parameter(ctx, "new name", new_name)
                and await self.check_parameter(ctx, "race", race)
                and await self.check_parameter(ctx, "class", character_class)
                and await self.check_parameter(ctx, "background", bg)):
            return None
        author = ctx.author
        char_embed = discord.Embed()
        char_embed.set_author(name=author.display_name, icon_url=author.display_avatar)
        char_embed.set_footer(text="React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
        stats = {
            'STR': sStr,
            'DEX': sDex,
            'CON': sCon,
            'INT': sInt,
            'WIS': sWis,
            'CHA': sCha}
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        char_remove_key_list = ['Image', 'Spellbook', 'Guild', 'Guild Rank']
        
        guild_name = ""
        
        if "Guild" in char_dict:
            guild_name = char_dict["Guild"]

        for c in char_remove_key_list:
            if c in char_dict:
                del char_dict[c]
        name = char_dict["Name"]
        for key, value in char_dict["Magic Items"]:
            del value["BUY"]
        for key, value in char_dict["Inventory"]:
            del value["BUY"]
            del value["CREATE"]
        for key, value in char_dict["Consumables"]:
            del value["BUY"]
        char_id = char_dict['_id']
        char_dict['GP'] = 0

        lvl = char_dict['Level']
        msg = ""

        if 'Death' in char_dict.keys():
            await core.send(f"You cannot respec a dead character. Use the following command to decide their fate:\n```yaml\n$death \"{char_dict['Name']}\"```")
            return None
        
        # level check
        if lvl > 4 and "Respecc" not in char_dict:
            msg += "• Your character's level is way too high to respec.\n"
            await core.send(msg)
            self.bot.get_command('respec').reset_cooldown(ctx) 
            return None
        if char_dict['Name'] != new_name:
            core = self.nameVerification(core, name, author)
        char_dict['Name'] = new_name

        extra_cp = char_dict['CP']
        char_level = char_dict['Level']

        #todo find a good way to refactor this
        level_cp = (((char_level-5) * 10) + 16)
        if lvl < 5:
            level_cp = ((char_level -1) * 4)
        cp_tp_gp_array = calculateTreasure(1, 0, (level_cp + extra_cp) * 3600)
        total_gp = cp_tp_gp_array[2]
        tp_bank = cp_tp_gp_array[1]
        char_dict["GP"] += total_gp
        if lvl > 20:
            lvl = 20
            char_dict["Level"] = 20
        point_buy_error = self.pointBuy(list(stats.values()))
        core.addError(point_buy_error)

        # check race
        race_record, core = await callAPI(core, 'races', race)
        if not core.isActive():
            return None
        if not race_record:
            core.addError(
                f'• {race} isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.')
        else:
            char_dict['Race'] = race_record['Name']
            if "Extra Feat" in race_record:
                core, feats_chosen, char_dict = await self.choose_feat(core, {}, ["Extra Feat"], char_dict)
                if not core.isActive():
                    return core, None
        inventory = char["Inventory"]
        core, classes, starting_class = await self.handle_class(core, character_class, lvl, inventory)
        char_dict["Class"] = {name: {"Subclass": entry["Subclass"], "Level": entry["Level"]} for name, entry in
                              classes.items()}
        char_dict["Starting Class"] = starting_class
        # check bg and gp
        bRecord, core = await callAPI(core, 'backgrounds', bg)
        if not bRecord:
            core.addError(
                f':warning: **{bg}** isn\'t on the list or it is banned! Check #allowed-and-banned-content and check your spelling.\n')
        if not core.hasError():
            char_dict['Background'] = bRecord['Name']
            char_dict["GP"] += bRecord["GP"]
            char_dict["Feats"] = [bRecord["Feat"]]
            core, inventory = await select_inventory_choices(core, bRecord["Equipment"], inventory, "CREATE")

        stats = {}
        # Stats - Point Buy
        if not core.hasError():
            core, stats = await self.starting_stat_modification(core,
                                                                [stats["STR"], stats["DEX"], stats["CON"], stats["INT"],
                                                                 stats["WIS"], stats["CHA"]], bRecord)
            if not core.isActive():
                return None

        # Stats - Feats
        if not core.hasError():
            core, char_dict = await self.selectClassFeats(core, classes, char_dict)

        # HP
        hp_records = []
        for class_name, entry in classes.items():
            hp_records.append({'Level': entry['Level'], 'Subclass': entry['Subclass'], 'Name': class_name,
                               'Hit Die Max': entry['Class']['Hit Die Max'],
                               'Hit Die Average': entry['Class']['Hit Die Average']})

        # Multiclass Requirements
        if len(classes) > 1:
            # TODO: pass a new dictionary
            core = self.check_multiclass(core, classes, char_dict)
        if not core.isActive() or core.hasError():
            await core.delete()
            if not core.isActive():
                core.addError('Command cancelled')
            error_text = '\n'.join(core.errors)
            main_message = f":warning: Command aborted. Reasons: {error_text}"
            await ctx.channel.send(main_message)
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None

        display_hp = 0
        stat_bonuses, max_stat_bonuses, stat_setters = self.calculate_stat_bonuses(char_dict, system)
        if hp_records:
            hp: int = self.calculate_base_hp(classes, char_dict, lvl)
            char_dict['HP'] = hp
            display_hp = hp + self.calculate_bonus_hp(lvl, stats["CON"], stat_bonuses, max_stat_bonuses, stat_setters)

        level = char_dict['Level']
        if level == 20:
            tier = 5
        else:
            tier = determine_tier(level)
        core.embed.clear_fields()
        core.embed.title = f"{char_dict['Name']} (Lv {level}): {char_dict['CP']}/{cp_bound_array[tier - 1][1]} CP"
        class_summary = format_classes(char_dict["Class"])
        core.embed.description = f"**Race**: {char_dict['Race']}\n**Class**: {class_summary}\n**Background**: {char_dict['Background']}\n**Max HP**: {display_hp}\n**GP**: {char_dict['GP']} "

        for x in range(1, 6):
            tier_key = f'T{x} TP'
            if tier_key in tp_bank:
                char_dict[tier_key] = tp_bank[tier_key]
                core.embed.add_field(name=f':warning: Unused T{x} TP', value=char_dict[f'T{x} TP'], inline=True)
        if len(char_dict['Magic Items']) > 0:
            core.embed.add_field(name='Magic Items', value=", ".join(show_inventory(char_dict['Magic Items'])),
                                 inline=False)
        if len(char_dict['Consumables']) > 0:
            core.embed.add_field(name='Consumables', value=", ".join(show_inventory(char_dict['Consumables'])),
                                 inline=False)
        core.embed.add_field(name='Feats', value=", ".join(char_dict['Feats']), inline=True)
        stat_string = ""
        for stat_name, stat_value in stats.items():
            _, description = self.determine_stat(stat_value, stat_name, max_stat_bonuses, stat_bonuses, stat_setters)
            stat_string += description + " "

        core.embed.add_field(name='Stats', value=stat_string, inline=False)

        if 'Wizard' in char_dict['Class']:
            core.embed.add_field(name='Spellbook (Wizard)',
                                 value=f"At 1st level, you have a spellbook containing six 1st-level Wizard spells of your choice (+2 free spells for each wizard level). Please use the `{commandPrefix}shop copy` command.",
                                 inline=False)
            free_spell_string = ""
            free_spell_index = 0
            for el in char_dict['Free Spells']:
                if el > 0:
                    free_spell_string += f"Level {free_spell_index + 1}: {el} free spells\n"
                free_spell_index += 1

            if free_spell_string:
                core.embed.add_field(name='Free Spellbook Copies Available', value=free_spell_string, inline=False)
        char_dict["Inventory"] = inventory
        if len(inventory) > 0:
            inventory_string = "\n".join(show_inventory(inventory))
            core.embed.add_field(name='Starting Equipment', value=inventory_string, inline=False)

        core.embed.set_footer(text=None)
        await core.send(
            "**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel.")
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']), timeout=60)
        except asyncio.TimeoutError:
            await core.delete()
            await channel.send(
                f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        else:
            await  core.message.clear_reactions()
            if tReaction.emoji == '❌':
                core.cancel()
                await core.message.edit(embed=None,
                                        content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"system\" \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await  core.message.clear_reactions()
                self.bot.get_command(command_name).reset_cooldown(ctx)
                return None
        try:
            if len(guild_name)>0:
                guild_members = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": guild_name, '$options': 'i' }}))
                # If there is only one of user's character in the guild remove the role.
                if len(guild_members) <= 1:
                    await author.remove_roles(get(guild.roles, name = guild_name), reason=f" Respecced")
            # Extra to unset
            if "Respecc" in char_dict:
                del char_dict["Respecc"]
            playersCollection.replace_one({'_id': char_id}, char_dict, upsert=True)
            
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send("Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            await core.send(f"Congratulations! You have respecced your character!")

            await self.level_check(ctx, char_dict["Level"], char_dict["Name"])
        self.bot.get_command(command_name).reset_cooldown(ctx)
        return None

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def applyTime(self, ctx, name, time_transfer: str):
        author = ctx.author
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, name)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        if "GID" in char_dict:
            core.addError(f":warning: Your character is still awaiting rewards!\n")
        if "Death" in char_dict:
            core.addError(f":warning: Your character is still dead!\n")

        _, _, cp_transferred, error_messages = self.time_transfer(time_transfer, char_dict['Level'], str(author.id))
        core.addError(error_messages)
        if core.hasError():
            char_embed.clear_fields()
            char_embed.description = "Command had errors: \n" + "\n".join(core.errors)
            await core.send()
            bot.get_command('applyTime').reset_cooldown(ctx)
            return None
        transferred_time = cp_transferred * 3600
        treasureArray  = calculateTreasure(char_dict["Level"], char_dict["CP"], transferred_time)
        inc_dic = {"GP": treasureArray[2], "CP": treasureArray[0]}
        inc_dic.update(treasureArray[1])
        confirm_embed = discord.Embed()
        confirm_embed.title = f"Please confirm the **{timeConversion(transferred_time, True)}** minute deduction."
        confirm_embed.description = f"\n**{char_dict['Name']}** will receive **{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP**"
        await core.send(embed=confirm_embed)
        decision = await confirm(confirm_message, ctx.author)
        if decision != 1:
            await core.send(f"*Time transfer cancelled*")
            bot.get_command('applyTime').reset_cooldown(ctx)
            return None
        try:
            db.players.update_one({"_id": char_dict["_id"]}, {"$inc": inc_dic})
            db.users.update_one({"User ID": f"{author.id}"}, {"$inc": {f"Time Bank": -transferred_time}})
            await core.send(f"**{char_dict['Name']}** has received **{treasureArray[0]} CP, {sum(treasureArray[1].values())} TP, {treasureArray[2]} GP**")
    
        except Exception as e:
            traceback.print_exc()
            
        bot.get_command('applyTime').reset_cooldown(ctx)
        return None

    @commands.cooldown(1, 5, type=commands.BucketType.user)
    @commands.command()
    async def export(self, ctx, char):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        desired = ["Name", "Consumables", "Magic Items", "Inventory", "Race", "STR", "INT", "CON", "WIS", "DEX", "CHA", "Class", "Spellbook", "GP", "Background", "Level", "Feats"]
        export = {}
        for key in desired:
            if key in charRecords:
                export[key] = charRecords[key]
            else:
                print(key)
        with io.StringIO(f"{export}") as f:
            await channel.send(file=discord.File(f, f"{charRecords['Name']}.json"))
        ctx.command.reset_cooldown(ctx)
        return None

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def retire(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        def retireEmbedCheck(r, u):
            sameMessage = False
            if char_embedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author
        if char_dict:
            charID = char_dict['_id']

            char_embed.title = f"Are you sure you want to retire {char_dict['Name']}?"
            char_embed.description = "✅: Yes\n\n❌: Cancel"
            if not char_embedmsg:
                char_embedmsg = await channel.send(embed=char_embed)
            else:
                await char_embedmsg.edit(embed=char_embed)

            await char_embedmsg.add_reaction('✅')
            await char_embedmsg.add_reaction('❌')
            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=retireEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await char_embedmsg.delete()
                await channel.send(f'Retire cancelled. Try again using the same command:\n```yaml\n{commandPrefix}retire "character name"```')
                self.bot.get_command('retire').reset_cooldown(ctx)
                return
            else:
                await char_embedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await char_embedmsg.edit(embed=None, content=f'Retire cancelled. Try again using the same command:\n```yaml\n{commandPrefix}retire "character name"```')
                    await char_embedmsg.clear_reactions()
                    self.bot.get_command('retire').reset_cooldown(ctx)
                    return
                elif tReaction.emoji == '✅':
                    char_embed.clear_fields()
                    try:
                        playersCollection = db.players
                        
                        deadCollection = db.dead
                        if "Guild" in char_dict:
                            guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": char_dict['Guild'], '$options': 'i' }}))
                            # If there is only one of user's character in the guild remove the role.
                            if (len(guildAmount) <= 1):
                                await author.remove_roles(get(guild.roles, name = char_dict['Guild']), reason=f"Left guild {char_dict['Guild']}")
                        playersCollection.delete_one({'_id': charID})
                        
                        deadCollection.insert_one(char_dict)
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try retiring your character again.")
                    else:
                        if char_embedmsg:
                            await char_embedmsg.clear_reactions()
                            await char_embedmsg.edit(embed=None, content =f"Congratulations! You have retired ***{char_dict['Name']}***. ")
                        else: 
                            char_embedmsg = await channel.send(embed=None, content=f"Congratulations! You have retired ***{char_dict['Name']}***.")

        self.bot.get_command('retire').reset_cooldown(ctx)

    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command()
    async def death(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None

        def retireEmbedCheck(r, u):
            sameMessage = False
            if char_embedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        def deathEmbedCheck(r, u):
            sameMessage = False
            if char_embedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '1️⃣') or (str(r.emoji) == '2️⃣') or (char_dict['GP'] + deathDict["inc"]['GP']  >= gpNeeded and str(r.emoji) == '3️⃣') or (str(r.emoji) == '❌')) and u == author

        if char_dict:
            if 'Death' not in char_dict:
                await channel.send("Your character is not dead. You cannot use this command.")
                self.bot.get_command('death').reset_cooldown(ctx)
                return
            
            deathDict = char_dict['Death']
            charID = char_dict['_id']
            charLevel = char_dict['Level']
            if charLevel < 5:
                gpNeeded = 100
            elif charLevel < 11:
                gpNeeded = 500
            elif charLevel < 17:
                gpNeeded = 750
            elif charLevel < 21:
                gpNeeded = 1000

            char_embed.title = f"Character Death - {char_dict['Name']}"
            char_embed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")

            if char_dict['GP'] + deathDict["inc"]['GP'] < gpNeeded:
                char_embed.description = f"Please choose between these three options for {char_dict['Name']}:\n\n1️⃣: Death - Retires your character.\n2️⃣: Survival - Forfeit rewards and survive.\n3️⃣: ~~Revival~~ - You currently have {char_dict['GP'] + deathDict['inc']['GP']} GP but need {gpNeeded} GP to be revived."
            else:
                char_embed.description = f"Please choose between these three options for {char_dict['Name']}:\n\n1️⃣: Death - Retires your character.\n2️⃣: Survival - Forfeit rewards and survive.\n3️⃣: Revival - Revives your character for {gpNeeded} GP."
            if not char_embedmsg:
                char_embedmsg = await channel.send(embed=char_embed)
            else:
                await char_embedmsg.edit(embed=char_embed)

            await char_embedmsg.add_reaction('1️⃣')
            await char_embedmsg.add_reaction('2️⃣')
            if char_dict['GP'] + deathDict["inc"]['GP']  >= gpNeeded:
                await char_embedmsg.add_reaction('3️⃣')
            await char_embedmsg.add_reaction('❌')
            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=deathEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await char_embedmsg.delete()
                await channel.send(f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                self.bot.get_command('death').reset_cooldown(ctx)
                return
            else:
                await char_embedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await char_embedmsg.edit(embed=None, content=f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                    await char_embedmsg.clear_reactions()
                    self.bot.get_command('death').reset_cooldown(ctx)

                    return
                elif tReaction.emoji == '1️⃣':
                    char_embed.title = f"Are you sure you want to retire {char_dict['Name']}?"
                    char_embed.description = "✅: Yes\n\n❌: Cancel"
                    char_embed.set_footer(text=None)
                    await char_embedmsg.edit(embed=char_embed)
                    await char_embedmsg.add_reaction('✅')
                    await char_embedmsg.add_reaction('❌')
                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=retireEmbedCheck , timeout=60)
                    except asyncio.TimeoutError:
                        await char_embedmsg.delete()
                        await channel.send(f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name"```')
                        self.bot.get_command('death').reset_cooldown(ctx)
                        return
                    else:
                        await char_embedmsg.clear_reactions()
                        if tReaction.emoji == '❌':
                            await char_embedmsg.edit(embed=None, content=f'Death cancelled. Try again using the same command:\n```yaml\n{commandPrefix}death "character name" "charactername"```')
                            await char_embedmsg.clear_reactions()
                            self.bot.get_command('death').reset_cooldown(ctx)
                            return
                        elif tReaction.emoji == '✅':
                            char_embed.clear_fields()
                            try:
                                playersCollection = db.players
                                deadCollection = db.dead
                                playersCollection.delete_one({'_id': charID})
                                guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": char_dict['Guild'], '$options': 'i' }}))
                                # If there is only one of user's character in the guild remove the role.
                                if (len(guildAmount) <= 1):
                                    await author.remove_roles(get(guild.roles, name = char_dict['Guild']), reason=f"Left guild {char_dict['Guild']}")

                                usersCollection = db.users
                                
                                deadCollection.insert_one(char_dict)
                                pass
                                
                            except Exception as e:
                                print ('MONGO ERROR: ' + str(e))
                                char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try retiring your character again.")
                            else:
                                if char_embedmsg:
                                    await char_embedmsg.clear_reactions()
                                    await char_embedmsg.edit(embed=None, content ="Congratulations! You have retired your character.")

                                else: 
                                    char_embedmsg = await channel.send(embed=None, content="Congratulations! You have retired your character.")
                    
                elif tReaction.emoji == '2️⃣' or tReaction.emoji == '3️⃣':
                    char_embed.clear_fields()
                    surviveString = f"Congratulations! ***{char_dict['Name']}*** has survived and has forfeited their rewards."
                    data ={}
                    if tReaction.emoji == '3️⃣':
                        for d in char_dict["Death"].keys():
                            data["$"+d] = char_dict["Death"][d]
                        data["$inc"]["GP"] -= gpNeeded
                        surviveString = f"Congratulations! ***{char_dict['Name']}*** has been revived and has kept their rewards!"
                    data["$unset"] = {"Death":1}
                    
                    try:
                        playersCollection = db.players
                        playersCollection.update_one({'_id': charID}, data)
                        
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try the command again.")
                    else:
                        if char_embedmsg:
                            await char_embedmsg.clear_reactions()
                            await char_embedmsg.edit(embed=None, content= surviveString)
                        else: 
                            char_embedmsg = await channel.send(embed=None, content=surviveString)
        self.bot.get_command('death').reset_cooldown(ctx)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command(aliases=['bag','inv'])
    async def inventory(self,ctx, char, mod_override=""):
        author = ctx.author
        guild = ctx.guild

        contents = []
        mod= False
        if mod_override:
            mod = "Mod Friend" in [role.name for role in author.roles]

        char_dict, char_embed, core = await check_for_char_with_end(ctx, char, mod=mod)
        if not core.isActive():
            await core.send("Character search cancelled")
            self.bot.get_command('inv').reset_cooldown(ctx)
            return
        if core.hasError():
            char_embed.clear_fields()
            char_embed.description = "Command had errors: \n" + "\n".join(core.errors)
            await core.send()
            self.bot.get_command('inv').reset_cooldown(ctx)
            return
        if not char_dict:
            self.bot.get_command('inv').reset_cooldown(ctx)
            return
        footer = f"To view your character's info, type the following command: {commandPrefix}info {char_dict['Name']}"
        char_level = char_dict['Level']
        if char_level == 20:
            tier = 5
        else:
            tier = determine_tier(char_level)
        color=self.determine_color(guild, tier)
        char_embed.colour = color
        spell_list = []
        if "Spellbook" in char_dict:
            spell_list = [spell["Name"] for spell in char_dict["Spellbook"]]
        if "Ritual Book" in char_dict:
            spell_list += [spell["Name"] for spell in char_dict["Ritual Book"]]
        if spell_list:
            spell_dict = {x["Name"] : x for x in db.spells.find({"Name": {"$in": spell_list}})}
            # Show Spellbook in inventory
            if "Spellbook" in char_dict:
                spellbook_string = ""
                spell_levels = {x: [] for x in range(0,10)}
                for spell in char_dict["Spellbook"]:
                    spell_levels[spell_dict[spell["Name"]]["Level"]].append(spell_dict[spell["Name"]])
                for level, spells in spell_levels.items():
                    if spells:
                        spellbook_string+= f"**Level {level}**\n"
                        for spell in sorted(spells, key=lambda s: s["Name"]):
                            spellbook_string += f"• {spell['Name']} ({spell['School']})\n"
                contents.append(("Spellbook", spellbook_string, False))
            if 'Ritual Book' in char_dict:
                ritual_book_string = ""
                spell_levels = {x: [] for x in range(0,10)}
                for spell in char_dict["Ritual Book"]:
                    spell_levels[spell_dict[spell["Name"]]["Level"]].append(spell_dict[spell["Name"]])
                for level, spells in spell_levels.items():
                    if spells:
                        ritual_book_string+= f"**Level {level}**\n"
                        for spell in sorted(spells, key=lambda s: s["Name"]):
                            ritual_book_string += f"• {spell['Name']} ({spell['School']})\n"
                contents.append(("Ritual Book", ritual_book_string, False))

        # Show Consumables in inventory.
        consumables = char_dict["Consumables"]
        if len(consumables) > 0:
            consumables_string = "\n".join(show_inventory(consumables))
            contents.append(("Consumables", consumables_string, False))

        # Show Magic items in inventory.
        magic_items = char_dict["Magic Items"]
        if len(magic_items) > 0:
            contents.append((f"Magic Items", "\n".join(show_inventory(magic_items)), False))

        member = guild.get_member(int(char_dict['User ID']))
        inventory  = char_dict['Inventory']
        if inventory:
            types = {}
            search_names = list(inventory.keys())
            db_entries: dict = list(db.shop.find({"System": char_dict['System'], "Name": {'$in': search_names}}))
            for entry in db_entries:
                type = entry['Type']
                sub_entries = {}
                types[type] = sub_entries
                item_names = []
                if isinstance(entry['Name'], str):
                    item_names.append(entry['Name'])
                else:
                    for name in entry['Name']:
                        item_names.append(name)
                for name in item_names:
                    if name in inventory:
                        sub_entries[name] = inventory[name]
            for k, v in types.items():
                output = '\n'.join(sorted(show_inventory(v)))
                contents.append((f"{k}", output, False))

        if "Collectibles" in char_dict:
            collectibles = char_dict["Collectibles"]
            if len(collectibles) > 0:
                collectibles_string = "\n".join(collectibles)
                contents.append(("Collectibles", collectibles_string, False))
        await paginate(ctx, self.bot, f"{char_dict['Name']} (Lv {char_level}): Inventory", contents, msg=core.message, separator="\n", author = member, color= color, footer=footer)
        self.bot.get_command('inv').reset_cooldown(ctx)

    def determine_color(self, guild, tier):
        role_colors = {r.name: r.colour for r in guild.roles}
        if tier == 1:
            return role_colors['Junior Friend']
        elif tier == 2:
            return role_colors['Journeyfriend']
        elif tier == 3:
            return role_colors['Elite Friend']
        elif tier == 4:
            return role_colors['True Friend']
        else:
            return role_colors['Ascended Friend']

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['u'])
    async def user(self,ctx):
        channel = ctx.channel
        author = ctx.author
        search_author = author
        contents = []
        if len(ctx.message.mentions)>0 and "Mod Friend" in [role.name for role in author.roles]:
            search_author = ctx.message.mentions[0]
        usersCollection = db.users
        userRecords = usersCollection.find_one({"User ID": str(search_author.id)})

        if not userRecords: 
            userRecords = {'User ID': str(search_author.id), 'Games' : 0}
            await channel.send(f'A user profile has been created.') 
        playersCollection = db.players
        charRecords = list(playersCollection.find({"User ID": str(search_author.id)}))

        totalGamesPlayed = 0
        charString = ""
        charDictTiers = [[],[],[],[],[]]
        if charRecords:
            charRecords = sorted(charRecords, key=lambda k: k['Name']) 
            for c in charRecords:
                charDictTiers[determine_tier(c["Level"]) - 1].append(c)
            for n in range(0,len(charDictTiers)):
                charString += f"\n———**Tier {n+1} Characters:**———\n"
                for char_dict in charDictTiers[n]:
                    system = char_dict["System"]
                    char_race = char_dict['Race']
                    char_class = format_classes(char_dict['Class'])
                    if "Reflavor" in char_dict:
                        rfarray = char_dict['Reflavor']
                        if 'Race' in rfarray:
                            char_race = f"{rfarray['Race']} | {char_race}"
                        if 'Class' in rfarray:
                            char_class = f"{rfarray['Class']} | {char_class}"
                            
                    paused = "Paused" in char_dict and char_dict["Paused"]
                    charString += f"**({system})** **{'[PAUSED] '*paused}{char_dict['Name']}**: Lv {char_dict['Level']}, {char_race}, {char_class}\n"

                    if 'Guild' in char_dict:
                        charString += f"---Guild: *{char_dict['Guild']}*\n"
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
        description = f"Total One-shots Played|Hosted: {totalGamesPlayed-games_hosted}|{games_hosted}\n{noodles_text}{dm_time}\nMax Creation Level: {self.getLeveLimit(list([role.name for role in author.roles]))}\n"
    
        description += f"Total Characters: {len(charRecords)}\nTier 1 Characters: {len(charDictTiers[0])}\nTier 2 Characters: {len(charDictTiers[1])}\nTier 3 Characters: {len(charDictTiers[2])}\nTier 4 Characters: {len(charDictTiers[3])}\nTier 5 Characters: {len(charDictTiers[4])}"

        contents.insert(0, (f"General Information",description, False))
        
        contents.append((f"Characters", charString, False))
        await paginate(ctx, self.bot, f"{search_author.display_name}" , contents, separator="\n", author = search_author)
            
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command()
    async def apply(self,ctx, name, cons="", mits=""):
        guild = ctx.guild
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, name)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        footer = f"Attuned magic items are bolded."
        if 'Image' in char_dict:
            char_embed.set_thumbnail(url=char_dict['Image'])
        char_race = char_dict['Race']
        char_class = format_classes(char_dict['Class'])
        char_background = char_dict['Background']
        if "Reflavor" in char_dict:
            rfdict = char_dict['Reflavor']
            if 'Race' in rfdict and rfdict['Race'] != "":
                char_race = f"{rfdict['Race']} | {char_race}"
            if 'Class' in rfdict and rfdict['Class'] != "":
                char_class = f"{rfdict['Class']} | {char_class}"
            if 'Background' in rfdict and rfdict['Background'] != "":
                char_background = f"{rfdict['Background']} | {char_background}"
        nick_string = ""
        if "Nickname" in char_dict and char_dict['Nickname'] != "":
            nick_string = f"• Goes By: **{char_dict['Nickname']}**\n"
        description = f"{nick_string}{char_race}\n{char_background}\n{char_class}\n"

        char_level = char_dict['Level']
        if char_level == 20:
            tier = 5
        else:
            tier = determine_tier(char_level)
        char_embed.colour = self.determine_color(guild, tier)

        if 'Guild' in char_dict:
            description += f"{char_dict['Guild']}: Rank {char_dict['Guild Rank']}"
        else:
            description += "No Guild"

        member = guild.get_member(int(char_dict['User ID']))
        char_embed.set_author(name=member, icon_url=member.display_avatar)
        char_embed.description = description
        char_embed.clear_fields()

        paused = "Paused" in char_dict and char_dict["Paused"]
        char_embed.title = f"{char_dict['System']} {'[PAUSED] ' * paused}{char_dict['Name']} (Lv {char_level}) - {char_dict['CP']}/{cp_bound_array[tier - 1][1]} CP"

        consumables = char_dict['Consumables']
        if cons:
            consumablesList = list(map(lambda x: x.strip(), cons.split(',')))

            allowed_count = 2 + (char_dict["Level"]-1)//4
            if "Ioun Stone (Mastery)" in char_dict['Magic Items']:
                allowed_count += 1
            # block the command if more consumables than allowed (limit or available) are being registerd
            if len(consumablesList) > allowed_count:
                core.addError(f'You are trying to bring in too many consumables (**{len(consumablesList)}/{allowed_count}**)! The limit for your character is **{allowed_count}**.')

            found = self.check_item_availability(consumables, consumablesList, core)
            consumesCount = found
        else:
            consumesCount = {key : sum_sources(entry) for key, entry in consumables.items()}

        # todo refactor this display code
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
                if cPageStops[p + 1] > cPageStops[p]:
                    char_embed.add_field(name=f'Consumables - p. {p+1}', value=consumesString[cPageStops[p]:cPageStops[p+1]], inline=True)
        else:
            char_embed.add_field(name='Consumables', value=consumesString, inline=True)

        # Show Magic items in inventory.
        mPages = 1
        mPageStops = [0]
        magic_items = char_dict['Magic Items']
        attune_list = list([key for key, value in magic_items.items() if 'Attuned' in value and value['Attuned']])
        if 'Attuned' in char_dict:
            for attune_item in char_dict['Attuned'].split(", "):
                attune_list.append(attune_item.split(" [", 1)[0])
        if mits:
            magic_item_list = list(map(lambda x: x.strip(), mits.split(',')))
            found = self.check_item_availability(magic_items, magic_item_list, core)
            rit_db_entries = []
            miArray = found
        else:
            rit_db_entries = [x["Name"] for x in list(db.rit.find({"Name": {"$in" : list(magic_items.keys())}}))]
            miArray = {key : sum_sources(entry) for key, entry in magic_items.items()}
        miString = ""
        for m, v in miArray.items():
            # mi was a non-con
            if m in rit_db_entries:
                continue
            bolding = ""
            if m in attune_list:
                bolding = "**"
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
                if mPageStops[p + 1] > mPageStops[p]:
                    char_embed.add_field(name=f'Magic Items - p. {p+1}', value=miString[mPageStops[p]:mPageStops[p+1]], inline=True)
        else:
            char_embed.add_field(name='Magic Items', value=miString, inline=True)

        if core.hasError():
            await core.delete()
            error_text = '\n'.join(core.errors)
            main_message = f":warning: Command aborted. Reasons: {error_text}"
            await ctx.channel.send(main_message)
            return None
        char_embed.set_footer(text=footer)
        await core.send()
        return None

    def check_item_availability(self, item_source: dict, brought_items: list, core: InteractionCore) -> dict:
        missing = []
        found = {}
        for i in brought_items:
            item_found = False
            for jk, jv in item_source.items():
                if self.similar_(i, jk):
                    add_to_dictionary(found, jk, 1)
                    item_found = True
            if not item_found:
                missing.append(i)

        # if there were any invalid consumables, inform the user on which ones cause the issue
        if len(missing) > 0:
            core.addError(
                f"The following items were not found in your character's inventory: {' ,'.join(missing)}")
        for key, value in found.items():
            available = sum_sources(item_source[key])
            if value > available:
                core.addError(f"You are trying to bring {value} {key} but only have {available}")
        return found

    def similar_(self, to_check: str, contain: str) -> bool:
        return to_check.strip() != "" and to_check.lower().replace(" ", "").strip() in contain.lower().replace(" ", "")

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

    #TODO rework
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel_or_game()
    @commands.command(aliases=['i', 'char'])
    async def info(self,ctx, char, mod_override = ""):
        author = ctx.author
        guild = ctx.guild
        mod= False
        author_check = None
        if mod_override:
            mod = "Mod Friend" in [role.name for role in author.roles]
            if ctx.message.mentions:
                author_check = ctx.message.mentions[0]
                mod = False
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char, mod, author_check)
        if not core.isActive():
            await core.send("Character search cancelled")
            self.bot.get_command('info').reset_cooldown(ctx)
            return
        if core.hasError():
            char_embed.clear_fields()
            char_embed.description = "Command had errors: \n" + "\n".join(core.errors)
            await core.send()
            self.bot.get_command('info').reset_cooldown(ctx)
            return
        footer = f"To view your character's inventory, type the following command: {commandPrefix}inv {char_dict['Name']}"
        system = core.system
        char_race = char_dict['Race']
        char_class = format_classes(char_dict['Class'])
        char_background = char_dict['Background']
        if "Reflavor" in char_dict:
            rfdict = char_dict['Reflavor']
            if 'Race' in rfdict and rfdict['Race'] != "":
                char_race = f"{rfdict['Race']} | {char_race}"
            if 'Class' in rfdict and rfdict['Class'] != "":
                char_class = f"{rfdict['Class']} | {char_class}"
            if 'Background' in rfdict and rfdict['Background'] != "":
                char_background = f"{rfdict['Background']} | {char_background}"
        nick_string = ""
        if "Nickname" in char_dict and char_dict['Nickname'] != "":
            nick_string = f"• Goes By: **{char_dict['Nickname']}**\n"
        alignment_string = "Alignment: Unknown\n"
        if "Alignment" in char_dict and char_dict['Alignment'] != "":
            alignment_string = f"Alignment: {char_dict['Alignment']}\n"

        description = f"{nick_string}• {char_race}\n• {char_class}\n• {char_background}\n• {alignment_string}• One-shots Played: {char_dict['Games']}\n"
        if 'Proficiency' in char_dict:
            description +=  f"• Extra Training: {char_dict['Proficiency']}\n"
        if 'NoodleTraining' in char_dict:
            description +=  f"• Noodle Training: {char_dict['NoodleTraining']}\n"
        if 'Event Token' in char_dict and char_dict['Event Token'] > 0:
            description +=  f"• Event Tokens: {char_dict['Event Token']}\n"
        description += f":moneybag: {char_dict['GP']} GP\n"
        char_level = char_dict['Level']
        if char_level == 20:
            tier = 5
        else:
            tier = determine_tier(char_level)
        char_embed.colour = self.determine_color(guild, tier)

        cp = char_dict['CP']
        if char_level < 20 and cp >= cp_bound_array[tier-1][0]:
            footer += f'\nYou need to level up! Use the following command before playing in another quest to do so: {commandPrefix}levelup {char_dict["Name"]}'

        if 'Death' in char_dict:
            status_emoji = "⚰️"
            description += f"{status_emoji} Status: **DEAD** -  decide their fate with the following command: {commandPrefix}death"
            char_embed.colour = discord.Colour(0xbb0a1e)

        member = guild.get_member(int(char_dict['User ID']))
        char_embed.set_author(name=member, icon_url=member.display_avatar)
        char_embed.description = description
        char_embed.clear_fields()
        
        paused = "Paused" in char_dict and char_dict["Paused"]
        char_embed.title = f"{char_dict['System']} {'[PAUSED] '*paused}{char_dict['Name']} (Lv {char_level}) - {char_dict['CP']}/{cp_bound_array[tier-1][1]} CP"
        tp_string = ""
        for i in range (1,6):
            if f"T{i} TP" in char_dict:
                tp_string += f"• Tier {i} TP: {char_dict[f'T{i} TP']} \n"
        if tp_string:
            char_embed.add_field(name='TP', value=f"{tp_string}", inline=True)
        if 'Guild' in char_dict:
            char_embed.add_field(name='Guild', value=f"{char_dict['Guild']}: Rank {char_dict['Guild Rank']}", inline=True)
        char_embed.add_field(name='Feats', value=", ".join(char_dict['Feats']), inline=False)

        if 'Free Spells' in char_dict:
            fsString = ""
            fsIndex = 0
            for el in char_dict['Free Spells']:
                if el > 0:
                    fsString += f"Level {fsIndex+1}: {el} free spells\n"
                fsIndex += 1

            if fsString:
                char_embed.add_field(name='Free Spellbook Copies Available', value=fsString , inline=False)
        stats = char_dict["Stats"]
        stat_bonuses, max_stat_bonuses, stat_setters = self.calculate_stat_bonuses(char_dict, system)
        display_hp = char_dict['HP'] + self.calculate_bonus_hp(char_level, stats["CON"], stat_bonuses, max_stat_bonuses, stat_setters)
        stat_string = ""
        for stat_name, stat_value in stats.items():
            _, description = self.determine_stat(stat_value, stat_name, max_stat_bonuses, stat_bonuses, stat_setters)
            stat_string += description + "\n"
        char_embed.add_field(name='Stats', value=f":heart: {display_hp} Max HP\n• STR: {stats['STR']} \n• DEX: {stats['DEX']} \n• CON: {stats['CON']} \n• INT: {stats['INT']} \n• WIS: {stats['WIS']} \n• CHA: {stats['CHA']}", inline=False)
        char_embed.set_footer(text=footer)
        if 'Image' in char_dict:
            char_embed.set_thumbnail(url=char_dict['Image'])
        await core.send()
        self.bot.get_command('info').reset_cooldown(ctx)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @commands.command(aliases=['img'])
    @is_log_channel()
    async def image(self,ctx, char, url):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        charID = char_dict['_id']
        data = {
            'Image': url
        }
        try:
            r = requests.head(url)
        except:
            await ctx.channel.send(content=f'It looks like the URL is either invalid or contains a broken image. Please follow this format:\n```yaml\n{commandPrefix}image "character name" URL```\n')
            return
        try:
            db.players.update_one({'_id': charID}, {"$set": data})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
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
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        charID = char_dict['_id']
        try:
            playersCollection = db.players
            playersCollection.update_one({'_id': charID}, {"$set": {"Paused": target}})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            await ctx.channel.send(content=f'I have {(not target)*"un"}paused the progress for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    async def reflavorKernel(self,ctx, char, rtype, new_flavor):
        if len(new_flavor) > 20:
            await ctx.channel.send(content=f'The new {rtype.lower()} must be between 1 and 20 symbols.')
            return
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        charID = char_dict['_id']

        try:
            db.players.update_one({'_id': charID}, {"$set": {'Reflavor.'+rtype: new_flavor}})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try reflavoring your character again.")
        else:
            await channel.send(content=f'I have updated the {rtype} for ***{char_dict["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
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
        if len(new_align) > 20 or len(new_align) <1:
            await ctx.channel.send(content=f'The new alignment must be between 1 and 20 symbols.')
            return
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        charID = char_dict['_id']
        data = {
            'Alignment': new_align
        }

        try:
            playersCollection = db.players
            playersCollection.update_one({'_id': charID}, {"$set": data})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            await channel.send(content=f'I have updated the alignment for ***{char_dict["Name"]}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
    
    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['rn'])
    async def rename(self,ctx, char, new_name = ""):
        channel = ctx.channel
        author = ctx.author
        msg = self.name_check(new_name, author)
        if msg:
            await channel.send(msg)
            return None
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        query = new_name
        query = query.replace('(', '\\(')
        query = query.replace(')', '\\)')
        query = query.replace('.', '\\.')
        playersCollection = db.players
        userRecords = list(playersCollection.find({"User ID": str(author.id), "Name": {"$regex": f"^{query}$", '$options': 'i' } }))

        if userRecords != list():
            await channel.send(f"\nYou already have a character by the name of ***{new_name}***! Please use a different name.")
            return None
        charID = char_dict['_id']
        data = {
            'Name': new_name
        }

        try:
            playersCollection = db.players
            playersCollection.update_one({'_id': charID}, {"$set": data})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            await ctx.channel.send(content=f'I have updated the name for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')

    
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['aka'])
    async def alias(self,ctx, char, new_name = ""):
        channel = ctx.channel
        author = ctx.author
        msg = self.name_check(new_name, author)
        if msg:
            await channel.send(msg)
            return
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        charID = char_dict['_id']
        data = {
            'Nickname': new_name
        }

        try:
            playersCollection = db.players
            playersCollection.update_one({'_id': charID}, {"$set": data})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            char_embedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your character again.")
        else:
            await ctx.channel.send(content=f'I have updated the name for ***{char}***. Please double-check using one of the following commands:\n```yaml\n{commandPrefix}info "character name"\n{commandPrefix}char "character name"\n{commandPrefix}i "character name"```')
            
    def name_check(self, name, author):
        msg = ""
        # Name should be less than 65 chars
        if len(name) > 64:
            msg += ":warning: Your character's name is too long! The limit is 64 characters.\n"

        # Reserved for regex, lets not use these for character names please
        invalidChars = ["[", "]", "?", "“","”", '"', "\\", "*", "$", "{", "+", "}", "^", ">", "<", "|", "(",")" ]

        for i in invalidChars:
            if i in name:
                msg += f":warning: Your character's name cannot contain `{i}`. Please revise your character name.\n"
        return msg
    
    @commands.cooldown(1, float('inf'), type=commands.BucketType.user)
    @is_log_channel()
    @commands.command(aliases=['lvl', 'lvlup', 'lv'])
    async def levelup(self,ctx, char):
        channel = ctx.channel
        author = ctx.author
        command_name = ctx.command.name
        char_dict, level_up_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        char_id = char_dict['_id']
        char_name = char_dict['Name']
        char_class = char_dict['Class']
        cp = char_dict['CP']
        char_level = char_dict['Level']
        stats = char_dict['Stats']
        free_spells = None
        if char_level == 20:
            tier = 5
        else:
            tier = determine_tier(char_level)
        if 'Free Spells' in char_dict:
            free_spells = char_dict['Free Spells']

        if 'Death' in char_dict.keys():
            await channel.send(f'You cannot level up a dead character. Use the following command to decide their fate:\n```yaml\n$death "{char_dict["Name"]}"```')
            self.bot.get_command('levelup').reset_cooldown(ctx)
            return None

        if char_level > 19:
            await channel.send(f"***{char_dict['Name']}*** is level 20 and cannot level up anymore.")
            self.bot.get_command('levelup').reset_cooldown(ctx)
            return None

        elif cp < cp_bound_array[tier-1][0]:
            await channel.send(f'***{char_name}*** is not ready to level up. They currently have **{cp}/{cp_bound_array[tier-1][1]}** CP.')
            self.bot.get_command('levelup').reset_cooldown(ctx)
            return None

        class_records, core = await callAPI(core,'classes')
        class_records = sorted(class_records, key=lambda k: k['Name'])
        remaining_cp = cp - cp_bound_array[tier-1][0]
        next_level = char_level  + 1
        level_up_embed.clear_fields()
        level_up_embed.title = f"{char_name}: Level Up! {char_level} → {next_level}"
        level_up_embed.description = f"{char_dict['Race']}: {format_classes(char_class)}\n**STR**: {stats['STR']} **DEX**: {stats['DEX']} **CON**: {stats['CON']} **INT**: {stats['INT']} **WIS**: {stats['WIS']} **CHA**: {stats['CHA']}"
        class_options = {}

        # Multiclass Requirements
        starting_class = char_dict["Starting Class"]
        records_dict = {}
        for cRecord in class_records:
            records_dict[cRecord['Name']] = cRecord
            if check_multiclass_requirement(cRecord, stats) is not None:
                continue
            class_options[cRecord['Name']] = cRecord

        base_class = records_dict[starting_class]
        # New Multiclass
        multi_class_blocker = None
        new_class_options = {name: entry for name, entry in class_options.items() if name not in char_class}
        if starting_class not in class_options:
            multi_class_blocker = f"You cannot multiclass right now because your base class, **{starting_class}**, requires at least **{base_class['Multiclass']}**.\nCurrent stats: **STR**: {stats['STR']} **DEX**: {stats['DEX']} **CON**: {stats['CON']} **INT**: {stats['INT']} **WIS**: {stats['WIS']} **CHA**: {stats['CHA']}\n"
        elif len(new_class_options) < 1:
            multi_class_blocker = "There are no classes available to multiclass into. \n"

        if multi_class_blocker is not None:
            level_up_embed.add_field(name=f"""~~Would you like to choose a new multiclass?~~\nPlease react with "No" to proceed.""", value=f'{multi_error}✅: ~~Yes~~\n\n🚫: No\n\n❌: Cancel')
        else:
            level_up_embed.add_field(name="Would you like to choose a new multiclass?", value='✅: Yes\n\n🚫: No\n\n❌: Cancel')
        await core.send()
        emoji_options = ['🚫', '❌']
        if multi_class_blocker is not None:
            emoji_options.append('✅')
            await core.message.add_reaction('✅')
        await core.message.add_reaction('🚫')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, core.context.author, emoji_options), timeout=60)
        except asyncio.TimeoutError:
            await core.send(content=f'Level up timed out. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup "character name"\n{commandPrefix}lvlup "character name"\n{commandPrefix}lvl "character name"\n{commandPrefix}lv "character name"```')
            self.bot.get_command('levelup').reset_cooldown(ctx)
            return None
        else:
            await core.message.clear_reactions()
            level_up_embed.clear_fields()
            if tReaction.emoji == '❌':
                await core.send(content=f"Level up cancelled. Try again using the same command or one of its shorthand forms:\n```yaml\n{commandPrefix}levelup \"character name\"\n{commandPrefix}lvlup \"character name\"\n{commandPrefix}lvl \"character name\"\n{commandPrefix}lv \"character name\"```")
                self.bot.get_command('levelup').reset_cooldown(ctx)
                return None
            elif tReaction.emoji == '✅':
                level_up_embed.add_field(name="Pick a new class that you would like to multiclass into.", value=chooseClassString)
                if len(new_class_options) == 1:
                    choice = 0
                else:
                    option_text = ""
                    alpha_index = 0
                    for name, entry in new_class_options.keys():
                        option_text += f"{alphaEmojis[alpha_index]}: {name} Level 1\n"
                        alpha_index += 1
                    level_up_embed.clear_fields()
                    level_up_embed.add_field(name=f"Which class would you like to level up?", value=option_text,
                                             inline=False)
                    choice = await disambiguate(len(new_class_options), core.message, author)
                    if choice is None:
                        await core.send(
                            content=f'Level up timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return None
                    elif choice == -1:
                        await core.send(
                            content=f'Level up timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return None
                    await core.message.clear_reactions()
                choice_level_class = list(new_class_options.keys())[choice]
                select_class = {"Subclass": None, "Level": 1}
                char_class[choice_level_class] = select_class
                if "Wizard" == choice_level_class:
                    free_spells[0] += 6
                    char_dict["Free Spells"] = free_spells
            elif tReaction.emoji == '🚫':
                choice_level_class = char_class.keys()[0]
                if len(char_class) > 1:
                    option_text = ""
                    alpha_index = 0
                    for name, entry in char_class.keys():
                        option_text += f"{alphaEmojis[alpha_index]}: {name} Level {entry['Level']}\n"
                        alpha_index += 1
                    level_up_embed.clear_fields()
                    level_up_embed.add_field(name=f"Which class would you like to level up?", value=option_text, inline=False)
                    choice = await disambiguate(len(char_class), core.message, author)
                    if choice is None:
                        await core.send(
                            content=f'Level up timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return None
                    elif choice == -1:
                        await core.send(
                            content=f'Level up timed out! Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
                        self.bot.get_command('levelup').reset_cooldown(ctx)
                        return None
                    await core.message.clear_reactions()
                    choice_level_class = char_class.keys()[choice]
                select_class = char_class[choice_level_class]
                select_class['Level'] += 1
        level_up_embed.clear_fields()
        level_up_embed.description = f"{char_dict['Race']}: {char_class}\n**STR**:{stats['STR']} **DEX**:{stats['DEX']} **CON**:{stats['CON']} **INT**:{stats['INT']} **WIS**:{stats['WIS']} **CHA**:{stats['CHA']}"
        if 'Wizard' == choice_level_class:
            fs_lvl = (select_class['Level'] - 1) // 2
            if fs_lvl > 8:
                fs_lvl = 8
            free_spells[fs_lvl] += 2
        selected_record = records_dict[choice_level_class]
        if selected_record['Subclass Level'] == select_class['Level']:
            subclasses = selected_record['Class']['Subclasses']
            core, subclass = await self.choose_subclass(core, subclasses, selected_record['Name'])
            if not subclass:
                return None
            select_class['Subclass'] = subclass

        char_dict['Level'] = next_level
        char_class[choice_level_class] = select_class
        # Feat
        feat_levels = []
        if select_class['Level'] in (4, 8, 12, 16, 19) or ('Fighter' == select_class['Name'] and select_class['Level'] in (6, 14)) or ('Rogue' == select_class['Name'] and select_class['Level']) == 10:
            feat_levels.append(int(select_class['Level']))
        char_feats_gained_str = ''
        if feat_levels != list():
            core, feats_picked, char_dict = await self.choose_feat(core, char_class, feat_levels, char_dict)
            if len(feats_picked) > 0:
                char_feats_gained_str = f"Feats Gained: **{''.join(feats_picked.keys())}**"

        if free_spells is not None:
            char_dict['Free Spells'] = free_spells

        tier += int(next_level in [5, 11, 17, 20])
        level_up_embed.title = f'{char_name} has leveled up to {next_level}!\nCurrent CP: {remaining_cp}/{cp_bound_array[tier-1][1]} CP'
        level_up_embed.description = f"{char_dict['Race']} {char_class}\n**STR**: {stats['STR']} **DEX**: {stats['DEX']} **CON**: {stats['CON']} **INT**: {stats['INT']} **WIS**: {stats['WIS']} **CHA**: {stats['CHA']}"
        level_up_embed.description += f"\n{char_feats_gained_str}"
        level_up_embed.description += f"\n{char_name} has put a level into **{choice_level_class}!** (Level {select_class['Level']-1} -> {select_class['Level']})"
        level_up_embed.set_footer(text= None)
        level_up_embed.clear_fields()

        core.embed.set_footer(text=None)
        await core.send(
            "**Double-check** your character information.\nIf this is correct, please react with one of the following:\n✅ to finish creating your character.\n❌ to cancel.")

        # TODO refactor this behavior?
        await core.message.add_reaction('✅')
        await core.message.add_reaction('❌')
        try:
            tReaction, _ = await self.bot.wait_for("reaction_add",
                                                       check=reaction_response_control(core.message, author,
                                                                                       ['✅', '❌']), timeout=60)
        except asyncio.TimeoutError:
            await core.delete()
            await channel.send(
                f'Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create "system" "character name" level "race" "class" "background" STR DEX CON INT WIS CHA "reward item1, reward item2, [...]"```')
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        else:
            await  core.message.clear_reactions()
            if tReaction.emoji == '❌':
                core.cancel()
                await core.message.edit(embed=None,
                                        content=f"Character creation cancelled. Try again using the same command:\n```yaml\n{commandPrefix}create \"character name\" level \"race\" \"class\" \"background\" STR DEX CON INT WIS CHA \"reward item1, reward item2, [...]\"```")
                await  core.message.clear_reactions()
                self.bot.get_command(command_name).reset_cooldown(ctx)
                return None

        try:
            db.players.update_one({'_id': char_id}, {"$set": data})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            await core.send(content="Uh oh, looks like something went wrong while saving your data")

        role_name = await self.level_check(ctx, next_level, char_name)
        level_up_embed.clear_fields()
        await levelUpEmbedmsg.edit(content=f":arrow_up:   __**L E V E L   U P!**__\n\n:warning:   **Don't forget to spend your TP!** Use one of the following commands to do so:\n```yaml\n$tp find \"{char_name}\" \"magic item\"\n$tp craft \"{char_name}\" \"magic item\"\n$tp meme \"{char_name}\" \"magic item\"```", embed=level_up_embed)

        if role_name != "":
            level_up_embed.title = f":tada: {role_name} role acquired! :tada:\n" + level_up_embed.title
            await levelUpEmbedmsg.edit(embed=level_up_embed)
            await levelUpEmbedmsg.add_reaction('🎉')
            await levelUpEmbedmsg.add_reaction('🎊')
            await levelUpEmbedmsg.add_reaction('🥳')
            await levelUpEmbedmsg.add_reaction('🍾')
            await levelUpEmbedmsg.add_reaction('🥂')

        self.bot.get_command('levelup').reset_cooldown(ctx)
        return None
    
    async def level_check(self, ctx, level, char_name):
        author = ctx.author
        roles = [r.name for r in author.roles]
        guild = ctx.guild
        role_name = ""
        if not any([(x in roles) for x in ['Junior Friend', 'Journeyfriend', 'Elite Friend', 'True Friend', 'Ascended Friend']]) and 'D&D Friend' in roles and level > 1:
            role_name = 'Junior Friend'
            level_role = get(guild.roles, name = role_name)
            await author.add_roles(level_role, reason=f"***{author}***'s character ***{char_name}*** is the first character who has reached level 2!")
        if 'Journeyfriend' not in roles and 'Junior Friend' in roles and level > 4:
            role_name = 'Journeyfriend'
            role_remove_str = 'Junior Friend'
            await self.upgrade_role(author, char_name, guild, role_name, role_remove_str)
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 2'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 2'))
        if 'Elite Friend' not in roles and 'Journeyfriend' in roles and level > 10:
            role_name = 'Elite Friend'
            role_remove_str = 'Journeyfriend'
            await self.upgrade_role(author, char_name, guild, role_name, role_remove_str)
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 3'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 3'))
        if 'True Friend' not in roles and 'Elite Friend' in roles and level > 16:
            role_name = 'True Friend'
            role_remove_str = 'Elite Friend'
            await self.upgrade_role(author, char_name, guild, role_name, role_remove_str)
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 4'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 4'))
            await author.add_roles(get(guild.roles, name = 'Roll20 Tier 5'))
            await author.add_roles(get(guild.roles, name = 'Foundry Tier 5'))
        if 'Ascended Friend' not in roles and 'True Friend' in roles and level > 19:
            role_name = 'Ascended Friend'
            role_remove_str = 'True Friend'
            await self.upgrade_role(author, char_name, guild, role_name, role_remove_str)
        return role_name

    async def upgrade_role(self, author, char_name, guild, roleName, roleRemoveStr):
        levelRole = get(guild.roles, name=roleName)
        roleRemove = get(guild.roles, name=roleRemoveStr)
        await author.add_roles(levelRole,
                               reason=f"***{author}***'s character ***{char_name}*** is the first character who has reached level 20!")
        await author.remove_roles(roleRemove)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['att'])
    async def attune(self, ctx, char, item_name):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        # Check number of items character can attune to. Artificer has exceptions.
        attune_length = 3
        if "Artificer" in char_dict['Class']:
            class_level = char_dict['Class']['Artificer']["Level"]
            if class_level >= 18:
                attune_length = 6
            elif class_level >= 14:
                attune_length = 5
            elif class_level >= 10:
                attune_length = 4

        char_id = char_dict['_id']
        magic_items = char_dict['Magic Items']
        attunable_items = {key: value for key, value in magic_items.items() if "Attunement" in value}
        attuned_items = {key: value for key, value in attunable_items.items() if value["Attuned"]}
        if len(attuned_items) >= attune_length:
            await channel.send(
                f"The maximum number of magic items you can attune to is {attune_length}! You cannot attune to any more items!")
            return None
        core, item_name = await self.select_magic_item(char_dict, core, item_name)
        if item_name is None:
            return None
        if item_name in attuned_items.keys():
            await core.send(f"You are already attuned to **{item_name}**!")
            return None
        if item_name not in attunable_items.keys():
            await core.send(
                f"`{item_name}` does not require attunement so there is no need to try to attune this item.!")
            return None
        magic_items[item_name]["Attuned"] = True
        data = char_dict
        try:
            db.players.update_one({'_id': char_id}, {"$set": data})
        except Exception as e:
            print('MONGO ERROR: ' + str(e))
            await channel.send(embed=None,
                               content="Uh oh, looks like something went wrong while saving your changes. Please try again.")
        else:
            await core.send(f"You successfully attuned to **{item_name}**!")

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @commands.command(aliases=['uatt', 'unatt'])
    async def unattune(self,ctx, char, item_name):
        channel = ctx.channel
        command_name = ctx.command.name
        char_dict, char_embed, core = await check_for_char_with_end(ctx, char)
        if not char_dict:
            self.bot.get_command(command_name).reset_cooldown(ctx)
            return None
        core, item_name = await self.select_magic_item(char_dict, core, item_name)
        if item_name is None:
            return None
        if item_name not in attuned_items.keys():
            await core.send(f"You are not attuned to **{item_name}**!")
            return None
        magic_items[item_name]["Attuned"] = False
        data = char_dict
        try:
            db.players.update_one({'_id': char_id}, {"$set": data})
        except Exception as e:
            print('MONGO ERROR: ' + str(e))
            await channel.send(embed=None,
                               content="Uh oh, looks like something went wrong while saving your changes. Please try again.")
        else:
            await core.send(f"You successfully attuned to **{item_name}**!")

    async def select_magic_item(self, char_dict, core, item_name) -> any:
        matches = search_magic_item(item_name, magic_items)
        # IF multiple matches, check which one the player meant.
        if len(matches) == 0:
            await core.send(f"`{item_name}` isn't in {char_dict['Name']}'s inventory.")
            return core, None
        if len(matches) == 1:
            item_name = matches[0]
        else:
            core, selected = paginate_options(core, self.bot, "Obtained Items", matches,
                                              content=f"There seems to be multiple results for **`{item_name}`**, please choose the correct one.\nIf the result you are looking for is not here, please cancel the command with ❌ and be more specific.")
            if core.cancelled():
                return core, None
            item_name = matches[selected]
        return core, item_name

    def calculate_base_hp(self, classes, char_dict, lvl):
        total_hp = classes[char_dict['Starting Class']]['Class']['Hit Die Max'] - classes[char_dict['Starting Class']]['Class']['Hit Die Average']
        for c in classes.values():
            level = int(c['Level'])
            total_hp += c['Class']['Hit Die Average'] * level

        total_hp += ((int(char_dict['Stats']['CON']) - 10) // 2) * lvl
        return total_hp

    def calculate_bonus_hp(self, level: int, con: int, stat_bonuses: dict, max_stat_bonuses: dict, stat_setters: dict):
        hp_bonus, _ = self.determine_stat(0, "HP", max_stat_bonuses, stat_bonuses, stat_setters)
        print(hp_bonus, level)
        total_hp = int(hp_bonus * level)
        con, _ = self.determine_stat(con, "CON", max_stat_bonuses, stat_bonuses, stat_setters)
        total_hp += floor(((con - 10)/2) * level)
        return total_hp

    def determine_stat(self, base_stat: int, key: str, max_stat_bonuses, stat_bonuses, stat_setters):
        max_value = 20
        final_stat = base_stat
        if max_stat_bonuses[key] > 0:
            max_value += max_stat_bonuses[key]
        bonus = stat_bonuses[key]
        final_stat += bonus
        final_stat = max(min(final_stat, max_value), stat_setters[key])
        description = f"**{key}**: {base_stat}"
        # TODO handle all constellations (bonus, reduced to max, exactly max?, set beyond max)
        if final_stat != base_stat:
            if final_stat == max_value:
                description += f"({max_value} MAX)"
            elif stat_setters[key] > max_value:
                description += f"(set to {stat_setters[key]})"
            elif bonus > 0:
                description += f"(+{bonus})"
        return final_stat, description

    def calculate_stat_bonuses(self, char_dict: dict, system: str):
        stat_bonuses = {'STR': 0, 'DEX': 0, 'CON': 0, 'INT': 0, 'WIS': 0, 'CHA': 0, 'HP': 0}
        stat_setters = dict(stat_bonuses)
        max_stat_bonuses = dict(stat_bonuses)
        applicable_entries = []

        special_records = list(db.special.find({"System": system}))
        for record in special_records:
            applies = False
            if record['Type'] == "Race" or record['Type'] == "Feats" or record['Type'] == "Magic Items":
                if record['Name'] in char_dict[record['Type']]:
                    applies = True
            elif record['Type'] == "Class":
                level_barrier = 0
                if "Bonus Level" in record:
                    level_barrier = record["Bonus Level"]
                for key, value in char_dict['Class'].items():
                    class_level = value['Level']
                    class_name = f"{key} ({value['Subclass']})"
                    if class_name == record["Name"] and level_barrier <= class_level:
                        applies = True
            if applies:
                applicable_entries.extend(record["Stat Bonuses"])

        for item in char_dict["Magic Items"]:
            if "Stat Bonuses" in item and (not "Attuned" in item or item["Attuned"]):
                applicable_entries.extend(item["Stat Bonuses"])
        for bonus in applicable_entries:
            type = bonus["Type"]
            stat = bonus["Stat"]
            value = bonus["Value"]
            if type == "MAX":
                stat_bonuses[stat] += value
                max_stat_bonuses[stat] += value
            if type == "FIXED":
                stat_setters[stat] = max(value, stat_setters[stat])
            if type == "BONUS":
                stat_bonuses[stat] += value
        return stat_bonuses, max_stat_bonuses, stat_setters

    #TODO switch to giving the stats dict
    async def starting_stat_modification(self, core, stats_array, source_record):
        author = core.context.author
        statsBonus = source_record['Modifiers'].replace(" ", "").split(',')
        uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
        allStatsArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
        
        for bonus in statsBonus:
            if 'STR' in bonus:
                stats_array[0] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('STR')
            elif 'DEX' in bonus:
                stats_array[1] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('DEX')
            elif 'CON' in bonus:
                stats_array[2] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('CON')
            elif 'INT' in bonus:
                stats_array[3] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('INT')
            elif 'WIS' in bonus:
                stats_array[4] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('WIS')
            elif 'CHA' in bonus:
                stats_array[5] += int(bonus[len(bonus) - 1]) if bonus[len(bonus) - 2] == "+" else int("-" + bonus[len(bonus) - 1])
                uniqueArray.remove('CHA')

            elif 'AOU' in bonus or 'ANY' in bonus:
                anyAmount = int(bonus[len(bonus)-1])
                uniqueStatStr = ""
                uniqueReacts = []

                if 'ANY' in bonus:
                    uniqueArray = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

                for u in range(0,len(uniqueArray)):
                    uniqueStatStr += f'{alphaEmojis[u]}: {uniqueArray[u]}\n'
                    uniqueReacts.append(alphaEmojis[u])

                core.embed.add_field(name=f"{source_record['Name']} lets you choose **1** extra stat to increase by {anyAmount}. React below with the stat you would like to choose.", value=uniqueStatStr, inline=False)
                await core.send()
                
                choice = await disambiguate(len(uniqueArray), core.message, author)
                if choice is None:
                    core.cancel()
                    return None, None
                elif choice == -1:
                    core.cancel()
                    return None, None 

                core.embed.clear_fields()
                if 'AOU' in bonus:
                    stats_array[allStatsArray.index(uniqueArray.pop(choice))] += anyAmount
                else:
                    stats_array[choice] += anyAmount
        return core, {"STR": stats_array[0],
            "DEX": stats_array[1],
            "CON": stats_array[2],
            "INT": stats_array[3],
            "WIS": stats_array[4],
            "CHA": stats_array[5]}

    async def choose_subclass(self, core: InteractionCore, subclasses: list, charClass: str):
        author = core.context.author
        subclass_string = ""
        for num in range(len(subclasses)):
            subclass_string += f'{alphaEmojis[num]}: {subclasses[num]}\n'
        core.embed.clear_fields()
        core.embed.add_field(name=f"The {charClass} class allows you to pick a subclass at this level. React to the choices below to select your subclass.", value=subclass_string, inline=False)
        await core.send()
            
        choice = await disambiguate(len(subclasses), core.message, author)
        if choice is None:
            core.cancel()
            return core, None
        elif choice == -1:
            core.cancel()
            return core, None
        core.embed.clear_fields()
        subclass = subclasses[choice].strip()
        return core, subclass

    async def choose_feat(self, core: InteractionCore, classes: dict, feat_levels: list, char_dict: dict):
        level: int = char_dict["Level"]
        race: str = char_dict["Race"]
        char_stats: dict = char_dict["Stats"]
        char_feats: list = char_dict["Feats"]
        stat_names = list(char_stats.keys())
        author = core.context.author
        feat_records = []
        feats_picked = {}
        epic_boons_count = 0
        epic_boons_limit = min(2, len([entry for entry in classes.values() if entry["Level"] > 3]))
        feats_collection = db.feats
        spellcasting = False
        # todo: lazy check spellcasting?
        for name, entry in classes.items():
            if "Spellcasting" in entry["Class"] and entry["Class"]["Spellcasting"] == True:
                spellcasting = True
        spellcasting_feats = list(feats_collection.find({"Spellcasting": True}))
        for f in spellcasting_feats:
            if f["Name"] in char_feats:
                 spellcasting = True
        for f in feat_levels:
            core.embed.clear_fields()
            is_extra_feat = f == 'Extra Feat'
            if not is_extra_feat:
                try:
                    core.embed.add_field(name=f"Your level allows you to pick an Ability Score Improvement or a feat. Please react with 1 or 2 for your level {f} ASI/feat.", value=f"{alphaEmojis[0]}: Ability Score Improvement\n{alphaEmojis[1]}: Feat\n", inline=False)
                    await core.send()
                    for num in range(0,2): await core.message.add_reaction(alphaEmojis[num])
                    await core.message.add_reaction('❌')
                    core.embed.set_footer(text= "React with ❌ to cancel.\nPlease react with a choice even if no reactions appear.")
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author, alphaEmojis[:2]), timeout=60)
                except asyncio.TimeoutError:
                    core.cancel()
                    return core, None, None
                else:
                    if tReaction.emoji == '❌':
                        core.cancel()
                        return core, None, None
                choice = alphaEmojis.index(tReaction.emoji)
                await core.message.clear_reactions()
            else:
                choice = 1
            if choice == 0:
                core.embed.clear_fields() 
                prev_selections = ""
                for _ in range(0,2):
                    options = []
                    content = prev_selections
                    max_stats = ""
                    for n in range(0,6):
                        if int(char_stats[stat_names[n]]) + 1 <= 20:
                            content += f"{stat_names[n]}: **{char_stats[stat_names[n]]}**\n"
                            options.append(stat_names[n])
                        else:
                            content += f"{stat_names[n]}: **{char_stats[stat_names[n]]}** (MAX)\n"
                    core, selection = await paginate_options(core, self.bot, "ASI", options, max_stats + content)
                    char_stats[options[selection]] = int(char_stats[options[selection]]) + 1
                    prev_selections = f"ASI First Stat: {alphaEmojis[selection]}: {options[selection]}\n"
            elif choice == 1:
                if feat_records == list():
                    feat_records, core = await callAPI(core,'feats')
                featChoices = []
                for feat in feat_records:
                    if feat['Name'] in char_feats or feat['Name'] in feats_picked:
                        continue
                    # allow only origin feats for extra feats in 5R
                    if is_extra_feat and core.system == '5R' and "Origin" not in feat:
                        continue
                    if "Epic Boon" in feat and epic_boons_count >= epic_boons_limit and level < 19:
                        continue
                    meets_restriction = False
                    level_only = True
                    if 'Feat Restriction' not in feat and 'Race Restriction' not in feat and 'Class Restriction' not in feat and 'Stat Restriction' not in feat and 'Race Unavailable' not in feat and 'Require Spellcasting' not in feat and 'Level Restriction' not in feat:
                        featChoices.append(feat)
                    else:
                        if 'Feat Restriction' in feat:
                            restrictions = [x.strip() for x in feat['Feat Restriction'].split(', ')]
                            level_only = False
                            for f in restrictions:
                                if f in char_feats or f in feats_picked:
                                    meets_restriction = True
                        if 'Race Restriction' in feat:
                            restrictions = [x.strip() for x in feat['Race Restriction'].split(', ')]
                            level_only = False
                            for f in restrictions:
                                if f in race:
                                    meets_restriction = True
                        if 'Race Unavailable' in feat:
                            level_only = False
                            if race not in feat['Race Unavailable']:
                                meets_restriction = True
                        if 'Class Restriction' in feat:
                            restrictions = [x.strip() for x in feat['Class Restriction'].split(', ')]
                            level_only = False
                            for name, entry in classes.items():
                                if name in restrictions or entry["Class"]['Subclass'] in restrictions:
                                    meets_restriction = True
                        if 'Stat Restriction' in feat:
                            level_only = False
                            s = feat['Stat Restriction']
                            statNumber = int(s[-2:])
                            if '/' in s:
                                checkStat = s[:len(s)-2].replace(" ", "").split('/')
                            else:
                                checkStat = [s[:len(s)-2].strip()]

                            for stat in checkStat:
                                if int(char_stats[stat]) >= statNumber:
                                    meets_restriction = True

                        if "Require Spellcasting" in feat:
                            level_only = False
                            meets_restriction = spellcasting
                            
                        if 'Level Restriction' in feat:
                            meets_restriction = (level_only or meets_restriction) and level >= feat['Level Restriction']
                        if meets_restriction:
                            featChoices.append(feat)
                    
                featChoices = sorted(featChoices, key = lambda i: i['Name']) 
                title = "Feat Selection"
                core, choice = await paginate_options(core, self.bot, title, list([feat["Name"] for feat in featChoices]))
                if not core.isActive():
                    return core, None, None
                featPicked = featChoices[choice]
                if "Spellcasting" in featPicked:
                    spellcasting = True
                feats_picked[featPicked["Name"]] = featPicked
                if featPicked['Name'] == "Ritual Caster":
                    ritualClasses = ["Bard", "Cleric", "Druid", "Sorcerer", "Warlock", "Wizard"]
                    core, selection = await paginate_options(core, self.bot, f"Ritual Caster Class Selection", ritualClasses, content)
                    ritualClass = ritualClasses[selection]
                    featPicked['Name'] = f"{featPicked['Name']} ({ritualClass})"
                    spellsCollection = db.spells
                    ritual_spells = list(spellsCollection.find({"$and": [{"Classes": {"$regex": ritualClass, '$options': 'i' }}, {"Ritual": True}, {"Level": 1}] }))
                    ritual_book = []
                    if len(ritual_spells) > 2:
                        content = "Please pick the first spell."
                        core, selection = await paginate_options(core, self.bot, f"Ritual Caster {ritualClass}", list([spell["Name"] for spell in ritual_spells]), content)
                        if not core.isActive():
                            return core, None, None
                        rChoice = ritual_spells.pop(selection)
                        ritual_book.append({'Name':rChoice['Name'], 'School':rChoice['School']})
                        content = "Please pick the second spell."
                        core, selection = await paginate_options(core, self.bot, f"Ritual Caster {ritualClass}", list([spell["Name"] for spell in ritual_spells]), content)
                        if not core.isActive():
                            return core, None, None
                        rChoice = ritual_spells.pop(selection)
                        ritual_book.append({'Name':rChoice['Name'], 'School':rChoice['School']})
                    else:
                        ritual_book.append({'Name':ritual_spells[0]['Name'], 'School':ritual_spells[0]['School']})
                        ritual_book.append({'Name':ritual_spells[1]['Name'], 'School':ritual_spells[1]['School']})
                    char_dict["Ritual Book"] = ritual_book
                if 'Stat Bonuses' in featPicked:
                    feat_bonus = featPicked['Stat Bonuses']
                    if '/' in feat_bonus or 'ANY' in feat_bonus:
                        if '/' in feat_bonus:
                            feat_bonus_list = feat_bonus[:len(feat_bonus) - 3].split('/')
                        elif 'ANY' in feat_bonus:
                            feat_bonus_list = statNames
                        content=f"The {featPicked['Name']} feat lets you choose between {feat_bonus}. React with [{alphaEmojis[0]}-{alphaEmojis[len(feat_bonus_list)-1]}] below with the stat(s) you would like to choose."
                        core, choice = await paginate_options(core, self.bot, "Feat Stats", feat_bonus_list, content)
                        if not core.isActive():
                            return core, None, None
                        char_stats[feat_bonus_list[choice]] = int(char_stats[feat_bonus_list[choice]]) + int(feat_bonus[-1:])
                    else:
                        feat_bonus_list = feat_bonus.split(', ')
                        for fb in feat_bonus_list:
                            char_stats[fb[:3]] = int(char_stats[fb[:3]]) + int(fb[-1:])
        char_dict['Feats'].extend(list([v['Name'] for v in feats_picked.values()]))
        return core, feats_picked, char_dict

async def setup(bot):
    await bot.add_cog(Character(bot))