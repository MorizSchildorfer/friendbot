import discord
import asyncio
import pytz
from discord.utils import get        
from discord.ext import commands
from bfunc import  timezoneVar, commandPrefix, db, traceBack, alphaEmojis, settingsRecord
from datetime import datetime, timezone,timedelta
from cogs.util import checkForChar, checkForGuild, paginate, noodle_roles

async def pin_control(self, ctx, goal):
    author = ctx.author
    channel = ctx.channel
    infoMessage = await channel.send(f"You have 60 seconds to react to the message you want to {ctx.invoked_with} with the 📌 emoji (`:pushpin:`)!")
    def pinnedEmbedCheck(event):
        return str(event.emoji) == '📌' and event.user_id == author.id
    try:
        event = await self.bot.wait_for("raw_reaction_add", check=pinnedEmbedCheck , timeout=60)
    except asyncio.TimeoutError:
        await infoMessage.edit(content=f'The `{ctx.invoked_with}` command has timed out! Try again.')
        return
    message = await channel.fetch_message(event.message_id)
    await (getattr(message, goal))()
    await ctx.message.delete()
    await infoMessage.edit(content = f"You have successfully {ctx.invoked_with}ned the message! This message will self-destruct in 10 seconds.")            
    await asyncio.sleep(10) 
    await infoMessage.delete()

