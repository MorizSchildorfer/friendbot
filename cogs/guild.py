import discord
import asyncio
import pytz
from discord.utils import get        
from discord.ext import commands
from bfunc import  timezoneVar, commandPrefix, db, traceBack, alphaEmojis, settingsRecord
from datetime import datetime, timezone,timedelta
from cogs.util import checkForChar, checkForGuild, paginate, noodle_roles, check_for_char_with_end


async def pin_control(self, ctx, goal):
    author = ctx.author
    channel = ctx.channel
    infoMessage = await channel.send(f"You have 60 seconds to react to the message you want to {ctx.invoked_with} with the 📌 emoji (`:pushpin:`)!")
    def pinned_embed_check(event):
        return str(event.emoji) == '📌' and event.user_id == author.id
    try:
        event = await self.bot.wait_for("raw_reaction_add", check=pinned_embed_check , timeout=60)
    except asyncio.TimeoutError:
        await infoMessage.edit(content=f'The `{ctx.invoked_with}` command has timed out! Try again.')
        return
    message = await channel.fetch_message(event.message_id)
    await (getattr(message, goal))()
    await ctx.message.delete()
    await infoMessage.edit(content = f"You have successfully {ctx.invoked_with}ned the message! This message will self-destruct in 10 seconds.")            
    await asyncio.sleep(10) 
    await infoMessage.delete()


def is_log_channel():
    async def predicate(ctx):
        if ctx.channel.type == discord.ChannelType.private:
            return False
        return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or
                ctx.channel.category_id == 698784680488730666)
    return commands.check(predicate)


def is_guild_channel():
    async def predicate(ctx):
        if ctx.channel.type == discord.ChannelType.private:
            return False
        return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Guild Rooms"]
    return commands.check(predicate)


def is_game_channel():
    async def predicate(ctx):
        if ctx.channel.type == discord.ChannelType.private:
            return False
        return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or
                ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Game Rooms"] or
                ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"]or
                ctx.channel.category_id == 698784680488730666)
    return commands.check(predicate)


