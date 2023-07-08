import discord
import decimal
import pytz
import re
import random
import requests
import asyncio
import collections
from discord.utils import get        
from math import floor
from datetime import datetime, timezone, timedelta 
from discord.ext import commands
from cogs.util import paginate, disambiguate, timeConversion
from bfunc import alphaEmojis, timezoneVar, commandPrefix, left,right,back, db, traceBack, settingsRecord


class Stats(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        
    def stats_special():
        async def predicate(ctx):
            if ctx.channel.type == discord.ChannelType.private:
                return False
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"] or
                    ctx.channel.id == 564994370416410624 or
                    ctx.channel.id == 548991524386373633 or
                    "A d m i n" in [r.name for r in ctx.author.roles])
        return commands.check(predicate) 
        
    
    
    async def cog_command_error(self, ctx, error):
        msg = None
        
        
        if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):

             return
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        elif isinstance(error, commands.BadArgument):
            await ctx.channel.send("One of your parameters was of an incorrect type.")
            return
        if msg:
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
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @stats_special()
    async def stats(self,ctx, month = None, year = None):                
        statsCollection = db.stats
        currentDate = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%y")
        if not year:
            year = int(currentDate.split("-")[1])
        elif year.isnumeric():
            year = int(year)%100
        else:
            await ctx.channel.send(f"Year needs to be a number.")
            ctx.command.reset_cooldown(ctx)
            return
        if month:
            if month.isnumeric() and int(month)>0 and int(month) < 13:
                currentDate = datetime.now(pytz.timezone(timezoneVar)).replace(year=2000+int(year), month= int(month), day=1).strftime("%b-%y")
                
            else:
                await ctx.channel.send(f"Month needs to be a number between 1 and 12.")
                ctx.command.reset_cooldown(ctx)
                return
                    
        statRecords = statsCollection.find_one({"Date": currentDate})
        statRecordsLife = statsCollection.find_one({"Life": 1})
        guild=ctx.guild
        channel = ctx.channel

        statsEmbed = discord.Embed()
        statsEmbedmsg = None
        statsEmbed.title = f'Stats' 

        statsTotalString = ""
        guildsString = ""
        superTotal = 0
        avgString = ""
        statsString = ""
        charString = ""
        raceString = ""
        bgString = ""
        author = ctx.author

        def userCheck(r,u):
            sameMessage = False
            if statsEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and u == ctx.author and (r.emoji == left or r.emoji == right)
        statsEmbed.description = f"Please choose a category:\n{alphaEmojis[0]}: Monthly Stats\n{alphaEmojis[1]}: Lifetime Main Stats\n{alphaEmojis[2]}: Lifetime Class Stats\n{alphaEmojis[3]}: Lifetime Race Stats\n{alphaEmojis[4]}: Lifetime Background Stats\n{alphaEmojis[5]}: Lifetime Feat Stats\n{alphaEmojis[6]}: Lifetime Magic Items Stats"
        statsEmbedmsg = await ctx.channel.send(embed=statsEmbed)
        choice = await disambiguate(7, statsEmbedmsg, author)
        statsEmbed.description = ""
        if choice is None or choice == -1:
            await statsEmbedmsg.edit(embed=None, content=f'Stats cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return
        contents = []
        # Lets the user choose a category to view stats
        if choice == 0 or choice == 1:
            identity_strings = ["Monthly", "Month"]
            if choice == 1:
                identity_strings = ["Server", "Server"]
                statRecords = statRecordsLife
            if statRecords is None:
                contents.append(("Monthly Quest Stats", "There have been 0 one-shots played this month. Check back later!", False))
            else:
                # Iterate through each DM and track tiers + total
                if "DM" in statRecords:
                    
                    for k,v in statRecords['DM'].items():
                        dmMember = guild.get_member(int(k))
                        if dmMember is None:
                            statsString += f"<@!{k}>" + " - "
                            # continue
                        else:
                            statsString += dmMember.mention + " - "
                        totalGames = 0
                        for i in range (0,6):
                            if f'T{i}' not in v:
                                statsString += f"T{i}: 0 | "
                            else:
                                statsString += f"T{i}: {v[f'T{i}']} | " 
                                totalGames += v[f'T{i}']
                       
                        # Total Number of Games per DM
                        statsString += f"Total: {totalGames}\n"

              
                # Total number of Games for the month
                if "Games" in statRecords:
                    superTotal += statRecords["Games"]

                gq_sum = 0
                if "GQ Total" in statRecords:
                    gq_sum = statRecords["GQ Total"]
                
                # Games By Guild
                if "Guilds" in statRecords:
                    guildGamesString = ""
                    guild_data_0s = ["GQ", "GQM", "GQNM", "GQDM", "DM Sparkles", "Player Sparkles", "Joins"]
                    for gk, gv in statRecords["Guilds"].items():
                        for data_key in guild_data_0s:
                            if not data_key in gv:
                                gv[data_key] = 0
                        
                        guildGamesString += f"• {gk}"    
                        guildGamesString += f": {gv['GQ']}\n"
                    
                    contents.append((f"Guilds", guildGamesString, False))
                    
                if "Campaigns" in statRecords:
                    contents.append((f"Campaigns", f"• Sessions: {statRecords['Campaigns']}", False))
                
                monthEnd = datetime.now(pytz.timezone(timezoneVar))
                if "Life" in statRecords:
                    monthStart = datetime.now(pytz.timezone(timezoneVar)).replace(day = 14).replace(month = 1).replace(year = 2021)
                elif month:
                    
                    monthStart = datetime.now(pytz.timezone(timezoneVar)).replace(year=2000+int(year), month= int(month), day=1) -  timedelta(days=1)
                    monthEnd = (datetime.now(pytz.timezone(timezoneVar)).replace(year=2000+int(year), month= int(month), day=28) +  timedelta(days=4)).replace(day=1)
                else:
                    monthStart = datetime.now(pytz.timezone(timezoneVar)).replace(day = 1) -  timedelta(days=1)
                
                # Stat for average player and average play time
                if 'Players' in statRecords and 'Playtime' in statRecords:
                    avgString += f"• Players per One-shot: {(int(statRecords['Players']  / superTotal *100) /100.0)}\n" 
                    avgString += f"• One-shot Length: {timeConversion(statRecords['Playtime'] / superTotal)}\n"
                    avgString += f"• One-shots per Day: {(int(superTotal / (max((monthEnd-monthStart).days, 1))*100) /100.0)}\n"
                    
                    contents.append((f"Averages", avgString, False))


                # Number of games by total and by tier
                statsTotalString += f"• One-shots Hosted: {superTotal}\n" 
                if superTotal > 0:
                    statsTotalString += f'• Guild Quest %: {round((gq_sum / superTotal)* 100,2) }%\n'                   
                for i in range (0,6):
                    if f'T{i}' not in statRecords:
                        statsTotalString += f"• Tier {i} One-shots Hosted: 0\n"
                    else: 
                        statsTotalString += f"• Tier {i} One-shots Hosted: {statRecords[f'T{i}']}\n"


                if 'Players' in statRecords and 'Playtime' in statRecords:
                    statsTotalString += f"• Hours Played: {timeConversion(statRecords['Playtime'])}\n"
                    statsTotalString += f"• Total Players: {statRecords['Players']}\n"
                if 'Unique Players' in statRecords and 'Playtime' in statRecords:
                    statsTotalString += f"• Unique Players: {len(statRecords['Unique Players'])}\n"
                    statsTotalString += f"• Unique DMs: {len(statRecords['DM'].items())}\n"
                
                contents.insert(0, (f"{identity_strings[0]} Stats", statsTotalString, False))
                if statsString:
                    contents.append(("One-shots by DM", statsString, True))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg)
                
          
        # Below are lifetime stats which consists of character data
        # Lifetime Class Stats
        elif choice == 2: 
            
            charString = ""
            srClass = collections.OrderedDict(sorted(statRecordsLife['Class'].items()))
            for k, v in srClass.items():
                charString += f"**{k}**: {v['Count']}\n"
                counter = 0
                for vk, vv in collections.OrderedDict(sorted(v.items())).items():
                    if vk != 'Count':
                        charString += f"• {vk}: {vv}\n"
                        counter += vv

                #charString += f"• No Sublcass: {v['Count'] - counter}\n"
                charString += f"━━━━━\n"
            if not charString:
                charString = "No stats yet."
            contents.append(("Character Class Stats (Lifetime)", charString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "━━━━━\n")
        # Lifetime race stats
        elif choice == 3:
            raceString = ""
            srRace = collections.OrderedDict(sorted(statRecordsLife['Race'].items()))
            for k, v in srRace.items():
                raceString += f"{k}: {v}\n"

            if not raceString:
                raceString = "No stats yet."
            
            contents.append(("Character Race Stats (Lifetime)", raceString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")

        # Lifetime background Stats
        elif choice == 4:
            bgString = ""
            srBg = collections.OrderedDict(sorted(statRecordsLife['Background'].items()))

            for k, v in srBg.items():
                bgString += f"{k}: {v}\n"

            if not bgString:
                bgString = "No stats yet."
                
            contents.append(("Character Background Stats (Lifetime)", bgString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")
        # Lifetime Feats Stats
        elif choice == 5:
            bgString = ""
            srBg = collections.OrderedDict(sorted(statRecordsLife['Feats'].items()))

            for k, v in srBg.items():
                bgString += f"{k}: {v}\n"

            if not bgString:
                bgString = "No stats yet."
            contents.append(("Character Feats Stats (Lifetime)", bgString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")
        # Lifetime Magic Items Stats
        elif choice == 6:
            bgString = ""
            srBg = collections.OrderedDict(sorted(statRecordsLife['Magic Items'].items()))

            for k, v in srBg.items():
                bgString += f"{k}: {v}\n"
            if not bgString:
                bgString = "No stats yet."
            contents.append(("Character Magic Item Stats (Lifetime)", bgString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")
        
        
        
    @commands.command()
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @stats_special()
    async def fanatic(self,ctx, month = None, year = None):                
        statsCollection = db.stats
        currentDate = datetime.now(pytz.timezone(timezoneVar)).strftime("%b-%y")
        if not year:
            year = currentDate.split("-")[1]
        if month:
            if month.isnumeric() and int(month)>0 and int(month) < 13:
                currentDate = datetime.now(pytz.timezone(timezoneVar)).replace(year=2000+int(year), month= int(month), day=1).strftime("%b-%y")
                
            else:
                await ctx.channel.send(f"Month needs to be a number between 1 and 12.")
                ctx.command.reset_cooldown(ctx)
                return
        statRecords = statsCollection.find_one({"Date": currentDate})
        guild=ctx.guild
        channel = ctx.channel

        statsEmbed = discord.Embed()
        statsEmbedmsg = None
        statsEmbed.title = f'Fanatic Competition' 

        friendString = ""
        guildString = ""
        author = ctx.author

        
        if statRecords is None or "DM" not in statRecords:
            statsEmbed.add_field(name="Fanatic Stats", value="There have been 0 valid one-shots played this month. Check back later!", inline=False)
        else:
            friend_list = []
            guild_list = []
            
            dm_dictionary = statRecords['DM']
            # Iterate through each DM and track tiers + total
            for k,v in dm_dictionary.items():
                dmMember = guild.get_member(int(k))
                if dmMember is None:
                    continue
                if "Friend" in v:
                    friend_list.append({"Member": dmMember, "Count": v["Friend"]})
                if "Guild Fanatic" in v:
                    guild_list.append({"Member": dmMember, "Count": v["Guild Fanatic"]})
            friend_list.sort(key = lambda x: -x["Count"])
            
            guild_list.sort(key = lambda x: -x["Count"])
            
            for f in friend_list:
                friendString += f"{f['Member'].mention}: {f['Count']} Points\n"
            for g in guild_list:
                guildString += f"{g['Member'].mention}: {g['Count']} Points\n"
            if friendString:
                statsEmbed.add_field(name=f"Friend Fanatic", value=friendString, inline=True) 
            if guildString: 
                statsEmbed.add_field(name=f"Guild Fanatic", value=guildString, inline=True)  
                
        await ctx.channel.send(embed=statsEmbed)
        
    
    async def rank_shell(self, ctx, name, query, limit):
        if limit < 1:
            await ctx.channel.send(f"{limit} is not a valid count")
            return
        player_collection = db.players
        top_results = player_collection.find(query)
        guild=ctx.guild
        channel = ctx.channel
        contents = []
        number = limit+1
        statsEmbedmsg = None
        for result in top_results:
            owner = guild.get_member(int(result["User ID"]))
            if not owner:
                continue
            char_string = f"{result[name]}      (<@!{result['User ID']}>)"
            contents.append((f'{number-limit}.) {result["Name"]}', char_string, False))
            
            limit -= 1
            if limit <= 0:
                break
        await paginate(ctx, self.bot, f"Top {number-1} Characters ({name})", contents, statsEmbedmsg)

    @commands.command()
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @stats_special()
    async def playtime(self,ctx, limit = 10):
        q = { "$query": {"Playtime": {"$exists": True}, "Test" : {"$exists" : False}}, 
               "$orderby": { "Playtime": -1}}
        await self.rank_shell(ctx, "Playtime", q, limit)
    @commands.command()
    @commands.cooldown(1, 5, type=commands.BucketType.member)
    @stats_special()
    async def top(self,ctx, limit = 10):
        q = { "$query": {"Test" : {"$exists" : False}}, 
              "$orderby": { "Level": -1, "CP" : -1 }}
        await self.rank_shell(ctx, "CP", q, limit)

async def setup(bot):
    await bot.add_cog(Stats(bot))