class Guild(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.creation_cost = 0
       
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
    async def create(self,ctx, charName, guildName, roleName="", channelName=""):
        channel = ctx.channel
        author = ctx.author
        guildEmbed = discord.Embed()
        guildCog = self.bot.get_cog('Guild')

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
            if r.name in noodleRoleArray and r.name not in ['Newdle', 'Good Noodle']:
                noodleRole = r

        if noodleRole:
            usersCollection = db.users
            userRecords = usersCollection.find_one({"User ID": str(author.id)})
            if userRecords: 
                charDict, guildEmbedmsg = await checkForChar(ctx, charName, guildEmbed)
                if charDict:

                    # GP needed to fund guild.
                    gpNeeded = 0

                    if charDict['Level'] < 5:
                        gpNeeded = 200
                    elif charDict['Level'] < 11:
                        gpNeeded = 400
                    elif charDict['Level'] < 17:
                        gpNeeded = 600
                    elif charDict['Level'] < 21:
                        gpNeeded = 800

                    if gpNeeded > charDict['GP']:
                        await channel.send(f"***{charDict['Name']}*** does not have at least {gpNeeded} GP in order to fund ***{guildName}***.")
                        return

                    charDict['GP'] -= float(gpNeeded)

                    noodleRep = ["Elite Noodle (0)", "True Noodle (10)", "Ascended Noodle (20)", "Immortal Noodle (30)", "Eternal Noodle (40)", "Infinity Noodle (50)", "Beyond Noodle (60)"]
                    charID = charDict['_id']
                    if 'Guilds' not in userRecords: 
                        userRecords['Guilds'] = []

                    if 'Guild' in charDict:
                        await channel.send(f"***{charDict['Name']}*** is already a part of ***{charDict['Guild']}*** and won't be able to create another guild.")
                        return

                    # Available Noodle Roles.
                    #for i in range (noodleRoleArray.index(noodleRole.name) + 2, len(noodleRoleArray)):
                    #    del noodleRep[-1]

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

                    def guildNoodleEmbedcheck(r, u):
                        sameMessage = False
                        if guildEmbedmsg.id == r.message.id:
                            sameMessage = True
                        return (r.emoji in alphaEmojis[:len(noodleRep)] or (str(r.emoji) == '❌')) and u == author and sameMessage


                    guildEmbed.add_field(name=f"Choose the Noodle role which you would like to use to create this guild. This will affect the amount of reputation which the guild starts with.", value=noodleRepStr, inline=False)
                    if guildEmbedmsg:
                        await guildEmbedmsg.edit(embed=guildEmbed)
                    else: 
                        guildEmbedmsg = await channel.send(embed=guildEmbed)

                    await guildEmbedmsg.add_reaction('❌')

                    try:
                        tReaction, tUser = await self.bot.wait_for("reaction_add", check=guildNoodleEmbedcheck, timeout=60)
                    except asyncio.TimeoutError:
                        await guildEmbedmsg.delete()
                        await channel.send('Guild command timed out! Try using the command again.')
                        ctx.command.reset_cooldown(ctx)
                        return
                    else:
                        if tReaction.emoji == '❌':
                            await guildEmbedmsg.edit(embed=None, content=f"Guild command cancelled. Please use the command and try again!")
                            await guildEmbedmsg.clear_reactions()
                            ctx.command.reset_cooldown(ctx)
                            return
                    guildName = guildRole[0].name
                    guildEmbed.clear_fields()
                    await guildEmbedmsg.clear_reactions()
                    baseRep = int(noodleRep[alphaEmojis.index(tReaction.emoji[0])].split(' (')[1].replace(')',""))
                    noodleRepUsed = noodleRep[alphaEmojis.index(tReaction.emoji[0])]
                    userRecords['Guilds'].append(f"{guildName}: {noodleRepUsed}")

                    # Quick check to see if guild already exists
                    guildsCollection = db.guilds
                    guildExists = guildsCollection.find_one({"Name": {"$regex": guildName, '$options': 'i' }})


                    if guildExists:
                        await channel.send(f"There is already a guild by the name of ***{guildName}***. Please try creating a guild with a different name.")
                        return

                    guildsDict = {'Role ID': str(guildRole[0].id), 'Channel ID': str(guildChannel[0].id), 'Name': guildName, 'Funds': gpNeeded, 'Guildmaster': charDict['Name'], 'Guildmaster ID': str(author.id), 'Reputation': baseRep, 'Total Reputation': baseRep, 'Noodle Used': noodleRepUsed}
                    await author.add_roles(guildRole[0], reason=f"Created guild {guildName}")

                    try:
                        playersCollection = db.players
                        playersCollection.update_one({'_id': charID}, {"$set": {"Guild": guildName, 'Guild Rank': 1, 'GP':charDict['GP']}})
                        usersCollection.update_one({"User ID": str(author.id)}, {"$set": {"Guilds": userRecords['Guilds']}})
                        guildsCollection.insert_one(guildsDict)
                    except Exception as e:
                        print ('MONGO ERROR: ' + str(e))
                        guildEmbedmsg = await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try creating your guild again.")


                        guildEmbed.title = f"Guild Creation: {guildName}"
                        guildEmbed.description = f"***{charDict['Name']}*** has created ***{guildName}***!\n\nThe guild's status can be checked using the following command:\n```yaml\n{commandPrefix}guild info #guild-channel```"
                        if guildEmbedmsg:
                            await guildEmbedmsg.clear_reactions()
                            await guildEmbedmsg.edit(embed=guildEmbed)
                        else: 
                            guildEmbedmsg = await channel.send(embed=guildEmbed)
                          
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
        author = ctx.author
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
            if month.isnumeric() and int(month)>0 and int(month) < 13:
                currentDate = datetime.now(pytz.timezone(timezoneVar)).replace(month = int(month)).replace(year = 2000+int(year)).strftime("%b-%y")
                
            else:
                await ctx.channel.send(f"Month needs to be a number between 1 and 12.")
                ctx.command.reset_cooldown(ctx)
                return
        if guildChannel == list():
            guildChannel = ctx.channel
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

    #@commands.cooldown(1, 5, type=commands.BucketType.member)
    #@is_log_channel()
    #@guild.command()
    async def fund(self,ctx, charName, guildName, gpFund = 0): 
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        guildEmbed = discord.Embed()
        guildEmbedEmbedmsg = None
        def guildEmbedCheck(r, u):
            sameMessage = False
            if guildEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        charRecords, guildEmbedmsg = await checkForChar(ctx, charName, guildEmbed)

        if charRecords:
            guildChannel = ctx.message.channel_mentions
            if guildChannel == list():
                await ctx.channel.send(f"You are missing the guild channel.")
                return 
            guildChannel = guildChannel[0]

            guildRecords = db.guilds.find_one({"Channel ID": str(guildChannel.id)})
            if guildRecords:
                if guildRecords['Funds'] >= self.creation_cost:
                    await channel.send(f"***{guildRecords['Name']}*** is not expecting any funds. This guild has already been opened.")
                    return

                if 'Guild' in charRecords:
                    if charRecords['Guild'] != guildRecords['Name']:
                        await channel.send(f"***{charRecords['Name']}*** cannot fund ***{guildRecords['Name']}*** because they belong to ***{charRecords['Guild']}***.")
                        return

                gpNeeded = 0
                refundGP = 0

                if charRecords['Level'] < 5:
                    gpNeeded = 200
                    if gpFund == 0:
                        gpFund = 200  
                elif charRecords['Level'] < 11:
                    gpNeeded = 400
                    if gpFund == 0:
                        gpFund = 400
                elif charRecords['Level'] < 17:
                    gpNeeded = 600
                    if gpFund == 0:
                        gpFund = 600
                elif charRecords['Level'] < 21:
                    gpNeeded = 800
                    if gpFund == 0:
                        gpFund = 800

                if (float(gpFund)) > charRecords['GP']:
                    await channel.send(f"***{charRecords['Name']}*** currently has {charRecords['GP']} GP and does not have {gpFund} GP in order to fund ***{guildRecords['Name']}***.")
                    return
                     
                if gpNeeded > charRecords['GP']:
                    await channel.send(f"***{charRecords['Name']}*** does not have at least {gpNeeded} GP in order to fund ***{guildRecords['Name']}***.")
                    return

                if gpNeeded > float(gpFund):
                    await channel.send(f"***{charRecords['Name']}*** needs to donate at least {gpNeeded} GP in order to fund ***{guildRecords['Name']}***.")
                    return

                        
                oldFundGP = guildRecords['Funds']
                guildRecords['Funds'] += float(gpFund) 

                if  (guildRecords['Funds'] > self.creation_cost)  and (oldFundGP < self.creation_cost) and gpNeeded < gpFund:
                    refundGP = guildRecords['Funds'] - max(self.creation_cost, gpNeeded+oldFundGP)

                newGP = (charRecords['GP'] - float(gpFund)) + refundGP

                maxGP = guildRecords['Funds']
                
                if maxGP > self.creation_cost:
                    maxGP = self.creation_cost

                guildEmbed.title = f"Fund Guild: {guildRecords['Name']}"
                guildEmbed.description = f"Are you sure you want to fund ***{guildRecords['Name']}***?\n:warning: ***{charRecords['Name']}* will automatically join *{guildRecords['Name']}* after funding the guild.**\n\n**Current Guild Funds**: {oldFundGP} GP / {self.creation_cost} GP → {maxGP} GP / {self.creation_cost} GP \n\nCurrent GP: {charRecords['GP']} GP\nNew GP: {newGP} GP\n\n✅: Yes\n\n❌: Cancel"


                if guildEmbedmsg:
                    await guildEmbedmsg.edit(embed=guildEmbed)
                else:
                    guildEmbedmsg = await channel.send(embed=guildEmbed)
                await guildEmbedmsg.add_reaction('✅')
                await guildEmbedmsg.add_reaction('❌')
                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=guildEmbedCheck , timeout=60)
                except asyncio.TimeoutError:
                    await guildEmbedmsg.delete()
                    await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild join```')
                    return
                else:
                    await guildEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await guildEmbedmsg.edit(embed=None, content=f"Shop cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild fund \"character name\" #guild-channel GP```")
                        await guildEmbedmsg.clear_reactions()
                        return

                await author.add_roles(guild.get_role(int(guildRecords['Role ID'])), reason=f"Funded guild {guildRecords['Name']}")


                try:
                    playersCollection = db.players
                    guildsCollection = db.guilds
                    playersCollection.update_one({'_id': charRecords['_id']}, {"$set": {'Guild': guildRecords['Name'], 'GP':newGP, 'Guild Rank': 1}})
                    if oldFundGP < self.creation_cost:
                        guildsCollection.update_one({'Name': guildRecords['Name']}, {"$set": {'Funds':guildRecords['Funds']}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try guild join again.")
                else:
                    guildEmbed.title = f"Fund Guild: {guildRecords['Name']}"
                    guildEmbed.description = f"***{charRecords['Name']}*** has joined ***{guildRecords['Name']}*** for {gpNeeded} GP.\n\n**Previous GP**: {charRecords['GP']} GP\n**Current GP**: {newGP} GP\n"


                    if guildRecords['Funds'] < self.creation_cost:
                        guildEmbed.description = f"***{charRecords['Name']}*** has funded ***{guildRecords['Name']}*** with {gpFund} GP.\nIf this amount puts the guild's funds over {self.creation_cost} GP, the leftover is given back to the character.\n\n**Current Guild Funds**: {maxGP} GP / {self.creation_cost} GP\n\n**Previous GP**: {charRecords['GP']} GP\n**Current GP**: {newGP} GP\n"
                    elif guildRecords['Funds'] >= self.creation_cost and oldFundGP < self.creation_cost:
                        guildEmbed.description = f"***{charRecords['Name']}*** has funded ***{guildRecords['Name']}*** with {gpFund} GP.\n\n**Previous GP**: {charRecords['GP']} GP\n**Current GP**: {newGP} GP\n\n"
                        guildEmbed.description += f"Congratulations! ***{guildRecords['Name']}***  is officially open! :tada:"
                        await guildEmbedmsg.add_reaction('🎉')
                        await guildEmbedmsg.add_reaction('🎊')
                        await guildEmbedmsg.add_reaction('🥳')
                        await guildEmbedmsg.add_reaction('🍾')
                        await guildEmbedmsg.add_reaction('🥂')
                        if refundGP:
                            guildEmbed.description += f"\n\n Because you funded the guild over {self.creation_cost} GP, you have been refunded {abs(refundGP)} GP."

                    else:
                        guildEmbed.description = f"***{charRecords['Name']}*** has joined ***{guildRecords['Name']}***.\n\n**Previous GP**: {charRecords['GP']} GP\n**Current GP**: {newGP} GP"

                    if guildEmbedmsg:
                        await guildEmbedmsg.edit(embed=guildEmbed)
                    else:
                        guildEmbedmsg = await channel.send(embed=guildEmbed)

            else:
                await channel.send(f'The guild ***{guildName}*** does not exist. Please try again.')
                return

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def join(self,ctx, charName, guildName): 
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        guildEmbed = discord.Embed()
        guildEmbedEmbedmsg = None

        def guildEmbedCheck(r, u):
            sameMessage = False
            if guildEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        charRecords, guildEmbedmsg = await checkForChar(ctx, charName, guildEmbed)

        if charRecords:
            if 'Guild' in charRecords:
                await channel.send(f"***{charRecords['Name']}*** cannot join any guilds because they belong to the guild ***{charRecords['Guild']}***.")
                return

            guildChannel = ctx.message.channel_mentions
            if guildChannel == list():
                await ctx.channel.send(f"You are missing the guild channel.")
                return 
            guildChannel = guildChannel[0]

            guildRecords = db.guilds.find_one({"Channel ID": str(guildChannel.id)})
            
            if guildRecords:
                if guildRecords['Funds'] < self.creation_cost:
                    await channel.send(f'***{guildRecords["Name"]}*** is not open and requires funding. If you would like to fund and join the guild, use the following command:\n```yaml\n{commandPrefix}guild fund "character name" #guild-channel GP```')
                    return

                gpNeeded = 0

                if charRecords['Level'] < 5:
                    gpNeeded = 200
                elif charRecords['Level'] < 11:
                    gpNeeded = 400
                elif charRecords['Level'] < 17:
                    gpNeeded = 600
                elif charRecords['Level'] < 21:
                    gpNeeded = 800
                drive = False
                if "Drive" in charRecords and guildRecords['Name'] == charRecords["Drive"]:
                    gpNeeded /= 2
                    drive = True

                if gpNeeded > charRecords['GP']:
                    await channel.send(f"***{charRecords['Name']}*** does not have the minimum {gpNeeded} GP to join ***{guildRecords['Name']}***.")
                    return

                newGP = (charRecords['GP'] - float(gpNeeded)) 
                        
                guildEmbed.title = f"Joining Guild: {guildRecords['Name']}"
                guildEmbed.description = f"Are you sure you want to join ***{guildRecords['Name']}*** for {gpNeeded} GP{' (Discounted)' * drive}? \n\nCurrent GP: {charRecords['GP']} GP\nNew GP: {newGP} GP\n\n✅: Yes\n\n❌: Cancel"

                if guildEmbedmsg:
                    await guildEmbedmsg.edit(embed=guildEmbed)
                else:
                    guildEmbedmsg = await channel.send(embed=guildEmbed)
                await guildEmbedmsg.add_reaction('✅')
                await guildEmbedmsg.add_reaction('❌') 

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=guildEmbedCheck , timeout=60)
                except asyncio.TimeoutError:
                    await guildEmbedmsg.delete()
                    await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild join "character name" #guild-channel```')
                    return
                else:
                    await guildEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await guildEmbedmsg.edit(embed=None, content=f"Guild join cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild join \"character name\" #guild-channel```")
                        await guildEmbedmsg.clear_reactions()
                        return

                await author.add_roles(guild.get_role(int(guildRecords['Role ID'])), reason=f"Joined guild {guildName}")

                try:
                    currentDate = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%y")
                    # update all the other data entries
                    # update the DB stats
                    db.stats.update_one({'Date': currentDate}, {"$inc": {"Guilds."+guildRecords['Name']+".Joins": 1}}, upsert=True)
                    db.stats.update_one({'Life': 1}, {"$inc": {"Guilds."+guildRecords['Name']+".Joins": 1}}, upsert=True)
            
                    playersCollection = db.players
                    playersCollection.update_one({'_id': charRecords['_id']}, {"$set": {'Guild': guildRecords['Name'], 'GP':newGP, 'Guild Rank': 1}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    guildEmbed.description = f"***{charRecords['Name']}*** has joined ***{guildRecords['Name']}*** for {gpNeeded} GP!\n\n**Previous GP**: {charRecords['GP']} GP\n**Current GP**: {newGP} GP\n"
                    if guildEmbedmsg:
                        await guildEmbedmsg.edit(embed=guildEmbed)
                    else:
                        guildEmbedmsg = await channel.send(embed=guildEmbed)
                
            else:
                await channel.send(f'The guild ***{guildName}*** does not exist. Please try again.')
                return

    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def rankup(self,ctx, charName):
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        guildEmbed = discord.Embed()
        guildEmbedEmbedmsg = None

        def guildEmbedCheck(r, u):
            sameMessage = False
            if guildEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        charRecords, guildEmbedmsg = await checkForChar(ctx, charName, guildEmbed)

        if charRecords:
            if 'Guild' not in charRecords:
                await channel.send(f"***{charRecords['Name']}*** cannot upgrade their guild rank because they currently do not belong to a guild.")
                return

            guildRecords, guildEmbedmsg = await checkForGuild(ctx,charRecords['Guild'],guildEmbed) 
            
            if guildRecords:

                if guildRecords['Funds'] < self.creation_cost: 
                    await channel.send(f"***{charRecords['Name']}*** cannot upgrade their guild rank because ***{charRecords['Guild']}*** is not officially open and still needs funding.")
                    return

                if charRecords['Guild Rank'] > 3:
                    await channel.send(f"***{charRecords['Name']}*** is already at the max rank and cannot increase their rank any further.")
                    return

                rankCosts = [1000, 3000, 3000]
                gpNeeded = rankCosts[charRecords['Guild Rank']-1]
                if gpNeeded > charRecords['GP']:
                    await channel.send(f"***{charRecords['Name']}*** does not have {gpNeeded} GP in order to upgrade their guild rank.")
                    return

                guildEmbed.title = f"Ranking Up - Guild: {guildRecords['Name']}"
                guildEmbed.description = f"Are you sure you want to upgrade your rank to **{charRecords['Guild Rank'] + 1}** for {gpNeeded} GP?\n\n**Current GP**: {charRecords['GP']} GP\n**Cost**: {gpNeeded} GP\n**New GP**: {charRecords['GP'] - gpNeeded} GP\n\n✅: Yes\n\n❌: Cancel"

                if guildEmbedmsg:
                    await guildEmbedmsg.edit(embed=guildEmbed)
                else:
                    guildEmbedmsg = await channel.send(embed=guildEmbed)
                await guildEmbedmsg.add_reaction('✅')
                await guildEmbedmsg.add_reaction('❌') 

                try:
                    tReaction, tUser = await self.bot.wait_for("reaction_add", check=guildEmbedCheck , timeout=60)
                except asyncio.TimeoutError:
                    await guildEmbedmsg.delete()
                    await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild rankup```')
                    return
                else:
                    await guildEmbedmsg.clear_reactions()
                    if tReaction.emoji == '❌':
                        await guildEmbedmsg.edit(embed=None, content=f"Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild rankup```")
                        await guildEmbedmsg.clear_reactions()
                        return

                newGP = (charRecords['GP'] - float(gpNeeded)) 
                try:
                    playersCollection = db.players
                    playersCollection.update_one({'_id': charRecords['_id']}, {"$set": {'GP':newGP, 'Guild Rank': charRecords['Guild Rank'] + 1}})
                except Exception as e:
                    print ('MONGO ERROR: ' + str(e))
                    await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
                else:
                    guildEmbed.description = f"***{charRecords['Name']}*** has ranked up using {gpNeeded} GP! Rank **{charRecords['Guild Rank']}** → **{charRecords['Guild Rank'] + 1}**\n\n**Previous GP**: {charRecords['GP']} GP\n**Cost**: {gpNeeded} GP\n**New GP**: {newGP} GP\n"
                    if guildEmbedmsg:
                        await guildEmbedmsg.edit(embed=guildEmbed)
                    else:
                        guildEmbedmsg = await channel.send(embed=guildEmbed)
                
            else:
                await channel.send(f'The guild ***{charRecords["Guild"]}*** does not exist. Please try again.')
                return


    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @is_log_channel()
    @guild.command()
    async def leave(self,ctx, charName): 
        channel = ctx.channel
        author = ctx.author
        guild = ctx.guild
        guildEmbed = discord.Embed()
        guildEmbedEmbedmsg = None

        def guildEmbedCheck(r, u):
            sameMessage = False
            if guildEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((str(r.emoji) == '✅') or (str(r.emoji) == '❌')) and u == author

        charRecords, guildEmbedmsg = await checkForChar(ctx, charName, guildEmbed)

        if charRecords:
            if 'Guild' not in charRecords:
                await channel.send(f"***{charRecords['Name']}*** cannot leave a guild because they currently do not belong to any guild.")
                return

            guildEmbed.title = f"Leaving Guild: {charRecords['Guild']}"
            guildEmbed.description = f"Are you sure you want to leave ***{charRecords['Guild']}***?\n\n✅: Yes\n\n❌: Cancel"

            if guildEmbedmsg:
                await guildEmbedmsg.edit(embed=guildEmbed)
            else:
                guildEmbedmsg = await channel.send(embed=guildEmbed)
            await guildEmbedmsg.add_reaction('✅')
            await guildEmbedmsg.add_reaction('❌') 

            try:
                tReaction, tUser = await self.bot.wait_for("reaction_add", check=guildEmbedCheck , timeout=60)
            except asyncio.TimeoutError:
                await guildEmbedmsg.delete()
                await channel.send(f'Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild leave```')
                return
            else:
                await guildEmbedmsg.clear_reactions()
                if tReaction.emoji == '❌':
                    await guildEmbedmsg.edit(embed=None, content=f"Guild cancelled. Try again using the following command:\n```yaml\n{commandPrefix}guild leave```")
                    await guildEmbedmsg.clear_reactions()
                    return

            playersCollection = db.players
            guildAmount = list(playersCollection.find({"User ID": str(author.id), "Guild": {"$regex": charRecords['Guild'], '$options': 'i' }}))
            # If there is only one of user's character in the guild remove the role.
            if (len(guildAmount) <= 1):
                await author.remove_roles(get(guild.roles, name = charRecords['Guild']), reason=f"Left guild {charRecords['Guild']}")

            try:
                playersCollection.update_one({'_id': charRecords['_id']}, {"$unset": {'Guild': 1, 'Guild Rank':1}})
            except Exception as e:
                print ('MONGO ERROR: ' + str(e))
                await channel.send(embed=None, content="Uh oh, looks like something went wrong. Please try shop buy again.")
            else:
                guildEmbed.description = f"***{charRecords['Name']}*** has left ***{charRecords['Guild']}***."
                if guildEmbedmsg:
                    await guildEmbedmsg.edit(embed=guildEmbed)
                else:
                    guildEmbedmsg = await channel.send(embed=guildEmbed)

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
        channel = ctx.channel
        await ctx.message.delete()  
        await ctx.channel.edit(topic=messageTopic)
        resultMessage = await ctx.channel.send(f"You have successfully updated the topic for your guild! This message will self-destruct in 10 seconds.")
        await asyncio.sleep(10) 
        await resultMessage.delete()
        
        
async def setup(bot):
    await bot.add_cog(Guild(bot))