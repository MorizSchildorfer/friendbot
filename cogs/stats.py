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
from cogs.char import paginate
from bfunc import alphaEmojis, commandPrefix, left,right,back, db, callAPI, checkForChar, timeConversion, traceBack, settingsRecord


class Stats(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        
    def is_log_channel():
        async def predicate(ctx):
            return ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"]
        return commands.check(predicate)
   
    def is_log_channel_or_game():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Game Rooms"])
        return commands.check(predicate) 
        
    def stats_special():
        async def predicate(ctx):
            return (ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Player Logs"] or 
                    ctx.channel.category_id == settingsRecord[str(ctx.guild.id)]["Mod Rooms"] or
                    ctx.channel.id == 564994370416410624)
        return commands.check(predicate) 
        
    
    
    async def cog_command_error(self, ctx, error):
        msg = None
        
        
        if isinstance(error, commands.UnexpectedQuoteError) or isinstance(error, commands.ExpectedClosingQuoteError) or isinstance(error, commands.InvalidEndOfQuotedStringError):

             return
        elif isinstance(error, commands.CheckFailure):
            msg = "This channel or user does not have permission for this command. "
        
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
        currentDate = datetime.now().strftime("%b-%y")
        if not year:
            year = currentDate.split("-")[1]
        if month:
            if month.isnumeric() and int(month)>0 and int(month) < 13:
                currentDate = datetime.now().replace(month = int(month)).replace(year = 2000+int(year)).strftime("%b-%y")
                
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

        def statsEmbedCheck(r, u):
            sameMessage = False
            if statsEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and ((r.emoji in alphaEmojis[:7]) or (str(r.emoji) == '❌')) and u == author
        
        def userCheck(r,u):
            sameMessage = False
            if statsEmbedmsg.id == r.message.id:
                sameMessage = True
            return sameMessage and u == ctx.author and (r.emoji == left or r.emoji == right)
        statsEmbed.description = f"Please choose a category:\n{alphaEmojis[0]}: Monthly Stats\n{alphaEmojis[1]}: Lifetime Main Stats\n{alphaEmojis[2]}: Lifetime Class Stats\n{alphaEmojis[3]}: Lifetime Race Stats\n{alphaEmojis[4]}: Lifetime Background Stats\n{alphaEmojis[5]}: Lifetime Feat Stats\n{alphaEmojis[6]}: Lifetime Magic Items Stats"
        statsEmbedmsg = await ctx.channel.send(embed=statsEmbed)
        for num in range(0,7): await statsEmbedmsg.add_reaction(alphaEmojis[num])
        try:
            
            tReaction, tUser = await self.bot.wait_for("reaction_add", check=statsEmbedCheck , timeout=60)
        except asyncio.TimeoutError:
            await statsEmbedmsg.delete()
            await channel.send(f'Stats cancelled. Try again using the same command!')
            ctx.command.reset_cooldown(ctx)
            return
        else:
            statsEmbed.description = ""
        
        contents = []
        # Lets the user choose a category to view stats
        if tReaction.emoji == alphaEmojis[0] or tReaction.emoji == alphaEmojis[1]:
        
            
            identity_strings = ["Monthly", "Month"]
            if tReaction.emoji == alphaEmojis[1]:
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
                    
                statsString += f"Unique DMs: {len(statRecords['DM'].items())}\n"


              
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
                    contents.append((f"Campaigns", f"Sessions: {statRecords['Campaigns']}", False))
                
                if "Life" in statRecords:
                    monthStart = datetime.now().replace(day = 14).replace(month = 1).replace(year = 2021)
                elif month:
                    
                    monthStart = datetime.now().replace(year=2000+int(year), month= int(month), day=1) -  timedelta(days=1)
                else:
                    monthStart = datetime.now().replace(day = 1)
                
                # Stat for average player and average play time
                if 'Players' in statRecords and 'Playtime' in statRecords:
                    avgString += f"Average Number of Players per Game: {(int(statRecords['Players']  / superTotal *100) /100.0)}\n" 
                    avgString += f"Average Game Time: {timeConversion(statRecords['Playtime'] / superTotal)}\n"
                    avgString += f"Average Games Per Day: {(int(superTotal / (max((datetime.now()-monthStart).days, 1))*100) /100.0)}\n"
                    
                    contents.append((f"Averages", avgString, False))


                # Number of games by total and by tier
                statsTotalString += f"Total One-shots for the {identity_strings[1]}: {superTotal}\n" 
                if superTotal > 0:
                    statsTotalString += f'Guild Quest % (Out of Total Quests): {round((gq_sum / superTotal)* 100,2) }%\n'                   
                for i in range (0,6):
                    if f'T{i}' not in statRecords:
                        statsTotalString += f"Tier {i} One-shots for the {identity_strings[1]}: 0\n"
                    else: 
                        statsTotalString += f"Tier {i} One-shots for the {identity_strings[1]}: {statRecords[f'T{i}']}\n"


                if 'Players' in statRecords and 'Playtime' in statRecords:
                    statsTotalString += f"Total Hours Played: {timeConversion(statRecords['Playtime'])}\n"
                    statsTotalString += f"Total Number of Players: {statRecords['Players']}\n"
                if 'Unique Players' in statRecords and 'Playtime' in statRecords:
                    statsTotalString += f"Number of Unique Players: {len(statRecords['Unique Players'])}\n"
                
                contents.insert(0, (f"{identity_strings[0]} Stats", statsTotalString, False))
                if statsString:
                    contents.append(("One-shots by DM", statsString, True))
                await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg)
                
          
        # Below are lifetime stats which consists of character data
        # Lifetime Class Stats
        elif tReaction.emoji == alphaEmojis[2]: 
            
            charString = ""
            srClass = collections.OrderedDict(sorted(statRecordsLife['Class'].items()))
            for k, v in srClass.items():
                charString += f"**{k}**: {v['Count']}\n"
                counter = 0
                for vk, vv in collections.OrderedDict(sorted(v.items())).items():
                    if vk != 'Count':
                        charString += f"• {vk}: {vv}\n"
                        counter += vv
                
                charString += f"• No Sublcass: {v['Count'] - counter}\n"
                charString += f"━━━━━\n"
            if not charString:
                charString = "No stats yet."
            contents.append(("Character Class Stats (Lifetime)", charString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "━━━━━\n")
        # Lifetime race stats
        elif tReaction.emoji == alphaEmojis[3]:
            raceString = ""
            srRace = collections.OrderedDict(sorted(statRecordsLife['Race'].items()))
            for k, v in srRace.items():
                raceString += f"{k}: {v}\n"

            if not raceString:
                raceString = "No stats yet."
            
            contents.append(("Character Race Stats (Lifetime)", raceString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")

        # Lifetime background Stats
        elif tReaction.emoji == alphaEmojis[4]:
            bgString = ""
            srBg = collections.OrderedDict(sorted(statRecordsLife['Background'].items()))

            for k, v in srBg.items():
                bgString += f"{k}: {v}\n"

            if not bgString:
                bgString = "No stats yet."
                
            contents.append(("Character Background Stats (Lifetime)", bgString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")
        # Lifetime Feats Stats
        elif tReaction.emoji == alphaEmojis[5]:
            bgString = ""
            srBg = collections.OrderedDict(sorted(statRecordsLife['Feats'].items()))

            for k, v in srBg.items():
                bgString += f"{k}: {v}\n"

            if not bgString:
                bgString = "No stats yet."
            contents.append(("Character Feats Stats (Lifetime)", bgString, False))
            await paginate(ctx, self.bot, "Stats", contents, statsEmbedmsg, "\n")
        # Lifetime Magic Items Stats
        elif tReaction.emoji == alphaEmojis[6]:
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
        currentDate = datetime.now().strftime("%b-%y")
        if not year:
            year = currentDate.split("-")[1]
        if month:
            if month.isnumeric() and int(month)>0 and int(month) < 13:
                currentDate = datetime.now().replace(month = int(month)).replace(year = 2000+int(year)).strftime("%b-%y")
                
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


def setup(bot):
    bot.add_cog(Stats(bot))