class Guild(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.creation_cost = 0

    @commands.group(aliases=['g'], case_insensitive=True)
    async def guild(self, ctx):	
        pass

    async def cog_command_error(self, ctx, error):
        msg = None
        if isinstance(error, commands.CommandNotFound):
            await ctx.channel.send(f'Sorry, the command `***{commandPrefix}{ctx.invoked_with}***` requires an additional keyword to the command or is invalid, please try again!')
            return
            
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.BadArgument):
            # convert string to int failed
            msg = "The GP amount needs to be a number. "
        if isinstance(error, commands.MissingRequiredArgument):
            if error.param.name == 'charName':
                msg = "You're missing your character name in the command. "
            elif error.param.name == "guildName":
                msg = "You're missing the guild name in the command. "
            elif error.param.name == "roleName":
                msg = "You're missing the @role for the guild you want to create. "
            elif error.param.name == "channelName":
                msg = "You're missing the #channel for the guild you want to create. "
            elif error.param.name == "gpName":
                msg = "You're missing the amount of GP you want to use to fund the guild. " 
            elif error.param.name == "gpFund":
                msg = "You're missing the amount of GP you want to use to fund the guild. " 
        # elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
        #     msg = "There seems to be an unexpected or a missing closing quote mark somewhere, please check your format and retry the command. "
        
        # bot.py handles this, so we don't get traceback called.
        elif isinstance(error, commands.CommandOnCooldown):
            return

        elif isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):
             return

        if msg:
            if ctx.command.name == "info":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild info #guild-channel```\n"
            elif ctx.command.name == "join":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild join \"character name\" #guild-channel```\n"
            elif ctx.command.name == "leave":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild leave \"character name\"```\n"
            elif ctx.command.name == "rep":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild rep \"character name\" sparkles```\n"
            elif ctx.command.name == "create":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild create \"character name\" \"guild name\" @rolename #channel-name```\n"
            elif ctx.command.name == "fund":
                msg += f"Please follow this format:\n```yaml\n{commandPrefix}guild fund \"character name\" #guild-channel GP```\n"

            ctx.command.reset_cooldown(ctx)
            await ctx.channel.send(msg)
        else:
            ctx.command.reset_cooldown(ctx)
            await traceBack(ctx,error)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @guild.command()
    @is_log_channel()
    async def create(self,ctx, charName, guildName, roleName, channelName):
        channel = ctx.channel
        author = ctx.author

        guildRole = ctx.message.role_mentions
        guildChannel = ctx.message.channel_mentions

        roles = [r.name for r in ctx.author.roles]

        # Check if the user using the command has the guildmaster role
        if 'Guildmaster' not in roles:
            await channel.send(f"You do not have the Guildmaster role to use this command.")
            return 

        if guildRole == list() or guildChannel == list():
            await channel.send(f"You are missing the guild channel.")
            return 
            

        #see if channel + role + guildname matchup.
        roleStr = (guildRole[0].name.lower().replace(',', '').replace('.', '').replace(' ', '').replace('-', ''))
        guildNameStr = (guildName.lower().replace(',', '').replace('.', '').replace(' ', '').replace('-', ''))
        
        guildChannelStr = (guildChannel[0].name.replace('-', ''))
        if guildChannelStr != guildNameStr:
            await channel.send(f"The guild: ***{guildName}*** does not match the guild channel ***{guildChannel[0].name}***. Please try the command again with the correct channel.")
            return 
        elif guildNameStr != roleStr:
            await channel.send(f"The guild: ***{guildName}*** does not match the guild role ***{guildRole[0].name}***. Please try the command again with the correct role.")
            return

        # Grab user's noodle role
        roles = author.roles
        noodleRole = None
        for r in roles:
            if r.name in noodle_roles and r.name not in ['Newdle', 'Good Noodle']:
                noodleRole = r

        if noodleRole:
            usersCollection = db.users
            userRecords = usersCollection.find_one({"User ID": str(author.id)})
            if userRecords:
                char_dict, char_embed, core = await check_for_char_with_end(ctx, charName)
                if char_dict:
                    # GP needed to fund guild.
                    gpNeeded = 0
                    if char_dict['Level'] < 5:
                        gpNeeded = 200
                    elif char_dict['Level'] < 11:
                        gpNeeded = 400
                    elif char_dict['Level'] < 17:
                        gpNeeded = 600
                    elif char_dict['Level'] < 21:
                        gpNeeded = 800

                    if gpNeeded > char_dict['GP']:
                        await channel.send(f"***{char_dict['Name']}*** does not have at least {gpNeeded} GP in order to fund ***{guildName}***.")
                        return

                    char_dict['GP'] -= float(gpNeeded)

                    noodleRep = ["Elite Noodle (0)", "True Noodle (10)", "Ascended Noodle (20)", "Immortal Noodle (30)", "Eternal Noodle (40)", "Infinity Noodle (50)", "Beyond Noodle (60)"]
                    charID = char_dict['_id']
                    if 'Guilds' not in userRecords: 
                        userRecords['Guilds'] = []

                    if 'Guild' in char_dict:
                        await channel.send(f"***{char_dict['Name']}*** is already a part of ***{char_dict['Guild']}*** and won't be able to create another guild.")
                        return

                    # Look through Noodles and filter used noodles for base rep.
                    for n in userRecords["Guilds"]:
                        if n.split(": ", 1)[1] in noodleRep:
                            noodleRep.remove(n.split(": ", 1)[1])

                    if noodleRep == list():
                        await channel.send(f"You can't create any more guilds because you have already used all of your Noodle roles to create guilds! Gain a new Noodle role if you want to create another guild!")
                        return

                    noodleRepStr = ""
                    for i in range(0, len(noodleRep)):
                        noodleRepStr += f"{alphaEmojis[i]}: {noodleRep[i]}\n"

                    char_embed.add_field(name=f"Choose the Noodle role which you would like to use to create this guild. This will affect the amount of reputation which the guild starts with.", value=noodleRepStr, inline=False)
                    core.send(char_embed)

                    await core.message.add_reaction('❌')

                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']), timeout=60)
                    except asyncio.TimeoutError:
                        await core.delete()
                        await channel.send('Guild command timed out! Try using the command again.')
                        ctx.command.reset_cooldown(ctx)
                        return
                    else:
                        if tReaction.emoji == '❌':
                            await core.send(f"Guild command cancelled. Please use the command and try again!")
                            await core.message.clear_reactions()
                            ctx.command.reset_cooldown(ctx)
                            return
                    guildName = guildRole[0].name
                    char_embed.clear_fields()
                    await core.message.clear_reactions()
                    baseRep = int(noodleRep[alphaEmojis.index(tReaction.emoji[0])].split(' (')[1].replace(')',""))
                    noodleRepUsed = noodleRep[alphaEmojis.index(tReaction.emoji[0])]
                    userRecords['Guilds'].append(f"{guildName}: {noodleRepUsed}")

                    # Quick check to see if guild already exists
                    guildsCollection = db.guilds
                    guildExists = guildsCollection.find_one({"Name": {"$regex": guildName, '$options': 'i' }})


                    if guildExists:
                        await channel.send(f"There is already a guild by the name of ***{guildName}***. Please try creating a guild with a different name.")
                        return

                    guildsDict = {'Role ID': str(guildRole[0].id), 'Channel ID': str(guildChannel[0].id), 'Name': guildName, 'Funds': gpNeeded, 'Guildmaster': char_dict['Name'], 'Guildmaster ID': str(author.id), 'Reputation': baseRep, 'Total Reputation': baseRep, 'Noodle Used': noodleRepUsed}
                    await author.add_roles(guildRole[0], reason=f"Created guild {guildName}")

                    try:
                        playersCollection = db.players
                        playersCollection.update_one({'_id': charID}, {"$set": {"Guild": guildName, 'Guild Rank': 1, 'GP':char_dict['GP']}})
                        usersCollection.update_one({"User ID": str(author.id)}, {"$set": {"Guilds": userRecords['Guilds']}})
                        guildsCollection.insert_one(guildsDict)
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your guild again.")
                        return

                    char_embed.title = f"Guild Creation: {guildName}"
                    char_embed.description = f"***{char_dict['Name']}*** has created ***{guildName}***!\n\nThe guild's status can be checked using the following command:\n```yaml\n{commandPrefix}guild info #guild-channel```"
                    await core.send(char_embed)
                          
            else:
                await channel.send(f'***{author.display_name}*** you will need to play at least one game with a character before you can create a guild.')
                return

        else:
            await channel.send(f'***{author.display_name}***, you need the ***Elite Noodle*** role or higher to create a guild. ')
            return

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_game_channel()
    @guild.command()
    async def info(self,ctx, guildName, month = None, year = None): 
        channel = ctx.channel
        guild = ctx.guild
        guildEmbed = discord.Embed()
        guildEmbedmsg = None
        guildChannel = ctx.message.channel_mentions
        content = []
        mention= ""
        currentDate = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%y")
        if not year:
            year = currentDate.split("-")[1]
        if month:
            if month.isnumeric() and 0 < int(month) < 13:
                currentDate = datetime.now(pytz.timezone(timezoneVar)).replace(month = int(month)).replace(year = 2000+int(year)).strftime("%b-%y")
                
            else:
                await ctx.channel.send(f"Month needs to be a number between 1 and 12.")
                ctx.command.reset_cooldown(ctx)
                return
        if guildChannel == list():
            mention= guildName
            guildRecords, guildEmbedmsg = await checkForGuild(ctx, guildName, guildEmbed)
        else:
            guildChannel = guildChannel[0]
            guild_id = guildChannel.id
            mention= guildChannel.mention
            guildRecords = db.guilds.find_one({"Channel ID": str(guild_id)})
            
        if guildRecords:

            title = f"{guildRecords['Name']}" 
           
            playersCollection = db.players
            guildMembers = list(playersCollection.find({"Guild": guildRecords['Name']}))
            
            guild_stats = db.stats.find_one({"Date": currentDate, "Guilds."+guildRecords['Name'] : {"$exists" : True}})
            guild_life_stats = db.stats.find_one({"Life": 1})
            guild_stats_string = ""
            gv = {}
            if not guild_stats:
                pass
            else:
                gv = guild_stats["Guilds"][guildRecords['Name']]
             
            guild_data_0s = ["GQ", "GQM", "GQNM", "GQDM", "DM Sparkles", "Player Sparkles", "Joins"]
            for data_key in guild_data_0s:
                if not data_key in gv:
                    gv[data_key] = 0
            guild_stats_string += f"• Guild Quests: {gv['GQ']}\n"

            # Total number of guild quests with a guild member who got rewards
            guild_stats_string += f"• Guild Quests with Active Members: {gv['GQM']}\n"

            # Total number of guild quests with no guild members who got rewards
            guild_stats_string += f"• Guild Quests with no Active Members: {gv['GQNM']}\n"
            
            guild_stats_string += f"• Guild Quests with only Active DM: {gv['GQDM']}\n"
            
            
            guild_stats_string += f"• :sparkles: gained by Members: {gv['Player Sparkles']}\n"
            guild_stats_string += f"• :sparkles: gained by DMs: {gv['DM Sparkles']}\n"
            
            guild_stats_string += f"• Guild Members Gained: {gv['Joins']}\n"
            
            dm_text=""
            if guild_stats and "DM" in guild_stats:
                all_guild_dms = list(filter(lambda dm_data: "Guilds" in dm_data[1] and guildRecords['Name'] in dm_data[1]["Guilds"], list(guild_stats["DM"].items())))
                
                all_guild_dms.sort(key=lambda dm_data: -dm_data[1]["Guilds"][guildRecords['Name']])

                for i in range(0, min(5, len(all_guild_dms))):
                    dm_id, dm_data = all_guild_dms[i]
                    dm_text += f"   <@{dm_id}>: {dm_data['Guilds'][guildRecords['Name']]}\n"


            guild_life_stats_string = ""
            gv = {}
            if (not "Guilds" in guild_life_stats) or (not guildRecords["Name"] in guild_life_stats["Guilds"]):
                pass
            else:
                gv = guild_life_stats["Guilds"][guildRecords['Name']]
            guild_data_0s = ["GQ", "GQM", "GQNM", "GQDM", "DM Sparkles", "Player Sparkles", "Joins"]
            for data_key in guild_data_0s:
                if not data_key in gv:
                    gv[data_key] = 0
                    
            guild_life_stats_string += f"• Guild Quests: {gv['GQ']}\n"

            # Total number of guild quests with a guild member who got rewards
            guild_life_stats_string += f"• Guild Quests with Active Members: {gv['GQM']}\n"

            # Total number of guild quests with no guild members who got rewards
            guild_life_stats_string += f"• Guild Quests with no Active Members: {gv['GQNM']}\n"
            
            guild_life_stats_string += f"• Guild Quests with only Active DM: {gv['GQDM']}\n"
            
            
            guild_life_stats_string += f"• :sparkles: gained by Members: {gv['Player Sparkles']}\n"
            guild_life_stats_string += f"• :sparkles: gained by DMs: {gv['DM Sparkles']}\n"
            
            guild_life_stats_string += f"• Guild Members Gained: {gv['Joins']}\n"
            
            dm_text_lifetime=""
                    
            if guild_life_stats and "DM" in guild_life_stats:
                all_guild_dms = list(filter(lambda dm_data: "Guilds" in dm_data[1] and guildRecords['Name'] in dm_data[1]["Guilds"], 
                    list(guild_life_stats["DM"].items())))
                
                all_guild_dms.sort(key=lambda dm_data: -dm_data[1]["Guilds"][guildRecords['Name']])

                for i in range(0, min(5, len(all_guild_dms))):
                    dm_id, dm_data = all_guild_dms[i]
                    dm_text_lifetime += f"   <@{dm_id}>: {dm_data['Guilds'][guildRecords['Name']]}\n"


            unique_members = set()
            
            
            
            guildMemberStr = "There are no guild members currently."
            if guildMembers != list():
                guildMemberStr = ""
                for g in guildMembers:
                    g_member = guild.get_member(int(g['User ID']))
                    if not g_member:
                        continue
                    unique_members.add(g['User ID'])
                    next_member_str = f"{guild.get_member(int(g['User ID'])).mention} **{g['Name']}** [Rank {g['Guild Rank']}]\n"
                    guildMemberStr += next_member_str 
            
            guild_life_stats_string += f"• Unique Members: {len(unique_members)}\n"
            
            
            if guildRecords['Funds'] < self.creation_cost:
                content.append(("Funds", f"{guildRecords['Funds']} GP / {self.creation_cost} GP\n**{self.creation_cost - guildRecords['Funds']} GP** required to open the guild!"))
            else:
                content.append(("Reputation", f"• Lifetime (Total): {guildRecords['Total Reputation']} :sparkles:"))
            
            content.append(("Monthly Stats", guild_stats_string))
            content.append(("Lifetime Stats", guild_life_stats_string))
            separate_page = False
            if dm_text:
                content.append(("This Month's Top DMs", dm_text, separate_page, True))
                separate_page = False
            if dm_text_lifetime:
                content.append(("All-time Top DMs", dm_text_lifetime, separate_page, True))
            
            content.append(("Members", guildMemberStr, True, True))
                
            await paginate(ctx, self.bot, title, content, msg = guildEmbedmsg, footer="")
    
        else:
            await channel.send(f'The ***{mention}*** guild does not exist. Check to see if it is a valid guild and check your spelling.')
            return

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def join(self,ctx, charName, guildName): 
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName)
        if char_dict:
            if 'Guild' in char_dict:
                await channel.send(f"***{char_dict['Name']}*** cannot join any guilds because they belong to the guild ***{char_dict['Guild']}***.")
                return

            guild_channel = ctx.message.channel_mentions
            if guild_channel == list():
                await ctx.channel.send(f"You are missing the guild channel.")
                return 
            guild_channel = guild_channel[0]

            guild_records = db.guilds.find_one({"Channel ID": str(guild_channel.id)})
            
            if guild_records:
                gpNeeded = 0
                if char_dict['Level'] < 5:
                    gpNeeded = 200
                elif char_dict['Level'] < 11:
                    gpNeeded = 400
                elif char_dict['Level'] < 17:
                    gpNeeded = 600
                elif char_dict['Level'] < 21:
                    gpNeeded = 800
                drive = False
                if "Drive" in char_dict and guild_records['Name'] == char_dict["Drive"]:
                    gpNeeded /= 2
                    drive = True

                if gpNeeded > char_dict['GP']:
                    await channel.send(f"***{char_dict['Name']}*** does not have the minimum {gpNeeded} GP to join ***{guild_records['Name']}***.")
                    return

                newGP = (char_dict['GP'] - float(gpNeeded))
                        
                char_embed.title = f"Joining Guild: {guild_records['Name']}"
                char_embed.description = f"Are you sure you want to join ***{guild_records['Name']}*** for {gpNeeded} GP{' (Discounted)' * drive}? \n\nCurrent GP: {char_dict['GP']} GP\nNew GP: {newGP} GP\n\n✅: Yes\n\n❌: Cancel"

                await core.send(char_embed)
                await core.message.add_reaction('✅')
                await core.message.add_reaction('❌')

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
                except asyncio.TimeoutError:
                    await core.delete()
                    await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild join "character name" #guild-channel```')
                    return
                else:
                    await core.mesasge.clear_reactions()
                    if tReaction.emoji == '❌':
                        await core.send(f"Guild join cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild join \"character name\" #guild-channel```")
                        await core.message.clear_reactions()
                        return

                await author.add_roles(guild.get_role(int(guild_records['Role ID'])), reason=f"Joined guild {guildName}")

                try:
                    currentDate = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%y")
                    # update all the other data entries
                    # update the DB stats
                    db.stats.update_one({'Date': currentDate}, {"$inc": {"Guilds."+guild_records['Name']+".Joins": 1}}, upsert=True)
                    db.stats.update_one({'Life': 1}, {"$inc": {"Guilds."+guild_records['Name']+".Joins": 1}}, upsert=True)
            
                    playersCollection = db.players
                    playersCollection.update_one({'_id': char_dict['_id']}, {"$set": {'Guild': guild_records['Name'], 'GP':newGP, 'Guild Rank': 1}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    char_embed.description = f"***{char_dict['Name']}*** has joined ***{guild_records['Name']}*** for {gpNeeded} GP!\n\n**Previous GP**: {char_dict['GP']} GP\n**Current GP**: {newGP} GP\n"
                    await core.send(char_embed)
                
            else:
                await channel.send(f'The guild ***{guildName}*** does not exist. Please try again.')
                return

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def rankup(self,ctx, charName):
        channel = ctx.channel
        author = ctx.author
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName)
        if char_dict:
            if 'Guild' not in char_dict:
                await channel.send(f"***{char_dict['Name']}*** cannot upgrade their guild rank because they currently do not belong to a guild.")
                return

            guild_records, guildEmbedmsg = await checkForGuild(ctx,char_dict['Guild'],char_embed)
            if guildEmbedmsg:
                core.message = guildEmbedmsg
            if guild_records:
                if char_dict['Guild Rank'] > 3:
                    await channel.send(f"***{char_dict['Name']}*** is already at the max rank and cannot increase their rank any further.")
                    return

                rankCosts = [1000, 3000, 3000]
                gpNeeded = rankCosts[char_dict['Guild Rank']-1]
                if gpNeeded > char_dict['GP']:
                    await channel.send(f"***{char_dict['Name']}*** does not have {gpNeeded} GP in order to upgrade their guild rank.")
                    return

                char_embed.title = f"Ranking Up - Guild: {guild_records['Name']}"
                char_embed.description = f"Are you sure you want to upgrade your rank to **{char_dict['Guild Rank'] + 1}** for {gpNeeded} GP?\n\n**Current GP**: {char_dict['GP']} GP\n**Cost**: {gpNeeded} GP\n**New GP**: {char_dict['GP'] - gpNeeded} GP\n\n✅: Yes\n\n❌: Cancel"

                await core.send()
                await core.message.add_reaction('✅')
                await core.message.add_reaction('❌')

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
                except asyncio.TimeoutError:
                    await core.delete()
                    await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild rankup```')
                    return
                else:
                    await core.message.clear_reactions()
                    if tReaction.emoji == '❌':
                        await core.send(f"Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild rankup```")
                        await core.message.clear_reactions()
                        return

                newGP = (char_dict['GP'] - float(gpNeeded))
                try:
                    playersCollection = db.players
                    playersCollection.update_one({'_id': char_dict['_id']}, {"$set": {'GP':newGP, 'Guild Rank': char_dict['Guild Rank'] + 1}})
                except Exception as e:
                    print('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    char_embed.description = f"***{char_dict['Name']}*** has ranked up using {gpNeeded} GP! Rank **{char_dict['Guild Rank']}** → **{char_dict['Guild Rank'] + 1}**\n\n**Previous GP**: {char_dict['GP']} GP\n**Cost**: {gpNeeded} GP\n**New GP**: {newGP} GP\n"
                    await core.send()
            else:
                await channel.send(f'The guild ***{char_dict["Guild"]}*** does not exist. Please try again.')
                return


    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def leave(self,ctx, charName): 
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        char_dict, char_embed, core = await check_for_char_with_end(ctx, charName)

        if char_dict:
            if 'Guild' not in char_dict:
                await channel.send(f"***{char_dict['Name']}*** cannot leave a guild because they currently do not belong to any guild.")
                return

            char_embed.title = f"Leaving Guild: {char_dict['Guild']}"
            char_embed.description = f"Are you sure you want to leave ***{char_dict['Guild']}***?\n\n✅: Yes\n\n❌: Cancel"
            await core.send(char_embed)
            await core.message.add_reaction('✅')
            await core.message.add_reaction('❌')

            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=reaction_response_control(core.message, author,['✅', '❌']) , timeout=60)
            except asyncio.TimeoutError:
                await core.delete()
                await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild leave```')
                return
            else:
                await core.message.clear_reactions()
                if tReaction.emoji == '❌':
                    await core.message.edit(embed=None, content=f"Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild leave```")
                    await core.message.clear_reactions()
                    return

            playersCollection = db.players
            guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": char_dict['Guild'], '$options': 'i' }}))
            # If there is only one of user's character in the guild remove the role.
            if len(guildAmount) <= 1:
                await author.remove_roles(get(guild.roles, name = char_dict['Guild']), reason=f"Left guild {char_dict['Guild']}")

            try:
                playersCollection.update_one({'_id': char_dict['_id']}, {"$unset": {'Guild': 1, 'Guild Rank':1}})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
            else:
                char_embed.description = f"***{char_dict['Name']}*** has left ***{char_dict['Guild']}***."
                await core.send(char_embed)

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    @commands.has_any_role('A d m i n')
    async def rename(self,ctx, newName, channelName=""):
        channel = ctx.channel
        
        guildChannel = ctx.message.channel_mentions 
        if guildChannel == list():  # checks to see if a channel was mentioned
            await ctx.channel.send(f"You are missing the guild channel.")
            return 
        guildChannel = guildChannel[0]

        try:
            guildRecords = db.guilds.find_one({"Channel ID": str(guildChannel.id)}) #finds the guild that has the same Channel ID as the channel mention.
            if not guildRecords:
                await ctx.channel.send(f"No guild was found.")
                return 
            
            #collects the important variables
            oldName = guildRecords['Name']
            noodleUsed = guildRecords['Noodle Used']
            
            #update guild log
            guildCollection = db.guilds
            guildCollection.update_one({"Name": guildRecords['Name']}, {"$set": {'Name':newName}}) # updates the guild with the new name
                  
            #update player logs
            playersCollection = db.players
            playersCollection.update_many({'Guild': oldName}, {"$set": {'Guild': newName}})
            
            #update noodle
            entryStr = "%s: %s" % (oldName, noodleUsed)
            newStr = "%s: %s" % (newName, noodleUsed)
            db.users.update_one({"Guilds": entryStr}, {"$set": {"Guilds.$": newStr}})
            
            #update stats
            db.stats.update_many({}, {"$rename": {'Guilds.'+oldName: 'Guilds.'+newName}})
        except Exception as e:
            print ('MONGO ERROR: ' + str(e))
            
            await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please renaming the guild again.")
        else:
            await ctx.channel.send(f"You have successfully renamed {oldName} to {newName}!")
            
    
    @guild.command()
    @is_guild_channel()
    @commands.has_any_role('Guildmaster')
    async def pin(self,ctx):
        async with ctx.channel.typing():
            await pin_control(self, ctx, "pin")
            async for message in ctx.channel.history(after=ctx.message): #searches for and deletes any non-default messages in the channel after the command to delete.
                if message.type != ctx.message.type:
                    await message.delete()
                    break

    @guild.command()
    @is_guild_channel()
    @commands.has_any_role('Guildmaster')
    async def unpin(self,ctx):
        async with ctx.channel.typing():
            await pin_control(self, ctx, "unpin")
    
    @guild.command()
    @is_guild_channel()
    @commands.has_any_role('Guildmaster')
    async def topic(self, ctx, *, messageTopic= ""):
        await ctx.message.delete()  
        await ctx.channel.edit(topic=messageTopic)
        resultMessage = await ctx.channel.send(f"You have successfully updated the topic for your guild! This message will self-destruct in 10 seconds.")
        await asyncio.sleep(10) 
        await resultMessage.delete()
        
        
async def setup(bot):
    await bot.add_cog(Guild(bot))